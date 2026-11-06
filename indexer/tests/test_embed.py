from dataclasses import replace

import httpx
import pytest

from pipeline import embed as stage
from pipeline.config import get_settings


def fake_ollama(monkeypatch: pytest.MonkeyPatch, handler) -> None:
    make_client = httpx.Client
    monkeypatch.setattr(stage.httpx, "Client", lambda **kw: make_client(
        transport=httpx.MockTransport(handler), **kw
    ))


def test_embeddings_use_ordered_batches_and_model_pin(monkeypatch: pytest.MonkeyPatch) -> None:
    import json

    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/embed"
        payload = json.loads(request.content)
        assert payload["model"] == "test-model"
        assert payload["truncate"] is False
        calls.append(payload["input"])
        return httpx.Response(200, json={"embeddings": [[int(t), 1] for t in calls[-1]]})

    fake_ollama(monkeypatch, handler)
    monkeypatch.setattr(stage, "_BATCH_SIZE", 2)
    vectors = stage.embed(["1", "2", "3"], replace(get_settings(), embed_model="test-model"))
    assert calls == [["1", "2"], ["3"]]
    assert vectors == [[1, 1], [2, 1], [3, 1]]


@pytest.mark.parametrize(("status", "body", "message"), [
    (503, {}, "503"),
    (200, {"embeddings": []}, "expected 1 embeddings"),
    (200, {"embeddings": [[1, 2]]}, "dimension 768"),
    (200, {"embeddings": [[True] * 768]}, "non-numeric"),
    (200, {"embeddings": [[0] * 768]}, "zero"),
])
def test_bad_embedding_fails_batch(monkeypatch, status, body, message) -> None:
    fake_ollama(monkeypatch, lambda _request: httpx.Response(status, json=body))
    settings = replace(get_settings(), embed_model="nomic-embed-text")
    with pytest.raises(ValueError, match=f"chunk 0.*{message}"):
        stage.embed(["a"], settings)


def test_dimension_must_match_across_batches(monkeypatch: pytest.MonkeyPatch) -> None:
    values = iter([[[1, 2]], [[1, 2, 3]]])
    fake_ollama(monkeypatch, lambda _req: httpx.Response(200, json={"embeddings": next(values)}))
    monkeypatch.setattr(stage, "_BATCH_SIZE", 1)
    with pytest.raises(ValueError, match=r"chunk 1.*dimension 2"):
        stage.embed(["a", "b"], replace(get_settings(), embed_model="other-model"))
