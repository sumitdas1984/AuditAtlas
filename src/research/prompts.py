"""Prompt templates for the answer-generation layer.

Single entry point: `build_cited_answer_prompt(query, chunks)` returns a
(system, user) prompt pair. Kept as plain functions (no Jinja2 / template
engine) so the prompts are easy to read and test.
"""

import re

from ..retrieval.models import RetrievedChunk


SYSTEM_PROMPT = """\
You are an audit research assistant. You help audit professionals by \
answering questions using authoritative sources: PCAOB auditing standards, \
SEC 10-K filings, and internal company documents.

When answering:
- Cite every claim by wrapping the chunk_id in double brackets, \
e.g. [[AS1105.12]] or [[AAPL.2025.Item1A.1]].
- Use only information from the provided source chunks. If the chunks \
don't contain enough information to answer, say so clearly.
- Be concise but complete. Use formal audit language.
- Never invent chunk_ids that aren't in the source chunks.\
"""

# Collapse any run of whitespace (newlines, tabs, multiple spaces) into
# single spaces so chunk content stays on a single prompt line.
_WHITESPACE_RUN = re.compile(r"\s+")


def _format_chunk_line(index: int, chunk: RetrievedChunk) -> str:
    """Format a single chunk as a numbered line for the user prompt."""
    content_preview = _WHITESPACE_RUN.sub(" ", chunk.content.strip())
    return f"{index}. [{chunk.chunk_id}] \"{content_preview}\""


def build_cited_answer_prompt(
    query: str,
    chunks: list[RetrievedChunk],
) -> tuple[str, str]:
    """Build the (system, user) prompt pair for cited answer generation.

    The system prompt defines the LLM's role and citation rules. The user
    prompt contains the question and the source chunks, each numbered with
    its chunk_id so the LLM can reference them.

    Args:
        query: The user's natural-language question.
        chunks: The retrieved chunks to ground the answer in.

    Returns:
        (system_prompt, user_prompt) tuple.
    """
    chunk_lines = "\n".join(
        _format_chunk_line(i + 1, chunk) for i, chunk in enumerate(chunks)
    )
    user_prompt = (
        f"Question: {query}\n\n"
        f"Source chunks:\n{chunk_lines}\n\n"
        "Answer:"
    )
    return SYSTEM_PROMPT, user_prompt


__all__ = ["SYSTEM_PROMPT", "build_cited_answer_prompt"]
