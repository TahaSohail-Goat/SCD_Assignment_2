# ADR 0005: Render complete cited evidence and retain bounded turns

Status: accepted for implementation, 8 November 2026; fresh live-model evaluation pending.

## Context

The previous real model returned valid citation triples but omitted conditions:
DOI/affiliation in the publication rule, F/A in the attendance consequence, and the
HoD condonement qualification. It also omitted inline markers. Merely asking for
a more complete answer did not enforce these requirements. The API had no turn
store, and lexical follow-up detection missed questions such as “Can I do that?”.

## Decision

The model still selects evidence and returns the required `Answer` schema. After
validating that its citations were actually retrieved, the server displays a
complete selected chunk, sentence by sentence with exact citation markers,
instead of trusting the model's paraphrase. Selection prefers an explicitly named
clause, then lexical relevance and dense score. Instruction-like attack lines are
not displayed as policy. This is generic evidence rendering; application code
does not import golden questions or expected answers.

The request accepts an optional `session_id` matching a bounded opaque identifier.
The old `{question: ...}` request remains valid and the response schema is unchanged.
UI tabs generate identifiers with browser randomness. Redis stores expiring turns
and the latest complete question for one hour. Follow-ups bypass semantic cache;
with no usable context, the API asks the user to restate the complete question.
Cache scope changes invalidate earlier response-format entries.

## Alternatives

Prompt-only paraphrase validation was insufficient in the saved run. A second
model as a truth judge adds cost and another fallible model. Returning full raw
retrieval without selection would overwhelm users and expose poisoned lines.
No turn persistence would leave the query pipeline's final step unimplemented.

## Consequences

Answers are longer and more extractive, but include source qualifications and
never display invented model prose as a policy claim. A complete relevant chunk
still depends on correct extraction/chunking and evidence selection. OCR errors,
cross-chunk rules and poorly selected passages remain limitations to evaluate.
The fixed citation-membership guard remains mandatory. Session IDs are correlation
tokens, not authorization; no private corpus or authenticated user data is served.
Users should not submit personal/student identifiers. Redis turn TTL is separate
from the 24-hour semantic cache TTL; chain of thought is never persisted or shown.
