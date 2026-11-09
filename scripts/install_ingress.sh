#!/usr/bin/env bash
# One verified controller manifest shared by CI and CD.
set -euo pipefail
mkdir -p output/deployment
manifest=output/deployment/ingress-nginx-kind.yaml
curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
  https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.15.1/deploy/static/provider/kind/deploy.yaml \
  --output "$manifest"
printf '2a3ae008c8786431115502644e77ab398fdebfb721a5d1195ed3089cde3299df  %s\n' "$manifest" | sha256sum --check --strict
kubectl apply -f "$manifest"
kubectl rollout status -n ingress-nginx deployment/ingress-nginx-controller --timeout=600s
