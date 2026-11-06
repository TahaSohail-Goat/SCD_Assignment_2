# Corpus

The corpus covers FAST-NUCES undergraduate academic rules, student guidance, reporting, and faculty entrepreneurship. It has six public PDFs and 194 physical pages. The [manifest](../corpus/MANIFEST.md) records every URL, document version, physical page count, SHA-256, and local filename. Policy dates describe the editions in the snapshot. The 2019–20 report describes its own reporting period.

| Required property | Verified source or probe |
| --- | --- |
| At least six documents and 40 pages | 2023 undergraduate rules (26), June 2026 academic rules (58), June 2026 student handbook (64), 2019–20 annual report (33), ORIC entrepreneurship policy (8), and the 2026 prospectus rules excerpt (5). |
| Genuine versions of one policy | August 2023 undergraduate rules and June 2026 academic rules. Physical page 20 in the older edition gives a summer term of 8 to 9 weeks. Clause 6.1 on physical page 28 in the newer edition gives 8 weeks. The older edition has `superseded=true`. The prospectus excerpt is a current summary with separate numbering. |
| Image-only PDF | All eight ORIC entrepreneurship-policy pages have no native PDF characters. The August 2023 rules also have 24 pages sent to OCR, including the page containing the old summer-semester rule. |
| Information-bearing table | June 2026 academic rules, physical page 11, clause 2.2 maps A and A- to “Excellent”. The annual report also contains a campus publication-count table on physical page 26. |
| Long definitions and clauses | The June 2026 student handbook has extended generative-AI guidance and definitions. The discussion of acceptable uses starts on physical page 50 and continues on page 51. |
| Deliberately absent topic | Hostel facility references can appear in the handbooks. The corpus omits the dedicated transport and hostel publication. Golden questions ask for two narrower missing facts, the overnight guest curfew and refundable room-key deposit for the Islamabad hostel. |
| Exact terms | Current clauses 1.21 and 1.22 use the attendance percentages and F/A grade. Clause 5.4 has the 2.00 CGPA threshold. The golden set cites physical PDF pages. |

The source publications are publicly downloadable from the [FAST-NUCES Downloads page](https://www.nu.edu.pk/Downloads), the [prospectus](https://www.nu.edu.pk/Admissions/Prospectus), and [ORIC policies](https://nu.edu.pk/Oric/Policies). Public availability gives us a reproducible source, and the repository distributes only provenance and checksums. Keep the downloaded files in the ignored `corpus/raw/` directory and keep the real-corpus image local.

From the repository root, with the indexer dependencies installed:

```powershell
.\.venv\Scripts\python.exe corpus/fetch.py
.\.venv\Scripts\python.exe corpus/fetch.py --verify
```

On the stronger laptop, substitute `python` from the activated virtual environment. The fetcher downloads sequentially with the starter's two-second pause and reuses existing files only after rechecking the pinned SHA-256 and page count. It writes the indexer's `_index.json` after the full set verifies. A publisher change causes a verification error and requires review of the new document and its golden references before updating the pin.
