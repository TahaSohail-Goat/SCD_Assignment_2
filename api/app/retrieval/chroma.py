"""The real retriever. Yours to build (sections 3.2 and 4.4).

Connection details are already here; the query is not.
"""

from __future__ import annotations

import re
from typing import Any

import httpx

from ..config import Settings
from ..schemas import Passage

_HISTORICAL = re.compile(
    r"\b(?:old|older|previous|prior|superseded|historical|former) "
    r"(?:edition|handbook|policy|regulations|rules|version)\b|\b20[0-2][0-5]\b",
    re.I,
)
_YEAR = re.compile(r"\b(20\d{2})\b")


def is_historical_question(question: str) -> bool:
    return bool(_HISTORICAL.search(question))


class ChromaRetriever:
    name = "chroma"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: Any = None

    @property
    def client(self) -> Any:
        if self._client is None:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            self._client = chromadb.HttpClient(
                host=self.settings.chroma_host,
                port=self.settings.chroma_port,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        return self._client

    def embed(self, question: str) -> list[float]:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                self.settings.ollama_url.rstrip("/") + "/api/embed",
                json={"model": self.settings.embed_model, "input": question},
            )
            response.raise_for_status()
            embeddings = response.json()["embeddings"]
        if not embeddings or not embeddings[0]:
            raise ValueError("embedding provider returned no vector")
        return [float(value) for value in embeddings[0]]

    def retrieve(self, question: str, k: int, embedding: list[float] | None = None) -> list[Passage]:
        collection = self.client.get_collection(self.settings.collection)
        historical = is_historical_question(question)
        count = int(collection.count())
        if count == 0:
            return []
        query: dict[str, Any] = {
            "query_embeddings": [embedding if embedding is not None else self.embed(question)],
            "n_results": min(count, k * 3 if historical else k),
            "include": ["documents", "metadatas", "distances"],
        }
        if not historical:
            query["where"] = {"superseded": False}
        result = collection.query(**query)
        ids = result["ids"][0]
        documents = result["documents"][0]
        metadatas = result["metadatas"][0]
        distances = result["distances"][0]
        passages: list[Passage] = []
        for chunk_id, document, metadata, distance in zip(ids, documents, metadatas, distances):
            meta = metadata or {}
            passages.append(Passage(
                chunk_id=str(chunk_id), text=str(document or ""),
                source=str(meta.get("source", "unknown")),
                section=str(meta.get("section", "unknown")),
                page=int(meta["page"]) if meta.get("page") is not None else None,
                score=1.0 - float(distance),
                doc_version=str(meta.get("doc_version", "")),
                superseded=bool(meta.get("superseded", False)),
            ))
        if historical and (year := _YEAR.search(question)):
            passages.sort(key=lambda p: (year.group(1) not in p.doc_version,
                                         -p.score))
        return passages[:k]
