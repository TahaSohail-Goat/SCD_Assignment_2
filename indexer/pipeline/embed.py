"""Embed batches with the same pinned Ollama model as the API."""

from __future__ import annotations

import math

import httpx

from .config import IndexerSettings

_BATCH_SIZE = 16
_KNOWN_DIMENSIONS = {"nomic-embed-text": 768}


def embed(texts: list[str], settings: IndexerSettings) -> list[list[float]]:
    """Validate shape, dimension and values before returning any vectors."""
    if not texts:
        raise ValueError("cannot embed an empty index")
    vectors: list[list[float]] = []
    dimension = _KNOWN_DIMENSIONS.get(settings.embed_model)
    url = settings.ollama_url.rstrip("/") + "/api/embed"
    with httpx.Client(timeout=httpx.Timeout(180, connect=10)) as client:
        for start in range(0, len(texts), _BATCH_SIZE):
            batch = texts[start:start + _BATCH_SIZE]
            try:
                response = client.post(url, json={
                    "model": settings.embed_model, "input": batch, "truncate": False,
                })
                response.raise_for_status()
                payload = response.json()
                returned = payload.get("embeddings") if isinstance(payload, dict) else None
                if not isinstance(returned, list) or len(returned) != len(batch):
                    raise ValueError(f"expected {len(batch)} embeddings")
                for vector in returned:
                    if not isinstance(vector, list) or not vector:
                        raise ValueError("empty or malformed embedding")
                    if dimension is None:
                        dimension = len(vector)
                    if len(vector) != dimension:
                        raise ValueError(f"expected embedding dimension {dimension}, got {len(vector)}")
                    if any(type(value) not in (int, float) or not math.isfinite(value)
                           for value in vector) or not any(vector):
                        raise ValueError("embedding is non-numeric, non-finite or zero")
                    vectors.append([float(value) for value in vector])
            except (httpx.HTTPError, ValueError, OverflowError) as exc:
                raise ValueError(f"Ollama embedding batch starting at chunk {start}: {exc}") from exc
    return vectors
