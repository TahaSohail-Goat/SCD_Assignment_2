"""Ollama provider: ollama-host or ollama-incluster (section 3.5). Yours to build."""

from __future__ import annotations

import httpx

from ...config import Settings
from ...schemas import Answer, Passage
from ...services.prompt import messages
from .base import GenerationResult


class OllamaProvider:
    name = "ollama"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings   # ollama_url, llm_model, temperature

    def generate(self, question: str, passages: list[Passage]) -> GenerationResult:
        payload = {
            "model": self.settings.llm_model,
            "messages": messages(question, passages),
            "format": Answer.model_json_schema(),
            "stream": False,
            "options": {"temperature": self.settings.temperature},
        }
        with httpx.Client(timeout=120) as client:
            response = client.post(self.settings.ollama_url.rstrip("/") + "/api/chat", json=payload)
            response.raise_for_status()
            body = response.json()
        answer = Answer.model_validate_json(body["message"]["content"])
        return GenerationResult(
            answer=answer,
            input_tokens=int(body.get("prompt_eval_count") or 0),
            output_tokens=int(body.get("eval_count") or 0),
        )
