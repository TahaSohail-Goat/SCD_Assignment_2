# Engineering notes

## 1. Why not index during API startup?

The API has three replicas in `k8s/base/api.yaml`. If each startup extracted and wrote documents, all three would race on one Chroma volume and restarts would reindex. `k8s/base/indexer.yaml` makes indexing a separate Job and CronJob; `api/app/main.py` starts readers only. See ADR 0001.

## 2. What if readiness and liveness are swapped and Chroma stalls for 90 seconds?

With a Chroma-dependent liveness probe, Kubernetes would restart healthy API processes repeatedly during the stall. Here liveness uses `/healthz`, which touches no dependency, while readiness uses `/readyz` and removes unready pods from Service endpoints. The API has a startup grace period and zero-unavailable rolling updates in `k8s/base/api.yaml`.

## 3. What does CPU HPA measure?

`k8s/base/hpa.yaml` uses API CPU utilization against its 200m request, scaling from three to eight replicas at 70%. That measures aggregate worker CPU, including token handling and serialization; it does not directly measure queued generation requests or host Ollama saturation. A production scale policy should also inspect request latency, in-flight requests, and Ollama queue depth.

## 4. Indexer peak memory and limit

The indexer limit is 2Gi and request is 512Mi in `k8s/base/indexer.yaml`. Peak real-corpus memory is **not measured yet** because the teammate's OCR pipeline and corpus are pending. During integration, record `kubectl top pod -n rahbar` and compare peak to 2Gi. Exceeding the limit causes an OOMKilled container and a nonzero Job, not a quiet partial success.

## 5. Which question type has worst recall@5?

Unknown until the teammate implements `eval/run_eval.py` and runs the real golden set. `docs/PIPELINE.md` will hold the measured breakdown. Exact terms and tables are expected risks, but this is a hypothesis rather than a reported result.

## 6. What if API EMBED_MODEL changes alone?

`api/app/services/readiness.py` compares the configured model and expected dimension with collection metadata on every readiness call. The API logs a pin conflict at startup in `api/app/main.py`, and `/readyz` returns 503. The deployment remains unready instead of returning nonsense retrieval results. The indexer and API must share the same ConfigMap key.

## 7. Failure costing more than one hour

Environment setup on Windows: the WSL package was staged but the Windows optional feature was disabled, and the service repair needed the MSI at a D: path. This delayed Ubuntu/Minikube startup. The successful fix enabled `Microsoft-Windows-Subsystem-Linux`, repaired the already installed WSL MSI as administrator, restarted, and installed Ubuntu on D:. The remaining application work is independent of this setup failure.
