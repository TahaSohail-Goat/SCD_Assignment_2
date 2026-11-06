"""Extract a document as numbered physical pages."""

from __future__ import annotations

from pathlib import Path

import pdfplumber

from .models import Document, Page


class ExtractionError(ValueError):
    """A document or one of its pages could not be read."""


def _pdf_pages(path: Path) -> list[Page]:
    pages = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            try:
                text = (page.extract_text() or "").strip()
                pages.append(Page(path.name, page.page_number, text))
            finally:
                page.close()
    return pages


def _text_page(path: Path) -> Page:
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".md" and text.startswith("---\n"):
        _, delimiter, body = text[4:].partition("\n---\n")
        if not delimiter:
            raise ExtractionError("unclosed Markdown front matter")
        text = body
    return Page(path.name, 1, text.strip())


def extract(path: str, doc_version: str, superseded: bool) -> Document:
    """Extract physical PDF pages or one logical text page."""
    source = Path(path)
    try:
        suffix = source.suffix.lower()
        if suffix == ".pdf":
            pages = _pdf_pages(source)
        elif suffix in {".md", ".txt"}:
            pages = [_text_page(source)]
        else:
            raise ExtractionError(f"unsupported document type {suffix!r}")
        if not any(page.text for page in pages):
            raise ExtractionError("no readable text in document")
    except Exception as exc:
        raise ExtractionError(f"{source.name}: {exc}") from exc
    return Document(source.name, doc_version, superseded, pages)
