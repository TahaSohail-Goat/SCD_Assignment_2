"""Measure labelled cache pairs with real pinned embeddings (no answer tuning)."""

from __future__ import annotations

import argparse
import ipaddress
import json
import math
import os
import socket
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import yaml

from api.app.services.cache import cosine
from scripts.artifact_paths import artifact_path, cases_path


def local_ollama_url(value: str) -> str:
    """Calibration may contact only the configured local/private Ollama server."""
    url = urlsplit(value)
    if (url.scheme not in {"http", "https"} or not url.hostname or url.username
            or url.password or url.query or url.fragment or url.path not in {"", "/"}
            or url.port != 11434):
        raise ValueError("use an Ollama HTTP(S) origin on port 11434")
    addresses = {item[4][0] for item in socket.getaddrinfo(url.hostname, url.port,
                                                        type=socket.SOCK_STREAM)}
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if ip.is_link_local or ip.is_unspecified or ip.is_multicast or not ip.is_private:
            raise ValueError("calibration requires a loopback or private Ollama address")
    # Pin the checked IP to prevent DNS changes between validation and connect.
    address = sorted(addresses)[0]
    host = f"[{address}]" if ":" in address else address
    return f"{url.scheme}://{host}:{url.port}"


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
    output = artifact_path(args.out)
    cases = yaml.safe_load(cases_path(args.cases).read_text(encoding="utf-8"))["cases"]
    origin = local_ollama_url(args.url)
    texts = list(dict.fromkeys(row[key] for row in cases for key in ("first", "second")))
    vectors = {}
    with httpx.Client(timeout=180, follow_redirects=False, trust_env=False) as client:
        for start in range(0, len(texts), 16):
            batch = texts[start:start + 16]
            result = client.post(origin + "/api/embed", json={
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
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(output), "selected_threshold": report["selected_threshold"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
