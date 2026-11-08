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

## Three measured settings: reviewed completion run

[Real audit run 42514806458](https://github.com/TahaSohail-Goat/SCD_Assignment_2/actions/runs/42514806458) passed all three configurations on source commit `f583517`. It completed on 9 November 2026 Pakistan time (8 November UTC). The corpus, pinned dependencies and actual model digests were identical across the isolated Docker jobs; see [comparison.json](../eval/runs/verified-f583517/comparison.json) and their individual reports. Original cleaned text contained 37,522 whitespace words; the denominator below is actual embedding-model tokens, not that word proxy.

| Word size | Overlap | Chunks | Original model tokens | Stored model tokens | Token amplification | Recall@5 | Required fact probes |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 120 | 20 | 802 | 51,512 | 56,251 | 1.091998 | 100% | 5/5 |
| 240 | 35 | 691 | 51,512 | 53,725 | 1.042961 | 100% | 5/5 |
| 400 | 50 | 669 | 51,512 | 52,720 | 1.023451 | 100% | 5/5 |

Every run measured recall@3 12/13, recall@5 13/13, citation validity 13/13 and both required abstentions. q10's current summer rule remains outside the first three retrieved references. 400/50 ties on recall and has the fewest vectors and least token expansion, so it remains selected. Larger excerpts can include irrelevant surrounding text and OCR furniture; this is a completeness/storage choice, not a claim that 400 words is universally best.

`python -m eval.live_audit` embeds all cleaned original pages and each chunk configuration, sums Ollama `/api/embed` `prompt_eval_count`, and records stored/original model tokens. Missing usage fails measurement. Full answer rows, actual model inventory/digests, API token logs and provenance are committed under [verified-f583517](../eval/runs/verified-f583517/). `eval/results.json` and `eval/baseline.json` now contain the reviewed 400/50 run and matching summary; the recall baseline remains 100%.

Earlier outcomes remain visible: [first-attempt-ad7239b](../eval/runs/first-attempt-ad7239b/) failed recall because a complete injection question was misrouted as a follow-up. [metadata-pass-1f15db9](../eval/runs/metadata-pass-1f15db9/) passed reference metrics but failed manual q04 review. Its unchanged answers fail the subsequently strengthened fact gate. November 6 word-count measurements remain historical in their original integration record.

## Cache thresholds and safety

Redis was chosen over a second Chroma collection to support TTL, atomic generation/pointer publication and bounded turn storage in the same persistent service; see ADR 0003. Semantic hits compare cosine similarity with the ConfigMap threshold. Keys also include model/provider/top-k/floor/temperature scope and a response-format version.

`eval/cache_cases.yaml` contains labelled paraphrases and hard negatives written before observing embedding scores: regular vs summer attendance, attendance vs condonable absence, degree minimum vs maximum, warning vs admission closure and old vs current policy. Historical questions bypass production cache regardless of their calibration similarity.

`python -m eval.calibrate_cache` embeds both questions, reports every score, and tests 0.85, 0.90 and 0.95. It chooses the **lowest tested threshold with zero false hits**, reports true-hit losses and records the negative pairs that disqualified lower thresholds. The first diagnostic audit tried a one-ULP boundary above the maximum negative similarity; that gives no practical numerical margin, so the rerun uses the coarse grid including the existing 0.95 setting. A conservative threshold may sacrifice most semantic hits; the experiment must state that tradeoff. If none of the tested settings avoids false hits, calibration fails and semantic reuse must be disabled pending further measurement.

The real [calibration report](../eval/runs/verified-f583517/400-50/cache-calibration.json) independently selects **0.95**, matching the existing ConfigMap; no threshold change was needed. Ten labelled pairs include four equivalent and six different-answer pairs. Results are below. This is calibration on this small set, not a held-out or universal false-hit guarantee. A cache threshold of 1.01 disables cache for retrieval/generation experiments and is not calibration evidence. Follow-ups, abstentions and invalid outputs are never cached. Tests reproduce previously missed pronoun follow-ups; absent session context produces an explicit request to restate the question.


| Threshold | False hits / 6 negatives | True hits / 4 paraphrases |
| ---: | ---: | ---: |
| 0.85 | 4/6 | 3/4 |
| 0.90 | 3/6 | 1/4 |
| 0.95 | 0/6 | 0/4 |

At 0.85, regular/summer attendance, minimum/maximum degree length, warning/closure and current/previous summer policy would be false hits. At 0.90, the latter three still fail. The chosen setting sacrifices all four tested paraphrase hits to avoid those different answers. Real repeated-question control is separate: during the live reindex test, 100 of 101 grounded answer probes were cache hits; the generation change forced one fresh answer. Historical requests bypass cache even when vectors are similar. Expand calibration when the model, corpus or query distribution changes.

## Generation and evaluation

The model receives the `Answer` JSON schema and temperature 0.2: low variance for policy facts/JSON, not a hallucination cure. Explicit filename titles constrain document selection when those candidates are retrieved. An explicitly requested clause takes priority in generation context. Otherwise a leading similarity margin of at least 0.10 uses the single standout passage to reduce distracting neighboring definitions; close matches retain all qualifying passages. This is a retrieval heuristic, not a probability of truth. The response still records the full retrieved top-k and logs the selected generation context separately.

Ollama's citation-item grammar enumerates only exact context source/section/page objects; a model cannot substitute an OCR clause number for a metadata section label. Server-side membership validation remains mandatory. Invalid output is retried once, then safely declined; a false context flag always becomes a canonical nonfactual decline. The server renders complete selected evidence verbatim with inline markers after sentences/table rows, avoiding model-invented wording and dropped qualifications. See ADR 0005 for the deliberate usability tradeoff and remaining OCR/selection limits.

`eval/golden.yaml` contains eight ordinary, two version, two exact, two must-abstain and one injection question. Its questions, evidence references and expected facts preceded live tuning in Git history. Recall@3/@5 matches distinct relevant references and is macro-averaged over answerable questions; per-type results are included. Citation validity is a micro percentage over exact triples. Abstentions require false context flag and no citations. After manual review caught q04's contact-hours answer passing those three metrics, five optional `required_answer_patterns` sets were added to encode the existing expected facts for q04/q06/q08/q11/q15. They strengthen the gate without changing questions, references or expected answers. All five must pass when present; fixtures without these fields retain the original three gates. These probes do not replace manual review of all 15 answers.

The November 6 reference result had valid citation ratios but incomplete qualification answers. Those historical records are preserved. The new reviewed answers retain the student handbook restriction, DOI/impact-factor/affiliation/two-year conditions, F/A consequence and 100% attendance with conditional HoD condonation. Manual review also corrected q04's credit-allocation/contact-hours confusion. All 15 selected answer rows were compared with the existing expected facts; the five automated probes supplement that review.

The evaluator fails if recall@5 drops over five percentage points, validity is below 95%, or any must-abstain probe is answered. A missing baseline is an immediate CLI error unless explicitly bootstrapping a reviewed baseline. Do not lower a baseline merely to obtain green CI.

## Reproduction and promotion

1. Follow README's real-corpus clean-clone deployment; use the same ConfigMap embedding pin and corpus checksums.
2. For an isolated measurement run, point `CHROMA_HOST/PORT`, `REDIS_HOST/PORT`, `OLLAMA_URL`, and `CORPUS_DIR` at real reachable services; set `RETRIEVER=chroma`, `LLM_PROVIDER=ollama-host`, `TOP_K=5` and `CACHE_THRESHOLD=1.01`.
3. Run `python -m eval.live_audit --out eval/runs/current`. The dedicated real audit workflow measures the three configurations in parallel isolated Docker jobs using `--configuration 120/20`, `240/35` and `400/50`; each saves its own provenance and token/cache report. The standalone default runs all three sequentially. Its environment is Docker, not a claimed Minikube run. The separate real Kubernetes evidence workflow deploys the actual corpus to Minikube with Calico and checks Ingress generation, isolation, recovery and visible rollback.
4. Review all 15 answer rows and qualification cases. Keep the two alternative configurations and raw token/cache measurements. Only then use `--publish` or copy the selected reviewed results/baseline into their shipped paths and update the table and calibrated ConfigMap threshold.
5. Redeploy the real cluster with normal cache enabled; run `make evidence` while indexing and `make rollout-demo` to capture fresh Kubernetes evidence.

`eval/fixtures/results.fixture.json` and `docs/evidence/faults/offline-current.json` are newly measured deterministic fixture evidence. They do not substitute for real-model calibration, token measurements or fresh Kubernetes rollout evidence. [SUBMISSION](SUBMISSION.md) states the outstanding external work explicitly.
