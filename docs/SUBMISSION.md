# Submission and evidence status

Updated 9 November 2026 (Pakistan time). The PDF requires repository Markdown documentation and seven hand-in links; no separate DOCX report is required.

## Reviewed implementation and release status

[PR #11](https://github.com/TahaSohail-Goat/SCD_Assignment_2/pull/11) was peer-approved and squash-merged as `98ff1c5860823d378d470d7794dcf89089a86fb8`. Its [CD run](https://github.com/TahaSohail-Goat/SCD_Assignment_2/actions/runs/42514102089) published images but failed the deployment smoke: UI HTTP 200 preceded API readiness. This is a failed release check, not successful CD evidence.

Follow-up [PR #12](https://github.com/TahaSohail-Goat/SCD_Assignment_2/pull/12) fixes answer-quality and deployment checks and retains reviewed real evidence. Its peer must review and merge. The corrected shared Ingress smoke already passed in [CI](https://github.com/TahaSohail-Goat/SCD_Assignment_2/actions/runs/42515793120); actual corrected main CD can run only after that merge. The agent has not merged or supplied peer approval.

## Requirement/evidence ledger

| Requirement | Verified result and evidence |
| --- | --- |
| Corpus and required properties | Six hash-verified PDFs, 194 physical pages; seven properties mapped in CORPUS. PDFs remain ignored. |
| Separate processes and safe publication | API readers and Job/CronJob writer; immutable Chroma snapshots with atomic Redis publication. |
| Three real chunk settings | [Reviewed reports](../eval/runs/verified-f583517/): 802/691/669 chunks; actual model-token amplification 1.091998/1.042961/1.023451. Selected 400/50. |
| Fifteen real questions | All three settings: recall@5 13/13, citation validity 13/13, abstentions 2/2, added qualification probes 5/5. Recall@3 12/13. All saved selected answers reviewed against existing expectations. |
| Three cache thresholds | 0.85/0.90/0.95 measured on 10 labelled pairs. Selected 0.95: 0/6 false hits, but 0/4 paraphrase hits. Finite calibration, no universal guarantee. |
| Four isolated failures | [Fixture faults](evidence/faults/offline-current.json), plus [actual ORIC OCR-disabled extraction](evidence/faults/real-scan-ocr-disabled.json). Scope and controls in FAILURE-ANALYSIS. |
| Live Kubernetes | [Successful real run](https://github.com/TahaSohail-Goat/SCD_Assignment_2/actions/runs/42514806549), [raw evidence](evidence/kubernetes-f583517/): 15 Ingress questions; 101/101 readiness and grounded-answer samples during reindex; pointer changed without API template changes; API/Chroma pod replacement and persistent count checked. |
| Isolation and visible rollback | Calico UI-to-Chroma denial with positive controls; blue-to-green-to-undo-blue HTML verified; original image restored. |
| Indexer resources | 39 five-second samples; maximum 170Mi against 2048Mi limit. Sampled margin 1878Mi; not an instantaneous peak. |
| Local checks and schemas | [Machine-readable verifier](evidence/local-validation.json); API coverage exceeds required 60%; prod/dev/CI strict schemas and security/resource contracts. |
| CI and code analysis | Six CI jobs and Sonar passed on the implementation; final documentation/evidence commit must also pass its PR checks. |
| New successful CD and exact image links | Pending peer merge of PR #12 and successful main CD. Do not substitute a failed deployment run. |
| Student understanding and hand-in | Both students must review and explain the work; Classroom submission is a human step. |

## Seven Classroom links

1. [Public repository](https://github.com/TahaSohail-Goat/SCD_Assignment_2).
2. Successful CD run for the final submitted release, after PR #12 is merged.
3. API Docker Hub page with that release's exact `sha-<full commit>` tag.
4. Indexer Docker Hub page with the same tag; image remains corpus-free.
5. UI Docker Hub page with the same tag.
6. [Reviewed results on the completion branch](https://github.com/TahaSohail-Goat/SCD_Assignment_2/blob/fix/assignment-completion/eval/results.json), using the main/permalink version after merge.
7. [Matching baseline on the completion branch](https://github.com/TahaSohail-Goat/SCD_Assignment_2/blob/fix/assignment-completion/eval/baseline.json), using the same submitted revision.

CD's `release-image-links` artifact records the three actual public Docker Hub tag URLs and full release commit, without registry credentials. Copy links from the successful final run. The historical [November 6 successful CD](https://github.com/TahaSohail-Goat/SCD_Assignment_2/actions/runs/42273870473) demonstrates that older release only. Classroom has not been opened or altered by this completion work.

## Final peer handoff

After all current PR checks pass, the peer reviews and merges PR #12 into protected main. Then verify all CD stages including Ingress smoke, collect the successful run and exact published image links, and submit the seven matching links. Keep one real approval and passing checks; do not push directly to main or weaken protection. Only the instructor awards marks, and automation cannot certify a student's viva understanding.
