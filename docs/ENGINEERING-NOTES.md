# Engineering notes: seven questions

Line references below were checked against the completion branch on 9 November 2026 (Pakistan time). Historical measurements are labelled; a successful static/test run is not a substitute for a real cluster sample.

## 1. Three API replicas, one Chroma volume: why not index at startup?

`k8s/base/api.yaml:6` requests three API replicas. Putting extraction/embedding/writes in `api/app/main.py:31` would repeat indexing three times during startup and again on every restart or scale-up. The failure is competing index writers, startup delays and readiness that either serves an incomplete index or never completes a rollout. `k8s/base/indexer.yaml:2` makes the writer a separate finite Job; its CronJob template supports manual reindexing without deploying API. `indexer/pipeline/store.py:79` publishes only a complete immutable snapshot through Redis. API only initializes readers and checks dependencies. ADR 0001 and ADR 0006 explain the separation/publication details.

## 2. What happens if readiness and liveness are swapped during a 90-second Chroma stall?

Liveness at `k8s/base/api.yaml:50` calls dependency-free `/healthz`. Readiness at line 53 calls `/readyz`; failing readiness removes a pod from endpoints without killing its healthy process. If these were swapped, the dependency stall would repeatedly fail liveness and restart the three API processes while the false health-only readiness still admits traffic. Startup at line 46 grants boot grace but does not repair the wrong liveness dependency. Correct probes contain the fault to dependency unavailability instead of turning it into a restart storm.

## 3. What does the CPU HPA measure while Ollama generates?

`k8s/base/hpa.yaml:13` targets 70% of the API's 200m CPU request (`api.yaml:59`), approximately 140m usage per replica. The pod mostly waits for HTTP generation on the host, so low API CPU is not evidence of spare model capacity. The HPA measures worker CPU for request handling, token/JSON processing and serialization; adding API pods does not multiply the host's generation throughput.

A better signal is in-flight generation requests or backend queue depth, with p95 generation/request latency as a check. To use it, add a trustworthy queue/in-flight gauge, scrape it with Prometheus, expose it through a custom/external metrics adapter, and change the autoscaling/v2 target. The current deployment uses CPU; no queue-based scaler is claimed. The earlier HPA capture shows a numeric 3–4% rather than `<unknown>`, and the startup recipe enables metrics-server.

## 4. Indexer memory: limit, margin, and failure exit

`k8s/base/indexer.yaml:47–48` sets a 512Mi request and 2Gi (2048Mi) limit; the CronJob uses the same values at lines 101–102. The new real run recorded 39 five-second samples with maximum **170Mi**. Sampled margin is 2048?170 = **1878Mi**, about **91.7%** of the limit. The 512Mi request is roughly three times this sample. Sparse metrics-server samples can miss instantaneous OCR spikes. Over a CPU limit a process is throttled; over its memory limit the container can be OOMKilled with exit code **137**. Job retries must remain visible, never publish partial content, and retain the previous snapshot.

Resource rationale and evidence limits:

| Container | Requests / limits | Observed evidence and rationale |
| --- | --- | --- |
| API | 200m, 256Mi / 1 CPU, 1Gi | Earlier stub samples 5–7m and 72–73Mi; memory request >3× sampled resident use and CPU denominator supports HPA. These are not fresh real-load peaks. |
| Chroma | 100m, 512Mi / 1 CPU, 2Gi | Fresh two-snapshot/669-chunk run showed 17m/52Mi after queries and pod recovery. Extra headroom covers larger indexes and transient work; this is not a measured optimum. |
| Redis | 50m, 128Mi / 500m, 512Mi | Fresh sample 5m/4Mi after cache and turn probes; allowance covers pointer, cache and one-hour turns. Longer workloads still need monitoring. |
| UI | 25m, 32Mi / 200m, 128Mi | Historical sample 1m/2Mi. The final metrics snapshot omitted the freshly restored UI pod, so no new UI memory measurement is claimed. |
| Indexer | 200m, 512Mi / 2 CPU, 2Gi | New 39-sample maximum 170Mi; conservative OCR/document-size allowance, not a measured 2Gi requirement. |
| Data-wait init | 10m, 16Mi / 50m, 32Mi | Bounded busybox connectivity wait; no independent sample captured yet. |
| CI model double | 100m, 128Mi / 500m, 256Mi | Bounded stdlib fixture server, now explicitly limited; not real Ollama. |

New raw samples are in `docs/evidence/kubernetes-f583517/indexer-memory-samples.txt` and `resources-after.txt`, with a computed `summary.json`. Older figures remain in their dated records. Requests provide scheduling headroom and limits cap bursts; these finite observations do not establish optimal resource settings.

## 5. Where is recall@5 worst, and what technique addresses it?

The new reviewed 15-question `eval/results.json` has a 100% recall@5 tie across answerable categories, so none is worst at k=5. Version questions are weaker at recall@3: 0.5, because q10's direct current summer rule was fourth/fifth. Heading-only navigation hits formerly outranked substantive evidence; `api/app/retrieval/chroma.py` now filters those candidates. Dense embeddings can blur a clause number, short code or closely related edition. A next experiment is lexical/BM25 plus dense retrieval or a reranker, measured against the same golden set. Hybrid retrieval is a proposed technique, not an implemented feature or a fabricated new result. The committed live comparison confirms these metrics for all three settings. The separate generation-context selector addresses distracting definitions; it does not claim to implement BM25 or improve the reported retrieval rank.

## 6. Change only the API embedding model: what happens?

`k8s/base/configmap.yaml:8` supplies the shared pin. `api/app/services/readiness.py:23` resolves the active snapshot, then lines 26–32 compare recorded model/dimension with configuration. Startup logs an explicit conflict; readiness returns 503 rather than admitting the mismatched pod. Retrieval also checks active metadata, protecting direct requests during an incompatible publication. Without this guardrail, the vector database could return semantically meaningless nearest neighbors without a useful error. The existing real mismatch capture shows a 0/1 new pod while the old three stay ready; the current fixture repeats the 503 check in `docs/evidence/faults/offline-current.json`.

## 7. A failure that cost more than an hour

The earlier Windows setup failure delayed Ubuntu/Minikube startup for over an hour. `wsl --install --no-distribution` reported that a path could not be found, while winget reported another WSL version already installed. The initial wrong belief was that reinstalling the package alone would fix it. `Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux` showed **Disabled**, while VirtualMachinePlatform was enabled. Enabling the missing Windows feature, repairing the prepared MSI, restarting and installing Ubuntu resolved that environment. Package presence was not proof the Windows feature/service was running.

The completion audit found a separate application trap: `/readyz` used to fall through Ingress to the UI and return HTML with HTTP 200. Checking only a status code therefore produced misleading evidence. Explicit health routes and a JSON `status=ready` assertion now distinguish API readiness from UI availability. Fresh evidence must retain the response body, not just `curl`'s exit status.