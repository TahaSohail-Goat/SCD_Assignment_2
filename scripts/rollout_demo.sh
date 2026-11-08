#!/usr/bin/env bash
# A real visible UI change and undo; restores the original image even on failure.
set -euo pipefail
INGRESS_IP=${INGRESS_IP:-127.0.0.1}
HOST=${HOST:-rahbar.local}
PYTHON=${PYTHON:-python3}
# This demonstration fetches public version labels only on a local test cluster.
INGRESS_IP="$INGRESS_IP" "$PYTHON" -c 'import ipaddress,os; p=ipaddress.ip_address(os.environ["INGRESS_IP"]); assert p.is_private and not (p.is_link_local or p.is_unspecified or p.is_multicast), "Use the local Minikube ingress IP"'
evidence=${1:-docs/evidence/rollout-current}
mkdir -p "$evidence"
sha=$(git rev-parse --short=12 HEAD)
original=$(kubectl --context=minikube -n rahbar get deployment ui -o jsonpath='{.spec.template.spec.containers[0].image}')
restore() {
  kubectl --context=minikube -n rahbar set image deployment/ui "ui=$original"
  kubectl --context=minikube -n rahbar rollout status deployment/ui --timeout=180s
}
trap restore EXIT
for color in blue green; do
  image="rahbar-ui:demo-$color-$sha"
  docker build --build-arg "VCS_REF=demo-$color-$sha" -t "$image" ui
  minikube image load "$image"
  kubectl --context=minikube -n rahbar set image deployment/ui "ui=$image"
  kubectl --context=minikube -n rahbar rollout status deployment/ui --timeout=180s \
    | tee "$evidence/$color-rollout.txt"
  curl -fsS -H "Host: $HOST" "http://$INGRESS_IP/" > "$evidence/$color.html" # NOSONAR: private test IP checked above; public version HTML only.
  grep -F "Version demo-$color-$sha" "$evidence/$color.html"
done
kubectl --context=minikube -n rahbar rollout undo deployment/ui | tee "$evidence/undo.txt"
kubectl --context=minikube -n rahbar rollout status deployment/ui --timeout=180s
curl -fsS -H "Host: $HOST" "http://$INGRESS_IP/" > "$evidence/after-undo.html" # NOSONAR: private test IP checked above; public version HTML only.
grep -F "Version demo-blue-$sha" "$evidence/after-undo.html"
kubectl --context=minikube -n rahbar rollout history deployment/ui > "$evidence/history.txt"
date -u +%FT%TZ > "$evidence/captured-at.txt"
