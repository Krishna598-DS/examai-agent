# eval/run_eval.py
"""
Evaluation harness for the ExamAI multi-agent system.

Runs questions through the orchestrator, collects answers,
computes RAGAS metrics, and generates a report.

Usage:
    python eval/run_eval.py --questions 20 --category JEE_Physics
    python eval/run_eval.py --questions 200  # full eval
"""
import asyncio
import json
import time
import argparse
import sys
import os
from pathlib import Path
from typing import Optional

# Add project root to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.orchestrator.graph import orchestrator
from app.logger import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


async def run_single_question(
    question_data: dict,
    question_num: int,
    total: int
) -> dict:
    """
    Run a single question through the orchestrator and collect results.
    Returns the question data enriched with the system's answer.
    """
    question = question_data["question"]
    ground_truth = question_data["ground_truth"]
    category = question_data["category"]
    qid = question_data["id"]

    print(f"\n[{question_num}/{total}] {qid} ({category})")
    print(f"Q: {question[:80]}...")

    start = time.time()

    try:
        result = await orchestrator.run(question)

        answer = result.get("final_answer", "")
        verdict = result.get("verdict", "ERROR")
        confidence = result.get("confidence_score", 0.0)
        from_cache = result.get("from_cache", False)
        duration = result.get("pipeline_duration_seconds", 0)

        print(f"✓ {verdict} (confidence: {confidence:.2f}, {duration:.1f}s{'  [CACHED]' if from_cache else ''})")

        return {
            "id": qid,
            "category": category,
            "difficulty": question_data.get("difficulty", "unknown"),
            "question": question,
            "ground_truth": ground_truth,
            "generated_answer": answer,
            "verdict": verdict,
            "confidence_score": confidence,
            "from_cache": from_cache,
            "pipeline_duration_seconds": duration,
            "agents_used": result.get("agents_used", []),
            "pdf_similarity": result.get("pdf_similarity", 0.0),
            "sources_agree": result.get("sources_agree", False),
            "error": None,
        }

    except Exception as e:
        duration = round(time.time() - start, 2)
        print(f"✗ ERROR: {str(e)[:100]}")
        logger.error("eval_question_failed", qid=qid, error=str(e))

        return {
            "id": qid,
            "category": category,
            "difficulty": question_data.get("difficulty", "unknown"),
            "question": question,
            "ground_truth": ground_truth,
            "generated_answer": "",
            "verdict": "ERROR",
            "confidence_score": 0.0,
            "from_cache": False,
            "pipeline_duration_seconds": duration,
            "agents_used": [],
            "pdf_similarity": 0.0,
            "sources_agree": False,
            "error": str(e),
        }


async def run_evaluation(
    num_questions: int = 20,
    category_filter: Optional[str] = None,
    output_file: str = "eval/results.json"
) -> dict:
    """
    Run the full evaluation pipeline.

    Args:
        num_questions: How many questions to evaluate
        category_filter: Only evaluate this category (e.g. "JEE_Physics")
        output_file: Where to save results JSON

    Returns:
        Summary statistics dict
    """
    # Load questions
    questions_path = Path("eval/questions.json")
    with open(questions_path) as f:
        data = json.load(f)

    questions = data["questions"]

    # Apply category filter
    if category_filter:
        questions = [q for q in questions
                    if q["category"] == category_filter]
        print(f"Filtered to {len(questions)} questions in {category_filter}")

    # Limit to num_questions
    questions = questions[:num_questions]
    total = len(questions)

    print(f"\n{'='*60}")
    print(f"ExamAI Evaluation Pipeline")
    print(f"Questions: {total}")
    print(f"Category filter: {category_filter or 'All'}")
    print(f"{'='*60}")

    eval_start = time.time()
    results = []

    for i, question_data in enumerate(questions, 1):
        result = await run_single_question(question_data, i, total)
        results.append(result)

        # Small delay between questions to avoid rate limiting
        # 2 seconds between questions = ~30 questions per minute
        if i < total:
            await asyncio.sleep(2)

    eval_duration = round(time.time() - eval_start, 2)

    # Compute summary statistics
    summary = compute_summary(results, eval_duration)

    # Save full results
    output = {
        "summary": summary,
        "results": results
    }

    Path(output_file).parent.mkdir(exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print_summary(summary)
    print(f"\nFull results saved to: {output_file}")

    return summary


def compute_summary(results: list, eval_duration: float) -> dict:
    """Compute aggregate statistics from evaluation results."""
    total = len(results)
    errors = [r for r in results if r["error"]]
    successful = [r for r in results if not r["error"]]

    if not successful:
        return {"error": "All questions failed", "total": total}

    # Verdict distribution
    verdicts = {}
    for r in successful:
        v = r["verdict"]
        verdicts[v] = verdicts.get(v, 0) + 1

    # Confidence statistics
    confidences = [r["confidence_score"] for r in successful]
    avg_confidence = sum(confidences) / len(confidences)

    # High confidence = >= 0.7
    high_confidence = len([c for c in confidences if c >= 0.7])

    # Latency statistics
    durations = [r["pipeline_duration_seconds"]
                for r in successful if not r["from_cache"]]
    avg_latency = sum(durations) / len(durations) if durations else 0

    # Cache hit rate
    cached = len([r for r in successful if r["from_cache"]])
    cache_hit_rate = cached / len(successful) if successful else 0

    # By category
    categories = {}
    for r in successful:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {
                "total": 0, "verified": 0,
                "avg_confidence": 0, "confidences": []
            }
        categories[cat]["total"] += 1
        if r["verdict"] == "VERIFIED":
            categories[cat]["verified"] += 1
        categories[cat]["confidences"].append(r["confidence_score"])

    for cat in categories:
        confs = categories[cat]["confidences"]
        categories[cat]["avg_confidence"] = round(
            sum(confs) / len(confs), 3
        )
        categories[cat]["verification_rate"] = round(
            categories[cat]["verified"] / categories[cat]["total"], 3
        )
        del categories[cat]["confidences"]

    # By difficulty
    difficulties = {}
    for r in successful:
        diff = r["difficulty"]
        if diff not in difficulties:
            difficulties[diff] = {"total": 0, "confidences": []}
        difficulties[diff]["total"] += 1
        difficulties[diff]["confidences"].append(r["confidence_score"])

    for diff in difficulties:
        confs = difficulties[diff]["confidences"]
        difficulties[diff]["avg_confidence"] = round(
            sum(confs) / len(confs), 3
        )
        del difficulties[diff]["confidences"]

    return {
        "total_questions": total,
        "successful": len(successful),
        "errors": len(errors),
        "eval_duration_seconds": eval_duration,
        "verdicts": verdicts,
        "verification_rate": round(
            verdicts.get("VERIFIED", 0) / len(successful), 3
        ),
        "avg_confidence_score": round(avg_confidence, 3),
        "high_confidence_rate": round(high_confidence / len(successful), 3),
        "avg_latency_seconds": round(avg_latency, 2),
        "cache_hit_rate": round(cache_hit_rate, 3),
        "by_category": categories,
        "by_difficulty": difficulties,
    }


def print_summary(summary: dict) -> None:
    """Print a formatted summary to console."""
    print(f"\n{'='*60}")
    print(f"EVALUATION RESULTS")
    print(f"{'='*60}")
    print(f"Total questions:      {summary['total_questions']}")
    print(f"Successful:           {summary['successful']}")
    print(f"Errors:               {summary['errors']}")
    print(f"")
    print(f"Verification rate:    {summary['verification_rate']:.1%}")
    print(f"Avg confidence:       {summary['avg_confidence_score']:.3f}")
    print(f"High confidence rate: {summary['high_confidence_rate']:.1%}")
    print(f"Avg latency:          {summary['avg_latency_seconds']:.1f}s")
    print(f"Cache hit rate:       {summary['cache_hit_rate']:.1%}")
    print(f"")
    print(f"Verdict breakdown:")
    for verdict, count in summary.get("verdicts", {}).items():
        pct = count / summary["successful"] * 100
        print(f"  {verdict:<20} {count:>3} ({pct:.1f}%)")
    print(f"")
    print(f"By category:")
    for cat, stats in summary.get("by_category", {}).items():
        print(f"  {cat:<25} "
              f"verified: {stats['verification_rate']:.1%}  "
              f"confidence: {stats['avg_confidence']:.3f}")
    print(f"")
    print(f"By difficulty:")
    for diff, stats in summary.get("by_difficulty", {}).items():
        print(f"  {diff:<10} "
              f"n={stats['total']}  "
              f"avg_confidence: {stats['avg_confidence']:.3f}")
    print(f"{'='*60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run ExamAI evaluation pipeline"
    )
    parser.add_argument(
        "--questions", type=int, default=20,
        help="Number of questions to evaluate (default: 20)"
    )
    parser.add_argument(
        "--category", type=str, default=None,
        help="Category filter e.g. JEE_Physics, UPSC_Polity"
    )
    parser.add_argument(
        "--output", type=str, default="eval/results.json",
        help="Output file path"
    )

    args = parser.parse_args()

    asyncio.run(run_evaluation(
        num_questions=args.questions,
        category_filter=args.category,
        output_file=args.output
    ))
