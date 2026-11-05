"""The LLM provider interface (section 3.5). Swapping providers is one file."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ...schemas import Answer, Passage


@dataclass(frozen=True)
class GenerationResult:
    answer: Answer
    input_tokens: int = 0
    output_tokens: int = 0


class LLMProvider(Protocol):
    name: str

    def generate(self, question: str, passages: list[Passage]) -> GenerationResult:
        """Generate a validated answer and report provider token usage."""
        ...
