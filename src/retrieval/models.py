"""Data models for the retrieval layer."""

from dataclasses import dataclass, field
from typing import Optional

from ..knowledge_engineering.citation import SourceType


@dataclass
class RetrievedChunk:
    """A chunk retrieved from the knowledge base, hydrated with full content and citation.

    Attributes:
        chunk_id: Unique chunk identifier (matches the one assigned by the chunker).
        source_type: One of "A" (PCAOB), "B" (SEC 10-K), "C" (Synthetic).
        document_id: The parent document identifier (e.g., "AS1105", "AAPL", "IA-2026-004").
        document_type: Human-readable doc type (e.g., "Standard", "10-K", "InternalAuditReport").
        content: Full chunk text content.
        metadata: Source-specific metadata (e.g., paragraph, item, ticker).
        citation: Pre-formatted citation string (e.g., "[AS 1105 § .12]").
        distance: ChromaDB similarity distance (lower = more similar).
    """

    chunk_id: str
    source_type: str
    document_id: str
    document_type: str
    content: str
    metadata: dict
    citation: str
    distance: float


@dataclass
class SearchResult:
    """The outcome of a retrieval query.

    Attributes:
        query: The original query string.
        chunks: Retrieved chunks ordered by relevance (most similar first).
        routing: Optional routing decision (set when Router is used; populated by TASK-5-3).
        sources_searched: Optional list of source types queried (populated by multi-source).
    """

    query: str
    chunks: list[RetrievedChunk] = field(default_factory=list)
    routing: Optional[object] = None  # RoutingResult from router.py; avoid import cycle
    sources_searched: list[str] = field(default_factory=list)


__all__ = ["RetrievedChunk", "SearchResult", "SourceType"]