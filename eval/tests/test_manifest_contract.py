from pathlib import Path

import yaml

from scripts.check_manifest_contract import inspect


def test_fixture_helper_cannot_lose_its_resource_contract():
    path = Path(__file__).resolve().parents[2] / "k8s/overlays/ci/fixture-model.yaml"
    objects = list(yaml.safe_load_all(path.read_text(encoding="utf-8")))
    for obj in objects:
        obj["metadata"]["namespace"] = "rahbar"
    assert inspect(objects)["errors"] == []
    deploy = next(obj for obj in objects if obj["kind"] == "Deployment")
    container = deploy["spec"]["template"]["spec"]["containers"][0]
    del container["resources"]["requests"]
    assert any("CPU/memory requests missing" in error for error in inspect(objects)["errors"])
