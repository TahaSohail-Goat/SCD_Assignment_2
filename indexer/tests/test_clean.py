from pipeline.clean import clean
from pipeline.models import Document, Page


def test_clean_removes_furniture_and_preserves_body_and_table() -> None:
    doc = Document("guide.pdf", "2026", False, [
        Page("guide.pdf", page, f"""UNIVERSITY
## Section {page}

Clause 2.4 protects the F/A grade and 2.00 CGPA.
| Grade | Points |
| B+    | 3.33   |
Handbook 2026  {page}""") for page in range(1, 5)
    ])
    result = clean(doc)
    assert result.pages[0].text == (
        "## Section 1\n\nClause 2.4 protects the F/A grade and 2.00 CGPA.\n"
        "| Grade | Points |\n| B+    | 3.33   |"
    )
    assert [page.page for page in result.pages] == [1, 2, 3, 4]
    assert doc.pages[0].text.startswith("UNIVERSITY")


def test_does_not_remove_single_page_headings() -> None:
    doc = Document("guide.pdf", "2026", False, [
        Page("guide.pdf", 1, "\n  ## Rules\n\nA\u00a0rule\u00ad.\n\n\nAnother rule.  \n", True)
    ])
    assert clean(doc).pages == [Page("guide.pdf", 1, "## Rules\n\nA rule.\n\nAnother rule.", True)]
