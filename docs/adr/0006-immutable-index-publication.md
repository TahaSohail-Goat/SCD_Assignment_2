# ADR 0006: Publish immutable indexes through an atomic pointer

Status: accepted, 8 November 2026.

## Context

The previous staging→backup→live rename sequence kept old data safe but exposed a
brief missing-collection interval to uncached readers. A Redis writer lock did not
protect API readers. A periodic readiness probe cannot protect a request already
routed during that interval.

## Decision

Every successful real build creates and verifies an immutable Chroma snapshot.
Under the publication lock, one Redis MULTI/EXEC transaction sets
`rahbar:index:<logical collection>:active` and increments the cache generation.
API retrieval/readiness resolve that name once per check/query. Existing logical
collections remain a migration fallback until the first snapshot is published.
No old collection is renamed or deleted during publication.

## Consequences

Old readers finish on their previous snapshot while new readers see the new one.
Pre-publication failure leaves the pointer unchanged. A lost transaction
acknowledgement retains the new snapshot and fails the Job visibly; retry is safe.
Retaining snapshots consumes PVC space. Operators must monitor it and perform
inactive-snapshot cleanup only after draining readers. This assignment does not
claim automatic garbage collection or a distributed database failover solution.
Redis persistence now protects operational state as well as cache data; restoring
only Redis or only Chroma may require rerunning the Job. Both are readiness dependencies.
