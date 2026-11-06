# RAHBAR live embedding-model mismatch demo

Captured November 6, 2026 on the local WSL2/Docker Desktop/Minikube deployment in namespace `rahbar`. The shared Chroma collection held 669 chunks, 768-dimensional vectors, and model `nomic-embed-text`.

## Healthy state before change

The API deployment had 3/3 available replicas. The shared `rahbar-config` ConfigMap set `EMBED_MODEL=nomic-embed-text`. The API `/readyz` endpoint returned HTTP 200 with `chroma: ok (669 chunks, 768 dimensions)`, `embedding_pin: ok`, and `redis: ok`.

## Intentional mismatch

The API Deployment alone was temporarily changed with:

```text
kubectl -n rahbar set env deployment/api EMBED_MODEL=intentional-mismatch-demo
```

The stored Chroma model was not changed. At 18:11:29 UTC, the affected new pod was present and unready while the three older replicas remained ready:

```text
NAME                   READY   STATUS    RESTARTS   AGE
api-545c6f6d7b-crvlw   1/1     Running   1          3h52m
api-545c6f6d7b-f7kw5   1/1     Running   1          3h52m
api-545c6f6d7b-pz7qg   1/1     Running   1          3h52m
api-7f58569cc6-s97xv   0/1     Running   0          57s
```

The affected pod logged:

```json
{"ts": "2026-11-06T18:10:33Z", "level": "ERROR", "logger": "rahbar.api", "msg": "embedding pin conflict", "request_id": "-", "conflict": "collection model 'nomic-embed-text' != configured model 'intentional-mismatch-demo'"}
```

## Restoration

The override was removed with `kubectl -n rahbar set env deployment/api EMBED_MODEL-`. `kubectl -n rahbar rollout status deployment/api --timeout=180s` reported a successful rollout. The deployment returned to 3/3 available; all three API pods were `1/1 Running` and the affected new pod was gone.

The restored `/readyz` response was HTTP 200:

```json
{"status":"ready","checks":{"chroma":"ok (669 chunks, 768 dimensions)","embedding_pin":"ok","redis":"ok"}}
```

The intentional mismatch was local to Minikube. No repository configuration or published image was changed.
