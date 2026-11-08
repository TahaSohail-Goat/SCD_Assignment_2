#!/usr/bin/env bash
# Exercise the same Ingress and exact image revision before and after release.
set -euo pipefail
PYTHON=${PYTHON:-python3}
out=output/ingress-smoke
mkdir -p "$out"
kubectl port-forward -n ingress-nginx svc/ingress-nginx-controller 18080:80 > "$out/port-forward.log" 2>&1 &
forward_pid=$!
trap 'kill "$forward_pid" 2>/dev/null || true' EXIT
# Deployment availability precedes EndpointSlice/Ingress propagation. Wait for
# API readiness JSON, rather than using UI HTTP 200 as a proxy for API routing.
curl -fsS --retry 30 --retry-connrefused --retry-delay 1 --max-time 10 \
  -H 'Host: rahbar.local' http://127.0.0.1:18080/readyz --output "$out/readiness.json"
"$PYTHON" - <<'PY'
import json
from pathlib import Path
x = json.loads(Path("output/ingress-smoke/readiness.json").read_text(encoding="utf-8"))
assert x["status"] == "ready"
assert x["checks"]["chroma"].startswith("ok (")
assert x["checks"]["embedding_pin"] == x["checks"]["redis"] == "ok"
PY
curl -fsS --retry 10 --retry-connrefused --retry-delay 1 --max-time 30 \
  -H 'Host: rahbar.local' -H 'Content-Type: application/json' \
  -d '{"question":"What is the attendance requirement?"}' \
  http://127.0.0.1:18080/api/ask --output "$out/answer.json"
"$PYTHON" - <<'PY'
import json
from pathlib import Path
x = json.loads(Path("output/ingress-smoke/answer.json").read_text(encoding="utf-8"))
assert x["citations"] and x["answered_from_context"]
PY
curl -fsS -H 'Host: rahbar.local' http://127.0.0.1:18080/api/version --output "$out/version.json"
curl -fsS -H 'Host: rahbar.local' http://127.0.0.1:18080/ --output "$out/ui.html"
"$PYTHON" - <<'PY'
import json, os
from pathlib import Path
p = Path("output/ingress-smoke")
x = json.loads((p / "version.json").read_text(encoding="utf-8"))
assert x["revision"]
expected = os.getenv("EXPECTED_REVISION")
if expected:
    assert x["revision"] == expected, "API runs a different image revision"
    assert "Version " + expected in (p / "ui.html").read_text(encoding="utf-8"), "UI runs a different revision"
print("Ingress readiness, grounded answer and API/UI revision checks passed")
PY
