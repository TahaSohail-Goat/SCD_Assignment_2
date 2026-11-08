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

Reproduce with `scripts/verify_local.py`, strict Kustomize/kubeconform, and the
fixture test's documented output environment variables. These are not live-model
or cluster evidence. Real cache/token/tuning measurements and new cluster
rollout/undo captures must be added after actual execution.

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
