# ADR 0003: Redis semantic answer cache

Status: accepted, 2026-11-06.

## Context

Repeated standalone questions otherwise incur embedding, retrieval, and generation latency. Cached answers can become stale after a policy reindex.

## Decision

`api/app/services/cache.py` stores response JSON and query vectors in Redis with a 24-hour TTL. Cosine threshold is configurable; the prior 0.95 is a reference pending review of the new real calibration. `eval/calibrate_cache.py` measures three thresholds and selects the lowest tested threshold with zero labelled false hits, retaining every pair's score and true-hit tradeoff. Follow-ups, abstentions and fallbacks are not stored. Keys include index generation plus model/prompt/retrieval scope; the indexer atomically increments generation with snapshot publication. Redis is required for readiness. Request handling can degrade to uncached answering if cache lookup alone fails. Separate turn records expire after one hour and never contain internal reasoning.

## Consequences

The current scan over cache entries is suitable for assignment scale, not a large production corpus. Cache ratio and error counters are exposed at `/metrics`. Old generations expire by TTL rather than immediate deletion.
