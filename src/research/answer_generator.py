"""Answer generation: takes a SearchResult, returns a CitedAnswer.

The `AnswerGenerator` orchestrates:
1. Build a cited-answer prompt from the query + chunks
2. Send to the LLM via the configured LLMClient
3. Scan the LLM's response for `[[chunk_id]]` markers
4. Build a Citation list, silently dropping unknown chunk_ids (hallucinations)
5. Return a CitedAnswer

Design notes:
- Citation ordering preserves the order of first appearance in the LLM text
- Unknown chunk_ids are logged at DEBUG level (not raised) — hallucinations
  shouldn't crash the workflow, they should be filtered out
- Empty SearchResult returns a graceful "I don't have enough information" message
"""

import logging
import re
from typing import Optional

from ..retrieval.models import RetrievedChunk, SearchResult
from .llm_client import LLMClient
from .models import Citation, CitedAnswer
from .prompts import build_cited_answer_prompt

logger = logging.getLogger(__name__)


# Pattern matches [[chunk_id]] where chunk_id is any non-bracket, non-whitespace
# text. chunk_ids in this project use letters, digits, dots, hyphens, underscores.
_CITATION_PATTERN = re.compile(r"\[\[([^\]\s]+)\]\]")

# Default response when no chunks are retrieved
_EMPTY_ANSWER_TEMPLATE = (
    "I don't have enough information in the knowledge base to answer '{query}'."
)


class AnswerGenerator:
    """Generates cited answers from a SearchResult via an LLMClient.

    Args:
        llm_client: Any object satisfying the LLMClient protocol
            (AnthropicClient, MockClient, etc.).
        model: Model identifier, included in CitedAnswer.model for transparency.
        max_tokens: Max tokens to request from the LLM (default 1024).
    """

    def __init__(
        self,
        llm_client: LLMClient,
        model: str = "claude-haiku-4-5",
        max_tokens: int = 1024,
    ):
        self.llm_client = llm_client
        self.model = model
        self.max_tokens = max_tokens

    def generate(self, search_result: SearchResult) -> CitedAnswer:
        """Generate a cited answer from a SearchResult.

        Empty chunks → graceful "I don't have enough information" response
        with no citations.
        """
        if not search_result.chunks:
            return CitedAnswer(
                text=_EMPTY_ANSWER_TEMPLATE.format(query=search_result.query),
                citations=[],
                model=self.model,
                usage={},
            )

        system_prompt, user_prompt = build_cited_answer_prompt(
            search_result.query, search_result.chunks
        )

        text = self.llm_client.complete(
            system=system_prompt, user=user_prompt, max_tokens=self.max_tokens
        )

        citations = self._resolve_citations(text, search_result.chunks)
        return CitedAnswer(
            text=text,
            citations=citations,
            model=self.model,
            # Real AnthropicClient would populate usage; MockClient doesn't.
            # Kept as a stub for now; populated properly in 6-2 if needed.
            usage={},
        )

    @staticmethod
    def _resolve_citations(
        text: str, retrieved_chunks: list[RetrievedChunk]
    ) -> list[Citation]:
        """Extract [[chunk_id]] markers from text and map to Citation objects.

        - Deduplicates by chunk_id (first occurrence wins)
        - Silently drops chunk_ids that weren't retrieved (LLM hallucination)
        - Preserves order of first appearance in the text
        """
        # Build lookup: chunk_id -> RetrievedChunk
        chunk_by_id: dict[str, RetrievedChunk] = {
            c.chunk_id: c for c in retrieved_chunks
        }

        citations: list[Citation] = []
        seen_ids: set[str] = set()
        unknown_ids: list[str] = []

        for match in _CITATION_PATTERN.finditer(text):
            chunk_id = match.group(1)
            marker = match.group(0)  # e.g., "[[AS1105.12]]"
            if chunk_id in seen_ids:
                continue  # dedupe
            if chunk_id in chunk_by_id:
                citations.append(Citation(
                    marker=marker,
                    chunk_id=chunk_id,
                    chunk=chunk_by_id[chunk_id],
                ))
                seen_ids.add(chunk_id)
            else:
                unknown_ids.append(chunk_id)

        if unknown_ids:
            logger.debug(
                "Answer generator: dropped %d unknown citation(s): %s",
                len(unknown_ids), unknown_ids,
            )

        return citations


__all__ = ["AnswerGenerator"]
