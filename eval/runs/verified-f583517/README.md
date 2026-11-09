# Reviewed real-model measurements

Source `f5835177565138f199da402abe93c87ee78b90dc`; [successful three-job run](https://github.com/TahaSohail-Goat/SCD_Assignment_2/actions/runs/42514806458), completed 9 November Pakistan time (8 November UTC). These are real PDFs, OCR, Chroma, Redis and Ollama in isolated Docker jobs, not Kubernetes or fixtures. Actual model inventory/digests are in each measurements report; comparison.json verifies identical models across configurations.

| Words/overlap | Chunks | Original tokens | Stored tokens | Amplification |
| --- | ---: | ---: | ---: | ---: |
| 120/20 | 802 | 51512 | 56251 | 1.091998 |
| 240/35 | 691 | 51512 | 53725 | 1.042961 |
| 400/50 | 669 | 51512 | 52720 | 1.023451 |

All configurations passed recall@3 12/13, recall@5 13/13, citation validity 13/13, abstentions 2/2 and five required-fact probes. Selected 400/50 minimizes vectors and token overhead at tied recall. Its saved 15 answers were reviewed against existing expected facts before copying to eval/results.json and baseline.json. Raw answers are retained unchanged, including OCR furniture and surrounding passage text.

Each folder retains measurements, API logs, cache calibration, resource samples and full answers. extraction.jsonl contains the six genuine extraction records from the 400/50 job. At cache thresholds 0.85/0.90/0.95 the false-hit counts are 4/6, 3/6, 0/6, and true-hit counts 3/4, 1/4, 0/4. Selected 0.95 favors avoiding different-answer reuse over semantic paraphrase coverage on this small labelled set.

Earlier failed and reference-only-passing runs remain in sibling folders. No baseline was lowered, no questions/references/expected facts changed, and five existing qualification expectations were subsequently made executable after manual review caught q04. See docs/PIPELINE.md and validation-provenance.json for scope and source-component identity.
