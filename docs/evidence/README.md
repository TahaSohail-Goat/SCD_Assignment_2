# Evidence index

## Current completion branch

- `local-validation.json`: actual local lint, type checks, separate test suites,
  API-only coverage and submission-checker output. Contains a source fingerprint
  and base commit; a dirty worktree is not represented as a released commit.
- `manifests/{prod,dev,ci}.json`: actual rendered-container security/resource and
  namespace contract results. Strict kubeconform also validated all three overlays
  without skipped schemas (26, 26 and 31 objects).
- `faults/offline-current.json`: four isolated fault observations and a healthy
  control, explicitly labelled as fixture doubles.
- `../../eval/fixtures/results.fixture.json`: fresh seven-question fixture results.

- `kubernetes-f583517/`: successful real Minikube/Calico run, 15 questions, concurrent reindex, persistence/recovery, negative network probe, visible update/undo and resource samples.
- `../../eval/runs/verified-f583517/`: successful real three-configuration model-token, cache and answer measurements.
- `ci-ingress-576d9a9/`: successful shared CI/CD readiness and revision smoke, using the deterministic integration stack.
- `validation-provenance.json`: exact audited source-component object hashes and workflow links.
- `faults/real-scan-ocr-disabled.json`: actual eight-page ORIC extraction failure with OCR deliberately disabled and linked real Tesseract control.

Reproduce with `scripts/verify_local.py`, strict Kustomize/kubeconform, and the
fixture test's documented output environment variables. Local checks and fixture reports are distinct from the separately retained real-model and real-cluster evidence above. Final main CD still awaits reviewed merge; see SUBMISSION.md.

## Historical November 5–6 release

`local-*.txt`, `local-ollama-smoke.md`, `real-corpus-integration-2026-11-06.md`,
`embedding-model-mismatch-2026-11-06.md`, `eval-gate.md` and its screenshots are
preserved with their original scope. Some early records use stubs or dummy
indexes. The real integration document reports a sampled 157Mi indexer maximum,
not a continuously measured instantaneous peak. Branch protection screenshots and
the deliberately failed/passed PR gate remain useful historical evidence.

Before the health-route correction, `/readyz` could reach UI HTML through the
Ingress catch-all. An old HTTP-200-only observation is therefore not independent
proof of API readiness. New evidence must include the JSON body/checks.

Never edit historical responses to make new code appear to have been tested.
Record a new run, its source commit, model inventory and exact environment.
