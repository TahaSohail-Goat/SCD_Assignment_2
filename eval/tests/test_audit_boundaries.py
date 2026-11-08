from pathlib import Path

import pytest

from eval.calibrate_cache import local_ollama_url
from scripts import artifact_paths


def test_artifact_paths_cannot_delete_or_overwrite_source_or_escape_repo(tmp_path, monkeypatch):
    monkeypatch.setattr(artifact_paths, "ROOT", tmp_path)
    monkeypatch.setattr(artifact_paths, "ARTIFACT_ROOTS", (tmp_path / "output",))
    monkeypatch.chdir(tmp_path)
    for value in ("README.md", "output/../../outside.json", "api/app/config.py", "output"):
        with pytest.raises(ValueError):
            artifact_paths.artifact_path(Path(value))
    assert artifact_paths.artifact_path(Path("output/report.json")) == tmp_path / "output/report.json"
    with pytest.raises(ValueError):
        artifact_paths.artifact_path(Path("output/../api"), directory=True)


def test_cache_cases_cannot_read_outside_eval(tmp_path, monkeypatch):
    monkeypatch.setattr(artifact_paths, "ROOT", tmp_path)
    outside = tmp_path / "outside.yaml"
    outside.write_text("cases: []")
    with pytest.raises(ValueError):
        artifact_paths.cases_path(outside)


@pytest.mark.parametrize("address", ["169.254.169.254", "8.8.8.8", "0.0.0.0", "224.0.0.1"])
def test_calibration_rejects_metadata_public_and_non_server_destinations(address):
    with pytest.raises(ValueError):
        local_ollama_url(f"http://{address}:11434")


def test_calibration_pins_loopback_ip_and_rejects_credentials():
    assert local_ollama_url("http://localhost:11434") == "http://127.0.0.1:11434"
    with pytest.raises(ValueError):
        local_ollama_url("http://user:password@localhost:11434")
