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
fetch_version() {
  expected=$1
  destination=$2
  for attempt in $(seq 1 30); do
    if curl -fsS --max-time 5 -H "Host: $HOST" "http://$INGRESS_IP/" --output "$destination" && grep -Fq "Version $expected" "$destination"; then # NOSONAR: validated private test IP, public version HTML only.
      date -u +%FT%TZ >> "$evidence/version-probes.txt"
      printf 'confirmed %s on attempt %s\n' "$expected" "$attempt" >> "$evidence/version-probes.txt"
      return 0
    fi
    date -u +%FT%TZ >> "$evidence/version-probes.txt"
    printf 'waiting for %s, attempt %s\n' "$expected" "$attempt" >> "$evidence/version-probes.txt"
    sleep 1
  done
  echo "Ingress did not expose Version $expected" >&2
  return 1
}
for color in blue green; do
  image="rahbar-ui:demo-$color-$sha"
  docker build --build-arg "VCS_REF=demo-$color-$sha" -t "$image" ui
  minikube image load "$image"
  kubectl --context=minikube -n rahbar set image deployment/ui "ui=$image"
  kubectl --context=minikube -n rahbar rollout status deployment/ui --timeout=180s \
    | tee "$evidence/$color-rollout.txt"
  fetch_version "demo-$color-$sha" "$evidence/$color.html"
  grep -F "Version demo-$color-$sha" "$evidence/$color.html"
done
kubectl --context=minikube -n rahbar rollout undo deployment/ui | tee "$evidence/undo.txt"
kubectl --context=minikube -n rahbar rollout status deployment/ui --timeout=180s
fetch_version "demo-blue-$sha" "$evidence/after-undo.html"
grep -F "Version demo-blue-$sha" "$evidence/after-undo.html"
kubectl --context=minikube -n rahbar rollout history deployment/ui > "$evidence/history.txt"
date -u +%FT%TZ > "$evidence/captured-at.txt"
