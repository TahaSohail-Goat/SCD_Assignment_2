"""Dependency checks used by readiness and the startup pin diagnostic."""

from __future__ import annotations

from typing import Any

from ..config import Settings
from .cache import SemanticCache

_KNOWN_DIMENSIONS = {"nomic-embed-text": 768, "dummy-768": 768}


def check_readiness(settings: Settings, cache: SemanticCache) -> dict[str, str]:
    checks: dict[str, str] = {}
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        client: Any = chromadb.HttpClient(
            host=settings.chroma_host, port=settings.chroma_port,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        collection = client.get_collection(cache.active_collection(settings.collection))
        count = int(collection.count())
        metadata = collection.metadata or {}
        recorded_model = str(metadata.get("embed_model", ""))
        dimension = int(metadata.get("dimension", 0))
        if count == 0:
            checks["chroma"] = "collection is empty"
        elif recorded_model != settings.embed_model:
            checks["embedding_pin"] = (
                f"collection model {recorded_model!r} != configured model {settings.embed_model!r}"
            )
        elif dimension < 1 or (
            settings.embed_model in _KNOWN_DIMENSIONS
            and dimension != _KNOWN_DIMENSIONS[settings.embed_model]
        ):
            checks["embedding_pin"] = f"collection dimension {dimension} is invalid"
        else:
            checks["chroma"] = f"ok ({count} chunks, {dimension} dimensions)"
            checks["embedding_pin"] = "ok"
    except Exception as exc:
        checks["chroma"] = f"unavailable ({type(exc).__name__})"
    try:
        checks["redis"] = "ok" if cache.ping() else "unavailable"
    except Exception as exc:
        checks["redis"] = f"unavailable ({type(exc).__name__})"
    return checks


def is_ready(checks: dict[str, str]) -> bool:
    return all(value == "ok" or value.startswith("ok (") for value in checks.values()) \
        and "embedding_pin" in checks and "redis" in checks
