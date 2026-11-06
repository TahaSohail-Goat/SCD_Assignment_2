"""Remove repeated page furniture while retaining meaningful line structure."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import replace

from .models import Document

_PAGE = re.compile(r"^(?:page\s+\d+(?:\s+of\s+\d+)?|[-–]\s*\d+\s*[-–])$", re.I)
_LEADING_PAGE = re.compile(r"^\d{1,3}\s+(?=[A-Za-z])")
_TRAILING_PAGE = re.compile(r"\s+\d{1,3}$")


def _edge_key(line: str, *, footer: bool) -> str | None:
    line = line.strip()
    if not line or line.startswith(("#", "|")) or re.match(r"\d+\.", line):
        return None
    if footer:
        line = _TRAILING_PAGE.sub("", _LEADING_PAGE.sub("", line))
    return " ".join(line.casefold().split())


def clean(doc: Document) -> Document:
    """Strip recurring first and last lines only, leaving clauses and table rows intact."""
    page_lines = []
    for page in doc.pages:
        text = unicodedata.normalize("NFC", page.text)
        text = text.replace("\u00ad", "").replace("\u00a0", " ").replace("\u200b", "")
        lines = [line.rstrip() for line in text.splitlines()]
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        page_lines.append(lines)

    headers = Counter(_edge_key(lines[0], footer=False) for lines in page_lines if len(lines) > 2)
    footers = Counter(_edge_key(lines[-1], footer=True) for lines in page_lines if len(lines) > 2)
    threshold = max(3, (sum(bool(lines) for lines in page_lines) + 1) // 2)
    pages = []
    for page, lines in zip(doc.pages, page_lines, strict=True):
        if len(lines) > 2 and headers[_edge_key(lines[0], footer=False)] >= threshold:
            if _edge_key(lines[0], footer=False) is not None:
                lines = lines[1:]
        if len(lines) > 1 and _edge_key(lines[-1], footer=True) is not None:
            if footers[_edge_key(lines[-1], footer=True)] >= threshold or _PAGE.fullmatch(
                lines[-1].strip()
            ):
                lines = lines[:-1]
        text = re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", "\n".join(lines))
        pages.append(replace(page, text=text.strip()))
    return replace(doc, pages=pages)
