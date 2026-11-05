# ADR 0001: Run indexing as a Job

Status: accepted, 2026-11-06.

## Context

The API runs three replicas and Chroma has one persistent volume. Indexing during each API startup would create three concurrent writers, delay readiness, and repeat work after routine restarts.

## Decision

Only `indexer/pipeline/run.py` writes the collection. `k8s/base/indexer.yaml` runs it as a bounded Job for initial indexing and a weekly CronJob for refresh. The API is a reader and checks collection count and embedding metadata before becoming ready. The teammate's real store stage must publish complete data before incrementing the Redis index generation, so existing semantic cache entries cannot survive a successful reindex.

## Options considered

Indexing in API startup was rejected because replica scaling would multiply writes. A long-running indexer Deployment was rejected because indexing is finite work and Kubernetes Jobs expose completion and retry status directly.

## Consequences

Deployment has an explicit apply order: data services, index Job, then ready API. A failed Job is visible and leaves the API unready for the first index. A future zero-gap refresh needs staging collection and a controlled switch; the initial dummy writer replaces its collection directly and is only for development.
