"""Core Retriever: wires Router + Embedder + ChromaDB + JSON Store + Citation formatter.

Single-source and multi-source (router-driven) search with structured
SearchResult output. CLI integration comes in TASK-5-4.
"""

import logging
from typing import Optional

from ..ingestion.embedder.embedder import Embedder
from ..ingestion.storage.chroma_store import ChromaStore
from ..ingestion.storage.json_store import JsonStore
from ..knowledge_engineering.citation import SourceType, format_citation
from ..knowledge_engineering.router import Router, RoutingResult
from .models import RetrievedChunk, SearchResult

logger = logging.getLogger(__name__)


class Retriever:
    """Hybrid retriever over ChromaDB (vector) + JSONL store (full content).

    The retrieval flow:
    1. If `router` is set and no explicit filters were provided:
       - Call `router.route(query)` to pick source(s)
       - Run a ChromaDB search per source with `where={"source_type": ...}`
       - Merge, sort by distance, dedupe by chunk_id, return top-K overall
    2. Else: single ChromaDB search with the merged `where` clause
    3. For each matched chunk_id, hydrate from JsonStore to get full content + metadata
    4. Format citations per source type
    5. Return a structured SearchResult

    Explicit filters (`where`, `ticker`, `standard_id`) bypass routing because
    the caller has already made a routing decision. Pass `use_router=False` to
    force single-search mode even when no explicit filters are given.
    """

    def __init__(
        self,
        chroma_store: Optional[ChromaStore] = None,
        json_store: Optional[JsonStore] = None,
        embedder: Optional[Embedder] = None,
        router: Optional[Router] = None,
    ):
        self.chroma_store = chroma_store or ChromaStore()
        self.json_store = json_store or JsonStore()
        self.embedder = embedder or Embedder()
        self.router = router  # may be None; search() checks before using

    def search(
        self,
        query: str,
        top_k: int = 5,
        where: Optional[dict] = None,
        ticker: Optional[str] = None,
        standard_id: Optional[str] = None,
        use_router: bool = True,
    ) -> SearchResult:
        """Search the knowledge base for chunks relevant to the query.

        Args:
            query: Natural-language query string.
            top_k: Maximum number of chunks to return.
            where: Optional ChromaDB metadata filter (e.g., {"source_type": "A"}).
                Combined with `ticker` / `standard_id` if those are also set.
                When set, bypasses the router.
            ticker: Optional Source B ticker filter (e.g., "AAPL").
                When set, bypasses the router.
            standard_id: Optional Source A standard ID filter (e.g., "AS1105").
                When set, bypasses the router.
            use_router: If True (default) and `router` is set and no explicit
                filters were given, route the query via the Router for
                multi-source aggregation. If False, force single-search mode.

        Returns:
            SearchResult with chunks ordered by ChromaDB distance (ascending).
            `routing` is populated only when router was used.
        """
        if not query or not query.strip():
            return SearchResult(query=query, chunks=[])

        # Routing decision: use the router when the caller hasn't already made
        # a routing decision (explicit filters) AND didn't opt out (use_router).
        # Intentional design: explicit filters bypass routing because the caller
        # has scoped the search — re-routing could narrow results the caller
        # explicitly wanted. Pass use_router=False to force single-search mode.
        #
        # Bypass-detection uses TRUTHY checks (not `is not None`) so it matches
        # `_build_where_clause()` semantics: empty values (`where={}`,
        # `ticker=""`, `standard_id=""`) are treated as no-filter and do NOT
        # trigger bypass — they would be silently ignored downstream anyway.
        has_explicit_filter = bool(where) or bool(ticker) or bool(standard_id)
        if use_router and self.router is not None and has_explicit_filter:
            logger.debug(
                "Bypassing router due to explicit filter "
                "(where=%r, ticker=%r, standard_id=%r)",
                where, ticker, standard_id,
            )
        should_route = (
            use_router and self.router is not None and not has_explicit_filter
        )

        if should_route:
            routing_result = self.router.route(query)
            if routing_result.sources:
                # Error propagation note: if any per-source ChromaDB query
                # raises (e.g., collection missing, transient error), the
                # exception propagates and the whole search fails. This is the
                # safer MVP default — partial results could mislead the caller.
                # Switch to per-source try/except if availability > correctness.
                chunks = self._search_multi_source(query, top_k, routing_result)
                return SearchResult(
                    query=query,
                    chunks=chunks,
                    routing=routing_result,
                    sources_searched=[s.value for s in routing_result.sources],
                )
            # Defensive fallback: Router returned no sources (shouldn't happen
            # with the current Router — every topic has at least one primary
            # source — but be defensive). Fall through to single search.

        # Single-search path (default when no router or explicit filter present)
        merged_where = self._build_where_clause(where, ticker, standard_id)
        raw = self.chroma_store.search(
            query_text=query,
            embedder=self.embedder,
            n_results=top_k,
            where=merged_where,
        )
        chunks = self._hydrate_chunks_from_raw(raw)

        return SearchResult(
            query=query,
            chunks=chunks,
            routing=None,
            sources_searched=self._infer_sources_searched(merged_where, ticker, standard_id),
        )

    def _search_multi_source(
        self,
        query: str,
        top_k: int,
        routing_result: RoutingResult,
    ) -> list[RetrievedChunk]:
        """Run a ChromaDB search per routed source and merge by distance.

        Cross-source distance comparability assumption:
            All sources MUST be embedded with the same model (same
            dimensionality + same model weights) AND stored in collections
            using the same distance metric. This is satisfied because every
            ChromaStore in the knowledge base uses the single Retriever's
            Embedder (sentence-transformers all-MiniLM-L6-v2, 384-dim) and
            ChromaDB's default distance metric (L2). If sources ever diverge
            on embedding model or distance metric, the global distance sort
            below will silently produce garbage rankings.

        Over-fetches `top_k` per source so the merged result has enough
        material for distance-based global ranking. Deduplicates by chunk_id
        (cross-source chunk_id collision should not happen but is defensive);
        when duplicates exist, the lowest-distance copy is kept (sort runs
        before dedupe).
        """
        all_chunks: list[RetrievedChunk] = []
        for source in routing_result.sources:
            raw = self.chroma_store.search(
                query_text=query,
                embedder=self.embedder,
                n_results=top_k,
                where={"source_type": source.value},
            )
            all_chunks.extend(self._hydrate_chunks_from_raw(raw))

        # Sort globally by distance ascending; then dedupe by chunk_id (first
        # occurrence wins, which is the lowest-distance copy).
        all_chunks.sort(key=lambda c: c.distance)
        return self._dedupe_chunks_by_id(all_chunks)[:top_k]

    @staticmethod
    def _dedupe_chunks_by_id(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        """Remove duplicates by chunk_id, preserving first occurrence.

        Callers should sort by distance before calling so the lowest-distance
        copy is the one retained.
        """
        seen: set[str] = set()
        deduped: list[RetrievedChunk] = []
        for chunk in chunks:
            if chunk.chunk_id in seen:
                continue
            seen.add(chunk.chunk_id)
            deduped.append(chunk)
        return deduped

    def _hydrate_chunks_from_raw(self, raw: dict) -> list[RetrievedChunk]:
        """Convert a ChromaDB query result into hydrated RetrievedChunks.

        Handles the drift case where ChromaDB has a chunk_id the JSON store
        doesn't — falls back to ChromaDB metadata only with empty content.
        """
        ids = (raw.get("ids") or [[]])[0]
        distances = (raw.get("distances") or [[]])[0]
        metadatas = (raw.get("metadatas") or [[]])[0]
        return self._hydrate_chunks(ids, distances, metadatas)

    def _hydrate_chunks(
        self,
        ids: list[str],
        distances: list[float],
        metadatas: list[dict],
    ) -> list[RetrievedChunk]:
        """Turn raw ChromaDB result tuples into hydrated RetrievedChunks."""
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
        return chunks

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

        # TODO(FEATURE-005): Add `classification=` kwarg for Source C filtering.
        # Currently deferred — `classification` is not in ChromaDB metadata
        # (only in chunk.metadata / JSON store), so it would need a SQLite
        # pre-filter pass that returns matching chunk_ids to feed into a
        # ChromaDB `$in` clause. Revisit if a use case demands it.
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