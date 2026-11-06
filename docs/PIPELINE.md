# Indexing and evaluation

## Extraction and cleaning

The indexer reads the verified `corpus/raw/_index.json` snapshot or a folder of Markdown/text fixtures. It keeps one-based physical PDF page numbers. pdfplumber clips each PDF to its visible crop box to avoid mixing facing pages in the 2026 handbooks. The pinned prospectus uses three columns, which are read in visual order. Ruled tables become pipe-delimited rows in their original position. For example, the academic-rules grade table on physical page 11 changes `A, A- Excellent` in plain extraction into `| A, A- | Excellent |`, with the surrounding grade and interpretation columns preserved. Unruled tables and unusually spaced type can still require inspection.

When native text is empty, or short and accompanied by page images, pdfplumber renders that page at 280 DPI using its PDFium backend. pytesseract runs English Tesseract on the rendered image with a per-page timeout. A file or engine failure names the document and page and fails the Job. A document must have readable text after cleaning. Empty individual pages are logged, preserving their physical position. The local real-corpus extraction attempted OCR on 24 pages of the older rules, eight ORIC pages, five academic-rules pages, and four student-handbook pages. The older rules left physical page 3 empty, the current rules left pages 2, 56, and 57 empty, and the student handbook left pages 2 and 63 empty. The ORIC text was recovered on all eight pages, but skew and layout can garble standalone clause numbers. Q08 therefore uses a physical-page reference.

Cleaning normalizes Unicode and invisible whitespace, trims trailing spaces, and strips recurring first and last lines across pages, including repeated edition footers with changing page numbers. It preserves line structure, clause labels, significant punctuation in terms such as F/A, and table rows. Markdown front matter is consumed as metadata. PDF filenames are the stable source names used by the API and golden set.

For real OCR on Windows, use the UB Mannheim 64-bit installer linked by Tesseract's documentation, include English language data, and put the installation directory on `PATH`. Open a fresh PowerShell terminal and check `tesseract --version` and `tesseract --list-langs` for `eng`. The bundled Python dependencies supply PDFium. The Dockerfile already installs Tesseract on Linux, and the Job and CronJob mount a bounded writable `/tmp` for OCR. [Tesseract Windows installation steps](https://tesseract-ocr.github.io/tessdoc/Installation.html)

## Chunks, embeddings and storage

Each chunk stays within a physical page and a detected section. Markdown headings own their numbered body text, and PDF numbered clauses become section labels. When a section exceeds its budget, the splitter prefers paragraph or table-row boundaries, then sentence boundaries, then a whitespace-word boundary. Overlap applies to adjacent windows in that section. IDs hash source name, document version, physical page, page-local ordinal and text. Chunk metadata is `source`, `section`, `page`, `doc_version`, and boolean `superseded`.

The shared ConfigMap pins `nomic-embed-text` at 768 dimensions. The Job sends at most 16 strings per Ollama `/api/embed` request, disables truncation, and checks count, dimension, and finite nonzero vectors before any write. Chroma stores text, IDs, metadata, and cosine vectors. Its collection metadata records string `embed_model` and integer `dimension`, which the API checks before serving. Normal retrieval excludes the older rules. Explicit historical questions can include them and get a year preference. Historical requests bypass semantic caching to keep editions separate.

A full reindex builds an isolated staging collection and verifies its row count before changing the API's configured collection name. The indexer holds a Redis publication lock while it renames the previous collection to a backup and promotes staging. There is a short interval between those two Chroma calls in which an uncached query can see the collection missing. During a failed build the existing collection remains active. An ordinary promotion failure attempts to restore the backup. If a pod dies during promotion, the previous complete rows remain under a `rahbar-backup-*` name. Check that no writer is running before inspecting or restoring a backup. After successful publication, the Job issues `INCR rahbar:index_generation`, then removes the backup. If Redis fails after Chroma promotion, the Job fails and keeps the full live index and its backup. Retry the Job before treating the cache as refreshed. A lost Redis acknowledgement can make the increment outcome uncertain. An in-flight API request keeps its original cache generation so it cannot populate the new cache with old evidence.

## Chunk setting measurements

Word counts use whitespace-delimited words after cleaning. Amplification is stored words divided by original words and describes text duplication. Vector count is the chunk count. Local extraction and chunking used all six verified publications. Real-model recall requires the stronger laptop.

| Chunk size | Overlap | Chunks | Original words | Stored words | Amplification | Real recall@5 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 120 | 20 | 802 | 37,508 | 40,248 | 1.0731× | 100% |
| 240 | 35 | 690 | 37,508 | 38,383 | 1.0233× | 100% |
| 400 | 50 | 669 | 37,508 | 37,708 | 1.0053× | 100% |

The live comparison used the six verified PDFs, `nomic-embed-text`, `llama3.2:3b`, top-k 5, and the same 15 golden questions for each setting. All three scored 100% recall@5 in every answerable question type, 100% citation-reference validity, and 2/2 correct abstentions. Recall@3 was 12/13 for each; the current summer-semester rule appeared at rank four or five. We chose `400/50` because it tied on measured recall with the fewest vectors and least duplication. The table uses the real Job's chunk log, which differs slightly from the earlier local planning count. The API's heading-only filtering was held constant across these live runs. Repeat the local storage calculation with:

```powershell
$env:PYTHONPATH = 'indexer'
$env:CORPUS_DIR = 'corpus/raw'
.\.venv\Scripts\python.exe -m pipeline.run --plan 120:20 240:35 400:50
```

## Evaluation and gate

Each golden reference names a source and optionally an exact section, physical page, or chunk ID. Recall measures the fraction of distinct references found in the first three or five results and macro-averages across questions with relevant evidence. Citation validity requires exact source, section and page triples and counts a grounded answer with no citation as a failure. Every abstention probe must be declined with no citations. The gate rejects a recall@5 drop above five percentage points, validity below 95%, or any failed required abstention. Expected answers in the real golden set support manual grounding review, especially for q09/q10 and q15.

The seven-question fixture test indexed the three checked-in Markdown files through the real stage runner and sent requests through FastAPI, with mocked Ollama, Chroma, Redis and HTTP. It measured 100% recall@3 and recall@5, six valid citations out of six, and one correct abstention out of one. The fixture checks both policy editions and confirms a planted instruction reached the prompt while the response retained the attendance rule. `eval/fixtures/baseline.fixture.json` records these fixture measurements. The CI Kind job uses the same fixture and model double with real Chroma and Redis. The offline and Kind gates measure deterministic fixture behavior. The live results and baseline are in `eval/results.json` and `eval/baseline.json`. A cache threshold above 1 was used for evaluation to force fresh retrieval.

The gate validates citation *references*, not whether every phrase of an answer is complete or supported. Manual review of the saved `llama3.2:3b` output found omitted qualifications: q06 said only “No” without explaining that AI can assist preparatory research but cannot be the sole source; q08 omitted the online DOI and NUCES affiliation conditions; q11 omitted the F/A grade; and q15 omitted the HoD's possible 20% condonement. These are answer-quality limits despite passing recall and citation gates. The q13/q14 abstentions gave no citations. Do not treat a valid citation triple as proof of full semantic grounding.

## Stronger-laptop handoff

Run from the repository root in Bash on the stronger laptop. In a separate terminal, serve the two models using the host interface. If Ollama is already listening on the correct interface, reuse that process.

```bash
OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

```bash
ollama pull llama3.2:3b
ollama pull nomic-embed-text
make install PY=python3.12
source .venv/bin/activate
python corpus/fetch.py
python corpus/fetch.py --verify
make cluster
docker build -t rahbar-api:dev api
docker build -t rahbar-ui:dev ui
docker build -t rahbar-indexer:corpus-base indexer
docker build -t rahbar-indexer:dev -f - corpus/raw <<'DOCKERFILE'
FROM rahbar-indexer:corpus-base
COPY --chown=10001:10001 *.pdf _index.json /corpus/
DOCKERFILE
for image in rahbar-api:dev rahbar-ui:dev rahbar-indexer:dev; do
  minikube image load --overwrite=true "$image"
done
```

The derived indexer image stays in the local Docker/Minikube stores. Both Job templates use it. The published base image is corpus-free. For the experiment, suspend the scheduled Job and bypass the semantic cache. The following Bash commands target the local Minikube context explicitly. Set `INDEX_OLLAMA_URL` to the address reachable from Minikube if it differs.

```bash
set -euo pipefail
mkdir -p /tmp/rahbar-corpus-eval
export INDEX_OLLAMA_URL=http://host.docker.internal:11434
kubectl --context=minikube delete job initial-index -n rahbar --ignore-not-found
kubectl --context=minikube kustomize k8s/overlays/prod | python -c '
import os, sys, yaml
docs = list(yaml.safe_load_all(sys.stdin))
for doc in docs:
    if doc["kind"] == "ConfigMap" and doc["metadata"]["name"] == "rahbar-config":
        doc["data"].update(OLLAMA_URL=os.environ["INDEX_OLLAMA_URL"],
                           CACHE_THRESHOLD="1.01", TOP_K="5",
                           CHUNK_SIZE="400", CHUNK_OVERLAP="50")
    if doc["kind"] == "CronJob" and doc["metadata"]["name"] == "reindex":
        doc["spec"]["suspend"] = True
yaml.safe_dump_all(docs, sys.stdout, sort_keys=False)
' | kubectl --context=minikube apply -f -
kubectl --context=minikube -n rahbar rollout restart deployment/api
kubectl --context=minikube -n rahbar wait --for=condition=complete job/initial-index --timeout=1200s
kubectl --context=minikube -n rahbar rollout status deployment/api --timeout=300s
kubectl --context=minikube -n rahbar logs job/initial-index > /tmp/rahbar-corpus-eval/400-50.jsonl
kubectl --context=minikube -n rahbar top pods | tee /tmp/rahbar-corpus-eval/pods.txt
kubectl --context=minikube -n rahbar port-forward svc/api 18000:8000
```

Leave the port forward open. In a second Bash terminal, keep `TOP_K`, the models, and the golden set fixed, and use the runner to save real results for each configuration. A failed gate still writes its JSON. Keep those files for diagnosis.

```bash
set -euo pipefail
source .venv/bin/activate
out=/tmp/rahbar-corpus-eval
api=http://127.0.0.1:18000
python eval/run_eval.py --api "$api" --baseline "$out/unset-baseline.json" --out "$out/400-50.json" ||
  test -s "$out/400-50.json"

for pair in 120:20 240:35; do
  size=${pair%:*}
  overlap=${pair#*:}
  run="$size-$overlap"
  kubectl --context=minikube -n rahbar patch configmap rahbar-config --type=merge \
    -p "{\"data\":{\"CHUNK_SIZE\":\"$size\",\"CHUNK_OVERLAP\":\"$overlap\"}}"
  job="tune-$run-$(date +%s)"
  kubectl --context=minikube -n rahbar create job --from=cronjob/reindex "$job"
  kubectl --context=minikube -n rahbar wait --for=condition=complete "job/$job" --timeout=1200s
  kubectl --context=minikube -n rahbar logs "job/$job" > "$out/$run.jsonl"
  python eval/run_eval.py --api "$api" --baseline "$out/unset-baseline.json" --out "$out/$run.json" ||
    test -s "$out/$run.json"
done

python - <<'PY'
import json
from pathlib import Path
root = Path("/tmp/rahbar-corpus-eval")
for run in ("120-20", "240-35", "400-50"):
    result = json.loads((root / f"{run}.json").read_text())
    logs = (root / f"{run}.jsonl").read_text().splitlines()
    chunk = next(row for line in logs if line.startswith("{")
                 if (row := json.loads(line)).get("msg") == "chunked")
    print(run, result["recall@5"], chunk["amplification"], chunk["chunks"])
PY
```

After choosing a setting, patch it into the shared ConfigMap and run one more Job from `cronjob/reindex` as above. Review every real expected answer and the failed gates. On the chosen, healthy live index run:

```bash
python eval/run_eval.py --api http://127.0.0.1:18000 --update-baseline
```

The 2026-11-06 live run followed these steps and selected 400/50. For a later rerun, restore the normal cache threshold in the deployed ConfigMap, restart the API, and resume the CronJob with `kubectl --context=minikube -n rahbar patch cronjob reindex --type=merge -p '{"spec":{"suspend":false}}'`. Collect the real Job's memory usage during indexing in another terminal with `kubectl --context=minikube -n rahbar top pods -l app=indexer`.
