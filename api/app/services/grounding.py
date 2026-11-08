"""Render complete, verbatim policy evidence selected by the model.

The model selects evidence; the server renders its text instead of trusting an
unverifiable paraphrase. No question-specific answers are embedded in code.
"""

from __future__ import annotations

import re

from ..schemas import Answer, Citation, Passage

_COMMAND = re.compile(
    r"(?:ignore|disregard|override|forget).{0,50}(?:instructions|rules)|"
    r"(?:reveal|print).{0,30}(?:secret|password|system prompt)", re.I,
)
_WORDS = re.compile(r"[a-z]{3,}|\d+(?:\.\d+)*", re.I)
_SENTENCES = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def render_evidence(answer: Answer, passages: list[Passage], question: str) -> Answer:
    """Keep whole chunks/conditions, exact metadata, and a marker per sentence.

    Navigation and instruction-like poisoned lines are omitted from display,
    but were still sent to the provider as untrusted evidence for the security
    test. Evidence text is never executed or interpreted as a command.
    """
    if not answer.answered_from_context:
        return answer
    allowed = {(c.source, c.section, c.page) for c in answer.citations}
    candidates = [p for p in passages if (p.source, p.section, p.page) in allowed]
    words = set(_WORDS.findall(question.casefold()))
    clause = re.search(r"\bclause\s+(\d+(?:\.\d+)+)", question, re.I)

    def rank(p: Passage) -> tuple[bool, int, float]:
        return (bool(clause and p.section == clause[1]),
                len(words & set(_WORDS.findall(p.text.casefold()))), p.score)

    # Prefer the precise requested clause. One complete chunk avoids dropping
    # a qualification while also avoiding an unrelated list of model citations.
    selected = max(candidates, key=rank)
    marker = f"[{selected.source} / {selected.section}]"
    blocks: list[str] = []
    paragraph: list[str] = []

    def flush() -> None:
        if paragraph:
            blocks.extend(f"{sentence} {marker}" for sentence in
                          _SENTENCES.split(" ".join(paragraph)))
            paragraph.clear()

    for line in selected.text.splitlines():
        line = line.strip()
        if not line:
            flush()
            continue
        if line.startswith("#") or _COMMAND.search(line):
            continue
        if line.startswith("|"):
            flush()
            blocks.append(f"{line} {marker}")
        else:
            paragraph.append(line)
    flush()
    if not blocks:
        raise ValueError("selected evidence contains no safe policy text")
    return answer.model_copy(update={
        "answer": "\n".join(blocks),
        "citations": [Citation(source=selected.source, section=selected.section, page=selected.page)],
    })
