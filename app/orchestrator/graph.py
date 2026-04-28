# app/orchestrator/graph.py
import asyncio
import json
import time
import hashlib
from typing import Optional
from app.agents.search_agent import search_agent
from app.agents.pdf_agent import pdf_agent
from app.agents.verifier_agent import verifier_agent
from app.config import settings
from app.logger import get_logger
from app.exceptions import AgentError

logger = get_logger(__name__)

# Sentinel object to distinguish "cache miss" from cached None
_CACHE_MISS = object()


class ExamAIOrchestrator:
    """
    Central coordinator for the multi-agent system.

    Responsibilities:
    1. Cache lookup — answer immediately if seen recently
    2. Parallel execution — run search + PDF agents concurrently
    3. Graceful degradation — handle individual agent failures
    4. Verification — cross-check answers for confidence scoring
    5. Self-correction — retry with reformulated query if needed
    6. Cache storage — save verified answer for future requests
    7. Metadata — track which agents ran, timings, cache hits

    This is the only entry point for the system. All other agents
    are implementation details — callers only talk to the orchestrator.
    """

    def __init__(self):
        # In-memory cache for development
        # In production this would be Redis (we'll add that in Day 14)
        # Key: question hash, Value: cached result dict
        self._cache: dict = {}
        # Track when each cache entry was stored
        self._cache_timestamps: dict = {}
        logger.info("orchestrator_initialized")

    def _get_cache_key(self, question: str) -> str:
        """
        Generate a cache key from a question.

        Why hash? Cache keys should be:
        1. Short (hashes are fixed length)
        2. Consistent (same question = same hash)
        3. Safe for use as dict keys

        We lowercase and strip whitespace first so
        "What is F=ma?" and "what is f=ma ?" hit the same cache entry.
        """
        normalized = question.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()

    def _get_from_cache(self, question: str) -> object:
        """
        Check cache for a previously answered question.
        Returns _CACHE_MISS if not found or expired.
        """
        key = self._get_cache_key(question)

        if key not in self._cache:
            return _CACHE_MISS

        # Check if cache entry has expired
        stored_at = self._cache_timestamps.get(key, 0)
        age_seconds = time.time() - stored_at

        if age_seconds > settings.cache_ttl_seconds:
            # Expired — remove and return miss
            del self._cache[key]
            del self._cache_timestamps[key]
            logger.info("cache_expired", age_seconds=round(age_seconds))
            return _CACHE_MISS

        logger.info(
            "cache_hit",
            age_seconds=round(age_seconds),
            question=question[:50]
        )
        return self._cache[key]

    def _store_in_cache(self, question: str, result: dict) -> None:
        """Store a result in cache with current timestamp."""
        # Only cache high-confidence results
        # Don't cache LOW_CONFIDENCE answers — they might be wrong
        if result.get("confidence_score", 0) < 0.5:
            logger.info("cache_skip_low_confidence",
                       confidence=result.get("confidence_score"))
            return

        key = self._get_cache_key(question)
        self._cache[key] = result
        self._cache_timestamps[key] = time.time()
        logger.info("cache_stored", question=question[:50])

    async def _run_search_agent(self, question: str) -> Optional[dict]:
        """Run search agent with error isolation."""
        try:
            result = await search_agent.run(question)
            logger.info("search_agent_success",
                       duration=result.get("duration_seconds"))
            return result
        except Exception as e:
            logger.error("search_agent_failed", error=str(e))
            # Return a structured failure — not None, not an exception
            # The orchestrator needs to handle this gracefully
            return {
                "answer": f"Web search unavailable: {str(e)}",
                "agent": "search",
                "failed": True,
                "duration_seconds": 0,
                "question": question,
            }

    async def _run_pdf_agent(self, question: str) -> Optional[dict]:
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
        Main entry point. Orchestrates all agents to answer a question.

        Flow:
        1. Check cache
        2. Run search + PDF concurrently
        3. Verify results
        4. Self-correct if needed
        5. Cache result
        6. Return with metadata

        Args:
            question: The JEE or UPSC question to answer

        Returns:
            Verified, confidence-scored answer with full metadata
        """
        pipeline_start = time.time()

        logger.info("orchestrator_run_started", question=question[:100])

        # Step 1: Cache check
        cached = self._get_from_cache(question)
        if cached is not _CACHE_MISS:
            cached["from_cache"] = True
            cached["cache_latency_ms"] = round(
                (time.time() - pipeline_start) * 1000, 2
            )
            return cached

        # Step 2: Run search and PDF agents CONCURRENTLY
        # asyncio.gather runs both at the same time
        # Total time = max(search_time, pdf_time) not search_time + pdf_time
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

        # Step 3: Handle complete failure
        if search_failed and pdf_failed:
            logger.error("all_agents_failed", question=question[:100])
            return {
                "question": question,
                "verdict": "ERROR",
                "confidence_score": 0.0,
                "final_answer": "Both search and PDF agents failed. Please try again.",
                "reasoning": "All agents unavailable",
                "sources_agree": False,
                "from_cache": False,
                "agents_used": [],
                "pipeline_duration_seconds": round(time.time() - pipeline_start, 2),
            }

        # Step 4: Verify results
        # Even if one agent failed, we can still verify with the other
        verified = await verifier_agent.verify(
            question=question,
            search_result=search_result,
            pdf_result=pdf_result,
        )

        # Step 5: Self-correct if confidence is low
        final = await verifier_agent.self_correct(
            question=question,
            initial_result=verified,
            retry_search_func=lambda q: self._run_search_agent(q),
        )

        # Step 6: Build final response with metadata
        pipeline_duration = round(time.time() - pipeline_start, 2)

        agents_used = []
        if not search_failed:
            agents_used.append("search")
        if not pdf_failed:
            agents_used.append("pdf")
        agents_used.append("verifier")

        final.update({
            "from_cache": False,
            "agents_used": agents_used,
            "agent_duration_seconds": agent_duration,
            "pipeline_duration_seconds": pipeline_duration,
            "search_failed": search_failed,
            "pdf_failed": pdf_failed,
        })

        # Step 7: Cache the result if confidence is good
        self._store_in_cache(question, final)

        logger.info(
            "orchestrator_run_completed",
            verdict=final.get("verdict"),
            confidence=final.get("confidence_score"),
            pipeline_duration=pipeline_duration,
            agents_used=agents_used,
            from_cache=False,
        )

        return final

    def get_stats(self) -> dict:
        """Return orchestrator statistics."""
        return {
            "cache_size": len(self._cache),
            "cache_ttl_seconds": settings.cache_ttl_seconds,
        }


# Singleton
orchestrator = ExamAIOrchestrator()
