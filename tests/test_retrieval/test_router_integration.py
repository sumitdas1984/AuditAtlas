"""Tests for Retriever ↔ Router integration (FEATURE-005-TASK-3).

Verifies that:
- Queries route to the correct source(s) via the Phase 3 Router
- Multi-source aggregation sorts by distance, dedupes, respects top_k
- `SearchResult.routing` and `sources_searched` are populated correctly
- Explicit filters bypass routing
- `use_router=False` and missing router gracefully fall back to single search
"""

import pytest

from src.knowledge_engineering.router import Router
from src.retrieval import Retriever, SearchResult


class TestRouterRoutesToCorrectSources:
    """Verify that routed queries hit the right source(s)."""

    def test_router_compliance_routes_to_all_sources(self, populated_stores):
        chroma, json_store, _ = populated_stores
        retriever = Retriever(chroma_store=chroma, json_store=json_store, router=Router())
        result = retriever.search("compliance requirements")

        assert isinstance(result, SearchResult)
        assert "A" in result.sources_searched
        assert "B" in result.sources_searched
        assert "C" in result.sources_searched
        assert result.routing is not None
        # All 4 chunks in fixture should be findable
        assert len(result.chunks) >= 3

    def test_router_requirement_intent_routes_to_source_a(self, populated_stores):
        chroma, json_store, _ = populated_stores
        retriever = Retriever(chroma_store=chroma, json_store=json_store, router=Router())
        result = retriever.search("What must auditors do?")

        assert result.routing is not None
        for chunk in result.chunks:
            assert chunk.source_type == "A"
        assert result.sources_searched == ["A"]

    def test_router_finding_intent_routes_to_source_c(self, populated_stores):
        chroma, json_store, _ = populated_stores
        retriever = Retriever(chroma_store=chroma, json_store=json_store, router=Router())
        result = retriever.search("Show me audit findings")

        for chunk in result.chunks:
            assert chunk.source_type == "C"
        assert "C" in result.sources_searched

    def test_router_audit_standards_routes_to_source_a(self, populated_stores):
        chroma, json_store, _ = populated_stores
        retriever = Retriever(chroma_store=chroma, json_store=json_store, router=Router())
        result = retriever.search("What does PCAOB say about audit evidence?")

        for chunk in result.chunks:
            assert chunk.source_type == "A"
        assert result.sources_searched == ["A"]

    def test_router_risk_factors_routes_to_source_b_primary(self, populated_stores):
        """RISK_FACTORS topic routes to B (primary) and C (secondary).

        The router's ROUTING_TABLE has risk_factors as primary=B, secondary=C,
        so both are searched. The test verifies B is in sources_searched and
        that the AAPL 10-K chunk (the actual matching content for 'Apple's
        risk factors') appears in the results.
        """
        chroma, json_store, _ = populated_stores
        retriever = Retriever(chroma_store=chroma, json_store=json_store, router=Router())
        result = retriever.search("What are Apple's risk factors?")

        assert "B" in result.sources_searched
        # AAPL chunk is in the fixture — must appear for this query
        chunk_ids = {c.chunk_id for c in result.chunks}
        assert "AAPL.2025.Item1A.1" in chunk_ids
        # No Source A chunks (auditor independence is not what was asked)
        for chunk in result.chunks:
            assert chunk.source_type in ("B", "C")

    def test_router_unclassified_routes_to_all_sources(self, populated_stores):
        chroma, json_store, _ = populated_stores
        retriever = Retriever(chroma_store=chroma, json_store=json_store, router=Router())
        result = retriever.search("asdfghjkl random text")  # unclassified

        assert len(result.sources_searched) == 3
        assert result.routing is not None


class TestMultiSourceAggregation:
    """Verify multi-source results are merged correctly."""

    def test_multi_source_results_sorted_by_distance_global(self, populated_stores):
        """Mixed-source chunks must be ordered by distance ascending across sources."""
        chroma, json_store, _ = populated_stores
        retriever = Retriever(chroma_store=chroma, json_store=json_store, router=Router())
        result = retriever.search("audit risk evidence", top_k=10)

        distances = [c.distance for c in result.chunks]
        assert distances == sorted(distances), (
            f"Expected ascending distances, got {distances}"
        )

    def test_multi_source_respects_top_k_after_merge(self, populated_stores):
        """Even when 3 sources contribute, total chunks ≤ top_k."""
        chroma, json_store, _ = populated_stores
        retriever = Retriever(chroma_store=chroma, json_store=json_store, router=Router())
        result = retriever.search("audit risk", top_k=2)

        assert len(result.chunks) <= 2

    def test_multi_source_preserves_source_attribution(self, populated_stores):
        """Every chunk's source_type must be one of the routed sources."""
        chroma, json_store, _ = populated_stores
        retriever = Retriever(chroma_store=chroma, json_store=json_store, router=Router())
        result = retriever.search("compliance", top_k=10)

        routed = set(result.sources_searched)
        for chunk in result.chunks:
            assert chunk.source_type in routed

    def test_multi_source_populates_routing_field(self, populated_stores):
        """routing field is the RoutingResult from the Router."""
        chroma, json_store, _ = populated_stores
        retriever = Retriever(chroma_store=chroma, json_store=json_store, router=Router())
        result = retriever.search("compliance requirements")

        assert result.routing is not None
        assert hasattr(result.routing, "sources")
        assert hasattr(result.routing, "confidence")
        assert hasattr(result.routing, "reasoning")
        assert len(result.routing.reasoning) > 0

    def test_multi_source_populates_sources_searched(self, populated_stores):
        """sources_searched mirrors routing.sources (as strings)."""
        chroma, json_store, _ = populated_stores
        retriever = Retriever(chroma_store=chroma, json_store=json_store, router=Router())
        result = retriever.search("compliance requirements")

        assert result.sources_searched == sorted(
            [s.value for s in result.routing.sources]
        )


class TestRouterBypass:
    """Explicit filters and flags should bypass routing."""

    def test_explicit_where_bypasses_router(self, populated_stores):
        chroma, json_store, _ = populated_stores
        retriever = Retriever(chroma_store=chroma, json_store=json_store, router=Router())
        result = retriever.search("anything", where={"source_type": "A"})

        # Single-search path: no routing populated
        assert result.routing is None
        for chunk in result.chunks:
            assert chunk.source_type == "A"
        assert result.sources_searched == ["A"]

    def test_explicit_ticker_bypasses_router(self, populated_stores):
        chroma, json_store, _ = populated_stores
        retriever = Retriever(chroma_store=chroma, json_store=json_store, router=Router())
        result = retriever.search("risk factors", ticker="AAPL")

        assert result.routing is None
        for chunk in result.chunks:
            assert chunk.source_type == "B"
            assert chunk.metadata.get("ticker") == "AAPL"

    def test_explicit_standard_id_bypasses_router(self, populated_stores):
        chroma, json_store, _ = populated_stores
        retriever = Retriever(chroma_store=chroma, json_store=json_store, router=Router())
        result = retriever.search("audit evidence", standard_id="AS1105")

        assert result.routing is None
        for chunk in result.chunks:
            assert chunk.source_type == "A"
            assert chunk.metadata.get("standard_id") == "AS1105"

    def test_use_router_false_skips_routing(self, populated_stores):
        """Even with router set, use_router=False forces single search."""
        chroma, json_store, _ = populated_stores
        retriever = Retriever(chroma_store=chroma, json_store=json_store, router=Router())
        result = retriever.search("compliance", use_router=False)

        assert result.routing is None
        # Single search returns whatever's closest — no source-scoping
        assert result.sources_searched == []

    def test_no_router_instance_skips_routing(self, populated_stores):
        """Retriever(router=None).search() works without error, no routing populated."""
        chroma, json_store, _ = populated_stores
        retriever = Retriever(chroma_store=chroma, json_store=json_store, router=None)
        result = retriever.search("audit risk")

        assert result.routing is None
        # Still gets results via single-search path
        assert isinstance(result, SearchResult)
        assert len(result.chunks) >= 1


class TestRetrieverWithRouterHelpers:
    """Direct unit tests for the multi-source aggregation helper."""

    def test_search_multi_source_dedupes_by_chunk_id(self, populated_stores):
        """If the same chunk_id appears in multiple sources, only the first (closer) is kept."""
        from src.ingestion.embedder.embedder import Embedder

        chroma, json_store, _ = populated_stores
        retriever = Retriever(
            chroma_store=chroma,
            json_store=json_store,
            embedder=Embedder(),
        )
        # Build a minimal routing result pointing to all 3 sources
        from src.knowledge_engineering.router import RoutingResult, SourceType
        routing = RoutingResult(
            sources=[SourceType.SOURCE_A, SourceType.SOURCE_B, SourceType.SOURCE_C],
            confidence=0.9,
            reasoning="test",
        )
        chunks = retriever._search_multi_source("audit evidence", top_k=5, routing_result=routing)

        chunk_ids = [c.chunk_id for c in chunks]
        assert len(chunk_ids) == len(set(chunk_ids)), f"Duplicate chunk_ids found: {chunk_ids}"
        assert len(chunks) <= 5

    def test_search_multi_source_empty_routing_returns_empty(self, populated_stores):
        """RoutingResult with no sources yields no chunks."""
        from src.ingestion.embedder.embedder import Embedder

        chroma, json_store, _ = populated_stores
        retriever = Retriever(
            chroma_store=chroma,
            json_store=json_store,
            embedder=Embedder(),
        )
        from src.knowledge_engineering.router import RoutingResult, SourceType
        routing = RoutingResult(sources=[], confidence=0.0, reasoning="empty")
        chunks = retriever._search_multi_source("anything", top_k=5, routing_result=routing)

        assert chunks == []