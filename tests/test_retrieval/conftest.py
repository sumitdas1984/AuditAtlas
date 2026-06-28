"""Shared fixtures for retrieval tests."""

import pytest
import tempfile
import shutil
from pathlib import Path

from src.ingestion.chunkers.chunker import Chunk
from src.ingestion.embedder.embedder import Embedder
from src.ingestion.storage.chroma_store import ChromaStore
from src.ingestion.storage.json_store import JsonStore


@pytest.fixture
def temp_dir():
    """Create a temp directory for storage."""
    d = tempfile.mkdtemp()
    yield d
    try:
        shutil.rmtree(d)
    except Exception:
        pass


@pytest.fixture(scope="module")
def embedder():
    """Default Embedder instance.

    Module-scoped because loading the sentence-transformer model is expensive
    (~1-2s) and the model is read-only — safe to share across tests in a
    module. Per-function fixtures that wrap it (e.g., populated_stores) still
    create fresh ChromaStore/JsonStore instances per test.
    """
    return Embedder()


@pytest.fixture
def populated_stores(temp_dir, embedder):
    """Build Chroma + JSON stores pre-populated with one chunk per source.

    Chunks cover all three source types (A: PCAOB, B: SEC 10-K, C: Synthetic)
    so routing tests can verify multi-source behavior end-to-end.
    """
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