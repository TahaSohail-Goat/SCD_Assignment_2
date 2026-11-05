# ADR 0004: Local Ollama provider and policy text

Status: accepted, 2026-11-06.

## Context

Policy documents and student questions may contain personal details. The stronger group laptop can run local models; the teammate laptop cannot.

## Decision

The default production overlay uses host Ollama with `llama3.2:3b` for generation and `nomic-embed-text` for embeddings. An optional hosted adapter exists but requires a Kubernetes Secret created outside Git. No hosted key is committed or placed in an example environment file. The prompt treats retrieved text and the user question as untrusted data. Model output is schema validated and citations are checked against retrieved source/section/page triples.

## Consequences

Ollama must listen on `0.0.0.0:11434` and the cluster needs access to the host. Local inference may be slower; generation latency and token metrics expose that cost. A hosted deployment would need a separate privacy review and a real secret.
