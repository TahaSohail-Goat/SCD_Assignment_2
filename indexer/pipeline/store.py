"""Build a complete Chroma collection before publishing it to API readers."""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

import redis
from chromadb.errors import NotFoundError

from .config import IndexerSettings
from .models import Chunk

_LOG = logging.getLogger(__name__)
_WRITE_BATCH = 128
GENERATION_KEY = "rahbar:index_generation"


def get_client(settings: IndexerSettings) -> Any:
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    return chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port,
                               settings=ChromaSettings(anonymized_telemetry=False))


def _discard(client: Any, name: str) -> None:
    try:
        client.delete_collection(name)
    except NotFoundError:
        pass
    except Exception:
        _LOG.exception("could not remove temporary Chroma collection %s", name)


def _publish(client: Any, staging: Any, name: str, backup: str) -> None:
    try:
        old = client.get_collection(name)
    except NotFoundError:
        old = None
    if old is not None:
        old.modify(name=backup)
    try:
        staging.modify(name=name)
    except Exception:
        if old is not None:
            # If the staging rename took effect but its response was lost, Chroma
            # rejects the rollback because the live name is already occupied.
            old.modify(name=name)
        raise


def store(chunks: list[Chunk], vectors: list[list[float]], settings: IndexerSettings) -> int:
    """Write and verify a cosine collection with the shared embedding pin."""
    if not chunks or len(vectors) != len(chunks):
        raise ValueError("store requires one vector for each chunk in a nonempty corpus")
    dimension = len(vectors[0])
    if not dimension or any(len(vector) != dimension for vector in vectors):
        raise ValueError("store requires consistent, nonempty vector dimensions")
    if len({chunk.id for chunk in chunks}) != len(chunks):
        raise ValueError("duplicate chunk IDs")

    client = get_client(settings)
    suffix = uuid4().hex
    pending = f"rahbar-staging-{suffix}"
    backup = f"rahbar-backup-{suffix}"
    try:
        staging = client.create_collection(
            name=pending,
            metadata={"hnsw:space": "cosine", "embed_model": settings.embed_model,
                      "dimension": dimension},
            embedding_function=None,
        )
        for start in range(0, len(chunks), _WRITE_BATCH):
            batch = chunks[start:start + _WRITE_BATCH]
            staging.add(ids=[c.id for c in batch], documents=[c.text for c in batch],
                        embeddings=vectors[start:start + len(batch)],
                        metadatas=[c.metadata() for c in batch])
        count = staging.count()
        if count != len(chunks):
            raise RuntimeError(f"Chroma counted {count} of {len(chunks)} chunks")
        cache = redis.Redis(
            host=settings.redis_host, port=settings.redis_port,
            socket_connect_timeout=5, socket_timeout=5,
        )
        try:
            # Only complete collections compete for the live name. Manual Jobs
            # can overlap the CronJob even with concurrencyPolicy: Forbid.
            with cache.lock("rahbar:index_publish", timeout=120, blocking_timeout=30):
                _publish(client, staging, settings.collection, backup)
                cache.incr(GENERATION_KEY)
                _discard(client, backup)
        finally:
            cache.close()
    except Exception:
        _discard(client, pending)
        raise
    return int(count)
