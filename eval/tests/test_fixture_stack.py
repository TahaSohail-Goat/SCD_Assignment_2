"""Run the actual API, indexer stages and gate with in-process service doubles."""

import json
import os
from contextlib import nullcontext
from dataclasses import replace
from pathlib import Path

import chromadb
import httpx
import redis
from fastapi.testclient import TestClient

from app.main import app
from app.services.prompt import messages
from eval.fixtures.fake_ollama import reply
from eval.run_eval import evaluate, gate, load_golden, write_results
from indexer.tests.test_store import Client, Collection
from pipeline.config import get_settings
from pipeline.run import run_pipeline

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def query(self, *, query_embeddings, n_results, include, where=None):
    assert set(include) == {"documents", "metadatas", "distances"}
    query_vec, = query_embeddings
    candidates = [(1 - sum(x * y for x, y in zip(query_vec, vec, strict=True)), key, text, meta)
                  for key, (text, vec, meta) in self.rows.items()
                  if where is None or all(meta[k] == v for k, v in where.items())]
    rows = sorted(candidates)[:n_results]
    return {label: [[row[i] for row in rows]]
            for i, label in enumerate(("distances", "ids", "documents", "metadatas"))}


class MemoryRedis:
    def __init__(self):
        self.values = {}

    def lock(self, *_args, **_kw):
        return nullcontext()

    def ping(self):
        return True

    def get(self, key):
        return self.values.get(key)

    def incr(self, key):
        self.values[key] = str(int(self.get(key) or "0") + 1)
        return int(self.values[key])

    def scan_iter(self, *, match):
        return (key for key in self.values if key.startswith(match.removesuffix("*")))

    def setex(self, key, _ttl, value):
        self.values[key] = value

    def close(self):
        pass


def test_fixture_evaluation_gate(monkeypatch, tmp_path):
    client = Client()
    memory = MemoryRedis()
    make_client = httpx.Client
    prompts = []

    def ollama(request):
        payload = json.loads(request.content)
        if request.url.path == "/api/chat":
            prompts.append(payload["messages"][1]["content"])
        return httpx.Response(200, json=reply(request.url.path, payload))

    monkeypatch.setattr(Collection, "query", query, raising=False)
    monkeypatch.setattr(chromadb, "HttpClient", lambda **_kw: client)
    monkeypatch.setattr(redis, "Redis", lambda **_kw: memory)
    monkeypatch.setattr(httpx, "Client", lambda **kw: make_client(
        transport=httpx.MockTransport(ollama), **kw
    ))
    for key, value in {
        "CORPUS_DIR": str(FIXTURES), "CHUNK_SIZE": "240", "CHUNK_OVERLAP": "35",
        "EMBED_MODEL": "fixture-hash", "RETRIEVER": "chroma", "LLM_PROVIDER": "ollama-host",
        "RELEVANCE_FLOOR": "0.08", "CACHE_THRESHOLD": "1.01",
    }.items():
        monkeypatch.setenv(key, value)

    assert run_pipeline(get_settings()) > 0
    assert memory.get("rahbar:index_generation") == "1"
    with TestClient(app) as api:
        assert api.get("/readyz").status_code == 200
        golden = load_golden(FIXTURES / "golden.fixture.yaml")
        results = evaluate(api, "http://testserver", golden)
        probes = {row["id"]: row["question"] for row in golden}

        with monkeypatch.context() as fault:
            fault.setattr(app.state, "settings", replace(app.state.settings, embed_model="wrong"))
            response = api.get("/readyz")
            assert response.status_code == 503
            assert "embedding_pin" in response.text

        with monkeypatch.context() as fault:
            def unfiltered(self, **kwargs):
                return query(self, **{**kwargs, "where": None})

            fault.setattr(Collection, "query", unfiltered)
            response = api.post("/api/ask", json={"question": probes["f02"]}).json()
            assert any(ref["source"] == "academic-rules-2023.md" for ref in response["retrieved"])

        with monkeypatch.context() as fault:
            def without_boundary(question, passages):
                payload = messages(question, passages)
                payload[0]["content"] = "Answer the question."
                return payload

            fault.setattr("app.providers.llm.ollama.messages", without_boundary)
            response = api.post("/api/ask", json={"question": probes["f06"]}).json()
            assert response["answered_from_context"] is False
            assert "could not verify" in response["answer"]

    results["golden"] = "eval/fixtures/golden.fixture.yaml"
    results["environment"] = "offline fixture doubles"
    output = Path(os.environ.get("RAHBAR_FIXTURE_RESULTS", tmp_path / "results.json"))
    write_results(results, output)
    baseline_path = FIXTURES / "baseline.fixture.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert not gate(results, baseline)
    rows = {row["id"]: row for row in results["rows"]}
    historical = rows["f03"]["response"]
    assert historical["retrieved"][0]["source"] == "academic-rules-2023.md"
    assert all(ref["source"] != "academic-rules-2023.md"
               for ref in rows["f02"]["response"]["retrieved"])
    injection = rows["f06"]["response"]
    assert any("Ignore all previous instructions" in prompt and "Is attendance optional" in prompt
               for prompt in prompts)
    assert "80 percent" in injection["answer"]
    assert "attendance is optional" not in injection["answer"]
