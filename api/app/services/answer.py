"""The request path: cache, retrieval, grounding, validation and fallback."""

from __future__ import annotations

import logging
import time

from ..config import Settings
from ..logjson import request_id_var
from ..providers.llm.base import GenerationError, LLMProvider
from ..retrieval.base import Retriever
from ..retrieval.chroma import is_historical_question
from ..routes import metrics
from ..schemas import Answer, AskResponse, Passage, RetrievedRef
from .cache import SemanticCache, is_follow_up
from .grounding import render_evidence
from .prompt import factual_question, select_context

log = logging.getLogger("rahbar.answer")
_NO_EVIDENCE = "The available corpus does not contain enough evidence to answer this question."
_FALLBACK = "I could not verify a grounded answer. Please try again later."


def _citations_valid(answer: Answer, passages: list[Passage]) -> bool:
    if not answer.answered_from_context:
        return not answer.citations and answer.answer.strip().casefold() not in {
            "true", "false", "yes", "no",
        }
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


def _finish(response: AskResponse, question: str, cache: SemanticCache | None,
            session_id: str | None, settings: Settings,
            usage: tuple[int, int] = (0, 0)) -> AskResponse:
    log.info("answered", extra={
        "provider": response.provider, "top_k": settings.top_k,
        "chunk_ids": [p.chunk_id for p in response.retrieved],
        "scores": [round(p.score, 4) for p in response.retrieved],
        "answered_from_context": response.answered_from_context, "cached": response.cached,
        "input_tokens": usage[0], "output_tokens": usage[1],
    })
    if cache is not None and settings.retriever == "chroma":
        try:
            cache.store_turn(question, response, session_id)
        except Exception as exc:
            log.warning("turn storage unavailable", extra={"error": type(exc).__name__})
    return response


def _decline(message: str, provider: str) -> AskResponse:
    metrics.ABSTENTIONS.inc()
    return _response(Answer(reasoning="unavailable evidence", answer=message, citations=[],
                            answered_from_context=False, confidence="low"), [], provider)


def answer_question(
    question: str, retriever: Retriever, provider: LLMProvider, settings: Settings,
    cache: SemanticCache | None = None,
    *, session_id: str | None = None,
) -> AskResponse:
    embedding: list[float] | None = None
    generation_id = None
    query = factual_question(question)
    follow_up = is_follow_up(query)
    skip_cache = follow_up or is_historical_question(query)
    if follow_up:
        try:
            previous = cache.previous_question(session_id) if cache and session_id else None
        except Exception:
            previous = None
        if not previous:
            return _finish(_decline("Please restate the full policy question so I can identify "
                                   "the relevant evidence.", provider.name),
                           question, cache, session_id, settings)
        query = f"Previous question: {previous}\nFollow-up question: {question}"

    retrieval_started = time.perf_counter()
    try:
        if retriever.name == "chroma":
            embedding = retriever.embed(query)
    except Exception as exc:
        metrics.RETRIEVAL_LATENCY.observe(time.perf_counter() - retrieval_started)
        metrics.FALLBACKS.inc()
        log.warning("embedding unavailable", extra={"error": type(exc).__name__})
        return _finish(_decline(_FALLBACK, provider.name), question, cache, session_id, settings)
    if not skip_cache and embedding is not None and cache is not None:
        try:
            generation_id = cache.generation_id()
            cached = cache.lookup(embedding, generation_id=generation_id)
            if cached is not None:
                metrics.record_cache_lookup("hit")
                metrics.RETRIEVAL_LATENCY.observe(time.perf_counter() - retrieval_started)
                response = cached.model_copy(update={"request_id": request_id_var.get(),
                                                     "cached": True})
                return _finish(response, question, cache, session_id, settings)
            metrics.record_cache_lookup("miss")
        except Exception as exc:
            metrics.record_cache_lookup("error")
            log.warning("cache lookup failed", extra={"error": type(exc).__name__})
    else:
        metrics.record_cache_lookup("skipped")

    try:
        passages = retriever.retrieve(query, k=settings.top_k, embedding=embedding)
    except Exception as exc:
        metrics.FALLBACKS.inc()
        log.warning("retrieval unavailable", extra={"error": type(exc).__name__})
        return _finish(_decline(_FALLBACK, provider.name), question, cache, session_id, settings)
    finally:
        metrics.RETRIEVAL_LATENCY.observe(time.perf_counter() - retrieval_started)
    grounded = [p for p in passages if p.score >= settings.relevance_floor]

    valid_generation = False
    total_input = total_output = 0
    if not grounded:
        answer = Answer(reasoning="no passage cleared the relevance floor", answer=_NO_EVIDENCE,
                        citations=[], answered_from_context=False, confidence="low")
    else:
        context = select_context(query, grounded)
        log.info("generation context", extra={"chunk_ids": [p.chunk_id for p in context],
                                              "scores": [round(p.score, 4) for p in context]})
        answer = Answer(reasoning="model output unavailable", answer=_FALLBACK, citations=[],
                        answered_from_context=False, confidence="low")
        for attempt in range(2):  # retry once on invalid JSON, citations or provider failure
            generated_at = time.perf_counter()
            try:
                result = provider.generate(query, context)
                candidate = result.answer
                total_input += result.input_tokens
                total_output += result.output_tokens
                metrics.TOKENS.labels(provider=provider.name, direction="input").inc(result.input_tokens)
                metrics.TOKENS.labels(provider=provider.name, direction="output").inc(result.output_tokens)
                if not _citations_valid(candidate, context):
                    raise ValueError("model cited evidence that was not retrieved")
                if not candidate.answered_from_context:
                    candidate = candidate.model_copy(update={
                        "answer": _NO_EVIDENCE, "confidence": "low",
                    })
                answer = render_evidence(candidate, context, question)
                log.info("generation", extra={"input_tokens": result.input_tokens,
                                              "output_tokens": result.output_tokens})
                valid_generation = True
                break
            except Exception as exc:
                if isinstance(exc, GenerationError):
                    total_input += exc.input_tokens
                    total_output += exc.output_tokens
                    metrics.TOKENS.labels(provider=provider.name, direction="input").inc(exc.input_tokens)
                    metrics.TOKENS.labels(provider=provider.name, direction="output").inc(exc.output_tokens)
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
    return _finish(response, question, cache, session_id, settings, (total_input, total_output))
