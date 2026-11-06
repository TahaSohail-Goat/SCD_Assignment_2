"""Chunk one physical page and section at a time, retaining exact evidence text."""

from __future__ import annotations

import hashlib
import re
from bisect import bisect_right
from collections.abc import Iterator

from .models import Chunk, Document

_MARKDOWN = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
_CLAUSE = re.compile(r"^(\d{1,2}(?:\.\d{1,2})+)[.)]?\s+\S")
_SECTION = re.compile(r"^\d{1,2}\.\s+[^\d|].*")
_WORD = re.compile(r"\S+")
_PARAGRAPH = re.compile(r"\n\s*\n|(?m:^[ \t]*\|[^\n]*\n)")
_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def _windows(text: str, size: int, overlap: int) -> Iterator[str]:
    words = list(_WORD.finditer(text))
    starts = [word.start() for word in words]
    boundaries = [
        sorted({bisect_right(starts, match.end() - 1) for match in pattern.finditer(text)})
        for pattern in (_PARAGRAPH, _SENTENCE)
    ]
    start = 0
    while start < len(words):
        end = min(start + size, len(words))
        if end < len(words):
            for options in boundaries:
                position = bisect_right(options, end) - 1
                if position >= 0 and options[position] >= start + max(overlap + 1, size // 2):
                    end = options[position]
                    break
        yield text[words[start].start():words[end - 1].end()]
        if end == len(words):
            break
        start = end - overlap


def chunk(doc: Document, size: int, overlap: int) -> list[Chunk]:
    """Prefer section, paragraph and sentence boundaries within a word budget."""
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError("chunk size must be positive and 0 <= overlap < size")

    pieces = []
    section = "Document"
    markdown = doc.source.lower().endswith(".md")
    for page in doc.pages:
        sections: list[tuple[str, list[str]]] = [(section, [])]
        for line in page.text.splitlines():
            stripped = line.strip()
            if heading := _MARKDOWN.fullmatch(stripped):
                section = heading[1]
            elif not markdown and (clause := _CLAUSE.match(stripped)):
                section = clause[1]
            elif not markdown and _SECTION.fullmatch(stripped):
                section = stripped
            else:
                sections[-1][1].append(line)
                continue
            sections.append((section, [stripped]))
        offset = 0
        for label, lines in sections:
            for text in _windows("\n".join(lines), size, overlap):
                identity = f"{doc.source}\0{doc.doc_version}\0{page.page}\0{offset}\0{text}"
                pieces.append(Chunk(hashlib.sha256(identity.encode()).hexdigest(), text,
                                    doc.source, label, page.page, doc.doc_version, doc.superseded))
                offset += 1
    return pieces
