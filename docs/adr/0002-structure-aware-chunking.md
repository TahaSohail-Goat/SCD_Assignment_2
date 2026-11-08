# ADR 0002: Preserve document structure in chunks

Status: accepted, 2026-11-06; completion update 2026-11-08.

## Context

Policy sections, tables, and page numbers matter for exact citations. A blind character window can split a clause from its heading or merge an old policy into a current one.

## Decision

`indexer/pipeline/chunk.py` splits at headings and paragraph boundaries, retains table rows where possible, and overlaps adjacent windows within a section/page. Each chunk carries source, section, page, document version and superseded status. Size/overlap units are whitespace words. The November 6 real comparison of 120/20, 240/35 and 400/50 tied at 100% recall@5. We selected 400/50 for 669 rather than 802 or 690 vectors and lower measured word duplication. The table and its historical scope are in `docs/PIPELINE.md`. Actual embedding-token amplification is now separately instrumented; fresh completion-branch measurements must be retained before claiming that requirement complete.

## Consequences

More metadata is stored per vector, but citations can be validated precisely. Page boundaries avoid false page citations but can split a multi-page rule. Chunking targets words; storage-cost reporting uses embedding-model tokens from Ollama usage. These are deliberately different units and must not be confused.
