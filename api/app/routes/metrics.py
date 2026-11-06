"""Prometheus metrics at /metrics (section 4.8).

Request count and latency are wired up already. Add your own the same way:
retrieval latency, generation latency, cache hits, abstentions, fallbacks, tokens.
"""

from __future__ import annotations

from threading import Lock

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

router = APIRouter()

REQUESTS = Counter("rahbar_requests_total", "HTTP requests", ["path", "status"])
LATENCY = Histogram(
    "rahbar_request_seconds",
    "HTTP request latency",
    ["path"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60),
)
RETRIEVAL_LATENCY = Histogram("rahbar_retrieval_seconds", "Time spent retrieving passages")
GENERATION_LATENCY = Histogram("rahbar_generation_seconds", "Time spent generating an answer")
CACHE_LOOKUPS = Counter("rahbar_cache_lookups_total", "Semantic cache lookups", ["result"])
CACHE_HIT_RATIO = Gauge("rahbar_cache_hit_ratio", "Semantic cache hit ratio for this API process")
ABSTENTIONS = Counter("rahbar_abstentions_total", "Answers declined for insufficient evidence")
FALLBACKS = Counter("rahbar_fallbacks_total", "Safe fallbacks after invalid model output")
TOKENS = Counter("rahbar_tokens_total", "Model tokens consumed", ["provider", "direction"])

_cache_lock = Lock()
_cache_lookups = 0
_cache_hits = 0


def record_cache_lookup(result: str) -> None:
    global _cache_lookups, _cache_hits
    CACHE_LOOKUPS.labels(result=result).inc()
    if result in {"hit", "miss"}:
        with _cache_lock:
            _cache_lookups += 1
            _cache_hits += int(result == "hit")
            CACHE_HIT_RATIO.set(_cache_hits / _cache_lookups)


@router.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
