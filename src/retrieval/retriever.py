"""Core Retriever: wires Embedder + ChromaDB + JSON Store + Citation formatter.

Single-source vector search with structured SearchResult output. Multi-source
aggregation and Router integration are added in TASK-5-3.
"""

from typing import Optional

from ..ingestion.embedder.embedder import Embedder
from ..ingestion.storage.chroma_store import ChromaStore
from ..ingestion.storage.json_store import JsonStore
from ..knowledge_engineering.citation import SourceType, format_citation
from .models import RetrievedChunk, SearchResult


class Retriever:
    """Hybrid retriever over ChromaDB (vector) + JSONL store (full content).

    The retrieval flow:
    1. Embed the query via Embedder
    2. Search ChromaDB for similar chunk vectors (optionally with `where` filter)
    3. For each matched chunk_id, hydrate from JsonStore to get full content + metadata
    4. Format citations per source type
    5. Return a structured SearchResult

    Multi-source aggregation (Router integration) is added in TASK-5-3.
    """

    def __init__(
        self,
        chroma_store: Optional[ChromaStore] = None,
        json_store: Optional[JsonStore] = None,
        embedder: Optional[Embedder] = None,
    ):
        self.chroma_store = chroma_store or ChromaStore()
        self.json_store = json_store or JsonStore()
        self.embedder = embedder or Embedder()

    def search(
        self,
        query: str,
        top_k: int = 5,
        where: Optional[dict] = None,
    ) -> SearchResult:
        """Search the knowledge base for chunks relevant to the query.

        Args:
            query: Natural-language query string.
            top_k: Maximum number of chunks to return.
            where: Optional ChromaDB metadata filter (e.g., {"source_type": "A"}).

        Returns:
            SearchResult with chunks ordered by ChromaDB distance (ascending).
        """
        if not query or not query.strip():
            return SearchResult(query=query, chunks=[])

        # Step 1+2: vector search via ChromaDB
        raw_results = self.chroma_store.search(
            query_text=query,
            embedder=self.embedder,
            n_results=top_k,
            where=where,
        )

        # ChromaDB returns a dict like:
        # {"ids": [["id1", "id2", ...]], "distances": [[0.1, 0.2, ...]], "metadatas": [[...]]}
        # For an empty collection, all lists are empty.
        ids = (raw_results.get("ids") or [[]])[0]
        distances = (raw_results.get("distances") or [[]])[0]
        metadatas = (raw_results.get("metadatas") or [[]])[0]

        chunks: list[RetrievedChunk] = []
        for chunk_id, distance, chroma_meta in zip(ids, distances, metadatas):
            # Step 3: hydrate from JSON store
            record = self.json_store.read(chunk_id)
            if record is None:
                # ChromaDB has an entry but JSON store doesn't (drift).
                # Build a minimal chunk from ChromaDB metadata alone.
                record = {
                    "chunk_id": chunk_id,
                    "source_type": chroma_meta.get("source_type", ""),
                    "document_id": chroma_meta.get("document_id", ""),
                    "document_type": chroma_meta.get("document_type", ""),
                    "content": "",
                    "metadata": {},
                }

            # Step 4: format citation
            try:
                source_type_enum = SourceType(record["source_type"])
                citation = format_citation(record["chunk_id"], source_type_enum)
            except (ValueError, KeyError):
                citation = f"[{record.get('chunk_id', chunk_id)}]"

            chunks.append(
                RetrievedChunk(
                    chunk_id=record["chunk_id"],
                    source_type=record.get("source_type", ""),
                    document_id=record.get("document_id", ""),
                    document_type=record.get("document_type", ""),
                    content=record.get("content", ""),
                    metadata=record.get("metadata", {}),
                    citation=citation,
                    distance=float(distance) if distance is not None else 0.0,
                )
            )

        return SearchResult(
            query=query,
            chunks=chunks,
            sources_searched=[where["source_type"]] if where and "source_type" in where else [],
        )