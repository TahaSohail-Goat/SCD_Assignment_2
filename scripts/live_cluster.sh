#!/usr/bin/env bash
# Mutates only an ephemeral Minikube test cluster; fails on a missing proof.
set -euo pipefail
PYTHON=${PYTHON:-python3}
out=output/cluster-audit
mkdir -p "$out"
git rev-parse HEAD > "$out/commit.txt"
date -u +%FT%TZ > "$out/started-at.txt"

PYTHON="$PYTHON" bash scripts/deploy_real.sh > "$out/deploy.log" 2>&1 &
deploy_pid=$!
trap 'kill "$deploy_pid" 2>/dev/null || true' EXIT
while kill -0 "$deploy_pid" 2>/dev/null; do
  {
    date -u +%FT%TZ
    kubectl --context=minikube -n rahbar top pods -l app=indexer || true
  } >> "$out/indexer-memory-samples.txt" 2>&1
  sleep 5
done
wait "$deploy_pid"
trap - EXIT
kubectl --context=minikube -n ingress-nginx rollout status deployment/ingress-nginx-controller --timeout=300s
INGRESS_IP=$(minikube ip)
export INGRESS_IP
HOST=rahbar.local
export HOST
INGRESS_IP="$INGRESS_IP" "$PYTHON" -c 'import ipaddress,os; p=ipaddress.ip_address(os.environ["INGRESS_IP"]); assert p.is_private and not (p.is_link_local or p.is_unspecified or p.is_multicast)'

fetch_ready() {
  curl -fsS --retry 60 --retry-connrefused --retry-delay 2 -H "Host: $HOST" "http://$INGRESS_IP/readyz" --output "$1" # NOSONAR: private ephemeral cluster IP checked above; dependency status only.
  "$PYTHON" -c 'import json,sys; x=json.load(open(sys.argv[1])); assert x["status"] == "ready"' "$1"
}
fetch_ready "$out/ready-before.json"

# Exercise genuine policy generation and abstention through the Ingress.
"$PYTHON" - <<'PY'
import os
from pathlib import Path
import httpx
from eval.run_eval import evaluate, gate, load_golden, write_results
questions = [q for q in load_golden(Path("eval/golden.yaml"))
             if q["id"] in {"q06", "q08", "q11", "q13", "q15"}]
with httpx.Client(timeout=300, headers={"Host": os.environ["HOST"]}) as client:
    results = evaluate(client, "http://" + os.environ["INGRESS_IP"], questions)
write_results(results, Path("output/cluster-audit/ingress-results.json"))
failures = gate(results, {"recall@5": 1.0})
if failures:
    raise SystemExit(str(failures))
PY

# Use the IP so blocked DNS cannot masquerade as denied Chroma connectivity.
chroma_ip=$(kubectl --context=minikube -n rahbar get service chroma -o jsonpath='{.spec.clusterIP}')
kubectl --context=minikube -n rahbar exec deployment/ui -- which wget > "$out/ui-wget.txt"
kubectl --context=minikube -n rahbar exec deployment/ui -- wget -q -O - http://127.0.0.1:8080/ > "$out/ui-positive.html"
if kubectl --context=minikube -n rahbar exec deployment/ui -- wget -T 5 -O - "http://$chroma_ip:8000/api/v2/heartbeat" > "$out/ui-chroma-denied.txt" 2>&1; then # NOSONAR: deliberate private-cluster negative connectivity test, no credentials.
  echo 'UI unexpectedly reached Chroma' >&2
  exit 1
fi
grep -Ei 'timed out|timeout|unreachable|refused' "$out/ui-chroma-denied.txt"
kubectl --context=minikube -n rahbar get networkpolicies -o yaml > "$out/networkpolicies.yaml"

kubectl --context=minikube -n rahbar get pods -l app=api -o json > "$out/api-before.json"
pod=$(kubectl --context=minikube -n rahbar get pods -l app=api -o jsonpath='{.items[0].metadata.name}')
kubectl --context=minikube -n rahbar delete pod "$pod" --wait=true > "$out/api-delete.txt"
kubectl --context=minikube -n rahbar rollout status deployment/api --timeout=300s
kubectl --context=minikube -n rahbar get pods -l app=api -o json > "$out/api-after.json"
fetch_ready "$out/ready-after-api-recovery.json"

kubectl --context=minikube -n rahbar get pod chroma-0 -o json > "$out/chroma-before.json"
kubectl --context=minikube -n rahbar delete pod chroma-0 --wait=true > "$out/chroma-delete.txt"
kubectl --context=minikube -n rahbar wait --for=condition=Ready pod/chroma-0 --timeout=240s
kubectl --context=minikube -n rahbar get pod chroma-0 -o json > "$out/chroma-after.json"
fetch_ready "$out/ready-after-chroma-recovery.json"
"$PYTHON" - <<'PY'
import json
from pathlib import Path
p = Path("output/cluster-audit")
read = lambda name: json.loads((p / name).read_text())
before = {x["metadata"]["uid"] for x in read("api-before.json")["items"]}
after = {x["metadata"]["uid"] for x in read("api-after.json")["items"]}
assert after - before, "API controller did not replace the deleted pod"
assert read("chroma-before.json")["metadata"]["uid"] != read("chroma-after.json")["metadata"]["uid"]
assert read("ready-before.json")["checks"]["chroma"] == read("ready-after-chroma-recovery.json")["checks"]["chroma"], "persisted index changed after pod recovery"
PY
INGRESS_IP="$INGRESS_IP" HOST="$HOST" PYTHON="$PYTHON" bash scripts/rollout_demo.sh "$out/rollout"
kubectl --context=minikube -n rahbar top pods > "$out/resources-after.txt"
date -u +%FT%TZ > "$out/completed-at.txt"
