"""Research workflow: orchestrates Retriever + AnswerGenerator.

The `ResearchWorkflow` is the end-to-end API for Phase 6:
1. `retriever.search(query, top_k, **kwargs)` → `SearchResult` (Phase 5)
2. `answer_generator.generate(search_result)` → `CitedAnswer` (Phase 6-1)
3. Bundle into `ResearchResult` with latency

Both retriever and LLM failures are caught and re-raised as `WorkflowError`
so callers have a single exception type to handle. The original exception
is chained via `__cause__` for debugging.
"""

import logging
import time
from typing import Any, Optional

from ..retrieval import Retriever, SearchResult
from .answer_generator import AnswerGenerator
from .llm_client import AnthropicClient
from .models import CitedAnswer, ResearchResult

logger = logging.getLogger(__name__)


class WorkflowError(RuntimeError):
    """Raised when the research workflow fails (retrieval or LLM error).

    The original exception is chained via `__cause__` for debugging:

        try:
            workflow.run(query)
        except WorkflowError as exc:
            print(exc)            # "retrieval failed: ..."
            print(exc.__cause__)  # the original exception
    """


class ResearchWorkflow:
    """Orchestrates Retriever (Phase 5) + AnswerGenerator (6-1) into a single API.

    Args:
        retriever: A `Retriever` instance. Defaults to `Retriever()` (standard
            stores + a Router).
        answer_generator: An `AnswerGenerator` instance. Defaults to
            `AnswerGenerator(AnthropicClient())` — requires ANTHROPIC_API_KEY.
            Tests should pass a `MockClient` explicitly so they don't need a key.
    """

    def __init__(
        self,
        retriever: Optional[Retriever] = None,
        answer_generator: Optional[AnswerGenerator] = None,
    ):
        self.retriever = retriever if retriever is not None else Retriever()
        self.answer_generator = (
            answer_generator
            if answer_generator is not None
            else AnswerGenerator(AnthropicClient())
        )

    def run(
        self,
        query: str,
        top_k: int = 5,
        **retriever_kwargs: Any,
    ) -> ResearchResult:
        """Run end-to-end research: retrieve chunks, generate cited answer.

        Args:
            query: Natural-language question.
            top_k: Maximum number of chunks to retrieve (default 5).
            **retriever_kwargs: Extra kwargs forwarded to `Retriever.search()`
                (e.g., `ticker`, `standard_id`, `where`, `use_router`).

        Returns:
            `ResearchResult` with answer, chunks, routing, sources_searched,
            and latency.

        Raises:
            WorkflowError: If retrieval or LLM generation fails. The original
                exception is chained via `__cause__`.
        """
        logger.info("Research started: query=%r, top_k=%d", query, top_k)
        t0 = time.monotonic()

        # Step 1: retrieval
        try:
            search_result = self.retriever.search(
                query=query, top_k=top_k, **retriever_kwargs
            )
        except Exception as exc:
            logger.exception("Research: retrieval failed")
            raise WorkflowError(f"retrieval failed: {exc}") from exc

        retrieval_ms = (time.monotonic() - t0) * 1000
        logger.debug(
            "Research: retrieved %d chunks in %.1fms",
            len(search_result.chunks), retrieval_ms,
        )

        # Step 2: answer generation
        try:
            answer = self.answer_generator.generate(search_result)
        except Exception as exc:
            logger.exception("Research: answer generation failed")
            raise WorkflowError(f"answer generation failed: {exc}") from exc

        # Step 3: bundle
        latency_ms = (time.monotonic() - t0) * 1000
        logger.info(
            "Research complete: query=%r, chunks=%d, latency=%.1fms",
            query, len(search_result.chunks), latency_ms,
        )

        return ResearchResult(
            query=query,
            answer=answer,
            chunks=search_result.chunks,
            routing=search_result.routing,
            sources_searched=search_result.sources_searched,
            latency_ms=latency_ms,
        )


__all__ = ["ResearchWorkflow", "WorkflowError"]