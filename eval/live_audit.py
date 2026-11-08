"""Run real OCR, three chunk settings, generation gates and token accounting.

Requires Chroma, Redis, Ollama and Tesseract. Writes measurements, never invented
numbers. Existing shipped results are replaced only with --publish after review.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from api.app.config import get_settings as api_settings
from api.app.providers.llm.ollama import OllamaProvider
from api.app.retrieval.chroma import ChromaRetriever
from api.app.services.answer import answer_question
from api.app.services.cache import SemanticCache
from eval.calibrate_cache import measure as calibrate
from eval.run_eval import evaluate, gate, load_golden, write_results
from indexer.pipeline.config import get_settings
from indexer.pipeline.embed import embed
from indexer.pipeline.run import build_chunks, prepare
from indexer.pipeline.store import store
from scripts.artifact_paths import artifact_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("eval/runs/current"))
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    args.out = artifact_path(args.out, directory=True)
    args.out.mkdir(parents=True, exist_ok=True)
    settings = get_settings()
    documents = prepare(settings.corpus_dir)
    original_usage: dict[str, int] = {}
    embed([page.text for doc in documents for page in doc.pages if page.text],
          settings, usage=original_usage)
    records = []
    server = None
    server_log = (args.out / "api.jsonl").open("w", encoding="utf-8")
    try:
        for size, overlap in ((120, 20), (240, 35), (400, 50)):
            chunks = build_chunks(documents, size, overlap)
            usage: dict[str, int] = {}
            vectors = embed([piece.text for piece in chunks], settings, usage=usage)
            store(chunks, vectors, settings)
            if server is None:
                environment = {**os.environ, "PYTHONPATH": str(Path("api").resolve())}
                server = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app",
                    "--host", "127.0.0.1", "--port", "18000"], env=environment,
                    stdout=server_log, stderr=subprocess.STDOUT)
            with httpx.Client(timeout=300) as client:
                for _ in range(60):
                    try:
                        if client.get("http://127.0.0.1:18000/readyz").status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(1)
                else:
                    raise RuntimeError("API did not become ready; inspect api.jsonl")
                result = evaluate(client, "http://127.0.0.1:18000", load_golden(Path("eval/golden.yaml")))
            result["golden"] = "eval/golden.yaml"
            runner = "GitHub Actions" if os.getenv("GITHUB_ACTIONS") == "true" else "local operator"
            result["environment"] = f"{runner} / {platform.system()} / real configured services / Ollama"
            result["commit"] = os.getenv("GITHUB_SHA", "local")
            write_results(result, args.out / f"{size}-{overlap}.json")
            original_tokens = original_usage.get("prompt_tokens", 0)
            stored_tokens = usage.get("prompt_tokens", 0)
            record = {"size": size, "overlap": overlap, "chunks": len(chunks),
                      "original_model_tokens": original_tokens, "stored_model_tokens": stored_tokens,
                      "amplification": stored_tokens / original_tokens if original_tokens else None,
                      "recall@3": result["recall@3"], "recall@5": result["recall@5"],
                      "gate_failures": gate(result, {"recall@5": 1.0})}
            records.append(record)
            print(json.dumps(record), flush=True)
        calibration = calibrate(settings.ollama_url, settings.embed_model,
                                Path("eval/cache_cases.yaml"))
        write_results(calibration, args.out / "cache-calibration.json")
        # Capture a complete-clause answer against the final published snapshot.
        config = api_settings()
        cache = SemanticCache(config)
        reader = ChromaRetriever(config)
        provider = OllamaProvider(config)
        control = answer_question("What does clause 1.22 specify?", reader, provider, config, cache)
        write_results(control.model_dump(mode="json"), args.out / "complete-clause-answer.json")
        summary = {"timestamp": datetime.now(timezone.utc).isoformat(),
                   "commit": os.getenv("GITHUB_SHA", "local"), "measurements": records,
                   "token_definition": "Ollama /api/embed prompt_eval_count summed per input batch"}
        with httpx.Client(timeout=30) as client:
            summary["model_inventory"] = client.get(settings.ollama_url.rstrip("/") + "/api/tags").json()
        write_results(summary, args.out / "measurements.json")
        if any(row["gate_failures"] or row["amplification"] is None for row in records):
            return 1
        if args.publish:
            # 400/50 is the final live index. Preserve all alternative-run evidence.
            chosen = json.loads((args.out / "400-50.json").read_text(encoding="utf-8"))
            write_results(chosen, Path("eval/results.json"))
            write_results({key: value for key, value in chosen.items() if key != "rows"},
                          Path("eval/baseline.json"))
        return 0
    finally:
        if server is not None:
            server.terminate()
            server.wait(timeout=30)
        server_log.close()


if __name__ == "__main__":
    raise SystemExit(main())
