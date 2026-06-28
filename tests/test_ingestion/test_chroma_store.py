import pytest
import tempfile
import shutil
from pathlib import Path
from src.ingestion.chunkers.chunker import Chunk
from src.ingestion.storage.chroma_store import ChromaStore
from src.ingestion.embedder.embedder import Embedder


@pytest.fixture
def sample_chunk():
    """Create a sample chunk for testing."""
    return Chunk(
        chunk_id="TEST-001.1",
        source_type="C",
        document_id="TEST-001",
        document_type="RiskRegister",
        chunk_index=1,
        content="## Risk Overview\n\nThis is a risk overview section.",
        metadata={
            "heading": "Risk Overview",
            "level": 1,
            "classification": "InternalConfidential",
            "effective_date": "2026-01-15",
        },
        citation={
            "format": "[RiskRegister:TEST-001]",
            "type": "synthetic",
        },
    )


@pytest.fixture
def embedder():
    """Create an embedder instance."""
    return Embedder()


class TestChromaStore:
    """Tests for ChromaDB store."""

    @pytest.fixture
    def temp_chroma(self):
        """Create a temporary ChromaDB store."""
        temp_dir = tempfile.mkdtemp()
        store = ChromaStore(persist_dir=temp_dir, collection_name="test_chunks")
        yield store
        # Cleanup
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass

    def test_add_single_chunk(self, temp_chroma, sample_chunk, embedder):
        """Test adding a single chunk."""
        temp_chroma.add([sample_chunk], embedder)

        # Verify by searching
        results = temp_chroma.search("risk overview", embedder, n_results=1)
        assert len(results['ids'][0]) >= 1

    def test_add_multiple_chunks(self, temp_chroma, sample_chunk, embedder):
        """Test adding multiple chunks."""
        chunks = [
            sample_chunk,
            Chunk(
                chunk_id="TEST-001.2",
                source_type="C",
                document_id="TEST-001",
                document_type="RiskRegister",
                chunk_index=2,
                content="## Financial Risk\n\nThis is a financial risk section.",
                metadata={"heading": "Financial Risk", "level": 1},
                citation={"format": "[RiskRegister:TEST-001]", "type": "synthetic"},
            ),
        ]
        temp_chroma.add(chunks, embedder)

        results = temp_chroma.search("risk", embedder, n_results=5)
        assert len(results['ids'][0]) >= 2

    def test_search_returns_distances(self, temp_chroma, sample_chunk, embedder):
        """Test that search returns distance scores."""
        temp_chroma.add([sample_chunk], embedder)

        results = temp_chroma.search("risk overview", embedder, n_results=1)
        assert 'distances' in results
        assert len(results['distances'][0]) == 1

    def test_search_with_filter(self, temp_chroma, sample_chunk, embedder):
        """Test search with metadata filter."""
        temp_chroma.add([sample_chunk], embedder)

        # Search with source_type filter
        results = temp_chroma.search(
            "risk",
            embedder,
            n_results=1,
            where={"source_type": "C"}
        )
        assert len(results['ids'][0]) >= 1

    def test_search_empty_query(self, temp_chroma, sample_chunk, embedder):
        """Test search with empty query."""
        temp_chroma.add([sample_chunk], embedder)

        # Empty query should still return results (uses embedding of empty string)
        results = temp_chroma.search("", embedder, n_results=1)
        assert 'ids' in results
