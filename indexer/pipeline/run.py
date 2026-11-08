"""The indexer Job's entry point. It runs once and exits (section 4.2).

    python -m pipeline.run --dummy    # week 1: three fake chunks, no model needed
    python -m pipeline.run            # the real pipeline: extract, clean, chunk, embed, store

Exit code 0 means the index was written; anything else fails the Job, and
Kubernetes retries it up to the Job's backoffLimit.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

from .config import IndexerSettings, get_settings
from .models import Chunk, Document


def log(msg: str, **fields: object) -> None:
    print(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                      "logger": "rahbar.indexer", "request_id": "indexer-" +
                      os.environ.get("HOSTNAME", "local"), "msg": msg, **fields}), flush=True)


class JsonHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        log(record.getMessage(), level=record.levelname,
            error=logging.Formatter().formatException(record.exc_info) if record.exc_info else None)


def _front_matter(path: Path) -> dict[str, str]:
    """Read `key: value` lines between leading '---' markers (used by eval/fixtures)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    meta: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta


def discover(corpus_dir: str) -> list[tuple[Path, str, bool]]:
    """List (path, doc_version, superseded) for every document to index.

    corpus/fetch.py writes _index.json next to the files it downloads; use it when
    present. Otherwise read Markdown front matter (the CI fixtures work this way).
    """
    root = Path(corpus_dir)
    index = root / "_index.json"
    if index.exists():
        entries = json.loads(index.read_text(encoding="utf-8"))
        return [(root / e["file"], str(e.get("doc_version", "unknown")),
                 bool(e.get("superseded", False))) for e in entries]
    found = []
    for path in sorted(root.glob("*")):
        if path.suffix.lower() not in {".pdf", ".md", ".txt"}:
            continue
        if path.name.lower().startswith("readme"):
            continue
        meta = _front_matter(path) if path.suffix.lower() == ".md" else {}
        found.append((path, meta.get("doc_version", "unknown"),
                      meta.get("superseded", "false").lower() == "true"))
    return found


def prepare(corpus_dir: str) -> list[Document]:
    from .clean import clean
    from .extract import extract

    sources = discover(corpus_dir)
    if not sources:
        raise ValueError(f"no documents found in {corpus_dir}")
    documents = []
    for path, doc_version, superseded in sources:
        doc = clean(extract(str(path), doc_version, superseded))
        readable = sum(bool(p.text) for p in doc.pages)
        if not readable:
            raise ValueError(f"{path.name}: no readable pages after cleaning")
        log("extracted", source=path.name, pages=len(doc.pages),
            ocr_pages=sum(p.ocr for p in doc.pages),
            empty_pages=[p.page for p in doc.pages if not p.text])
        documents.append(doc)
    return documents


def build_chunks(documents: list[Document], size: int, overlap: int) -> list[Chunk]:
    from .chunk import chunk

    chunks = [piece for doc in documents for piece in chunk(doc, size, overlap)]
    original_words = sum(len(p.text.split()) for doc in documents for p in doc.pages)
    stored_words = sum(len(c.text.split()) for c in chunks)
    log("chunked", size=size, overlap=overlap, chunks=len(chunks), original_words=original_words,
        stored_words=stored_words, amplification=round(stored_words / original_words, 4))
    return chunks


def run_pipeline(settings: IndexerSettings) -> int:
    from .embed import embed
    from .store import store

    documents = prepare(settings.corpus_dir)
    chunks = build_chunks(documents, settings.chunk_size, settings.chunk_overlap)
    vectors = embed([c.text for c in chunks], settings)
    return store(chunks, vectors, settings)


def _plan_pair(value: str) -> tuple[int, int]:
    try:
        size, overlap = map(int, value.split(":"))
        if not 0 <= overlap < size:
            raise ValueError
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected SIZE:OVERLAP with 0 <= OVERLAP < SIZE") from exc
    return size, overlap


def main() -> int:
    logging.basicConfig(level=logging.INFO, handlers=[JsonHandler()], force=True)
    parser = argparse.ArgumentParser(description="Build the RAHBAR index, then exit.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dummy", action="store_true", help="write three fake chunks")
    mode.add_argument("--plan", nargs="+", type=_plan_pair, metavar="SIZE:OVERLAP",
                      help="measure chunk counts and amplification without services")
    args = parser.parse_args()
    settings = get_settings()
    log("indexer starting", dummy=args.dummy, embed_model=settings.embed_model,
        collection=settings.collection, chroma=f"{settings.chroma_host}:{settings.chroma_port}",
        pod=os.environ.get("HOSTNAME", "-"))
    started = time.perf_counter()
    try:
        if args.plan:
            documents = prepare(settings.corpus_dir)
            for size, overlap in args.plan:
                build_chunks(documents, size, overlap)
            return 0
        if args.dummy:
            from .dummy import write_dummy_index
            from .store import get_client

            count = write_dummy_index(settings, get_client(settings))
            # The dummy writer is only for development. Reset any previously
            # published production pointer when switching an existing dev cluster.
            import redis
            cache = redis.Redis(host=settings.redis_host, port=settings.redis_port,
                                socket_connect_timeout=5, socket_timeout=5)
            with cache.pipeline(transaction=True) as transaction:
                transaction.delete(f"rahbar:index:{settings.collection}:active")
                transaction.incr("rahbar:index_generation")
                transaction.execute()
            cache.close()
        else:
            count = run_pipeline(settings)
    except Exception as exc:
        log("indexer failed", error_type=type(exc).__name__, error=str(exc))
        return 1
    log("indexer finished", chunks=count, seconds=round(time.perf_counter() - started, 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
