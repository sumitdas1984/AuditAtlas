import pytest
from pathlib import Path

from src.ingestion.chunkers.chunker import Chunk
from src.ingestion.storage.chroma_store import ChromaStore
from src.ingestion.storage.json_store import JsonStore
from src.retrieval import Retriever, RetrievedChunk, SearchResult


# Shared fixtures (temp_dir, embedder, populated_stores) live in conftest.py


class TestRetriever:
    """Tests for the Retriever class."""

    def test_search_returns_search_result(self, populated_stores):
        chroma, json_store, _ = populated_stores
        retriever = Retriever(chroma_store=chroma, json_store=json_store)
        result = retriever.search("audit evidence")
        assert isinstance(result, SearchResult)
        assert result.query == "audit evidence"

    def test_search_includes_content_and_citation(self, populated_stores):
        chroma, json_store, _ = populated_stores
        retriever = Retriever(chroma_store=chroma, json_store=json_store)
        result = retriever.search("audit evidence")

        assert len(result.chunks) > 0
        for chunk in result.chunks:
            assert isinstance(chunk, RetrievedChunk)
            assert chunk.content  # non-empty
            assert chunk.citation  # non-empty
            assert chunk.chunk_id  # non-empty

    def test_search_respects_top_k(self, populated_stores):
        chroma, json_store, _ = populated_stores
        retriever = Retriever(chroma_store=chroma, json_store=json_store)
        result = retriever.search("audit", top_k=2)
        assert len(result.chunks) <= 2

    def test_search_with_source_filter(self, populated_stores):
        chroma, json_store, _ = populated_stores
        retriever = Retriever(chroma_store=chroma, json_store=json_store)
        result = retriever.search("risk", where={"source_type": "A"}, top_k=10)
        # All returned chunks must be Source A
        assert len(result.chunks) > 0
        for chunk in result.chunks:
            assert chunk.source_type == "A"
        assert "A" in result.sources_searched

    def test_search_empty_kb_returns_empty_chunks(self, temp_dir, embedder):
        """If ChromaDB has no chunks, SearchResult has empty chunks (no error)."""
        chroma = ChromaStore(persist_dir=str(Path(temp_dir) / "empty_chroma"), collection_name="empty")
        json_store = JsonStore(store_path=str(Path(temp_dir) / "empty.jsonl"))
        retriever = Retriever(chroma_store=chroma, json_store=json_store, embedder=embedder)

        result = retriever.search("anything")
        assert isinstance(result, SearchResult)
        assert len(result.chunks) == 0

    def test_search_handles_missing_json_entry(self, temp_dir, embedder):
        """If ChromaDB has a chunk_id not in JSON store, skip gracefully (no crash)."""
        chroma = ChromaStore(persist_dir=str(Path(temp_dir) / "drift_chroma"), collection_name="drift")
        json_store = JsonStore(store_path=str(Path(temp_dir) / "drift.jsonl"))

        chunk = Chunk(
            chunk_id="ONLY-IN-CHROMA.1",
            source_type="A",
            document_id="ONLY-IN-CHROMA",
            document_type="Standard",
            chunk_index=1,
            content="phantom chunk",
            metadata={"standard_id": "ONLY-IN-CHROMA"},
            citation={"format": "[phantom]", "type": "pcaob"},
        )
        chroma.add([chunk], embedder)
        # Intentionally do NOT write to json_store

        retriever = Retriever(chroma_store=chroma, json_store=json_store, embedder=embedder)
        result = retriever.search("phantom")
        # Should not raise — falls back to ChromaDB metadata
        assert len(result.chunks) == 1
        assert result.chunks[0].chunk_id == "ONLY-IN-CHROMA.1"
        assert result.chunks[0].content == ""  # empty since JSON store has no record

    def test_citation_format_for_each_source(self, populated_stores):
        chroma, json_store, _ = populated_stores
        retriever = Retriever(chroma_store=chroma, json_store=json_store)
        # Query that should hit all three sources
        result = retriever.search("audit risk", top_k=10)

        # Collect citations by source_type
        seen_sources = {c.source_type for c in result.chunks}
        citations_by_source = {
            c.source_type: c.citation for c in result.chunks
        }

        # Source A citation: starts with [AS or [QC
        if "A" in citations_by_source:
            assert citations_by_source["A"].startswith("[AS ") or citations_by_source["A"].startswith("[QC ")
            assert "§" in citations_by_source["A"]

        # Source B citation: starts with [TICKER 10-K
        if "B" in citations_by_source:
            assert "10-K" in citations_by_source["B"]
            assert "Item" in citations_by_source["B"]

        # Source C citation: contains doc type prefix
        if "C" in citations_by_source:
            assert ":" in citations_by_source["C"] or "InternalAuditReport" in citations_by_source["C"]

    def test_search_results_ordered_by_distance(self, populated_stores):
        """Chunks should be ordered by ChromaDB distance (ascending — closer first)."""
        chroma, json_store, _ = populated_stores
        retriever = Retriever(chroma_store=chroma, json_store=json_store)
        result = retriever.search("audit", top_k=10)

        distances = [c.distance for c in result.chunks]
        assert distances == sorted(distances), f"Expected ascending distances, got {distances}"

    def test_empty_query_returns_empty_result(self, populated_stores):
        """Empty query string returns empty SearchResult without calling ChromaDB."""
        chroma, json_store, _ = populated_stores
        retriever = Retriever(chroma_store=chroma, json_store=json_store)

        result = retriever.search("")
        assert isinstance(result, SearchResult)
        assert result.chunks == []

    def test_default_construction_uses_standard_stores(self, populated_stores):
        """Retriever() with no args should construct default stores and run a search."""
        # Smoke test: instantiate with no args, run a query against real defaults.
        # This will hit the production data/knowledge_base/ if present, but
        # gracefully returns empty if not.
        retriever = Retriever()
        result = retriever.search("audit", top_k=2)
        assert isinstance(result, SearchResult)
        # Either finds chunks in the real KB, or empty — never raises

    def test_search_filter_by_ticker(self, populated_stores):
        """ticker='AAPL' returns only Source B chunks tagged with AAPL."""
        chroma, json_store, _ = populated_stores
        retriever = Retriever(chroma_store=chroma, json_store=json_store)
        result = retriever.search("risk", ticker="AAPL", top_k=10)

        assert len(result.chunks) > 0
        for chunk in result.chunks:
            assert chunk.source_type == "B"
            assert chunk.metadata.get("ticker") == "AAPL"
        assert "B" in result.sources_searched

    def test_search_filter_by_standard_id(self, populated_stores):
        """standard_id='AS1105' returns only the AS1105 chunk."""
        chroma, json_store, _ = populated_stores
        retriever = Retriever(chroma_store=chroma, json_store=json_store)
        result = retriever.search("audit evidence", standard_id="AS1105", top_k=10)

        assert len(result.chunks) > 0
        for chunk in result.chunks:
            assert chunk.source_type == "A"
            assert chunk.metadata.get("standard_id") == "AS1105"
        assert "A" in result.sources_searched

    def test_search_filter_combined_with_where(self, populated_stores):
        """Combining where={source_type: A} + standard_id='AS1105' narrows to AS1105 only."""
        chroma, json_store, _ = populated_stores
        retriever = Retriever(chroma_store=chroma, json_store=json_store)
        result = retriever.search(
            "audit risk",
            where={"source_type": "A"},
            standard_id="AS1105",
            top_k=10,
        )

        # Should match AS1105.12 only (not AS2110.5)
        assert len(result.chunks) > 0
        for chunk in result.chunks:
            assert chunk.source_type == "A"
            assert chunk.metadata.get("standard_id") == "AS1105"

    def test_search_filter_no_match(self, populated_stores):
        """ticker='XYZ' (unknown) returns empty SearchResult without raising."""
        chroma, json_store, _ = populated_stores
        retriever = Retriever(chroma_store=chroma, json_store=json_store)
        result = retriever.search("anything", ticker="XYZ")

        assert isinstance(result, SearchResult)
        assert result.chunks == []
        assert "B" in result.sources_searched  # filter was applied, just no matches

    def test_search_filter_kwarg_only(self, populated_stores):
        """standard_id kwarg alone (no explicit where) translates to where-clause and works."""
        chroma, json_store, _ = populated_stores
        retriever = Retriever(chroma_store=chroma, json_store=json_store)
        # AS2110 chunk is in the fixture
        result = retriever.search("risk", standard_id="AS2110", top_k=10)

        assert len(result.chunks) > 0
        for chunk in result.chunks:
            assert chunk.metadata.get("standard_id") == "AS2110"
        assert "A" in result.sources_searched

    def test_search_filter_ticker_and_standard_id_together(self, populated_stores):
        """Setting both ticker and standard_id together wraps them in $and and returns no matches."""
        chroma, json_store, _ = populated_stores
        retriever = Retriever(chroma_store=chroma, json_store=json_store)
        # No chunk in fixture has both ticker and standard_id, so result is empty
        result = retriever.search("anything", ticker="AAPL", standard_id="AS1105")

        assert isinstance(result, SearchResult)
        assert result.chunks == []
        # Both filters were applied — sources_searched reflects both
        assert "A" in result.sources_searched
        assert "B" in result.sources_searched


class TestRetrieverHelpers:
    """Direct unit tests for the static helpers on Retriever."""

    def test_build_where_clause_no_filters_returns_none(self):
        """With no filters at all, the clause is None (no ChromaDB filter)."""
        result = Retriever._build_where_clause(None, None, None)
        assert result is None

    def test_build_where_clause_empty_where_only(self):
        """Only the raw `where` dict is supplied (no kwargs)."""
        result = Retriever._build_where_clause({"source_type": "A"}, None, None)
        assert result == {"source_type": "A"}

    def test_build_where_clause_ticker_only(self):
        """Only ticker is supplied."""
        result = Retriever._build_where_clause(None, "AAPL", None)
        assert result == {"ticker": "AAPL"}

    def test_build_where_clause_standard_id_only(self):
        """Only standard_id is supplied."""
        result = Retriever._build_where_clause(None, None, "AS1105")
        assert result == {"standard_id": "AS1105"}

    def test_build_where_clause_combined_wraps_in_and(self):
        """Multiple filters are wrapped in $and."""
        result = Retriever._build_where_clause(
            {"source_type": "A"}, "AAPL", "AS1105"
        )
        assert result == {
            "$and": [
                {"source_type": "A"},
                {"ticker": "AAPL"},
                {"standard_id": "AS1105"},
            ]
        }

    def test_build_where_clause_does_not_mutate_input(self):
        """The caller's `where` dict must not be mutated by the helper."""
        original = {"source_type": "A"}
        Retriever._build_where_clause(original, "AAPL", None)
        assert original == {"source_type": "A"}  # unchanged

    def test_build_where_clause_all_none_returns_none(self):
        """With all kwargs None and no where, return None (not {}).

        Critical: passing {} to ChromaDB raises ValueError because ChromaDB
        requires exactly one top-level operator. So the helper must return
        None (which the search() method passes through as 'no filter'),
        never an empty dict.
        """
        result = Retriever._build_where_clause(None, None, None)
        assert result is None
        assert result != {}  # explicit: never return empty dict

    def test_build_where_clause_empty_where_dict_returns_none(self):
        """An empty `where={}` is treated as no filter (returns None)."""
        result = Retriever._build_where_clause({}, None, None)
        assert result is None

    def test_build_where_clause_empty_string_ticker_is_skipped(self):
        """ticker='' is treated as 'no filter' (skipped), not a literal match.

        Rationale: a literal {"ticker": ""} would match no real chunks and
        almost always indicates a caller bug. We silently skip it.
        """
        result = Retriever._build_where_clause(None, "", None)
        assert result is None

    def test_build_where_clause_empty_string_standard_id_is_skipped(self):
        """standard_id='' is treated as 'no filter' (skipped), not a literal match."""
        result = Retriever._build_where_clause(None, None, "")
        assert result is None

    def test_build_where_clause_both_empty_strings_returns_none(self):
        """Both ticker='' and standard_id='' → no filter at all."""
        result = Retriever._build_where_clause(None, "", "")
        assert result is None

    def test_build_where_clause_mixed_none_and_empty(self):
        """Mixed None and '' are both skipped; only truthy filters survive."""
        result = Retriever._build_where_clause({"source_type": "A"}, "", None)
        assert result == {"source_type": "A"}

    def test_build_where_clause_passes_through_special_chars(self):
        """Filter values with quotes or $ chars are passed through unchanged.

        The helper builds a Python dict (not a SQL string), so there's no
        injection risk and no escaping is needed. ChromaDB receives the
        literal value and handles matching itself.
        """
        result = Retriever._build_where_clause(
            None, 'AAPL"$special', "AS\"1105"
        )
        assert result == {
            "$and": [
                {"ticker": 'AAPL"$special'},
                {"standard_id": 'AS"1105'},
            ]
        }

    def test_infer_sources_searched_empty_string_ticker_not_counted(self):
        """Empty-string ticker doesn't imply Source B (no actual filter applied)."""
        result = Retriever._infer_sources_searched(None, "", None)
        assert result == []

    def test_infer_sources_searched_empty_string_standard_id_not_counted(self):
        """Empty-string standard_id doesn't imply Source A (no actual filter applied)."""
        result = Retriever._infer_sources_searched(None, None, "")
        assert result == []

    def test_infer_sources_searched_no_filters(self):
        """No filters → empty list."""
        result = Retriever._infer_sources_searched(None, None, None)
        assert result == []

    def test_infer_sources_searched_ticker_implies_b(self):
        """Ticker filter implies Source B."""
        result = Retriever._infer_sources_searched(None, "AAPL", None)
        assert result == ["B"]

    def test_infer_sources_searched_standard_id_implies_a(self):
        """Standard_id filter implies Source A."""
        result = Retriever._infer_sources_searched(None, None, "AS1105")
        assert result == ["A"]

    def test_infer_sources_searched_combined_returns_sorted(self):
        """Both ticker and standard_id → both source types, sorted."""
        result = Retriever._infer_sources_searched(None, "AAPL", "AS1105")
        assert result == ["A", "B"]

    def test_infer_sources_searched_dedupes_when_source_type_matches_implication(self):
        """Setting where={source_type: A} + standard_id='AS1105' dedupes to ['A']."""
        result = Retriever._infer_sources_searched(
            {"source_type": "A"}, None, "AS1105"
        )
        assert result == ["A"]