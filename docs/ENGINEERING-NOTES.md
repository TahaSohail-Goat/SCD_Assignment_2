# Engineering notes

## 1. Why not index during API startup?

The API has three replicas in `k8s/base/api.yaml:6`. If each startup extracted and wrote documents, all three would race on one Chroma volume and restarts would reindex. `k8s/base/indexer.yaml:2` makes indexing a separate Job and CronJob; `api/app/main.py:30` starts readers only. See ADR 0001.

## 2. What if readiness and liveness are swapped and Chroma stalls for 90 seconds?

With a Chroma-dependent liveness probe, Kubernetes would restart healthy API processes repeatedly during the stall. Here liveness uses `/healthz` at `k8s/base/api.yaml:46`, which touches no dependency, while readiness uses `/readyz` at line 49 and removes unready pods from Service endpoints. The API has a startup grace period and zero-unavailable rolling updates at line 9.

## 3. What does CPU HPA measure?

`k8s/base/hpa.yaml:8` uses API CPU utilization against its 200m request at `k8s/base/api.yaml:55`, scaling from three to eight replicas at 70%. That measures API worker CPU, including request processing and serialization; it does not measure host Ollama queueing or saturation. For generation-heavy traffic, a better scaling signal would be in-flight API requests or Ollama queue depth, with request/generation latency as a check. Instrument the chosen metric, expose it to Prometheus, and connect it to the HPA through a custom or external metrics adapter. This is a proposed improvement; the deployed HPA uses CPU.

## 4. Indexer peak memory and limit

The indexer limit is 2Gi (2048Mi) and request is 512Mi in `k8s/base/indexer.yaml:40-42`. During the real 120/20 reindex, `kubectl top pod` samples every eight seconds reached 157Mi. The observed margin to the limit was 1891Mi, about 92% of the limit. This is the highest *observed sample*, not an instrumented instantaneous peak; an eight-second interval can miss a spike. Exceeding the limit causes an OOMKilled container (exit code 137) and a failed Job, not a quiet partial success.

## 5. Which question type has worst recall@5?

The three real-corpus settings tied at 100% recall@5 in every answerable type, so none has the worst recall@5. Version questions were weakest at recall@3: q10's current eight-week rule appeared at rank four or five. Section-title-only hits were ahead of the actual rule before the API filtered heading-only passages. A next experiment would combine lexical and dense retrieval or rerank candidates, then compare recall@3 and answer completeness on the same golden set. That technique was not implemented in the reported run. The final `eval/results.json` retains the per-type breakdown.

## 6. What if API EMBED_MODEL changes alone?

`api/app/services/readiness.py:29-41` compares the configured model and expected dimension with collection metadata on every readiness call. The API logs a pin conflict at startup in `api/app/main.py:39-40`, and `/readyz` returns 503 for a mismatched pod. The deployment remains unready instead of returning nonsense retrieval results. The indexer and API must share `k8s/base/configmap.yaml:8`. In the [live Minikube demo](evidence/embedding-model-mismatch-2026-11-06.md), changing only the API Deployment from `nomic-embed-text` to `intentional-mismatch-demo` left the new pod at `0/1 Ready`; its log named both models. Removing the override restored 3/3 available and `/readyz` HTTP 200.

## 7. Failure costing more than one hour

Environment setup on Windows delayed Ubuntu/Minikube startup by more than an hour. `wsl --install --no-distribution` reported "The system cannot find the path specified," while `winget install Microsoft.WSL` reported that another version was already installed. These messages initially pointed us toward reinstalling the WSL package. The decisive diagnostic was `Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux`, which showed `State: Disabled`; `VirtualMachinePlatform` was enabled. The fix enabled the WSL feature, repaired the installed WSL MSI from the prepared D: path as administrator, restarted, and installed Ubuntu on D:. The package's presence alone did not mean the Windows feature and service were working.
