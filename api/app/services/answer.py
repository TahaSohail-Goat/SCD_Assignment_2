"""The request path: cache, retrieval, grounding, validation and fallback."""

from __future__ import annotations

import logging
import time

from ..config import Settings
from ..logjson import request_id_var
from ..providers.llm.base import LLMProvider
from ..retrieval.base import Retriever
from ..retrieval.chroma import is_historical_question
from ..routes import metrics
from ..schemas import Answer, AskResponse, Passage, RetrievedRef
from .cache import SemanticCache, is_follow_up

log = logging.getLogger("rahbar.answer")
_NO_EVIDENCE = "The available corpus does not contain enough evidence to answer this question."
_FALLBACK = "I could not verify a grounded answer. Please try again later."


def _citations_valid(answer: Answer, passages: list[Passage]) -> bool:
    if not answer.answered_from_context:
        return not answer.citations
    allowed = {(p.source, p.section, p.page) for p in passages}
    return bool(answer.citations) and all(
        (c.source, c.section, c.page) in allowed for c in answer.citations
    )


def _response(answer: Answer, passages: list[Passage], provider: str) -> AskResponse:
    return AskResponse(
        request_id=request_id_var.get(), answer=answer.answer, citations=answer.citations,
        answered_from_context=answer.answered_from_context, confidence=answer.confidence,
        retrieved=[RetrievedRef(
            chunk_id=p.chunk_id, source=p.source, section=p.section, page=p.page, score=p.score
        ) for p in passages],
        provider=provider,
    )


def answer_question(
    question: str, retriever: Retriever, provider: LLMProvider, settings: Settings,
    cache: SemanticCache | None = None,
) -> AskResponse:
    embedding: list[float] | None = None
    generation_id = None
    skip_cache = is_follow_up(question) or is_historical_question(question)
    if retriever.name == "chroma":
        embedding = retriever.embed(question)
    if not skip_cache and embedding is not None and cache is not None:
        try:
            generation_id = cache.generation_id()
            cached = cache.lookup(embedding, generation_id=generation_id)
            if cached is not None:
                metrics.record_cache_lookup("hit")
                log.info("cache hit", extra={"provider": cached.provider})
                return cached.model_copy(update={"request_id": request_id_var.get(), "cached": True})
            metrics.record_cache_lookup("miss")
        except Exception as exc:
            metrics.record_cache_lookup("error")
            log.warning("cache lookup failed", extra={"error": type(exc).__name__})
    else:
        metrics.record_cache_lookup("skipped")

    started = time.perf_counter()
    passages = retriever.retrieve(question, k=settings.top_k, embedding=embedding)
    metrics.RETRIEVAL_LATENCY.observe(time.perf_counter() - started)
    grounded = [p for p in passages if p.score >= settings.relevance_floor]

    valid_generation = False
    if not grounded:
        answer = Answer(reasoning="no passage cleared the relevance floor", answer=_NO_EVIDENCE,
                        citations=[], answered_from_context=False, confidence="low")
    else:
        answer = Answer(reasoning="model output unavailable", answer=_FALLBACK, citations=[],
                        answered_from_context=False, confidence="low")
        for attempt in range(2):  # retry once on invalid JSON, citations or provider failure
            generated_at = time.perf_counter()
            try:
                result = provider.generate(question, grounded)
                candidate = result.answer
                if not _citations_valid(candidate, grounded):
                    raise ValueError("model cited evidence that was not retrieved")
                answer = candidate
                metrics.TOKENS.labels(provider=provider.name, direction="input").inc(result.input_tokens)
                metrics.TOKENS.labels(provider=provider.name, direction="output").inc(result.output_tokens)
                valid_generation = True
                break
            except Exception as exc:
                log.warning("retrying invalid generation" if attempt == 0 else "invalid generation",
                            extra={"attempt": attempt + 1, "error": type(exc).__name__})
            finally:
                metrics.GENERATION_LATENCY.observe(time.perf_counter() - generated_at)
        if not valid_generation:
            metrics.FALLBACKS.inc()

    if not answer.answered_from_context:
        metrics.ABSTENTIONS.inc()
    response = _response(answer, passages, provider.name)
    if (generation_id is not None and valid_generation and answer.answered_from_context
            and embedding is not None and cache is not None):
        try:
            cache.store(question, embedding, response, generation_id=generation_id)
        except Exception as exc:
            log.warning("cache store failed", extra={"error": type(exc).__name__})
    log.info("answered", extra={
        "retriever": retriever.name, "provider": provider.name, "top_k": settings.top_k,
        "chunk_ids": [p.chunk_id for p in passages],
        "scores": [round(p.score, 4) for p in passages],
        "answered_from_context": answer.answered_from_context,
    })
    return response
