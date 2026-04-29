# app/agents/verifier_agent.py
import time
from typing import Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.config import settings
from app.logger import get_logger
from app.exceptions import VerificationError
import re

logger = get_logger(__name__)


# Structured output schema for verification result
# Why Pydantic here? We need the LLM to return structured data
# not free-form text. Pydantic enforces the schema.
class VerificationResult(BaseModel):
    verdict: str = Field(
        description="One of: VERIFIED, CONFLICTED, UNVERIFIED, LOW_CONFIDENCE"
    )
    confidence_score: float = Field(
        description="Confidence from 0.0 to 1.0",
        ge=0.0,
        le=1.0
    )
    final_answer: str = Field(
        description="The best answer based on all sources"
    )
    reasoning: str = Field(
        description="Why this verdict was reached"
    )
    sources_agree: bool = Field(
        description="Whether the sources agree with each other"
    )
    conflict_explanation: Optional[str] = Field(
        default=None,
        description="If sources conflict, explain the difference"
    )


# Verdict meanings — important to understand for interviews
# VERIFIED: multiple sources agree → high confidence
# CONFLICTED: sources disagree → flag it, show both, explain difference
# UNVERIFIED: only one source found anything → medium confidence
# LOW_CONFIDENCE: similarity scores too low → answer may be a guess

VERIFIER_SYSTEM_PROMPT = """You are a fact-checking expert for Indian competitive 
exams (JEE and UPSC). Your job is to verify answers by comparing multiple sources.

You will receive:
1. A question
2. An answer from a web search agent
3. An answer from a PDF/textbook agent
4. Similarity scores showing how confident each source is

CRITICAL DISTINCTION:
- CONFLICTED means sources state CONTRADICTORY FACTS (e.g. different formulas, 
  different article numbers, opposite statements)
- NOT CONFLICTED means sources agree on core facts but differ in detail/depth
  (e.g. one gives formula only, other gives formula + explanation = VERIFIED)

Verdict rules:
- VERIFIED: sources agree on key facts (even if one has more detail) → confidence 0.7-1.0
- CONFLICTED: sources state genuinely contradictory facts → confidence 0.3-0.6
- UNVERIFIED: only one source has relevant info → confidence 0.4-0.7
- LOW_CONFIDENCE: pdf similarity < 0.3 AND search result vague → confidence 0.1-0.4

For JEE: focus on formulas, units, numerical values being consistent.
For UPSC: focus on article numbers, dates, constitutional provisions being consistent.

If both sources give the same formula/article/fact but different amounts of 
explanation, that is VERIFIED not CONFLICTED.

Respond ONLY with a valid JSON object:
{
  "verdict": "VERIFIED|CONFLICTED|UNVERIFIED|LOW_CONFIDENCE",
  "confidence_score": 0.0-1.0,
  "final_answer": "the best complete answer combining both sources",
  "reasoning": "why you reached this verdict",
  "sources_agree": true|false,
  "conflict_explanation": "only if genuinely CONFLICTED, else null"
}"""

class VerifierAgent:
    """
    Cross-verification agent that compares answers from multiple sources
    and produces a confidence-scored, verified final answer.

    This implements a key AI safety pattern: never trust a single source.
    In production AI systems at MAANG companies, multi-source verification
    is standard practice for any high-stakes output.
    """

    def __init__(self):
        # GPT-4o-mini for verification — we need reliable JSON output
        # temperature=0 is critical here — we want deterministic
        # structured output, not creative variation
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=settings.openai_api_key,
        )
        logger.info("verifier_agent_initialized")

    async def verify(
        self,
        question: str,
        search_result: dict,
        pdf_result: dict,
    ) -> dict:
        """
        Verify answers from search and PDF agents.

        Args:
            question: Original question
            search_result: Output from SearchAgent.run()
            pdf_result: Output from PDFAgent.run()

        Returns:
            Verified result with confidence score and verdict
        """
        import json
        start = time.time()

        logger.info("verification_started", question=question[:100])

        # Extract key info from agent results
        search_answer = search_result.get("answer", "No answer from search")
        pdf_answer = pdf_result.get("answer", "No answer from PDF")
        pdf_similarity = pdf_result.get("top_similarity", 0.0)
        pdf_chunks = pdf_result.get("chunks_retrieved", 0)
        pdf_sources = pdf_result.get("sources", [])

        # Build the verification prompt
        # We give the LLM all the context it needs to make a good judgment
        verification_prompt = f"""Question: {question}

--- Web Search Agent Answer ---
{search_answer}

--- PDF/Textbook Agent Answer ---
{pdf_answer}

PDF Retrieval Confidence: {pdf_similarity:.2f} (0=no match, 1=perfect match)
PDF Chunks Found: {pdf_chunks}
PDF Sources: {', '.join(pdf_sources) if pdf_sources else 'None'}

Note: If PDF similarity < 0.4, the textbook agent may be guessing.
If PDF answer says 'no relevant content found', treat PDF as unavailable.

Verify these answers and respond with the JSON schema specified."""

        messages = [
            SystemMessage(content=VERIFIER_SYSTEM_PROMPT),
            HumanMessage(content=verification_prompt)
        ]

        try:
            response = await self.llm.ainvoke(messages)
            raw_content = response.content.strip()

            # Clean the response — LLMs sometimes wrap JSON in markdown
            # code blocks like ```json ... ``` even when told not to
            if raw_content.startswith("```"):
                lines = raw_content.split("\n")
                # Remove first line (```json) and last line (```)
                raw_content = "\n".join(lines[1:-1])
            raw_content = re.sub(
                r'\\(?!["\\/ bfnrtu])',
                r'\\\\',
                raw_content
            )

            # Parse the JSON response
            result_data = json.loads(raw_content)

            # Validate with Pydantic
            verification = VerificationResult(**result_data)

            duration = round(time.time() - start, 2)

            logger.info(
                "verification_completed",
                verdict=verification.verdict,
                confidence=verification.confidence_score,
                sources_agree=verification.sources_agree,
                duration_seconds=duration
            )

            return {
                "question": question,
                "verdict": verification.verdict,
                "confidence_score": verification.confidence_score,
                "final_answer": verification.final_answer,
                "reasoning": verification.reasoning,
                "sources_agree": verification.sources_agree,
                "conflict_explanation": verification.conflict_explanation,
                "duration_seconds": duration,
                "agent": "verifier",
                "source_answers": {
                    "search": search_answer[:500],
                    "pdf": pdf_answer[:500],
                },
                "pdf_similarity": pdf_similarity,
            }

        except json.JSONDecodeError as e:
            logger.error("verification_json_parse_failed", error=str(e))
            # Graceful degradation — if JSON parsing fails,
            # return the search answer with low confidence
            return self._fallback_result(
                question, search_answer, pdf_answer,
                reason=f"JSON parse failed: {str(e)}"
            )

        except Exception as e:
            logger.error("verification_failed", error=str(e))
            raise VerificationError(
                f"Verification failed: {str(e)}",
                details={"question": question}
            )

    async def self_correct(
        self,
        question: str,
        initial_result: dict,
        retry_search_func,
    ) -> dict:
        """
        Self-correction loop.

        If confidence is below threshold, reformulate the query
        and search again. This implements the self-RAG pattern —
        the system evaluates its own output and decides if it needs
        to try again.

        Args:
            question: Original question
            initial_result: First verification result
            retry_search_func: Async function to call for new search

        Returns:
            Improved result or original if correction doesn't help
        """
        CONFIDENCE_THRESHOLD = 0.5
        MAX_CORRECTION_ATTEMPTS = 2

        if initial_result["confidence_score"] >= CONFIDENCE_THRESHOLD:
            logger.info("self_correction_not_needed",
                       confidence=initial_result["confidence_score"])
            return initial_result

        logger.info(
            "self_correction_triggered",
            confidence=initial_result["confidence_score"],
            verdict=initial_result["verdict"]
        )

        best_result = initial_result

        for attempt in range(1, MAX_CORRECTION_ATTEMPTS + 1):
            # Ask the LLM to reformulate the query
            reformulated = await self._reformulate_query(
                question, initial_result["reasoning"], attempt
            )

            logger.info(
                "self_correction_attempt",
                attempt=attempt,
                reformulated_query=reformulated
            )

            # Run new search with reformulated query
            new_search_result = await retry_search_func(reformulated)

            # Re-verify with new search result
            new_verification = await self.verify(
                question=question,
                search_result=new_search_result,
                pdf_result={"answer": initial_result["source_answers"]["pdf"],
                           "top_similarity": initial_result["pdf_similarity"],
                           "chunks_retrieved": 0,
                           "sources": []}
            )

            logger.info(
                "self_correction_result",
                attempt=attempt,
                old_confidence=best_result["confidence_score"],
                new_confidence=new_verification["confidence_score"]
            )

            # Keep the better result
            if new_verification["confidence_score"] > best_result["confidence_score"]:
                best_result = new_verification
                best_result["self_corrected"] = True
                best_result["correction_attempts"] = attempt

            # Stop if confidence is now acceptable
            if best_result["confidence_score"] >= CONFIDENCE_THRESHOLD:
                break

        return best_result

    async def _reformulate_query(
        self,
        original_question: str,
        failure_reason: str,
        attempt: int
    ) -> str:
        """
        Ask the LLM to reformulate a query that got low confidence results.
        Different reformulation strategy per attempt.
        """
        strategies = [
            "Make the query more specific with technical terms",
            "Try a completely different angle or phrasing",
        ]
        strategy = strategies[min(attempt - 1, len(strategies) - 1)]

        messages = [
            SystemMessage(content=(
                "You are a search query optimizer for Indian competitive exam research. "
                "Reformulate queries to get better search results."
            )),
            HumanMessage(content=f"""Original question: {original_question}

Why previous search failed: {failure_reason}

Strategy: {strategy}

Write ONLY the reformulated search query, nothing else.""")
        ]

        response = await self.llm.ainvoke(messages)
        return response.content.strip()

    def _fallback_result(
        self,
        question: str,
        search_answer: str,
        pdf_answer: str,
        reason: str
    ) -> dict:
        """Return a safe fallback when verification itself fails."""
        return {
            "question": question,
            "verdict": "UNVERIFIED",
            "confidence_score": 0.3,
            "final_answer": search_answer,
            "reasoning": f"Verification process failed: {reason}. Showing search result.",
            "sources_agree": False,
            "conflict_explanation": None,
            "duration_seconds": 0,
            "agent": "verifier",
            "source_answers": {
                "search": search_answer[:500],
                "pdf": pdf_answer[:500],
            },
            "pdf_similarity": 0.0,
        }


# Singleton
verifier_agent = VerifierAgent()
