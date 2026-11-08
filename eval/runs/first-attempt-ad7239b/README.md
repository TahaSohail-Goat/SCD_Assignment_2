# Failed first completion audit, retained for diagnosis

Run: https://github.com/TahaSohail-Goat/SCD_Assignment_2/actions/runs/42508098303

These are actual OCR, Ollama and Chroma measurements from commit `ad7239b`,
8 November 2026. All three configurations failed the unchanged 100% recall@5
baseline at 12/13. They are **not release results** and do not replace the shipped
baseline. The exact six corpus PDFs and their checksums were verified by the run.

The injection question returned in 3ms with an empty retrieval list: `that` in
its malicious preamble was misclassified as a pronoun follow-up. This was a
request-routing error before embedding or generation. The fix extracts the
factual question before follow-up detection, retrieval and caching. A regression
test uses the same grammatical failure with a complete policy question.

The 400/50 run also declined the scanned start-up publication question after two
metadata-validation errors, while the real Kubernetes run answered it correctly.
The retrieved OCR text contained the required DOI, impact-factor, two-year and
affiliation conditions. This is intermittent citation selection, not missing OCR
evidence. Ollama's output grammar now enumerates only retrieved citation objects;
server-side validation still rejects invalid metadata. Document-title matching
also prevents citing duplicated handbook text from a different named document.

Token amplification was genuinely measured: 56,251/51,512 (120/20),
53,725/51,512 (240/35), and 52,720/51,512 (400/50). The diagnostic cache report
used a one-ULP boundary; the final experiment reruns a coarse 0.85/0.90/0.95 grid
with room for floating-point variation. No failed output has been edited to look
successful. Fresh runs must verify the fixes before promotion.
