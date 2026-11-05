# Teammate handoff: indexer, corpus, and evaluation

## Why this division is balanced

Student A owns the FastAPI retrieval and generation path, Redis cache, validation, readiness, images, Kubernetes, CI/CD, deployment evidence, and integration. Student B owns the real document corpus, OCR and extraction, cleaning, chunking, embeddings, Chroma writes, fixture and real evaluation, measured tuning, and failure analysis. Both students should make their own substantive commits. Student B can write and test on a modest laptop without Docker, WSL, or a local LLM; Student A runs the cluster and Ollama and shares actual results for Student B to analyze.

## Start on the teammate laptop

Install Git and Python 3.12. Codex is optional for the commands but is part of this collaboration. Clone the repo, fetch `dev`, create your own branch, and install Python dependencies. In PowerShell:

```powershell
git clone https://github.com/TahaSohail-Goat/SCD_Assignment_2.git
cd SCD_Assignment_2
git fetch origin
git switch -c feat/indexer-eval origin/dev
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r indexer/requirements-dev.txt -r api/requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q indexer/tests
```

If `py -3.12` is unavailable, install Python 3.12 and use its full path. The teammate does not need Docker Desktop, Minikube, WSL, Ollama, or model downloads. Unit tests should stub Chroma and HTTP calls. Use a small fixture corpus and fake vectors locally. Student A will run full model and Kubernetes tests after your PR.

## Copy this prompt into Codex on your laptop

> You are implementing the indexer, corpus, and evaluation half of RAHBAR Assignment 02. First read the assignment PDF, `STARTER.md`, `README.md`, this handoff file, the code under `indexer/`, `corpus/`, `eval/`, the API schemas/retriever/cache, and any `AGENTS.md`. Inspect Git status and branch before editing. Work only on branch `feat/indexer-eval` based on current `origin/dev`; preserve Student A's API, Kubernetes, and CI/CD files unless a documented interface mismatch requires a small coordinated change. Do not ask to install Docker, WSL, Minikube, or Ollama on this modest laptop. Implement all starter TODOs in `indexer/` and `eval/` with meaningful offline tests. Pick a real corpus of at least six documents and 40 pages, including two policy versions, one scanned PDF, a table, long definitions, absent-topic coverage, and exact terms. Follow the starter fetch rate limit. Commit `corpus/sources.yaml` and `corpus/MANIFEST.md` with verified URLs and hashes; never commit `corpus/raw/` or copyrighted raw PDFs. Complete `docs/CORPUS.md`, `docs/PIPELINE.md`, and `docs/FAILURE-ANALYSIS.md` with methods and honest measured results. Add at least 15 golden questions before tuning. Implement extraction with OCR fallback, cleaning, structure-aware overlapping chunks, Ollama embeddings, and Chroma storage. Match the exact contract below. Run `ruff check`, `mypy`, unit tests, and `make check` when possible. Make small conventional commits with your own Git identity. Push only your feature branch; open a PR into `dev`, never push `main`. Do not commit `.env`, `.env.example`, credentials, kubeconfig, or model files. Report remaining integration tasks and the exact commands Student A must run. Do not invent evaluation scores or claim the real corpus was tested if it was not.

### Shared contract Codex must preserve

1. Chroma collection name is `CHROMA_COLLECTION` (default `rahbar`). Use cosine distance. Collection metadata must include string `embed_model` equal to `EMBED_MODEL` and integer `dimension` equal to vector length. API readiness checks both. Chunks need `source`, `section`, `page`, `doc_version`, `superseded` metadata. The API's normal queries exclude superseded chunks; historical queries may include them.
2. Embed using Ollama `POST ${OLLAMA_URL}/api/embed` with `model=${EMBED_MODEL}` and `input=[...]`. Default model is `nomic-embed-text`; the API uses the same endpoint. Batch within memory limits, validate dimensional consistency, and fail the Job on errors. No silent fake-vector fallback in production.
3. After successful full reindex, increment Redis key `rahbar:index_generation` once via `INCR`. Do not increment on partial failure. The API prefixes cache keys with the current generation. Keep old index available until the new collection can be switched safely; document the chosen strategy and any brief availability gap.
4. `indexer/Dockerfile` currently copies only `pipeline/`. Decide how real corpus files reach `/corpus` in production (image build context, init fetch, or volume). Do not assume `corpus/raw/` is in Git. Coordinate the chosen method with Student A, then update the Dockerfile/manifests only as needed.
5. Fixture evaluation must index `eval/fixtures/` and use its golden questions without external university downloads. `eval/run_eval.py` must compute recall@3/5, citation validity, abstention correctness, breakdown by type, and a nonzero regression gate. Commit baseline/results only after a real run and state the run conditions.

### Acceptance checklist for the teammate PR

- No `STARTER-TODO` or `NotImplementedError` remains in owned files.
- Offline tests cover scanned-page OCR fallback, section/page propagation, table preservation, overlap, stable IDs, superseded metadata, embedding dimensions, Redis invalidation, recall@5, citation validity, and gate failures.
- `ruff check indexer eval corpus` and `mypy pipeline` pass; `pytest -q indexer/tests` passes. No network is needed for unit tests.
- At least 15 committed real-corpus golden questions, source manifest, and substantive corpus/pipeline/failure documents.
- Evidence of 3 chunk configurations and their measured recall@5 and storage amplification, or an explicit note that Student A's cluster run is required to obtain those measurements.
- PR description lists commits, local test output, any API contract changes, and commands Student A must run to finish integration.

## Push and review steps

```powershell
git status --short
git add indexer corpus eval docs/CORPUS.md docs/PIPELINE.md docs/FAILURE-ANALYSIS.md
git diff --cached --name-only
git diff --cached --check
git commit -m "feat(indexer): implement extraction and chunking"
git push -u origin feat/indexer-eval
```

Repeat commits per logical area. If `git diff --cached --name-only` contains `.env`, `.env.example`, `corpus/raw/`, secrets, or a kubeconfig, remove those paths from the index before committing with `git restore --staged <path>`. Open a GitHub PR from `feat/indexer-eval` into `dev`, request Student A's review, fix CI feedback, then merge through the PR. If GitHub rejects the push because the teammate lacks WRITE access, the repository owner must invite them as a collaborator. Do not share credentials in chat.

After merge, Student A will fetch `dev`, rebuild the indexer image, run the real Job and evaluation on the stronger laptop, and send measured results for the teammate's documents. Both students review the final `dev` to `main` PR. Only the repository owner can enable protection if collaborator permissions remain WRITE.
