from pathlib import Path

import pytest
from pypdf import PdfWriter
from pypdf.generic import (
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
)

from pipeline.extract import ExtractionError, extract


def write_pdf(path: Path, *texts: str, operators: str = "") -> None:
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
        stream.set_data(f"BT /F1 12 Tf 15 170 Td ({text}) Tj ET {operators}".encode())
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


def test_empty_pdf_page_calls_mock_ocr(tmp_path, monkeypatch) -> None:
    path = tmp_path / "scanned.pdf"
    write_pdf(path, "Native text", "")
    calls = []

    def fake_ocr(image, *, lang, timeout):
        calls.append((image.size, lang, timeout))
        return "Read by OCR"

    monkeypatch.setattr("pipeline.extract.pytesseract.image_to_string", fake_ocr)
    doc = extract(str(path), "2023", True)
    assert [(page.text, page.ocr) for page in doc.pages] == [
        ("Native text", False), ("Read by OCR", True),
    ]
    assert len(calls) == 1
    assert calls[0][1] == "eng"


@pytest.mark.parametrize("failure", ["missing-engine", "empty"])
def test_ocr_failure_or_wholly_unreadable_scan_fails(tmp_path, monkeypatch, failure) -> None:
    path = tmp_path / "scanned.pdf"
    write_pdf(path, "")

    def fake_ocr(*_args, **_kwargs):
        if failure == "missing-engine":
            raise RuntimeError("engine missing")
        return "   "

    monkeypatch.setattr("pipeline.extract.pytesseract.image_to_string", fake_ocr)
    match = "page 1: engine missing" if failure == "missing-engine" else "no readable text"
    with pytest.raises(ExtractionError, match=match):
        extract(str(path), "2023", True)


def test_ruled_pdf_table_retains_column_and_row_order(tmp_path) -> None:
    path = tmp_path / "table.pdf"
    operators = "15 70 200 70 re S 15 105 m 215 105 l S 90 70 m 90 140 l S "
    for text, x, y in [("Grade", 20, 120), ("Points", 100, 120),
                       ("B+", 20, 85), ("3.33", 100, 85)]:
        operators += f"BT /F1 12 Tf {x} {y} Td ({text}) Tj ET "
    write_pdf(path, "Grade points", operators=operators)
    doc = extract(str(path), "2026", False)
    assert doc.pages[0].text == "Grade points\n| Grade | Points |\n| B+ | 3.33 |"


def test_text_outside_visible_page_is_not_retrievable(tmp_path) -> None:
    path = tmp_path / "booklet.pdf"
    write_pdf(path, "Rule A", operators="BT /F1 12 Tf 330 170 Td (Adjacent page) Tj ET")
    doc = extract(str(path), "2026", False)
    assert doc.pages[0].text == "Rule A"
