# eval/metrics.py
"""
Compute RAGAS-style metrics on evaluation results.
Analyzes the saved results.json and produces detailed metrics.

Usage:
    python eval/metrics.py --input eval/results.json
"""
import json
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def compute_faithfulness(result: dict) -> float:
    """
    Faithfulness: does the answer stick to what sources provided?

    Heuristic approximation of RAGAS faithfulness:
    - VERIFIED + high confidence = high faithfulness
    - CONFLICTED = medium faithfulness
    - LOW_CONFIDENCE = low faithfulness (may be hallucinating)
    - ERROR = zero faithfulness

    In production RAGAS, this uses an LLM to check each claim
    in the answer against the retrieved context. We approximate
    it here using our existing verdict and confidence signals
    to avoid the cost of LLM calls per evaluation question.
    """
    verdict = result.get("verdict", "ERROR")
    confidence = result.get("confidence_score", 0.0)

    if verdict == "VERIFIED":
        return min(1.0, confidence + 0.1)
    elif verdict == "UNVERIFIED":
        return confidence * 0.8
    elif verdict == "CONFLICTED":
        return confidence * 0.6
    elif verdict == "LOW_CONFIDENCE":
        return confidence * 0.4
    else:
        return 0.0


def compute_answer_relevancy(result: dict) -> float:
    """
    Answer relevancy: does the answer address the question?

    Heuristic: if the system produced an answer (not error/empty)
    and has a reasonable confidence score, we assume relevancy.
    Low confidence often correlates with off-topic answers.
    """
    answer = result.get("generated_answer", "")
    confidence = result.get("confidence_score", 0.0)

    if not answer or result.get("error"):
        return 0.0

    # Penalize very short answers — they're often evasions
    if len(answer) < 50:
        return 0.2

    return min(1.0, confidence + 0.05)


def compute_context_recall(result: dict) -> float:
    """
    Context recall: did retrieval find relevant content?

    We use PDF similarity score as a proxy.
    High similarity = relevant chunks were found.
    Low similarity = relevant content may not be in indexed PDFs.
    """
    similarity = result.get("pdf_similarity", 0.0)
    chunks = result.get("chunks_retrieved", 0)

    if chunks == 0:
        return 0.2  # No PDF content found at all

    # Normalize similarity to 0-1 range
    return min(1.0, similarity * 1.2)


def compute_context_precision(result: dict) -> float:
    """
    Context precision: how many retrieved chunks were actually useful?

    Proxy: if sources agreed and verdict is VERIFIED,
    the retrieved context was precise. If conflicted,
    some retrieved content may have been noise.
    """
    verdict = result.get("verdict", "ERROR")
    sources_agree = result.get("sources_agree", False)
    similarity = result.get("pdf_similarity", 0.0)

    if verdict == "VERIFIED" and sources_agree:
        return min(1.0, similarity + 0.2)
    elif verdict == "CONFLICTED":
        return similarity * 0.7
    elif verdict == "UNVERIFIED":
        return similarity * 0.8
    else:
        return similarity * 0.5


def analyze_results(input_file: str) -> None:
    """Load results and compute all metrics."""
    with open(input_file) as f:
        data = json.load(f)

    results = data["results"]
    summary = data["summary"]

    print(f"\n{'='*60}")
    print(f"RAGAS-STYLE METRICS ANALYSIS")
    print(f"{'='*60}")

    # Compute metrics per question
    metrics_per_question = []
    for r in results:
        if r.get("error"):
            continue

        metrics = {
            "id": r["id"],
            "category": r["category"],
            "difficulty": r["difficulty"],
            "faithfulness": compute_faithfulness(r),
            "answer_relevancy": compute_answer_relevancy(r),
            "context_recall": compute_context_recall(r),
            "context_precision": compute_context_precision(r),
        }
        metrics["ragas_score"] = round(
            (metrics["faithfulness"] +
             metrics["answer_relevancy"] +
             metrics["context_recall"] +
             metrics["context_precision"]) / 4, 3
        )
        metrics_per_question.append(metrics)

    if not metrics_per_question:
        print("No successful results to analyze")
        return

    # Overall metrics
    n = len(metrics_per_question)
    avg_faithfulness = sum(m["faithfulness"]
                          for m in metrics_per_question) / n
    avg_relevancy = sum(m["answer_relevancy"]
                       for m in metrics_per_question) / n
    avg_recall = sum(m["context_recall"]
                    for m in metrics_per_question) / n
    avg_precision = sum(m["context_precision"]
                       for m in metrics_per_question) / n
    avg_ragas = sum(m["ragas_score"]
                   for m in metrics_per_question) / n

    print(f"\nOverall RAGAS Metrics (n={n}):")
    print(f"  Faithfulness:       {avg_faithfulness:.3f}")
    print(f"  Answer Relevancy:   {avg_relevancy:.3f}")
    print(f"  Context Recall:     {avg_recall:.3f}")
    print(f"  Context Precision:  {avg_precision:.3f}")
    print(f"  ─────────────────────────")
    print(f"  RAGAS Score:        {avg_ragas:.3f}")

    # By category
    categories = {}
    for m in metrics_per_question:
        cat = m["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(m["ragas_score"])

    print(f"\nRAGAS Score by Category:")
    for cat, scores in sorted(categories.items()):
        avg = sum(scores) / len(scores)
        print(f"  {cat:<25} {avg:.3f}  (n={len(scores)})")

    # By difficulty
    difficulties = {}
    for m in metrics_per_question:
        diff = m["difficulty"]
        if diff not in difficulties:
            difficulties[diff] = []
        difficulties[diff].append(m["ragas_score"])

    print(f"\nRAGAS Score by Difficulty:")
    for diff, scores in sorted(difficulties.items()):
        avg = sum(scores) / len(scores)
        print(f"  {diff:<10} {avg:.3f}  (n={len(scores)})")

    # Save metrics
    metrics_output = {
        "overall": {
            "faithfulness": round(avg_faithfulness, 3),
            "answer_relevancy": round(avg_relevancy, 3),
            "context_recall": round(avg_recall, 3),
            "context_precision": round(avg_precision, 3),
            "ragas_score": round(avg_ragas, 3),
            "n": n,
        },
        "by_category": {
            cat: round(sum(scores) / len(scores), 3)
            for cat, scores in categories.items()
        },
        "by_difficulty": {
            diff: round(sum(scores) / len(scores), 3)
            for diff, scores in difficulties.items()
        },
        "per_question": metrics_per_question,
    }

    output_path = Path(input_file).parent / "metrics.json"
    with open(output_path, "w") as f:
        json.dump(metrics_output, f, indent=2)

    print(f"\nDetailed metrics saved to: {output_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="eval/results.json")
    args = parser.parse_args()
    analyze_results(args.input)
