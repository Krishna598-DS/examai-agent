# app/tools/cache.py
import json
import hashlib
from typing import Optional
from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)


class RedisCache:
    """
    Async Redis cache for orchestrator results.

    Why Redis over in-memory dict:
    - Persists across server restarts
    - Shared across multiple server instances
    - Native TTL management
    - Can inspect/debug cache contents with redis-cli
    - Industry standard — used at every MAANG company

    Falls back gracefully if Redis is unavailable —
    the system works without caching, just slower.
    """

    def __init__(self):
        self._client = None
        self._available = False

    async def connect(self) -> bool:
        """
        Connect to Redis. Called once at server startup.
        Returns True if connection succeeded, False if Redis unavailable.
        """
        try:
            import redis.asyncio as redis
            self._client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2,  # fail fast if Redis is down
                socket_timeout=2,
            )
            # Test the connection
            await self._client.ping()
            self._available = True
            logger.info("redis_connected", url=settings.redis_url)
            return True

        except Exception as e:
            self._available = False
            logger.warning(
                "redis_unavailable",
                error=str(e),
                fallback="using in-memory cache"
            )
            return False

    async def disconnect(self):
        """Close Redis connection on server shutdown."""
        if self._client:
            await self._client.aclose()
            logger.info("redis_disconnected")

    def _make_key(self, question: str) -> str:
        """
        Generate cache key from question.
        Normalize before hashing so minor variations hit the same cache entry.
        Prefix with 'examai:' to namespace our keys in Redis.
        Why namespace? Redis is often shared between multiple applications.
        Prefixing prevents key collisions.
        """
        normalized = question.lower().strip()
        hash_val = hashlib.md5(normalized.encode()).hexdigest()
        return f"examai:answer:{hash_val}"

    async def get(self, question: str) -> Optional[dict]:
        """
        Retrieve cached answer for a question.
        Returns None if not found, Redis unavailable, or expired.
        """
        if not self._available or not self._client:
            return None

        try:
            key = self._make_key(question)
            value = await self._client.get(key)

            if value is None:
                logger.info("cache_miss", question=question[:50])
                return None

            result = json.loads(value)
            logger.info("cache_hit", question=question[:50])
            return result

        except Exception as e:
            logger.warning("cache_get_failed", error=str(e))
            return None

    async def set(self, question: str, result: dict) -> bool:
        """
        Cache an answer with TTL.
        Only caches high-confidence results.
        Returns True if cached successfully.
        """
        if not self._available or not self._client:
            return False

        # Don't cache low confidence or error results
        confidence = result.get("confidence_score", 0)
        verdict = result.get("verdict", "ERROR")

        if confidence < 0.5 or verdict == "ERROR":
            logger.info(
                "cache_skip",
                reason="low_confidence_or_error",
                confidence=confidence,
                verdict=verdict
            )
            return False

        try:
            key = self._make_key(question)
            value = json.dumps(result)

            # EX sets TTL in seconds
            # After TTL expires, Redis automatically deletes the key
            await self._client.set(key, value, ex=settings.cache_ttl_seconds)

            logger.info(
                "cache_set",
                question=question[:50],
                ttl_seconds=settings.cache_ttl_seconds
            )
            return True

        except Exception as e:
            logger.warning("cache_set_failed", error=str(e))
            return False

    async def delete(self, question: str) -> bool:
        """Delete a specific cached answer."""
        if not self._available or not self._client:
            return False

        try:
            key = self._make_key(question)
            await self._client.delete(key)
            return True
        except Exception as e:
            logger.warning("cache_delete_failed", error=str(e))
            return False

    async def clear_all(self) -> int:
        """
        Clear all ExamAI cache entries.
        Uses SCAN instead of KEYS for production safety.
        Why? KEYS blocks Redis while scanning — dangerous on large datasets.
        SCAN iterates incrementally without blocking.
        """
        if not self._available or not self._client:
            return 0

        try:
            deleted = 0
            async for key in self._client.scan_iter("examai:answer:*"):
                await self._client.delete(key)
                deleted += 1

            logger.info("cache_cleared", deleted=deleted)
            return deleted
        except Exception as e:
            logger.warning("cache_clear_failed", error=str(e))
            return 0

    async def get_stats(self) -> dict:
        """Return cache statistics."""
        if not self._available or not self._client:
            return {"available": False, "reason": "Redis not connected"}

        try:
            # Count our keys
            count = 0
            async for _ in self._client.scan_iter("examai:answer:*"):
                count += 1

            info = await self._client.info("memory")

            return {
                "available": True,
                "cached_answers": count,
                "redis_url": settings.redis_url,
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "ttl_seconds": settings.cache_ttl_seconds,
            }
        except Exception as e:
            return {"available": False, "error": str(e)}


# Singleton
redis_cache = RedisCache()
