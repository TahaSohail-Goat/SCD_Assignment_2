from contextlib import nullcontext
from dataclasses import replace

import pytest
from chromadb.errors import NotFoundError

from pipeline import store as stage
from pipeline.config import get_settings
from pipeline.models import Chunk


class Collection:
    def __init__(self, client, name, metadata):
        self.client = client
        self.name = name
        self.id = object()
        self.metadata = metadata
        self.rows = {}

    def add(self, ids, documents, embeddings, metadatas):
        if self.client.fail_after is not None and len(self.rows) >= self.client.fail_after:
            raise RuntimeError("write failed")
        for key, doc, vec, meta in zip(ids, documents, embeddings, metadatas, strict=True):
            self.rows[key] = (doc, vec, meta)

    def count(self):
        return len(self.rows)

    def modify(self, *, name):
        if name in self.client.collections:
            raise ValueError("name occupied")
        if self.client.fail_publish and self.name.startswith("rahbar-staging-"):
            raise RuntimeError("publish failed")
        del self.client.collections[self.name]
        self.client.collections[name] = self
        self.name = name
        if name == self.client.lost_ack:
            raise RuntimeError("rename acknowledgement lost")


class Client:
    def __init__(self):
        self.collections = {}
        self.fail_after = None
        self.fail_publish = False
        self.lost_ack = None

    def create_collection(self, *, name, metadata, embedding_function=None):
        col = self.collections[name] = Collection(self, name, metadata)
        return col

    def get_collection(self, name):
        if name not in self.collections:
            raise NotFoundError("no such collection")
        return self.collections[name]

    def delete_collection(self, name):
        self.get_collection(name)
        del self.collections[name]


CHUNKS = [
    Chunk("a", "Rule A", "policy.pdf", "1.2", 2, "2026", False),
    Chunk("b", "Rule B", "old-policy.pdf", "1.4", 3, "2023", True),
]
VECTORS = [[0.2, 0.4], [0.4, 0.2]]


@pytest.fixture
def chroma(monkeypatch):
    client = Client()
    client.generation = 0

    class Cache:
        def lock(self, name, **options):
            assert name == "rahbar:index_publish"
            return nullcontext()

        def incr(self, key):
            assert key == "rahbar:index_generation"
            client.generation += 1
            return client.generation

        def close(self):
            pass

    monkeypatch.setattr(stage.redis, "Redis", lambda **_kw: Cache())
    monkeypatch.setattr(stage, "get_client", lambda _settings: client)
    monkeypatch.setattr(stage, "_WRITE_BATCH", 1)
    return client


def test_store_publishes_complete_cosine_index(chroma):
    settings = replace(get_settings(), embed_model="test-model", collection="policy")
    old = chroma.create_collection(name="policy", metadata={})
    assert stage.store(CHUNKS, VECTORS, settings) == 2
    published = chroma.get_collection("policy")
    assert published is not old
    assert set(chroma.collections) == {"policy"}
    assert chroma.generation == 1
    assert published.metadata == {"hnsw:space": "cosine", "embed_model": "test-model",
                                  "dimension": 2}
    assert published.rows["b"] == ("Rule B", [0.4, 0.2], CHUNKS[1].metadata())


@pytest.mark.parametrize("failure", ["partial-write", "publish"])
def test_failed_build_or_publish_preserves_previous_index(chroma, failure):
    settings = get_settings()
    old = chroma.create_collection(name=settings.collection, metadata={})
    if failure == "partial-write":
        chroma.fail_after = 1
    else:
        chroma.fail_publish = True
    with pytest.raises(RuntimeError, match="failed"):
        stage.store(CHUNKS, VECTORS, settings)
    assert chroma.collections == {settings.collection: old}
    assert chroma.generation == 0


def test_store_validates_shape_before_writing(chroma):
    with pytest.raises(ValueError, match="dimensions"):
        stage.store(CHUNKS, [[1.0], [1.0, 2.0]], get_settings())
    assert chroma.collections == {}


def test_rename_acknowledgement_loss_checks_live_collection_id(chroma):
    settings = get_settings()
    chroma.create_collection(name=settings.collection, metadata={})
    chroma.lost_ack = settings.collection
    assert stage.store(CHUNKS, VECTORS, settings) == 2
    assert chroma.get_collection(settings.collection).count() == 2
    assert chroma.generation == 1
