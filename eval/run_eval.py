#!/usr/bin/env python3
"""Score a running RAHBAR against a golden set, and gate CI on the result (section 5).

    python eval/run_eval.py --api http://<ingress>                 # your corpus
    python eval/run_eval.py --api ... --golden eval/fixtures/golden.fixture.yaml
    python eval/run_eval.py --api ... --update-baseline            # after a deliberate improvement

Exit code 0 when every gate passes, 1 when any fails. CI relies on that exit code.

The fixture runner can supply the same evaluator with an in-process API transport.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from statistics import mean
from pathlib import Path

import httpx
import yaml

HERE = Path(__file__).resolve().parent

# The gate from section 5.4. Change these only with a reason written in docs/PIPELINE.md.
MAX_RECALL5_DROP = 0.05        # recall@5 may fall at most 5 points below the baseline
MIN_CITATION_VALIDITY = 0.95   # at least 95% of citations must match retrieved passages
REQUIRED_ABSTENTION = 1.0      # every must-abstain question must be declined


def load_golden(path: Path) -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    questions = data.get("questions") or []
    if not questions:
        sys.exit(f"no questions in {path}")
    return questions


def ask(client: httpx.Client, api: str, question: str) -> dict:
    """POST one question and return the AskResponse as a dict (see api/app/schemas.py)."""
    response = client.post(f"{api.rstrip('/')}/api/ask", json={"question": question})
    response.raise_for_status()
    return response.json()


def recall_at_k(relevant: list[dict], retrieved: list[dict], k: int) -> float | None:
    """Match distinct evidence references by their explicitly supplied fields."""
    fields = ("chunk_id", "source", "section", "page")
    references = {tuple((key, ref[key]) for key in fields if key in ref) for ref in relevant}
    if not references:
        return None
    if any(not dict(ref).keys() & {"chunk_id", "source"} for ref in references):
        raise ValueError("each relevant reference needs a chunk_id or source")
    return sum(
        any(all(passage.get(key) == value for key, value in ref) for passage in retrieved[:k])
        for ref in references
    ) / len(references)


def _citation_counts(response: dict) -> tuple[int, int]:
    def key(ref: dict) -> tuple:
        return ref["source"], ref["section"], ref.get("page")

    citations = response["citations"]
    allowed = {key(ref) for ref in response["retrieved"]}
    if not response["answered_from_context"]:
        return 0, len(citations)
    return sum(key(citation) in allowed for citation in citations), max(1, len(citations))


def citation_validity(response: dict) -> float | None:
    """Match exact source, section and page; a grounded answer needs a citation."""
    valid, total = _citation_counts(response)
    return valid / total if total else None


def _metrics(rows: list[dict]) -> dict:
    valid = total = 0
    for row in rows:
        right, checked = _citation_counts(row["response"])
        valid += right
        total += checked
    abstentions = [row["abstention_correct"] for row in rows if row["must_abstain"]]
    return {
        **{f"recall@{k}": mean(scores) if (scores := [
            row[f"recall@{k}"] for row in rows if row[f"recall@{k}"] is not None
        ]) else None for k in (3, 5)},
        "citation_validity": valid / total if total else None,
        "valid_citations": valid,
        "checked_citations": total,
        "abstention_correctness": mean(abstentions) if abstentions else None,
        "must_abstain_questions": len(abstentions),
        "questions": len(rows),
    }


def summarise(rows: list[dict]) -> dict:
    """Compute macro recall over answerable questions and micro citation validity."""
    groups = defaultdict(list)
    scored = []
    for row in rows:
        response = row["response"]
        result = {
            **row,
            "recall@3": recall_at_k(row["relevant"], response["retrieved"], 3),
            "recall@5": recall_at_k(row["relevant"], response["retrieved"], 5),
            "citation_validity": citation_validity(response),
            "abstention_correct": (
                response["answered_from_context"] is False and not response["citations"]
                if row["must_abstain"] else None
            ),
        }
        scored.append(result)
        groups[row["type"]].append(result)
    return {**_metrics(scored), "by_type": {kind: _metrics(group)
                                            for kind, group in sorted(groups.items())},
            "rows": scored}


def gate(results: dict, baseline: dict | None) -> list[str]:
    """Return all failed gates; do not let missing data pass by default."""
    failures = []
    recall5 = results["recall@5"]
    if recall5 is None:
        failures.append("no recall@5 evidence to score")
    elif baseline is not None and (
        baseline["recall@5"] - recall5 > MAX_RECALL5_DROP + 1e-12
    ):
        failures.append(f"recall@5 {recall5:.1%} fell below baseline {baseline['recall@5']:.1%}")
    validity = results["citation_validity"]
    if validity is None or validity < MIN_CITATION_VALIDITY:
        failures.append(f"citation validity {validity!r} is below {MIN_CITATION_VALIDITY:.0%}")
    if results["abstention_correctness"] != REQUIRED_ABSTENTION:
        failures.append("all must-abstain questions must be declined without citations")
    return failures


def evaluate(client: httpx.Client, api: str, questions: list[dict]) -> dict:
    rows = []
    for q in questions:
        started = time.perf_counter()
        response = ask(client, api, q["question"])
        rows.append({
            "id": q["id"], "type": q.get("type", "ordinary"),
            "question": q["question"], "must_abstain": bool(q.get("must_abstain", False)),
            "relevant": q.get("relevant") or [], "expect": q.get("expect"),
            "response": response, "seconds": round(time.perf_counter() - started, 3),
        })
    return summarise(rows)


def write_results(results: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate RAHBAR against a golden set.")
    parser.add_argument("--api", required=True, help="base URL, e.g. http://192.168.49.2")
    parser.add_argument("--host", help="Host header, when your Ingress rule names a host")
    parser.add_argument("--golden", type=Path, default=HERE / "golden.yaml")
    parser.add_argument("--baseline", type=Path, default=HERE / "baseline.json")
    parser.add_argument("--out", type=Path, default=HERE / "results.json")
    parser.add_argument("--update-baseline", action="store_true",
                        help="write these results as the new baseline")
    args = parser.parse_args()

    questions = load_golden(args.golden)
    headers = {"Host": args.host} if args.host else {}
    with httpx.Client(timeout=120.0, headers=headers) as client:
        results = evaluate(client, args.api, questions)

    results["golden"] = args.golden.resolve().relative_to(HERE.parent).as_posix() \
        if args.golden.resolve().is_relative_to(HERE.parent) else str(args.golden)
    baseline = json.loads(args.baseline.read_text(encoding="utf-8")) if args.baseline.exists() else None
    if baseline and baseline.get("golden") != results["golden"]:
        parser.error("baseline belongs to a different golden set; specify the matching --baseline")
    failures = gate(results, baseline)
    write_results(results, args.out)
    print(f"results written to {args.out}")
    if args.update_baseline and not failures:
        write_results({key: value for key, value in results.items() if key != "rows"}, args.baseline)
        print(f"baseline updated: {args.baseline}")

    if failures:
        print("\nGATE FAILED")
        for message in failures:
            print(f"  - {message}")
        return 1
    print("\ngate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
