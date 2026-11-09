# Actual Kubernetes completion evidence

[Successful workflow](https://github.com/TahaSohail-Goat/SCD_Assignment_2/actions/runs/42514806549), source f583517, Minikube 1.37.0 / Kubernetes 1.33.0 with Calico and real PDFs/Ollama. summary.json is computed from these retained raw files.

All 15 Ingress questions passed: recall@5 13/13, citation validity 13/13, two abstentions and five fact probes. During real reindex, all 101 readiness and 101 grounded-answer samples succeeded; 100 answers were cached and one fresh after generation change. Redis pointer changed while the API Pod template stayed identical. These discrete probes do not prove every instant was available.

Before/after pod UIDs and readiness show API replacement and Chroma recovery with unchanged persisted 669 vectors / 768 dimensions. UI-to-Chroma service-IP access timed out under Calico; the UI wget binary and local UI positive control were verified. Network-policy manifests and events are retained.

rollout/ retains actual blue, green and undo-blue HTML and bounded version probes; each visible version appeared on attempt 3. The original UI image was restored. This demonstrates update/undo rather than merely a successful rollout status.

39 five-second indexer memory samples reached 170Mi. Against the 2048Mi limit, sampled margin is 1878Mi (91.7%). This is not an instantaneous memory peak. resources-after.txt records API 13?98m / 69?212Mi, Chroma 17m/52Mi and Redis 5m/4Mi; the newly restored UI had no final metrics sample.
