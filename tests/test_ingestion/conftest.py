"""Shared fixtures for ingestion tests."""

import pytest

from src.ingestion.chunkers.chunker import Chunk
from src.ingestion.embedder.embedder import Embedder


@pytest.fixture
def embedder():
    """Default Embedder instance.

    Function-scoped because the Embedder itself is cheap to construct; the
    underlying sentence-transformer model is cached internally so re-creating
    the wrapper does not re-load weights.
    """
    return Embedder()


@pytest.fixture
def sample_chunk():
    """Source-C RiskRegister chunk used by ChromaStore tests."""
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
        citation={"format": "[RiskRegister:TEST-001]", "type": "synthetic"},
    )


@pytest.fixture
def sample_internal_audit_chunk():
    """Source-C InternalAuditReport chunk used by storage tests.

    Distinct from `sample_chunk` because storage tests assert against the
    literal chunk_id (`IA-2026-004.1`); sharing the RiskRegister shape would
    break those assertions.
    """
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
        citation={"format": "[InternalAuditReport:IA-2026-004]", "type": "synthetic"},
    )