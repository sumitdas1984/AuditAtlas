"""Data models for the research (answer generation) layer."""

from dataclasses import dataclass, field

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


__all__ = ["Citation", "CitedAnswer"]
