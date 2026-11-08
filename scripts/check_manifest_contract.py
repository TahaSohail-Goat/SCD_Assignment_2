"""Check assignment/security invariants in rendered Kubernetes objects."""

import argparse
import json
import sys
from pathlib import Path

import yaml

if __package__:
    from .artifact_paths import artifact_path
else:
    from artifact_paths import artifact_path


def inspect(objects):
    errors = []
    checked = []
    for obj in objects:
        kind, meta = obj["kind"], obj["metadata"]
        name = meta["name"]
        if kind != "Namespace" and meta.get("namespace") != "rahbar":
            errors.append(f"{kind}/{name}: namespace must be rahbar")
        if kind == "Service" and obj["spec"].get("type", "ClusterIP") != "ClusterIP":
            errors.append(f"Service/{name}: external service type is forbidden")
        if kind == "HorizontalPodAutoscaler":
            if (obj["spec"]["minReplicas"], obj["spec"]["maxReplicas"]) != (3, 8):
                errors.append(f"HPA/{name}: require 3..8 replicas")
        if kind not in {"Deployment", "StatefulSet", "Job", "CronJob"}:
            continue
        template = obj["spec"] if kind != "CronJob" else obj["spec"]["jobTemplate"]["spec"]
        pod = template["template"]["spec"]
        if pod.get("automountServiceAccountToken") is not False:
            errors.append(f"{kind}/{name}: service account token must not be mounted")
        if not pod.get("serviceAccountName") or pod["serviceAccountName"] == "default":
            errors.append(f"{kind}/{name}: dedicated service account required")
        for container in pod.get("containers", []) + pod.get("initContainers", []):
            identity = f"{kind}/{name}/{container['name']}"
            checked.append(identity)
            context = {**pod.get("securityContext", {}), **container.get("securityContext", {})}
            if context.get("runAsNonRoot") is not True or context.get("runAsUser", 0) <= 0:
                errors.append(f"{identity}: explicit non-root identity required")
            if context.get("allowPrivilegeEscalation") is not False:
                errors.append(f"{identity}: privilege escalation must be false")
            if context.get("readOnlyRootFilesystem") is not True:
                errors.append(f"{identity}: readonly root required")
            if "ALL" not in context.get("capabilities", {}).get("drop", []):
                errors.append(f"{identity}: all capabilities must be dropped")
            for field in ("requests", "limits"):
                values = container.get("resources", {}).get(field, {})
                if not all(values.get(key) for key in ("cpu", "memory")):
                    errors.append(f"{identity}: CPU/memory {field} missing")
    return {"resources": len(objects), "containers": checked, "errors": errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    output = artifact_path(args.out) if args.out else None
    result = inspect([obj for obj in yaml.safe_load_all(sys.stdin) if obj])
    body = json.dumps(result, indent=2) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(body, encoding="utf-8")
    print(body)
    return int(bool(result["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
