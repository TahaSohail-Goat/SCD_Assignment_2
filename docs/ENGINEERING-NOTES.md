# Engineering notes

## 1. Why not index during API startup?

The API has three replicas in `k8s/base/api.yaml:6`. If each startup extracted and wrote documents, all three would race on one Chroma volume and restarts would reindex. `k8s/base/indexer.yaml:2` makes indexing a separate Job and CronJob; `api/app/main.py:30` starts readers only. See ADR 0001.

## 2. What if readiness and liveness are swapped and Chroma stalls for 90 seconds?

With a Chroma-dependent liveness probe, Kubernetes would restart healthy API processes repeatedly during the stall. Here liveness uses `/healthz` at `k8s/base/api.yaml:46`, which touches no dependency, while readiness uses `/readyz` at line 49 and removes unready pods from Service endpoints. The API has a startup grace period and zero-unavailable rolling updates at line 9.

## 3. What does CPU HPA measure?

`k8s/base/hpa.yaml:8` uses API CPU utilization against its 200m request at `k8s/base/api.yaml:55`, scaling from three to eight replicas at 70%. That measures aggregate worker CPU, including token handling and serialization; it does not directly measure queued generation requests or host Ollama saturation. A production scale policy should also inspect request latency, in-flight requests, and Ollama queue depth.

## 4. Indexer peak memory and limit

The indexer limit is 2Gi and request is 512Mi in `k8s/base/indexer.yaml:40-42`. During the real 120/20 reindex, `kubectl top pod` samples every eight seconds reached 157Mi. This is the highest *observed sample*, not an exact peak; it is well below the 2Gi limit. Exceeding the limit causes an OOMKilled container (exit code 137) and a nonzero Job, not a quiet partial success.

## 5. Which question type has worst recall@5?

The three real-corpus settings tied at 100% recall@5 in every answerable type, so none has the worst recall@5. Version questions were weakest at recall@3: q10's current eight-week rule appeared at rank four or five. Section-title-only hits were ahead of the actual rule before the API filtered heading-only passages. The final `eval/results.json` retains the per-type breakdown.

## 6. What if API EMBED_MODEL changes alone?

`api/app/services/readiness.py:29-41` compares the configured model and expected dimension with collection metadata on every readiness call. The API logs a pin conflict at startup in `api/app/main.py:39-40`, and `/readyz` returns 503. The deployment remains unready instead of returning nonsense retrieval results. The indexer and API must share `k8s/base/configmap.yaml:8`.

## 7. Failure costing more than one hour

Environment setup on Windows: the WSL package was staged but the Windows optional feature was disabled, and the service repair needed the MSI at a D: path. This delayed Ubuntu/Minikube startup. The successful fix enabled `Microsoft-Windows-Subsystem-Linux`, repaired the already installed WSL MSI as administrator, restarted, and installed Ubuntu on D:. The remaining application work is independent of this setup failure.
