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
        ticker: Optional[str] = None,
        standard_id: Optional[str] = None,
    ) -> SearchResult:
        """Search the knowledge base for chunks relevant to the query.

        Args:
            query: Natural-language query string.
            top_k: Maximum number of chunks to return.
            where: Optional ChromaDB metadata filter (e.g., {"source_type": "A"}).
                Combined with `ticker` / `standard_id` if those are also set.
            ticker: Optional Source B ticker filter (e.g., "AAPL").
            standard_id: Optional Source A standard ID filter (e.g., "AS1105").

        Returns:
            SearchResult with chunks ordered by ChromaDB distance (ascending).
        """
        if not query or not query.strip():
            return SearchResult(query=query, chunks=[])

        # Build merged where clause from raw `where` plus convenience kwargs
        merged_where = self._build_where_clause(where, ticker, standard_id)

        # Step 1+2: vector search via ChromaDB
        raw_results = self.chroma_store.search(
            query_text=query,
            embedder=self.embedder,
            n_results=top_k,
            where=merged_where,
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
            sources_searched=self._infer_sources_searched(merged_where, ticker, standard_id),
        )

    @staticmethod
    def _infer_sources_searched(
        where: Optional[dict],
        ticker: Optional[str],
        standard_id: Optional[str],
    ) -> list[str]:
        """Derive the list of source types filtered to, based on the active filters.

        Used to populate `SearchResult.sources_searched` for caller visibility
        into which source(s) the search was scoped to.
        """
        sources: set[str] = set()
        if where and "source_type" in where:
            sources.add(str(where["source_type"]))
        if ticker:  # truthy check skips None and ""
            sources.add("B")  # ticker is a Source B field
        if standard_id:  # truthy check skips None and ""
            sources.add("A")  # standard_id is a Source A field
        return sorted(sources)

    @staticmethod
    def _build_where_clause(
        where: Optional[dict],
        ticker: Optional[str],
        standard_id: Optional[str],
    ) -> Optional[dict]:
        """Build a ChromaDB-compatible where clause from caller filters.

        ChromaDB requires a single top-level operator (`field=value`,
        `$and=[...]`, `$or=[...]`). When multiple filters are supplied, we
        combine them with `$and` so callers don't have to.

        Empty-string filter values (`ticker=""`, `standard_id=""`) are treated
        the same as `None` — they are skipped, not turned into a literal match.
        Rationale: a literal `{"ticker": ""}` would match no real chunks and
        almost always indicates a caller bug, so we silently ignore it.
        Empty `where={}` is also skipped.
        """
        conditions: list[dict] = []
        if where:
            conditions.append(dict(where))
        if ticker:  # truthy check skips None and ""
            conditions.append({"ticker": ticker})
        if standard_id:  # truthy check skips None and ""
            conditions.append({"standard_id": standard_id})

        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}