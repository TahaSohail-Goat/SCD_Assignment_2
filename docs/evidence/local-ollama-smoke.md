# Local Ollama smoke check — 2026-11-06

Environment: Windows Ollama at `http://127.0.0.1:11434`, model `llama3.2:3b`, with the repository's `OllamaProvider`. This check used a synthetic passage. It does **not** measure real-corpus retrieval or assignment accuracy.

## No relevant evidence

`answer_question("What is the attendance requirement?", StubRetriever(), OllamaProvider(settings), settings)` returned `answered_from_context: false`, `citations: []`, and `confidence: low`. The stub passages describe the stub itself and contain no attendance rule.

## Explicit synthetic evidence

The passage text was: “For this synthetic test policy only, students must attend 80 percent of classes.” Its citation triple was `synthetic-test.pdf / Attendance / page 4`. `OllamaProvider.generate()` returned `answer: "80 percent"`, `answered_from_context: true`, `confidence: high`, and exactly that citation triple.

Both calls completed through the real locally installed Ollama service. The production corpus and Chroma retrieval still need the teammate's indexer and evaluation branch.
