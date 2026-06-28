import pytest
import tempfile
import os
import json
from pathlib import Path
from src.ingestion.parsers.base_parser import ParsedDocument
from src.ingestion.chunkers.chunker import Chunk
from src.ingestion.storage.json_store import JsonStore
from src.ingestion.storage.sqlite_index import SqliteIndex


@pytest.fixture
def sample_chunk():
    """Create a sample chunk for testing."""
    return Chunk(
        chunk_id="IA-2026-004.1",
        source_type="C",
        document_id="IA-2026-004",
        document_type="InternalAuditReport",
        chunk_index=1,
        content="## Executive Summary\n\nThis is the content.",
        metadata={
            "heading": "Executive Summary",
            "level": 1,
            "classification": "InternalConfidential",
            "effective_date": "2026-01-15",
            "owner": "Margaret Thornton",
            "company": "Northwind Retail Solutions Ltd.",
        },
        citation={
            "format": "[InternalAuditReport:IA-2026-004]",
            "type": "synthetic",
        },
    )


class TestJsonStore:
    """Tests for JSONL store."""

    @pytest.fixture
    def temp_store(self):
        """Create a temporary JSON store."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f:
            temp_path = f.name
        store = JsonStore(temp_path)
        yield store
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    def test_write_and_read(self, temp_store, sample_chunk):
        """Test writing and reading a chunk."""
        temp_store.write(sample_chunk)

        result = temp_store.read(sample_chunk.chunk_id)
        assert result is not None
        assert result["chunk_id"] == sample_chunk.chunk_id
        assert result["document_type"] == sample_chunk.document_type

    def test_write_batch(self, temp_store, sample_chunk):
        """Test writing multiple chunks."""
        chunks = [
            sample_chunk,
            Chunk(
                chunk_id="IA-2026-004.2",
                source_type="C",
                document_id="IA-2026-004",
                document_type="InternalAuditReport",
                chunk_index=2,
                content="## Finding 2025-H-001",
                metadata={"heading": "Finding 2025-H-001"},
                citation={"format": "[InternalAuditReport:2025-H-001]", "type": "synthetic"},
            ),
        ]

        temp_store.write_batch(chunks)
        all_chunks = temp_store.read_all()

        assert len(all_chunks) == 2
        assert all(c["chunk_id"] in ["IA-2026-004.1", "IA-2026-004.2"] for c in all_chunks)

    def test_read_nonexistent(self, temp_store):
        """Test reading a chunk that doesn't exist."""
        result = temp_store.read("nonexistent")
        assert result is None

    def test_read_missing_file_returns_none(self):
        """Reading from a path that doesn't exist should return None, not raise."""
        import os
        missing_path = os.path.join(tempfile.gettempdir(), "definitely_not_here.jsonl")
        # Ensure the file does not exist
        if os.path.exists(missing_path):
            os.unlink(missing_path)
        store = JsonStore(missing_path)
        # Both read() and read_all() should handle the missing file gracefully
        assert store.read("anything") is None
        assert store.read_all() == []

    def test_clear(self, temp_store, sample_chunk):
        """Test clearing the store."""
        temp_store.write(sample_chunk)
        temp_store.clear()

        result = temp_store.read_all()
        assert len(result) == 0


class TestSqliteIndex:
    """Tests for SQLite index."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary SQLite database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_path = f.name
        store = SqliteIndex(temp_path)
        yield store
        # Close any open connections before deletion
        import sqlite3
        try:
            sqlite3.connect(temp_path).close()
        except Exception:
            pass
        import gc
        gc.collect()  # Force cleanup of any lingering connections
        try:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        except PermissionError:
            pass  # Windows file locking - ignore

    def test_insert_and_query_by_source(self, temp_db, sample_chunk):
        """Test inserting and querying by source type."""
        temp_db.insert(sample_chunk)

        results = temp_db.query_by_source("C")
        assert sample_chunk.chunk_id in results

    def test_insert_batch(self, temp_db, sample_chunk):
        """Test inserting multiple chunks."""
        chunks = [
            sample_chunk,
            Chunk(
                chunk_id="IA-2026-004.2",
                source_type="C",
                document_id="IA-2026-004",
                document_type="InternalAuditReport",
                chunk_index=2,
                content="Test",
                metadata={},
                citation={"format": "[Test]", "type": "synthetic"},
            ),
        ]

        temp_db.insert_batch(chunks)

        results = temp_db.query_by_source("C")
        assert len(results) == 2
        assert all(r in ["IA-2026-004.1", "IA-2026-004.2"] for r in results)

    def test_query_by_document(self, temp_db, sample_chunk):
        """Test querying by document ID."""
        temp_db.insert(sample_chunk)

        results = temp_db.query_by_document(sample_chunk.document_id)
        assert sample_chunk.chunk_id in results

    def test_query_nonexistent_source(self, temp_db):
        """Test querying a source with no chunks."""
        results = temp_db.query_by_source("Z")
        assert len(results) == 0

    def test_insert_and_query_by_ticker(self, temp_db, sample_chunk):
        """Insert chunks with tickers and verify query_by_ticker returns the right ones."""
        aapl_chunk = Chunk(
            chunk_id="AAPL.2025.Item1A.1",
            source_type="B",
            document_id="AAPL",
            document_type="10-K",
            chunk_index=1,
            content="Apple risk factors.",
            metadata={"ticker": "AAPL", "fiscal_year": "2025", "item": "Item 1A"},
            citation={"format": "[AAPL 10-K, Item 1A (2025)]", "type": "sec"},
        )
        msft_chunk = Chunk(
            chunk_id="MSFT.2025.Item1A.1",
            source_type="B",
            document_id="MSFT",
            document_type="10-K",
            chunk_index=1,
            content="Microsoft risk factors.",
            metadata={"ticker": "MSFT", "fiscal_year": "2025", "item": "Item 1A"},
            citation={"format": "[MSFT 10-K, Item 1A (2025)]", "type": "sec"},
        )
        temp_db.insert_batch([sample_chunk, aapl_chunk, msft_chunk])

        aapl_results = temp_db.query_by_ticker("AAPL")
        assert aapl_results == ["AAPL.2025.Item1A.1"]

        msft_results = temp_db.query_by_ticker("MSFT")
        assert msft_results == ["MSFT.2025.Item1A.1"]

    def test_insert_and_query_by_standard_id(self, temp_db, sample_chunk):
        """Insert chunks with standard_ids and verify query_by_standard_id returns the right ones."""
        as1105_chunk = Chunk(
            chunk_id="AS1105.12",
            source_type="A",
            document_id="AS1105",
            document_type="Standard",
            chunk_index=12,
            content="Audit evidence paragraph.",
            metadata={"paragraph": ".12", "standard_id": "AS1105"},
            citation={"format": "[AS 1105 § .12]", "type": "pcaob"},
        )
        as2110_chunk = Chunk(
            chunk_id="AS2110.5",
            source_type="A",
            document_id="AS2110",
            document_type="Standard",
            chunk_index=5,
            content="Risk assessment paragraph.",
            metadata={"paragraph": ".5", "standard_id": "AS2110"},
            citation={"format": "[AS 2110 § .5]", "type": "pcaob"},
        )
        temp_db.insert_batch([sample_chunk, as1105_chunk, as2110_chunk])

        as1105_results = temp_db.query_by_standard_id("AS1105")
        assert as1105_results == ["AS1105.12"]

        as2110_results = temp_db.query_by_standard_id("AS2110")
        assert as2110_results == ["AS2110.5"]

    def test_query_by_ticker_no_match(self, temp_db, sample_chunk):
        """query_by_ticker for an unknown ticker returns an empty list."""
        temp_db.insert(sample_chunk)
        results = temp_db.query_by_ticker("XYZ")
        assert results == []

    def test_query_by_standard_id_no_match(self, temp_db, sample_chunk):
        """query_by_standard_id for an unknown standard returns an empty list."""
        temp_db.insert(sample_chunk)
        results = temp_db.query_by_standard_id("AS9999")
        assert results == []
