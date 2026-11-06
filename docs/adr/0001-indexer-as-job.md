# ADR 0001: Run indexing as a Job

Status: accepted, 2026-11-06.

## Context

The API runs three replicas and Chroma has one persistent volume. Indexing during each API startup would create three concurrent writers, delay readiness, and repeat work after routine restarts.

## Decision

Only `indexer/pipeline/run.py` writes the collection. `k8s/base/indexer.yaml` runs it as a bounded Job for initial indexing and a weekly CronJob for refresh. The API is a reader and checks collection count and embedding metadata before becoming ready. The real store stage verifies a staging collection and publishes it under the API's collection name before incrementing the Redis index generation.

## Options considered

Indexing in API startup was rejected because replica scaling would multiply writes. A long-running indexer Deployment was rejected because indexing is finite work and Kubernetes Jobs expose completion and retry status directly.

## Consequences

Deployment has an explicit apply order: data services, index Job, then ready API. A failed Job is visible and leaves the API unready for the first index. Real reindexing keeps the previous collection readable during the build. Publication uses two Chroma renames under a Redis lock and has a brief interval where the configured name is missing. In-flight requests retain their original cache generation. The dummy writer is restricted to the development workflow. See [Pipeline](../PIPELINE.md#chunks-embeddings-and-storage) for recovery behavior.
