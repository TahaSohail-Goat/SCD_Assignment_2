import pytest

from pipeline.chunk import chunk
from pipeline.models import Document, Page


def test_sections_continue_across_pages_and_chunks_never_cross_pages() -> None:
    doc = Document("rules.pdf", "2023-08", True, [
        Page("rules.pdf", 8, "1. Attendance\n\n1.21 All students must attend."),
        Page("rules.pdf", 9, "The HoD may condone absence.\n\n1.22 F/A grade applies."),
    ])
    pieces = chunk(doc, 50, 5)
    assert [(p.section, p.page) for p in pieces] == [
        ("1. Attendance", 8), ("1.21", 8), ("1.21", 9), ("1.22", 9),
    ]
    assert pieces[2].metadata() == {
        "source": "rules.pdf", "page": 9, "section": "1.21",
        "doc_version": "2023-08", "superseded": True,
    }


def test_overlap_is_bounded_and_ids_are_stable() -> None:
    text = " ".join(f"word{i}" for i in range(19))
    doc = Document("rules.md", "2026", False, [Page("rules.md", 1, text)])
    pieces = chunk(doc, 8, 3)
    assert [len(p.text.split()) for p in pieces] == [8, 8, 8, 4]
    assert pieces[0].text.split()[-3:] == pieces[1].text.split()[:3]
    assert len({p.id for p in pieces}) == len(pieces)
    assert pieces == chunk(doc, 8, 3)
    assert pieces[0].metadata()["superseded"] is False
    assert chunk(Document("rules.md", "2023", True, doc.pages), 8, 3)[0].id != pieces[0].id


@pytest.mark.parametrize(("size", "overlap"), [(0, 0), (10, 10), (10, -1)])
def test_chunk_settings_must_allow_forward_progress(size: int, overlap: int) -> None:
    with pytest.raises(ValueError, match="overlap"):
        chunk(Document("rules.pdf", "2026", False), size, overlap)


def test_markdown_numbered_items_remain_under_explicit_heading() -> None:
    doc = Document("rules.md", "2026", False, [
        Page("rules.md", 1, "## 1. Attendance\n\n1.1 All students must attend."),
    ])
    [piece] = chunk(doc, 50, 5)
    assert piece.section == "1. Attendance"
    assert "1.1 All students must attend." in piece.text
