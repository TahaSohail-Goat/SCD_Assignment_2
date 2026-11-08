#!/usr/bin/env bash
# Read-only capture. Run while the real indexer Job is active for its peak samples.
set -euo pipefail
out=${1:-docs/evidence/current}
mkdir -p "$out"
git rev-parse HEAD > "$out/commit.txt"
date -u +%FT%TZ > "$out/captured-at.txt"
kubectl --context=minikube -n rahbar get pods,svc,ingress,pvc,hpa -o wide > "$out/objects.txt"
kubectl --context=minikube -n rahbar get endpointslices -o yaml > "$out/endpoints.yaml"
kubectl --context=minikube -n rahbar top pods > "$out/resources.txt"
kubectl --context=minikube -n rahbar logs job/initial-index > "$out/indexer.jsonl"
kubectl --context=minikube -n rahbar get networkpolicies -o yaml > "$out/networkpolicies.yaml"
kubectl --context=minikube -n rahbar get deployment api -o yaml > "$out/api-deployment.yaml"
for sample in $(seq 1 30); do
  date -u +%FT%TZ
  kubectl --context=minikube -n rahbar top pods -l app=indexer || true
  sleep 2
done > "$out/indexer-memory-samples.txt"
