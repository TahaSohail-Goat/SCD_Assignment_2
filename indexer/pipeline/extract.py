"""Extract a document as numbered physical pages."""

from __future__ import annotations

from pathlib import Path

import pdfplumber
import pytesseract
from pdfplumber.page import Page as PDFPage

from .models import Document, Page


class ExtractionError(ValueError):
    """A document or one of its pages could not be read."""


def _native_text(page: PDFPage) -> str:
    # Preserve rows for ruled tables, skipping decorative grids and page frames.
    tables = []
    for table in page.find_tables():
        x0, top, x1, bottom = table.bbox
        if not (0 <= x0 < x1 <= page.width and 0 <= top < bottom <= page.height):
            continue
        rows = [[" ".join((cell or "").split()) for cell in row] for row in table.extract()]
        if sum(sum(bool(cell) for cell in row) >= 2 for row in rows) < 2:
            continue
        text = "\n".join(
            "| " + " | ".join(cell.replace("|", r"\|") for cell in row) + " |"
            for row in rows if any(row)
        )
        tables.append((table.bbox, text))
    if not tables:
        return (page.extract_text() or "").strip()

    def outside_tables(obj: dict) -> bool:
        if obj["object_type"] != "char":
            return True
        x, y = (obj["x0"] + obj["x1"]) / 2, (obj["top"] + obj["bottom"]) / 2
        return not any(x0 <= x < x1 and top <= y < bottom
                       for (x0, top, x1, bottom), _ in tables)

    blocks = [(line["top"], line["text"])
              for line in page.filter(outside_tables).extract_text_lines(return_chars=False)]
    blocks.extend((bbox[1], text) for bbox, text in tables)
    return "\n".join(text for _, text in sorted(blocks)).strip()


def _ocr(page: PDFPage) -> str:
    image = page.to_image(resolution=280, antialias=True).original
    try:
        return str(pytesseract.image_to_string(image, lang="eng", timeout=60)).strip()
    finally:
        image.close()


def _pdf_pages(path: Path) -> list[Page]:
    pages = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            try:
                text = _native_text(page) if page.chars else ""
                # Some scans have a stray digital footer or watermark.
                needs_ocr = not text or (len(text) < 70 and bool(page.images))
                if needs_ocr:
                    text = _ocr(page) or text
                pages.append(Page(path.name, page.page_number, text, ocr=needs_ocr))
            except Exception as exc:
                raise ExtractionError(f"page {page.page_number}: {exc}") from exc
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
