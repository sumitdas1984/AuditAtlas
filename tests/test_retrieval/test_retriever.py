import pytest
import tempfile
import shutil
from pathlib import Path

from src.ingestion.chunkers.chunker import Chunk
from src.ingestion.embedder.embedder import Embedder
from src.ingestion.storage.chroma_store import ChromaStore
from src.ingestion.storage.json_store import JsonStore
from src.retrieval import Retriever, RetrievedChunk, SearchResult


@pytest.fixture
def temp_dir():
    """Create a temp directory for storage."""
    d = tempfile.mkdtemp()
    yield d
    try:
        shutil.rmtree(d)
    except Exception:
        pass


@pytest.fixture
def embedder():
    return Embedder()


@pytest.fixture
def populated_stores(temp_dir, embedder):
    """Build Chroma + JSON stores pre-populated with chunks from all three sources."""
    chroma = ChromaStore(persist_dir=str(Path(temp_dir) / "chroma"), collection_name="test_retriever")
    json_store = JsonStore(store_path=str(Path(temp_dir) / "chunks.jsonl"))

    chunks = [
        Chunk(
            chunk_id="AS1105.12",
            source_type="A",
            document_id="AS1105",
            document_type="Standard",
            chunk_index=12,
            content="The auditor must obtain sufficient appropriate audit evidence to support the audit opinion.",
            metadata={"paragraph": ".12", "standard_id": "AS1105"},
            citation={"format": "[AS 1105 § .12]", "type": "pcaob"},
        ),
        Chunk(
            chunk_id="AS2110.5",
            source_type="A",
            document_id="AS2110",
            document_type="Standard",
            chunk_index=5,
            content="Identifying and assessing risks of material misstatement is fundamental to the audit.",
            metadata={"paragraph": ".5", "standard_id": "AS2110"},
            citation={"format": "[AS 2110 § .5]", "type": "pcaob"},
        ),
        Chunk(
            chunk_id="AAPL.2025.Item1A.1",
            source_type="B",
            document_id="AAPL",
            document_type="10-K",
            chunk_index=1,
            content="Risk factors include supply chain disruption, regulatory scrutiny, and cybersecurity threats.",
            metadata={"ticker": "AAPL", "fiscal_year": "2025", "item": "Item 1A"},
            citation={"format": "[AAPL 10-K, Item 1A (2025)]", "type": "sec"},
        ),
        Chunk(
            chunk_id="IA-2026-004.3.1",
            source_type="C",
            document_id="IA-2026-004",
            document_type="InternalAuditReport",
            chunk_index=1,
            content="Finding 2025-H-001: E-Commerce Payment Reconciliation Gap. Severity: High.",
            metadata={"heading": "Finding 2025-H-001", "classification": "InternalConfidential"},
            citation={"format": "[InternalAuditReport:2025-H-001]", "type": "synthetic"},
        ),
    ]
    chroma.add(chunks, embedder)
    json_store.write_batch(chunks)
    return chroma, json_store, chunks


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