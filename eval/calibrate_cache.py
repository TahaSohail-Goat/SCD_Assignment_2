"""Measure labelled cache pairs with real pinned embeddings (no answer tuning)."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
import yaml

from api.app.services.cache import cosine
from scripts.artifact_paths import cases_path


def local_ollama_url(value: str) -> str:
    """Use a loopback Ollama server or a local port-forward; never resolve DNS."""
    origins = {
        "http://localhost:11434": "http://127.0.0.1:11434",
        "http://127.0.0.1:11434": "http://127.0.0.1:11434",
        "http://[::1]:11434": "http://[::1]:11434",
        "https://localhost:11434": "https://localhost:11434",
        "https://127.0.0.1:11434": "https://127.0.0.1:11434",
        "https://[::1]:11434": "https://[::1]:11434",
    }
    try:
        return origins[value.rstrip("/")]
    except KeyError as exc:
        raise ValueError("use a loopback Ollama origin on port 11434") from exc


def summarise_pairs(pairs: list[dict]) -> dict:
    negatives = [row["similarity"] for row in pairs if not row["equivalent"]]
    if not negatives or not any(row["equivalent"] for row in pairs):
        raise ValueError("calibration needs positive and negative labelled pairs")
    # Coarse thresholds leave a practical margin; a one-ULP boundary above a
    # negative pair is too sensitive to floating-point/model execution changes.
    thresholds = (0.85, 0.90, 0.95)
    trials = []
    for threshold in thresholds:
        false_hits = [row["id"] for row in pairs
                      if not row["equivalent"] and row["similarity"] >= threshold]
        true_hits = [row["id"] for row in pairs
                     if row["equivalent"] and row["similarity"] >= threshold]
        trials.append({"threshold": threshold, "false_hits": false_hits, "true_hits": true_hits})
    safe_trials = [row for row in trials if not row["false_hits"]]
    if not safe_trials:
        raise ValueError("no tested threshold avoids false hits; disable semantic reuse and recalibrate")
    chosen = safe_trials[0]["threshold"]
    return {"trials": trials, "selected_threshold": chosen, "pairs": pairs,
            "selection_rule": "lowest tested threshold with zero labelled false hits"}


def measure(url: str, model: str, case_file: Path) -> dict:
    cases = yaml.safe_load(cases_path(case_file).read_text(encoding="utf-8"))["cases"]
    origin = local_ollama_url(url)
    texts = list(dict.fromkeys(row[key] for row in cases for key in ("first", "second")))
    vectors = {}
    with httpx.Client(timeout=180, follow_redirects=False, trust_env=False) as client:
        for start in range(0, len(texts), 16):
            batch = texts[start:start + 16]
            result = client.post(origin + "/api/embed", json={
                "model": model, "input": batch, "truncate": False,
            })
            result.raise_for_status()
            returned = result.json()["embeddings"]
            if len(returned) != len(batch):
                raise ValueError("embedding count mismatch")
            vectors.update(zip(batch, returned, strict=True))
    pairs = [{**row, "similarity": cosine(vectors[row["first"]], vectors[row["second"]])}
             for row in cases]
    return {"model": model, "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": "live Ollama embeddings", **summarise_pairs(pairs)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"))
    parser.add_argument("--model", default=os.getenv("EMBED_MODEL", "nomic-embed-text"))
    parser.add_argument("--cases", type=Path, default=Path("eval/cache_cases.yaml"))
    args = parser.parse_args()
    report = measure(args.url, args.model, args.cases)
    # Standalone output is fixed; the live audit persists returned measurements
    # under its separately validated run directory, without mutating sys.argv.
    output = Path(__file__).resolve().parent / "cache-calibration.json"
    if output.is_symlink():
        raise ValueError("calibration output must not be a symbolic link")
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(output), "selected_threshold": report["selected_threshold"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
