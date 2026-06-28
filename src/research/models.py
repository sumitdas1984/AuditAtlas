"""Data models for the research (answer generation) layer."""

from dataclasses import dataclass, field
from typing import Optional

from ..retrieval.models import RetrievedChunk


@dataclass
class Citation:
    """A citation marker in the answer text, mapped back to a chunk.

    Attributes:
        marker: The literal citation marker as it appears in the answer text
            (e.g., "[[AS1105.12]]").
        chunk_id: The parsed chunk identifier (e.g., "AS1105.12").
        chunk: The full RetrievedChunk for rendering the formal citation.
    """

    marker: str
    chunk_id: str
    chunk: RetrievedChunk


@dataclass
class CitedAnswer:
    """An LLM-generated answer with grounded citations.

    Attributes:
        text: The raw answer text from the LLM, with [[chunk_id]] markers
            where the LLM cited a source.
        citations: Ordered list of Citation objects, one per unique chunk_id
            mentioned in the text. Order = first appearance in text.
        model: The LLM model used (e.g., "claude-haiku-4-5").
        usage: Token usage dict, e.g., {"input_tokens": N, "output_tokens": M}.
    """

    text: str
    citations: list[Citation] = field(default_factory=list)
    model: str = ""
    usage: dict = field(default_factory=dict)


@dataclass
class ResearchResult:
    """The outcome of a complete research workflow run.

    Bundles the LLM-generated answer with the retrieved chunks, the routing
    decision (if any), the sources searched, and the wall-clock latency.

    Attributes:
        query: The original user query.
        answer: The LLM-generated CitedAnswer.
        chunks: The retrieved chunks (mirrors what's in answer.citations).
        routing: The RoutingResult if the Router was used, else None.
        sources_searched: List of source types queried (e.g., ["A", "B", "C"]).
        latency_ms: Wall-clock time for the full workflow run, in milliseconds.
    """

    query: str
    answer: CitedAnswer
    chunks: list[RetrievedChunk] = field(default_factory=list)
    routing: Optional[object] = None  # RoutingResult; avoid import cycle
    sources_searched: list[str] = field(default_factory=list)
    latency_ms: float = 0.0


__all__ = ["Citation", "CitedAnswer", "ResearchResult"]
