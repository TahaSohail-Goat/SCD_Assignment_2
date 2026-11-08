# Submission and evidence status

Updated 8 November 2026. The assignment requires repository Markdown documentation and seven hand-in links across four groups; it does not require a separate DOCX report.

## Release distinction

The prior public release is main commit `1818a03a23527e411865e4c6b25020d92eadfaf9`. Its successful [CD run](https://github.com/TahaSohail-Goat/SCD_Assignment_2/actions/runs/42273870473), [CI run](https://github.com/TahaSohail-Goat/SCD_Assignment_2/actions/runs/42272439538), real results and branch-protection/gate screenshots are historical evidence. The local `fix/assignment-completion` branch changes application and manifests. It must pass new CI, actual model measurements and cluster demonstrations before those old links can support a new release claim.

The GitHub connector returned HTTP 403 for branch/tree writes. GitHub CLI was then installed and authenticated interactively by the repository owner. The completion branch is pushed, with [PR #11](https://github.com/TahaSohail-Goat/SCD_Assignment_2/pull/11) now targeting protected `main` at the owner's request; their peer will review and merge. [Implementation CI](https://github.com/TahaSohail-Goat/SCD_Assignment_2/actions/runs/42508130233) and [documentation CI](https://github.com/TahaSohail-Goat/SCD_Assignment_2/actions/runs/42508420723) passed all six jobs. SonarCloud subsequently reported additional findings; fixes and the local transport review are recorded in `docs/SECURITY-REVIEW.md` and must pass a fresh analysis. The [real-corpus audit](https://github.com/TahaSohail-Goat/SCD_Assignment_2/actions/runs/42508098303) is running; it is not yet passing evidence. No token belongs in chat, repository files or Git history.

## Requirement/evidence ledger

| Item | Current state |
| --- | --- |
| Six real PDFs, 194 pages, checksums | Downloaded and independently verified in audit; raw PDFs stay ignored. |
| Full local tests, lint/type checks | Run on this branch; latest machine-readable local validation is captured separately. |
| Strict rendered Kubernetes schemas | Prod/dev/CI validated without skipped schemas. |
| Four isolated failures | Fresh bounded fixture outputs in `docs/evidence/faults/offline-current.json`; no live-model hallucination claims. |
| Fixture gate | Fresh seven-question outputs in `eval/fixtures/results.fixture.json`; deterministic doubles explicitly labelled. |
| Inline citation/complete evidence, follow-up safety, dependency fallback | Implemented with regression tests; real model pass still needed. |
| Three real chunk settings and token amplification | New live audit command/workflow implemented; run artifacts must be reviewed and retained. Prior table remains historical. |
| Three cache thresholds and measured false hits | Labelled cases/calibrator implemented; production threshold must come from the new real embedding report. |
| Hardened stateful data/fixture workloads | Explicit non-root, readonly root, capabilities, per-workload accounts/resources; new Kubernetes fixture CI passed. Real-corpus runtime evidence remains separate. |
| Scoped host egress and real clean-clone runbook | Deployment renderer/helper implemented; fresh Minikube run needed. |
| Visible image change/rollback and pod survival | Capture scripts ready; fresh real output must be collected. |
| Real indexing resource samples | Older sampled 157Mi retained; collect current raw samples while indexing. |
| New successful CD and Docker Hub tag links | Await reviewed merge to protected main and a successful new CD. |
| Both students understand implementation | Human responsibility; cannot be certified by generated documentation. |

## Required Classroom links

1. Repository: <https://github.com/TahaSohail-Goat/SCD_Assignment_2> (public).
2. A successful CD run **for the release actually submitted**; prior run is linked above.
3. API image page with exact `sha-<full commit>` tag.
4. Indexer image page with the same commit tag; published image must remain corpus-free.
5. UI image page with the same commit tag.
6. Committed `eval/results.json` for the selected reviewed real run.
7. Committed matching `eval/baseline.json`.

Docker Hub namespace is not hard-coded because the workflow takes it from GitHub Secrets and masks it in logs. Fill the three image links from the actual registry after publishing; do not invent them. The prior README reports a November 6 Classroom hand-in, but this completion workflow has not independently opened Classroom or changed that submission.

## Final release sequence

1. Finish real calibration/tuning run and review every saved response against original policy, especially q06/q08/q11/q15.
2. Commit reviewed real results/baseline, all three configuration outputs, model token counts, selected threshold and the filled measured table. Preserve provenance of old vs new runs.
3. Run the real clean-clone recipe and collect Ingress JSON, four failure outputs, negative UI→Chroma connectivity, pod recovery, resource samples and visible rollout/undo evidence.
4. Run the full local verifier and submission checker. All checks on PR #11 must be green, then the owner's peer supplies the real review and merges to protected `main`. The existing `dev` branch remains available for development; its push CI trigger remains enabled. Do not push directly to main, merge on the peer's behalf or forge their approval.
5. Wait for CD to test, publish SHA images, deploy and smoke. Record the successful run URL and three exact Docker Hub links, then use the matching results/baseline links in the one team hand-in.

Only the instructor awards marks. A passing checker cannot establish answer quality, genuine live execution, publication permissions or a student's viva understanding.
