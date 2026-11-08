"""Hosted free-tier provider (Groq, Google AI Studio, OpenRouter). Yours to build.

The key arrives as LLM_API_KEY from a Kubernetes Secret created on the command
line. It never appears in a file you commit, and never in a log line.
"""

from __future__ import annotations

import httpx

from ...config import Settings
from ...schemas import Answer, Passage
from ...services.prompt import messages
from .base import GenerationError, GenerationResult


class HostedProvider:
    name = "hosted"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings   # hosted_base_url, llm_model, llm_api_key, temperature

    def generate(self, question: str, passages: list[Passage]) -> GenerationResult:
        if not self.settings.hosted_base_url or not self.settings.llm_api_key:
            raise ValueError("HOSTED_BASE_URL and LLM_API_KEY are required for hosted mode")
        url = self.settings.hosted_base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.settings.llm_model,
            "messages": messages(question, passages),
            "response_format": {"type": "json_object"},
            "temperature": self.settings.temperature,
        }
        with httpx.Client(timeout=120) as client:
            response = client.post(
                url, json=payload, headers={"Authorization": "Bearer " + self.settings.llm_api_key}
            )
            response.raise_for_status()
            body = response.json()
        usage = body.get("usage") or {}
        input_tokens = int(usage.get("prompt_tokens") or 0)
        output_tokens = int(usage.get("completion_tokens") or 0)
        try:
            answer = Answer.model_validate_json(body["choices"][0]["message"]["content"])
        except ValueError as exc:
            raise GenerationError("invalid model schema", input_tokens, output_tokens) from exc
        return GenerationResult(
            answer=answer,
            input_tokens=input_tokens, output_tokens=output_tokens,
        )
