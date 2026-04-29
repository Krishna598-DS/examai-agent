# app/orchestrator/graph.py
import asyncio
import time
from typing import Optional
from app.agents.search_agent import search_agent
from app.agents.pdf_agent import pdf_agent
from app.agents.verifier_agent import verifier_agent
from app.tools.cache import redis_cache
from app.config import settings
from app.logger import get_logger
from app.exceptions import AgentError

logger = get_logger(__name__)


class ExamAIOrchestrator:
    """
    Central coordinator for the multi-agent system.

    Caching strategy:
    - Primary: Redis (shared, persistent, TTL-managed)
    - Fallback: in-memory dict (if Redis unavailable)
    Both are checked/written transparently.
    """

    def __init__(self):
        # Fallback in-memory cache when Redis is unavailable
        self._memory_cache: dict = {}
        self._memory_timestamps: dict = {}
        logger.info("orchestrator_initialized")

    def _get_from_memory(self, question: str) -> Optional[dict]:
        """Check in-memory fallback cache."""
        import hashlib
        key = hashlib.md5(question.lower().strip().encode()).hexdigest()

        if key not in self._memory_cache:
            return None

        age = time.time() - self._memory_timestamps.get(key, 0)
        if age > settings.cache_ttl_seconds:
            del self._memory_cache[key]
            del self._memory_timestamps[key]
            return None

        return self._memory_cache[key]

    def _store_in_memory(self, question: str, result: dict):
        """Store in in-memory fallback cache."""
        import hashlib
        if result.get("confidence_score", 0) < 0.5:
            return
        key = hashlib.md5(question.lower().strip().encode()).hexdigest()
        self._memory_cache[key] = result
        self._memory_timestamps[key] = time.time()

    async def _run_search_agent(self, question: str) -> dict:
        """Run search agent with error isolation."""
        try:
            result = await search_agent.run(question)
            logger.info("search_agent_success",
                       duration=result.get("duration_seconds"))
            return result
        except Exception as e:
            logger.error("search_agent_failed", error=str(e))
            return {
                "answer": f"Web search unavailable: {str(e)}",
                "agent": "search",
                "failed": True,
                "duration_seconds": 0,
                "question": question,
            }

    async def _run_pdf_agent(self, question: str) -> dict:
        """Run PDF agent with error isolation."""
        try:
            result = await pdf_agent.run(question)
            logger.info("pdf_agent_success",
                       chunks=result.get("chunks_retrieved"),
                       similarity=result.get("top_similarity"))
            return result
        except Exception as e:
            logger.error("pdf_agent_failed", error=str(e))
            return {
                "answer": f"PDF search unavailable: {str(e)}",
                "agent": "pdf",
                "failed": True,
                "top_similarity": 0.0,
                "chunks_retrieved": 0,
                "sources": [],
                "duration_seconds": 0,
                "question": question,
            }

    async def run(self, question: str) -> dict:
        """
        Main orchestration entry point.
        1. Redis cache check
        2. Memory cache fallback
        3. Run agents concurrently
        4. Verify + self-correct
        5. Cache result
        """
        pipeline_start = time.time()
        logger.info("orchestrator_run_started", question=question[:100])

        # Step 1: Check Redis cache
        cached = await redis_cache.get(question)
        if cached:
            cached["from_cache"] = True
            cached["cache_backend"] = "redis"
            cached["cache_latency_ms"] = round(
                (time.time() - pipeline_start) * 1000, 2
            )
            return cached

        # Step 2: Check memory fallback cache
        cached = self._get_from_memory(question)
        if cached:
            cached["from_cache"] = True
            cached["cache_backend"] = "memory"
            cached["cache_latency_ms"] = round(
                (time.time() - pipeline_start) * 1000, 2
            )
            return cached

        # Step 3: Run agents concurrently
        agent_start = time.time()
        search_result, pdf_result = await asyncio.gather(
            self._run_search_agent(question),
            self._run_pdf_agent(question),
        )
        agent_duration = round(time.time() - agent_start, 2)

        search_failed = search_result.get("failed", False)
        pdf_failed = pdf_result.get("failed", False)

        logger.info(
            "agents_completed",
            agent_duration=agent_duration,
            search_failed=search_failed,
            pdf_failed=pdf_failed,
        )

        # Step 4: Handle complete failure
        if search_failed and pdf_failed:
            return {
                "question": question,
                "verdict": "ERROR",
                "confidence_score": 0.0,
                "final_answer": "Both agents failed. Please try again.",
                "reasoning": "All agents unavailable",
                "sources_agree": False,
                "from_cache": False,
                "agents_used": [],
                "pipeline_duration_seconds": round(
                    time.time() - pipeline_start, 2
                ),
            }

        # Step 5: Verify
        verified = await verifier_agent.verify(
            question=question,
            search_result=search_result,
            pdf_result=pdf_result,
        )

        # Step 6: Self-correct if needed
        final = await verifier_agent.self_correct(
            question=question,
            initial_result=verified,
            retry_search_func=lambda q: self._run_search_agent(q),
        )

        # Step 7: Build metadata
        pipeline_duration = round(time.time() - pipeline_start, 2)
        agents_used = []
        if not search_failed:
            agents_used.append("search")
        if not pdf_failed:
            agents_used.append("pdf")
        agents_used.append("verifier")

        final.update({
            "from_cache": False,
            "cache_backend": None,
            "agents_used": agents_used,
            "agent_duration_seconds": agent_duration,
            "pipeline_duration_seconds": pipeline_duration,
            "search_failed": search_failed,
            "pdf_failed": pdf_failed,
        })

        # Step 8: Store in both caches
        await redis_cache.set(question, final)
        self._store_in_memory(question, final)

        logger.info(
            "orchestrator_run_completed",
            verdict=final.get("verdict"),
            confidence=final.get("confidence_score"),
            pipeline_duration=pipeline_duration,
        )

        return final

    def get_stats(self) -> dict:
        return {
            "memory_cache_size": len(self._memory_cache),
            "cache_ttl_seconds": settings.cache_ttl_seconds,
        }


# Singleton
orchestrator = ExamAIOrchestrator()
