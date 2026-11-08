import json
from pathlib import Path

import httpx
import pytest

from eval import run_eval

GOOD = {"source": "rules.pdf", "section": "2.2", "page": 11}
OTHER = {"source": "rules.pdf", "section": "2.2", "page": 12}


def test_recall_uses_rank_and_counts_distinct_evidence() -> None:
    refs = [{"source": "rules.pdf", "section": "2.2", "page": 11}, {"chunk_id": "other"}]
    result = [{"chunk_id": "other", **OTHER}] * 3 + [GOOD]
    assert run_eval.recall_at_k(refs + refs, result, 3) == 0.5
    assert run_eval.recall_at_k(refs, result, 5) == 1
    assert run_eval.recall_at_k([], result, 5) is None


@pytest.mark.parametrize(("answered", "citations", "expected"), [
    (True, [GOOD, OTHER], 0.5),
    (True, [], 0.0),
    (False, [], None),
    (False, [GOOD], 0.0),
])
def test_citations_match_all_three_fields(answered, citations, expected) -> None:
    response = {"answered_from_context": answered, "retrieved": [GOOD], "citations": citations}
    assert run_eval.citation_validity(response) == expected


def test_summary_groups_questions_and_checks_abstention() -> None:
    response = {"answered_from_context": True, "citations": [GOOD], "retrieved": [GOOD]}
    rows = [
        {"id": "a", "type": "exact", "must_abstain": False, "relevant": [GOOD],
         "response": response},
        {"id": "b", "type": "abstain", "must_abstain": True, "relevant": [],
         "response": {**response, "answered_from_context": False, "citations": []}},
    ]
    summary = run_eval.summarise(rows)
    assert summary["recall@3"] == summary["recall@5"] == 1
    assert summary["citation_validity"] == summary["abstention_correctness"] == 1
    assert summary["by_type"]["abstain"]["recall@5"] is None
    assert summary["by_type"]["exact"]["recall@5"] == 1


def test_gate_thresholds_and_missing_values() -> None:
    result = {"recall@5": 0.95, "citation_validity": 0.95, "abstention_correctness": 1}
    assert run_eval.gate(result, {"recall@5": 1}) == []
    assert len(run_eval.gate(dict.fromkeys(result), None)) == 3
    broken = {"recall@5": 0.949, "citation_validity": 0.949, "abstention_correctness": 0}
    assert len(run_eval.gate(broken, {"recall@5": 1})) == 3


def test_correct_retrieval_and_citations_cannot_hide_a_wrong_unit_or_missing_fact():
    response = {"answered_from_context": True, "citations": [GOOD], "retrieved": [GOOD],
                "answer": "One credit corresponds to three contact hours."}
    rows = [
        {"id": "quantity", "type": "ordinary", "must_abstain": False, "relevant": [GOOD],
         "required_answer_patterns": [r"1\s+or\s+2\s+credits"], "response": response},
        {"id": "unknown", "type": "abstain", "must_abstain": True, "relevant": [],
         "response": {**response, "answered_from_context": False, "citations": []}},
    ]
    result = run_eval.summarise(rows)
    assert result["recall@5"] == result["citation_validity"] == result["abstention_correctness"] == 1
    assert run_eval.gate(result, {"recall@5": 1}) == [
        "required answer facts or qualifications are missing"]
    response["answer"] = "The unit is assigned 1 or 2 credits."
    assert run_eval.gate(run_eval.summarise(rows), {"recall@5": 1}) == []


def test_cli_writes_failure_details_without_overwriting_baseline(tmp_path, monkeypatch) -> None:
    golden = tmp_path / "golden.yaml"
    golden.write_text(json.dumps({"questions": [
        {"id": "a", "question": "Find the policy", "relevant": [GOOD]},
        {"id": "b", "question": "Outside the corpus", "must_abstain": True},
    ]}), encoding="utf-8")
    baseline, output = tmp_path / "baseline.json", tmp_path / "results.json"
    initial = {"golden": str(golden), "recall@5": 1}
    baseline.write_text(json.dumps(initial), encoding="utf-8")
    monkeypatch.setattr("sys.argv", [
        "run_eval.py", "--api", "http://fake", "--golden", str(golden),
        "--baseline", str(baseline), "--out", str(output), "--update-baseline",
    ])

    def respond(request):
        assert request.url.path == "/api/ask"
        return httpx.Response(200, json={
            "answered_from_context": True, "citations": [OTHER], "retrieved": [OTHER],
        })

    make_client = httpx.Client
    monkeypatch.setattr(run_eval.httpx, "Client",
                        lambda **kw: make_client(transport=httpx.MockTransport(respond), **kw))
    assert run_eval.main() == 1
    assert json.loads(output.read_text())["recall@5"] == 0
    assert json.loads(baseline.read_text()) == initial


def test_real_golden_matches_required_mix() -> None:
    from collections import Counter

    golden = Path(__file__).resolve().parents[1] / "golden.yaml"
    questions = run_eval.load_golden(golden)
    assert Counter(q["type"] for q in questions) == {
        "ordinary": 8, "version": 2, "exact": 2, "abstain": 2, "injection": 1,
    }


def test_missing_baseline_fails_before_sending_any_requests(tmp_path, monkeypatch):
    monkeypatch.setattr("sys.argv", ["run_eval.py", "--api", "http://unreachable",
        "--baseline", str(tmp_path / "missing.json")])
    with pytest.raises(SystemExit) as stopped:
        run_eval.main()
    assert stopped.value.code == 2
