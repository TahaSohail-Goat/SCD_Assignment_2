# ADR 0003: Redis semantic answer cache

Status: accepted, 2026-11-06.

## Context

Repeated standalone questions otherwise incur embedding, retrieval, and generation latency. Cached answers can become stale after a policy reindex.

## Decision

`api/app/services/cache.py` stores response JSON and query vectors in Redis with a 24 hour TTL. It compares cosine similarity against configurable threshold 0.95. Follow-up questions, abstentions, and fallbacks are not stored. Keys include the `rahbar:index_generation` counter. The indexer must increment that counter after a complete successful write. Redis is required for readiness so cache failures are operationally visible; request handling degrades to uncached answering if one lookup fails.

## Consequences

The current scan over cache entries is suitable for assignment scale, not a large production corpus. Cache ratio and error counters are exposed at `/metrics`. Old generations expire by TTL rather than immediate deletion.
