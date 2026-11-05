# AI usage

| Tool | Work it shaped | Human verification and changes |
| --- | --- | --- |
| OpenAI Codex | API grounding and cache code, Kubernetes manifests, Dockerfiles, workflows, ADRs, documentation, team handoff | Codex read the assignment and code, ran lint, tests and coverage; Student A must review the implementation and final real-corpus results. |
| Ollama `llama3.2:3b` | Runtime answer generation after the real index is integrated | API validates JSON and citations; ungrounded responses must abstain. No model-written answer is treated as policy authority. |
| Ollama `nomic-embed-text` | Runtime query and corpus embeddings after integration | API checks collection model and dimension; indexer tests and evaluation will measure retrieval quality. |

Student B must add their own Codex use and exact verification steps before submission. Do not claim unrun evaluations or screenshots as evidence.
