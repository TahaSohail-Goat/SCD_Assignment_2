# Indexing, querying and measured evaluation

## Extraction and cleaning

The six pinned FAST-NUCES PDFs total 194 physical pages. `corpus/fetch.py` checks URL content against committed SHA-256 and page counts before writing `_index.json`. PDF numbers below are physical pages, not printed footer numbers. The indexer clips to the visible crop so facing-page objects cannot leak into evidence; the pinned prospectus is read in its three-column order.

`extract.py` uses native text where readable, renders empty/short image pages at 280 DPI and invokes English Tesseract with a per-page timeout. The earlier verified run attempted OCR on 24 pages of the 2023 rules, all eight ORIC pages, five current-rules pages and four handbook pages. Some blank/decorative pages remain empty and are logged without renumbering pages. ORIC clause labels can be garbled; q08 therefore references its physical page. A failed engine or wholly unreadable document fails the Job visibly.

A real table example is the current academic rules, physical page 11, section 2.2. Plain extraction has adjacent words `A, A- Excellent`, without a reliable cell boundary. The table-aware representation is:

```text
| Grade | Interpretation |
| A+ | Outstanding |
| A, A- | Excellent |
| B+, B, B- | Good |
```

The column separator prevents the interpretation being assigned to the neighboring grade. Tests include a ruled PDF with Grade/Points cells and verify row/column order. Unruled tables and skewed OCR still require visual review.

Cleaning normalizes Unicode, removes soft hyphens/invisible whitespace, trims trailing spaces and repeated edge furniture, including changing page numbers. It deliberately preserves headings, numbered clauses, F/A punctuation, table rows and paragraph breaks. Markdown front matter becomes metadata rather than policy text.

## Chunking, embeddings and publication

The splitter uses sections, paragraphs/table rows, sentences and finally whitespace words within a physical page. Chunk size/overlap are measured in whitespace-delimited **words**, not model tokens. IDs hash source, version, page, ordinal and text. Required metadata is `source`, `section`, `page`, `doc_version`, and boolean `superseded`.

The chosen embedding pin is `nomic-embed-text`, 768 dimensions, from the shared ConfigMap. API and indexer use the same Ollama host. Batched `/api/embed` requests use at most 16 strings, no silent truncation, count/dimension/finite/nonzero validation. Chroma stores IDs, text, vectors and all metadata in a cosine collection. Each immutable snapshot also records model and dimension. Readiness checks them; retrieval rechecks the model so a direct request cannot silently query a newly published incompatible index.

[ADR 0006](adr/0006-immutable-index-publication.md) replaces the old two-rename publication gap. A successful build verifies the complete snapshot before a Redis transaction publishes its name and increments cache generation. Readers finish against their own immutable snapshot. Old snapshots remain for in-flight readers; monitor PVC capacity and drain before maintenance cleanup. Lost publication acknowledgement causes a visible failed Job and retains the potentially active snapshot.

## Three measured settings: released reference run

These are the **November 6 release measurements**, retained as prior evidence. The completion branch changes answer rendering and publication, so these rows must not be relabelled as a fresh run of this branch.

| Word size | Overlap | Chunks | Original words | Stored words | Word amplification | Recall@5 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 120 | 20 | 802 | 37,508 | 40,248 | 1.0731 | 100% |
| 240 | 35 | 690 | 37,508 | 38,383 | 1.0233 | 100% |
| 400 | 50 | 669 | 37,508 | 37,708 | 1.0053 | 100% |

All three used the same six PDFs, 15 golden questions, embedding/generation models, top-k 5 and heading-only filter. Recall@3 was 12/13. The current summer rule was below rank three. 400/50 tied on recall with the smallest vector count and duplication, so it remains the reference setting pending new measurements.

The handout asks for **token** amplification; word ratio alone is a proxy. `python -m eval.live_audit` now separately embeds all cleaned original pages and each chunk configuration, sums Ollama's actual `prompt_eval_count`, and records `stored_model_tokens / original_model_tokens`. This includes the embedding model's per-input token accounting. Missing usage is a failed measurement, not a made-up value. The workflow records model inventory/digests, commit, raw result rows and each configuration in `measurements.json` and three run JSON files.

## Cache thresholds and safety

Redis was chosen over a second Chroma collection to support TTL, atomic generation/pointer publication and bounded turn storage in the same persistent service; see ADR 0003. Semantic hits compare cosine similarity with the ConfigMap threshold. Keys also include model/provider/top-k/floor/temperature scope and a response-format version.

`eval/cache_cases.yaml` contains labelled paraphrases and hard negatives written before observing embedding scores: regular vs summer attendance, attendance vs condonable absence, degree minimum vs maximum, warning vs admission closure and old vs current policy. Historical questions bypass production cache regardless of their calibration similarity.

`python -m eval.calibrate_cache` embeds both questions, reports every score, and tests 0.85, 0.90 and 0.95. It chooses the **lowest tested threshold with zero false hits**, reports true-hit losses and records the negative pairs that disqualified lower thresholds. The first diagnostic audit tried a one-ULP boundary above the maximum negative similarity; that gives no practical numerical margin, so the rerun uses the coarse grid including the existing 0.95 setting. A conservative threshold may sacrifice most semantic hits; the experiment must state that tradeoff. If none of the tested settings avoids false hits, calibration fails and semantic reuse must be disabled pending further measurement.

The ConfigMap's old 0.95 remains a **reference value, not a newly calibrated claim** until the real-model report is reviewed. Copy the selected threshold from the real report into the ConfigMap, roll out API and retain the report. A cache threshold of 1.01 disables cache for retrieval/generation experiments and is not calibration evidence. Follow-ups, abstentions and invalid outputs are never cached. Tests reproduce previously missed pronoun follow-ups; absent session context produces an explicit request to restate the question.

## Generation and evaluation

The model receives the `Answer` JSON schema and temperature 0.2: low variance for policy facts/JSON, not a hallucination cure. Ollama's citation-item grammar enumerates only exact retrieved source/section/page objects; a model cannot substitute an OCR clause number for a metadata section label. Server-side membership validation remains mandatory. Invalid output is retried once, then safely declined; a false context flag always becomes a canonical nonfactual decline. The completion branch renders complete selected evidence verbatim with inline markers after sentences/table rows, avoiding model-invented wording and dropped qualifications. Explicit filename titles constrain document selection when those candidates are retrieved. See ADR 0005 for the deliberate usability tradeoff and remaining OCR/selection limits.

`eval/golden.yaml` contains eight ordinary, two version, two exact, two must-abstain and one injection question. It preceded live tuning in Git history. Recall@3/@5 matches distinct relevant references and is macro-averaged over answerable questions; per-type results are included. Citation validity is a micro percentage over exact triples. Abstentions require false context flag and no citations. Generation correctness still needs checking against the actual source, including qualifiers, completeness, question relevance and unsupported claims.

The released result is recall@3 12/13, recall@5 13/13, citations 23/23 and abstentions 2/2. Its terse q06/q08/q11/q15 answers were incomplete despite passing reference metrics. They are preserved in the old result rather than rewritten by hand. The new evidence renderer has regression tests for whole conditions, F/A, poisoned lines and inline citations, but fresh live results remain a separate required verification.

The evaluator fails if recall@5 drops over five percentage points, validity is below 95%, or any must-abstain probe is answered. A missing baseline is an immediate CLI error unless explicitly bootstrapping a reviewed baseline. Do not lower a baseline merely to obtain green CI.

## Reproduction and promotion

1. Follow README's real-corpus clean-clone deployment; use the same ConfigMap embedding pin and corpus checksums.
2. For an isolated measurement run, point `CHROMA_HOST/PORT`, `REDIS_HOST/PORT`, `OLLAMA_URL`, and `CORPUS_DIR` at real reachable services; set `RETRIEVER=chroma`, `LLM_PROVIDER=ollama-host`, `TOP_K=5` and `CACHE_THRESHOLD=1.01`.
3. Run `python -m eval.live_audit --out eval/runs/current`. The dedicated real audit workflow measures the three configurations in parallel isolated Docker jobs using `--configuration 120/20`, `240/35` and `400/50`; each saves its own provenance and token/cache report. The standalone default runs all three sequentially. Its environment is Docker, not a claimed Minikube run. The separate real Kubernetes evidence workflow deploys the actual corpus to Minikube with Calico and checks Ingress generation, isolation, recovery and visible rollback.
4. Review all 15 answer rows and qualification cases. Keep the two alternative configurations and raw token/cache measurements. Only then use `--publish` or copy the selected reviewed results/baseline into their shipped paths and update the table and calibrated ConfigMap threshold.
5. Redeploy the real cluster with normal cache enabled; run `make evidence` while indexing and `make rollout-demo` to capture fresh Kubernetes evidence.

`eval/fixtures/results.fixture.json` and `docs/evidence/faults/offline-current.json` are newly measured deterministic fixture evidence. They do not substitute for real-model calibration, token measurements or fresh Kubernetes rollout evidence. [SUBMISSION](SUBMISSION.md) states the outstanding external work explicitly.
