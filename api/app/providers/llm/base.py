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


class GenerationError(ValueError):
    """Invalid output can still have consumed known provider tokens."""

    def __init__(self, message: str, input_tokens: int = 0, output_tokens: int = 0) -> None:
        super().__init__(message)
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class LLMProvider(Protocol):
    name: str

    def generate(self, question: str, passages: list[Passage]) -> GenerationResult:
        """Generate a validated answer and report provider token usage."""
        ...
