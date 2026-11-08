# Failure analysis: four isolated stages

The current controlled run is saved in [offline-current.json](evidence/faults/offline-current.json), with healthy metrics in [the fixture result](../eval/fixtures/results.fixture.json). Reproduce it with:

```bash
RAHBAR_FAULT_RESULTS=docs/evidence/faults/offline-current.json \
RAHBAR_FIXTURE_RESULTS=eval/fixtures/results.fixture.json \
python -m pytest -q -c eval/pyproject.toml eval/tests/test_fixture_stack.py
```

The fixture runs the actual indexer, retriever, API, prompt assembly, validators and evaluator, with deterministic Chroma/Redis/Ollama doubles. Each fault is isolated with a restored control before the next. This is explicitly bounded integration evidence, not a claim of real-model hallucination experiments. The healthy seven-question control measured 100% recall@3/@5, six valid citations and one correct abstention.

| Stage | Deliberate fault and observed symptom | Diagnosis without prior knowledge | Remedy and confirming signal |
| --- | --- | --- | --- |
| A: extraction | An actual synthetic raster PDF is readable with the deterministic OCR control. Disabling OCR leaves no native text and raises `image-only-policy.pdf: no readable text in document`. The exact error/control text is saved. | Inspect per-source `ocr_pages`, `empty_pages`, extraction errors and the rendered page. Zero native characters in the real eight-page ORIC PDF were independently verified during the audit. Do not start by increasing temperature. | Enable Tesseract and retain the page-numbered text; compare the physical source to OCR. The real ORIC control still requires the live run; the fixture does not pretend its OCR double is Tesseract. |
| C: retrieval/pin | Change only API settings from `fixture-hash` to `wrong`. `/readyz` returns 503 and names both models in `embedding_pin`; saved JSON contains the exact response. | Check readiness body and startup conflict log, ConfigMap values and active collection metadata. A dimension/model mismatch corrupts similarity even when the database responds. | Restore the shared pin and rerun readiness. The existing real Minikube mismatch capture remains additional historical proof; the completion branch must be re-demonstrated after deployment. |
| E: source version | Remove only the superseded filter for the ordinary attendance question. Three references from `academic-rules-2023.md` enter the returned context; the healthy ordinary response has none. | Inspect source/version metadata, the returned filenames and version-sensitive recall. The retriever can faithfully retrieve a policy from the wrong year. | Restore `superseded:false` for current questions and explicit historical selection/cache bypass. Verify no stale references on the ordinary probe and retain the old edition for the explicit 2023 probe. |
| D: prompt | Remove the untrusted-evidence system instruction while keeping indexed poisoned evidence. The deterministic provider rejects both attempts and the API returns its safe `could not verify` fallback. Exact response is saved. | Check provider validation/fallback counters, generation logs, prompt boundaries and whether the poisoned text reached evidence. This controlled double demonstrates assembly/fallback behavior, not a measured real-model claim about obedience. | Restore system boundaries and schema. Healthy fixture answer contains the 80% rule and does not repeat the attack. Run the real q15 again before promoting the new result. |

Only four of six stages are required. A fixed 100-word/no-overlap experiment (B) and temperature 1.2 (F) are not claimed as completed. Do not treat the presence of six stage names as six experiments.

## Publication failure and dependency outages

The earlier two-rename publication could expose a missing collection to an in-flight query. The completion changes use immutable snapshots and a Redis pointer/generation transaction. Storage tests prove failed pre-publication batches keep the previous snapshot active, successful reindexing leaves previous readers' snapshot queryable, and a lost transaction acknowledgement never deletes a possibly active snapshot. A failed Job must be diagnosed through its logs and pointer state, not by deleting Chroma data.

Embedding and retrieval failures previously escaped as HTTP 500. Regression probes now raise each dependency error separately and require a safe decline without invoking generation. Cache-hit logs now include top-k, evidence IDs/scores, context flag and cache state, so operational visibility is retained on hits as well as fresh answers.

## Limits of these findings

Source data, OCR and evidence selection still matter. Rendering a real retrieved passage cannot prove that passage answers the intended question, and reference-valid citations do not prove every condition has been recovered. The previous live incomplete q06/q08/q11/q15 cases remain in the historical result for transparency. Fresh real-model evidence and concurrent cluster queries during reindexing belong in the new run artifacts; they must not be inferred from the fixture.