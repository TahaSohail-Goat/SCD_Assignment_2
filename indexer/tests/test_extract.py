from pathlib import Path

import pytest
from pypdf import PdfWriter
from pypdf.generic import (
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
)

from pipeline.extract import ExtractionError, extract


def write_pdf(path: Path, *texts: str) -> None:
    writer = PdfWriter()
    for text in texts:
        writer.add_blank_page(width=300, height=200)
        page = writer.pages[-1]
        if not text:
            continue
        font = DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        })
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): font}),
        })
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 15 170 Td ({text}) Tj ET".encode())
        page.replace_contents(stream)
    writer.write(path)


def test_extract_pdf_keeps_physical_page_numbers(tmp_path: Path) -> None:
    path = tmp_path / "policy.pdf"
    write_pdf(path, "First page", "Second page")
    doc = extract(str(path), "2026", False)
    assert doc.source == path.name
    assert [(p.page, p.text, p.ocr) for p in doc.pages] == [
        (1, "First page", False), (2, "Second page", False),
    ]


def test_extract_strips_markdown_front_matter(tmp_path: Path) -> None:
    path = tmp_path / "policy.md"
    path.write_text("---\ndoc_version: 2025\n---\n## Attendance\n\nPolicy text", encoding="utf-8")
    doc = extract(str(path), "2025", True)
    assert doc.doc_version == "2025"
    assert doc.superseded is True
    assert doc.pages[0].text == "## Attendance\n\nPolicy text"


@pytest.mark.parametrize("body", [b"", b"definitely not a PDF"])
def test_unreadable_pdf_identifies_file(tmp_path: Path, body: bytes) -> None:
    path = tmp_path / "broken.pdf"
    path.write_bytes(body)
    with pytest.raises(ExtractionError, match=r"broken\.pdf"):
        extract(str(path), "2026", False)
