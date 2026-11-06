# Evaluation gate evidence

[Demo PR #7](https://github.com/TahaSohail-Goat/SCD_Assignment_2/pull/7) targeted protected main from a separate evidence branch. Commit 2c2dcc5 replaced the f01 source with missing-policy.md while keeping the fixture documents, question, and baseline intact.

- [Failing CI run](https://github.com/TahaSohail-Goat/SCD_Assignment_2/actions/runs/42259592376). Fixture indexing and API readiness passed. The e2e-eval job then failed at Enforce the fixture baseline because recall@5 fell from 100% to 83.3% (5 of 6 answerable questions). The offline fixture assertion also failed in quality. See [blocked merge](eval-gate-pr7-blocked.png) and the [failed evaluation log](eval-gate-pr7-failure-log.png).
- [Passing CI run](https://github.com/TahaSohail-Goat/SCD_Assignment_2/actions/runs/42260457866). Commit 8dd8e56 restored the fixture byte-for-byte to the dev version. All six checks passed. The [passing PR screenshot](eval-gate-pr7-green.png) shows that an approving review was still required.

The demo PR was closed unmerged. See the existing main rule's [required approval](main-protection-approval.png) and [six required checks](main-protection-checks.png). GitHub reports that administrator enforcement is enabled.
