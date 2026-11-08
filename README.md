# RAHBAR: grounded university-policy answers on Kubernetes

![CI](https://github.com/TahaSohail-Goat/SCD_Assignment_2/actions/workflows/ci.yml/badge.svg?branch=dev)

RAHBAR retrieves public FAST-NUCES policy passages, selects evidence through a schema-constrained model, and displays complete cited policy text. It declines questions the corpus cannot answer. A separate indexer Job prepares the vector database; three FastAPI readers serve questions through an Ingress.

## Submission status

The November 6 released implementation has six checksum-verified PDFs (194 pages), 15 golden questions, recorded real-model results, protected-main review evidence, and successful CI/CD. This completion branch fixes the audit findings: follow-up safety, inline citations and complete evidence, immutable reindex publication, turn storage, controlled dependency errors, security for every workload, resource-limited CI fixtures, scoped egress, real health routing and repeatable deployment/evidence tools.

**Fresh real-model measurements and cluster demonstrations for this branch must be run and reviewed before calling it a final full-compliance release.** Existing `eval/results.json` and `eval/baseline.json` are the previous shipped measurements, not a claim that changed code was evaluated live. [Submission status](docs/SUBMISSION.md) tracks the exact remaining evidence. A grade cannot be guaranteed by a clean checker.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the data flow, StatefulSet/PVC rationale, immutable index publication and security boundaries. [ADR 0001](docs/adr/0001-indexer-as-job.md) explains why indexing never runs during API startup. [ADR 0005](docs/adr/0005-grounded-evidence-and-turns.md) explains the evidence-first answer format and backward-compatible session field.

## Clean-clone installation and local checks

Use Git, Python 3.12, Bash, make, Docker, kubectl and Minikube. On Windows the cluster recipe runs inside WSL2 with Docker Desktop integration. Install the host Ollama models on the stronger laptop. A copied Windows virtual environment cannot be reused inside WSL or after its base Python disappears; create a fresh one in the clean clone.

```bash
git clone https://github.com/TahaSohail-Goat/SCD_Assignment_2.git
cd SCD_Assignment_2
make install PY=python3.12
source .venv/bin/activate
make test
make lint
make check
```

For native Windows tests, create a Python 3.12 virtual environment, install `api/requirements-dev.txt` and `indexer/requirements-dev.txt`, and run:

```powershell
python -m pytest -q -c eval/pyproject.toml api/tests indexer/tests eval/tests
python -m ruff check api indexer eval corpus scripts
python scripts/check_submission.py
```

## Deploy the actual corpus and model

Start Ollama on the host, listening on the interface reachable from Minikube. Generation and embeddings both use that host; `llama3.2:3b` generates and `nomic-embed-text` embeds.

```bash
OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

In a second terminal:

```bash
ollama pull llama3.2:3b
ollama pull nomic-embed-text
source .venv/bin/activate
make deploy-real
```

`make deploy-real` performs the complete apply order: download and verify PDFs; start Minikube with Calico; enable ingress/metrics-server; build API/UI and a **local-only corpus-bearing indexer image**; load images; resolve the Ollama host to a single allowed IPv4 `/32`; create namespace; apply the prod objects; wait for initial indexing; and wait for API readiness. It writes the exact rendered deployment to ignored `output/deployment/prod.yaml`.

The default endpoint is `http://host.minikube.internal:11434`. If Windows Docker Desktop requires its other host name, use:

```bash
OLLAMA_URL=http://host.docker.internal:11434 make deploy-real
```

If name resolution inside the Minikube node is unavailable, supply `OLLAMA_IP` with the actual host IPv4 address reachable from that node. Do not replace it with unrestricted egress. The helper validates the `/32` and changes both the ConfigMap URL and NetworkPolicy. Corpus PDFs are never committed or pushed to public images.

On Windows/macOS Docker drivers, run `minikube tunnel` in another terminal. Then:

```bash
make ask INGRESS_IP=127.0.0.1 Q="Under the current undergraduate rules, how long is the summer semester?"
make ask INGRESS_IP=127.0.0.1 Q="How much is the refundable room-key deposit at the FAST Islamabad hostel?"
curl -fsS -H 'Host: rahbar.local' http://127.0.0.1/readyz
```

The first question should return the actual summer rule with inline citations; the second must decline. `/readyz` must return API JSON, not the UI's fallback HTML. On Linux use the Minikube IP instead of `127.0.0.1`. To inspect API directly, use `kubectl -n rahbar port-forward svc/api 8000:8000`.

`make index` creates a new Job from `cronjob/reindex` without redeploying readers. The Job writes a complete immutable snapshot and atomically changes the active pointer/cache generation. Do not delete old snapshots while readers might still use them.

## Quick infrastructure-only mode

`make dev` serves the local UI with stub retrieval/generation. `make cluster && make images && make apply` deploys the **dev stub** overlay. These commands are useful for plumbing checks but are not the real-corpus demonstration above. CD uses this repeatable mode for image delivery smoke testing; the separate CI fixture gate tests actual Chroma/Redis retrieval and the real audit workflow tests live Ollama.

## Corpus and evaluation

[CORPUS](docs/CORPUS.md) maps all seven required properties. [MANIFEST](corpus/MANIFEST.md) records six public URLs, versions, physical page counts and SHA-256 checksums. `python corpus/fetch.py --verify` checks downloaded files. Do not commit third-party PDFs in `corpus/raw/`.

[PIPELINE](docs/PIPELINE.md) documents extraction/OCR, tables, boundaries, token accounting, three chunk settings, cache calibration and evaluation limits. [FAILURE-ANALYSIS](docs/FAILURE-ANALYSIS.md) links controlled faults to symptoms and diagnostics.

```bash
make eval INGRESS_IP=127.0.0.1
# Calibrator connects only to loopback; forward the model service locally if needed.
make calibrate-cache
```

The evaluator rejects a recall@5 regression above five percentage points, citation validity below 95%, and any answered must-abstain question. A missing baseline is an error unless an explicit reviewed initial `--update-baseline` run is requested. Do not update a baseline merely to hide a failed gate.

`python -m eval.live_audit --out eval/runs/current` runs OCR and three chunk configurations against locally reachable real services, records embedding-model token amplification, evaluates all 15 questions and measures three cache thresholds against labels written before observing similarities. The dedicated GitHub workflow performs the same experiment on an isolated runner. It uploads artifacts and does not silently commit new numbers. Review outputs before promoting them.

## API

| Method | Endpoint | Contract |
| --- | --- | --- |
| POST | `/api/ask` | `{question, session_id?}`; question 3–500 trimmed characters. Grounded answer or safe decline. |
| GET | `/healthz` | Process liveness; no dependency checks. |
| GET | `/readyz` | Nonempty active Chroma snapshot, embedding pin and Redis; 503 with failed checks. |
| GET | `/metrics` | Prometheus request/retrieval/generation/cache/abstention/fallback/token metrics. |
| GET | `/api/version` | Revision embedded in the API image. |

A response includes `answer`, `citations`, `answered_from_context`, `confidence`, `retrieved`, `provider`, `cached`, and `request_id`. Internal reasoning is not returned. Every citation must match a retrieved source/section/page. Complete selected evidence is rendered with inline markers. Correlation comes from `X-Request-ID` or an automatically generated value.

The UI uses an opaque per-tab session ID. Redis retains question/response turn records for one hour and valid standalone cache entries for 24 hours. Unresolved/contextual follow-ups, abstentions and invalid outputs are never cached. No private documents or student identifiers belong in this service.

## Operations, evidence and secrets

```bash
make evidence
make rollout-demo INGRESS_IP=127.0.0.1
kubectl -n rahbar get pods,svc,ingress,hpa
kubectl -n rahbar top pods
```

Capture resource samples while the real indexer is active. `rollout_demo.sh` builds two visibly labelled UI images, performs `kubectl set image`, observes rollouts, executes `rollout undo`, verifies the old visible version and restores the original image. See [ENGINEERING-NOTES](docs/ENGINEERING-NOTES.md) for probe semantics, HPA limits, memory margins and troubleshooting.

Default local Ollama needs no hosted key. For a deliberately selected hosted adapter, create its Secret only from your environment:

```bash
kubectl -n rahbar create secret generic rahbar-secret \
  --from-literal=LLM_API_KEY="$LLM_API_KEY" --dry-run=client -o yaml | kubectl apply -f -
```

Also configure hosted model/base URL and a narrowly scoped HTTPS egress policy. The placeholder Secret is never included in Kustomize. No real secrets, `.env*`, kubeconfig or raw corpus files belong in Git.

## CI/CD and hand-in

CI on PRs and `dev` runs lint/type checks, API coverage ≥60%, all offline tests, strict manifest validation, three image builds, Trivy and the Kind fixture gate. The submission checker is required, not ignored. CD on `main` has `test → build-push → deploy` dependencies, publishes `sha-<full commit>` tags and smoke-tests their deployment through Ingress. `main` requires a PR, passing checks and one approval; never bypass that rule.

The [reviewed real audit](eval/runs/verified-f583517/) passed all three chunk settings (recall@5 and citation validity 100%, both abstentions, five fact probes). [Real Kubernetes evidence](docs/evidence/kubernetes-f583517/) verifies reindex availability samples, isolation, recovery and visible rollback. Follow-up [PR #12](https://github.com/TahaSohail-Goat/SCD_Assignment_2/pull/12) awaits peer review/merge; corrected deployment smoke passed CI, while final main CD remains pending.

The previous successful [CD run](https://github.com/TahaSohail-Goat/SCD_Assignment_2/actions/runs/42273870473) and [evaluation-gate demonstration](docs/evidence/eval-gate.md) remain historical evidence. They do not prove this unmerged completion branch. Record the new successful run and exact Docker Hub tag links in [SUBMISSION](docs/SUBMISSION.md) after this branch is reviewed and released.

[AI-USAGE](docs/AI-USAGE.md) attributes generated work and verification. [LICENSE](LICENSE) reserves third-party terms and permits academic assessment. Both teammates must understand the implementation and explain the evidence in a viva; automation cannot satisfy that personal requirement.