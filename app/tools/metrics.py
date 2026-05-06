# app/tools/metrics.py
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

requests_total = Counter(
    "examai_requests_total",
    "Total number of questions asked",
    ["endpoint", "verdict"]
)

errors_total = Counter(
    "examai_errors_total",
    "Total number of errors",
    ["endpoint", "error_type"]
)

cache_hits_total = Counter(
    "examai_cache_hits_total",
    "Total number of cache hits",
    ["backend"]
)

cache_misses_total = Counter(
    "examai_cache_misses_total",
    "Total number of cache misses"
)

pipeline_duration = Histogram(
    "examai_pipeline_duration_seconds",
    "Time taken for full orchestrator pipeline",
    buckets=[1, 5, 10, 15, 20, 30, 60, 120]
)

agent_duration = Histogram(
    "examai_agent_duration_seconds",
    "Time taken for individual agent runs",
    ["agent_name"],
    buckets=[0.5, 1, 2, 5, 10, 20, 30]
)

confidence_score = Histogram(
    "examai_confidence_score",
    "Confidence scores of verified answers",
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

cache_size = Gauge(
    "examai_cache_size",
    "Current number of cached answers"
)

chunks_indexed = Gauge(
    "examai_chunks_indexed",
    "Total number of PDF chunks in vector store"
)

active_requests = Gauge(
    "examai_active_requests",
    "Number of requests currently being processed"
)


def record_request(endpoint: str, verdict: str, duration: float,
                   confidence: float, from_cache: bool,
                   cache_backend: str = None):
    requests_total.labels(endpoint=endpoint, verdict=verdict).inc()
    pipeline_duration.observe(duration)
    confidence_score.observe(confidence)
    if from_cache:
        cache_hits_total.labels(backend=cache_backend or "unknown").inc()
    else:
        cache_misses_total.inc()


def record_error(endpoint: str, error_type: str):
    errors_total.labels(endpoint=endpoint, error_type=error_type).inc()


def update_gauges(cache_size_val: int, chunks_val: int):
    cache_size.set(cache_size_val)
    chunks_indexed.set(chunks_val)
