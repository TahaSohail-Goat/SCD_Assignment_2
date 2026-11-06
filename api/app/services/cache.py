"""Redis-backed semantic cache scoped to an index generation."""

from __future__ import annotations

import hashlib
import json
import math
import re

import redis

from ..config import Settings
from ..schemas import AskResponse

GENERATION_KEY = "rahbar:index_generation"
_FOLLOW_UP = re.compile(r"^(and |also |what about |how about |why |it\b|they\b|that\b)|\b(this|those|them|its)\b", re.I)


def is_follow_up(question: str) -> bool:
    return bool(_FOLLOW_UP.search(question.strip()))


def cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return -1.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / (norm_a * norm_b) if norm_a and norm_b else -1.0


class SemanticCache:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = redis.Redis(
            host=settings.redis_host, port=settings.redis_port,
            decode_responses=True, socket_connect_timeout=2, socket_timeout=2,
        )

    def ping(self) -> bool:
        return bool(self.client.ping())

    def generation_id(self) -> str:
        """A completed reindex increments this key to invalidate older cache entries."""
        return str(self.client.get(GENERATION_KEY) or "0")

    def _prefix(self, generation_id: str | None) -> str:
        return f"rahbar:cache:{generation_id if generation_id is not None else self.generation_id()}:"

    def lookup(self, embedding: list[float], *, generation_id: str | None = None) -> AskResponse | None:
        prefix = self._prefix(generation_id)
        best_score = self.settings.cache_threshold
        best: AskResponse | None = None
        for key in self.client.scan_iter(match=prefix + "*"):
            raw = self.client.get(key)
            if not isinstance(raw, str):
                continue
            entry = json.loads(raw)
            score = cosine(embedding, entry["embedding"])
            if score >= best_score:
                best_score = score
                best = AskResponse.model_validate(entry["response"])
        return best

    def store(
        self, question: str, embedding: list[float], response: AskResponse,
        *, generation_id: str | None = None,
    ) -> None:
        key = self._prefix(generation_id) + hashlib.sha256(question.strip().lower().encode()).hexdigest()
        payload = {"embedding": embedding, "response": response.model_dump(mode="json")}
        self.client.setex(key, self.settings.cache_ttl_seconds, json.dumps(payload))
