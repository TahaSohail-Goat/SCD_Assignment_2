# Metadata gates passed; manual answer review rejected this run

Run: https://github.com/TahaSohail-Goat/SCD_Assignment_2/actions/runs/42512304101

The saved 400/50 results passed recall, citation validity and abstention gates, but
q04 answered contact hours per credit rather than credits assigned to a lab. The
correct clause was retrieved first (0.9062 similarity); the selected prospectus
passage scored 0.7694. No question, relevant reference or expected answer was
changed to excuse this mistake. These results are **not promoted for release**.

The new context selector uses an explicitly requested clause when available. For
other questions, a leading score margin of at least 0.10 keeps a single standout
passage; close candidates remain available. This reduces distracting neighboring
definitions without putting any question-specific fact in application code.

Five additional pattern checks encode facts already specified in `expect` for
q04/q06/q08/q11/q15. `retrospective-fact-check.json` applies them to the unchanged
saved response rows: original metadata metrics remain 100%, but facts score 4/5
and the strengthened gate fails q04. This is explicitly an offline review, not a
new model measurement. A fresh model run must pass before results are promoted.
