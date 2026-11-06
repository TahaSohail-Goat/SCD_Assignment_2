# ADR 0002: Preserve document structure in chunks

Status: accepted as interface, 2026-11-06; empirical settings pending teammate measurements.

## Context

Policy sections, tables, and page numbers matter for exact citations. A blind character window can split a clause from its heading or merge an old policy into a current one.

## Decision

`indexer/pipeline/chunk.py` will split at headings and paragraph boundaries, retain table rows as units where possible, and overlap adjacent text. Each chunk carries source, section, page, document version, and superseded status. The default ConfigMap has size 400 and overlap 50. These are provisional values until the teammate evaluates three configurations against the golden set and records recall@5 and storage amplification in `docs/PIPELINE.md`.

## Consequences

More metadata is stored per vector, but citations can be validated precisely. The unit of size and the final values must be documented after measurement, not inferred from the defaults.
