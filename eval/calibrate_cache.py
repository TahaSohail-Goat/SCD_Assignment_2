"""Measure labelled cache pairs with real pinned embeddings (no answer tuning)."""

from __future__ import annotations

import argparse
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
import yaml

from api.app.services.cache import cosine


def summarise_pairs(pairs: list[dict]) -> dict:
    negatives = [row["similarity"] for row in pairs if not row["equivalent"]]
    if not negatives or not any(row["equivalent"] for row in pairs):
        raise ValueError("calibration needs positive and negative labelled pairs")
    # Compare two permissive settings with the first safe representable boundary.
    safe = math.nextafter(max(negatives), math.inf)
    if safe > 1:
        raise ValueError("different answers have indistinguishable embeddings; disable semantic hits")
    thresholds = sorted({max(0.0, safe - 0.10), max(0.0, safe - 0.05), safe})
    trials = []
    for threshold in thresholds:
        false_hits = [row["id"] for row in pairs
                      if not row["equivalent"] and row["similarity"] >= threshold]
        true_hits = [row["id"] for row in pairs
                     if row["equivalent"] and row["similarity"] >= threshold]
        trials.append({"threshold": threshold, "false_hits": false_hits, "true_hits": true_hits})
    chosen = next(row["threshold"] for row in trials if not row["false_hits"])
    return {"trials": trials, "selected_threshold": chosen, "pairs": pairs,
            "selection_rule": "lowest tested threshold with zero labelled false hits"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"))
    parser.add_argument("--model", default=os.getenv("EMBED_MODEL", "nomic-embed-text"))
    parser.add_argument("--cases", type=Path, default=Path("eval/cache_cases.yaml"))
    parser.add_argument("--out", type=Path, default=Path("eval/cache-calibration.json"))
    args = parser.parse_args()
    cases = yaml.safe_load(args.cases.read_text(encoding="utf-8"))["cases"]
    texts = list(dict.fromkeys(row[key] for row in cases for key in ("first", "second")))
    vectors = {}
    with httpx.Client(timeout=180) as client:
        for start in range(0, len(texts), 16):
            batch = texts[start:start + 16]
            result = client.post(args.url.rstrip("/") + "/api/embed", json={
                "model": args.model, "input": batch, "truncate": False,
            })
            result.raise_for_status()
            returned = result.json()["embeddings"]
            if len(returned) != len(batch):
                raise ValueError("embedding count mismatch")
            vectors.update(zip(batch, returned, strict=True))
    pairs = [{**row, "similarity": cosine(vectors[row["first"]], vectors[row["second"]])}
             for row in cases]
    report = {"model": args.model, "timestamp": datetime.now(timezone.utc).isoformat(),
              "environment": "live Ollama embeddings", **summarise_pairs(pairs)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(args.out), "selected_threshold": report["selected_threshold"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
