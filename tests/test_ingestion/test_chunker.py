import pytest
from src.ingestion.parsers.base_parser import ParsedDocument
from src.ingestion.chunkers.chunker import SourceCChunker


@pytest.fixture
def sample_parsed_doc():
    """Sample parsed document for chunking."""
    return ParsedDocument(
        file_path="data/raw/synthetic_company_docs/01-Risk-Register.md",
        document_id="IA-2026-RR01",
        document_type="RiskRegister",
        metadata={
            "effective_date": "2026-01-15",
            "classification": "InternalConfidential",
            "owner": "Chief Risk Officer",
            "company": "Northwind Retail Solutions Ltd.",
        },
        content_blocks=[
            {
                "heading": "Risk Register Overview",
                "level": 1,
                "content": "This document tracks all identified risks for the organization.",
            },
            {
                "heading": "Financial Risks",
                "level": 1,
                "content": "Risks related to financial reporting and treasury operations.",
            },
            {
                "heading": "Credit Risk",
                "level": 2,
                "content": "Risk of loss due to counterparty default.",
            },
            {
                "heading": "Operational Risks",
                "level": 1,
                "content": "Internal process and system failures.",
            },
        ],
    )


def test_chunker_creates_chunks(sample_parsed_doc):
    """Test that chunker creates correct number of chunks."""
    chunker = SourceCChunker()
    chunks = chunker.chunk(sample_parsed_doc)

    # Only content blocks with sufficient content are chunked
    assert len(chunks) >= 1
    assert all(c.source_type == "C" for c in chunks)


def test_chunker_chunk_id_format(sample_parsed_doc):
    """Test chunk ID follows {doc_id}.{section_index} format."""
    chunker = SourceCChunker()
    chunks = chunker.chunk(sample_parsed_doc)

    for chunk in chunks:
        assert "." in chunk.chunk_id
        assert chunk.chunk_id.startswith(sample_parsed_doc.document_id)


def test_chunker_metadata_preserved(sample_parsed_doc):
    """Test that metadata is correctly passed to chunks."""
    chunker = SourceCChunker()
    chunks = chunker.chunk(sample_parsed_doc)

    for chunk in chunks:
        assert chunk.metadata["company"] == "Northwind Retail Solutions Ltd."
        assert chunk.metadata["classification"] == "InternalConfidential"
        assert chunk.metadata["effective_date"] == "2026-01-15"


def test_chunker_citation_format(sample_parsed_doc):
    """Test that citation is correctly formatted."""
    chunker = SourceCChunker()
    chunks = chunker.chunk(sample_parsed_doc)

    for chunk in chunks:
        assert "format" in chunk.citation
        assert "type" in chunk.citation
        assert chunk.citation["type"] == "synthetic"


def test_chunker_skips_short_content():
    """Test that chunks with very little content are skipped."""
    chunker = SourceCChunker()
    doc = ParsedDocument(
        file_path="test.md",
        document_id="TEST-001",
        document_type="RiskRegister",
        metadata={},
        content_blocks=[
            {"heading": "Short", "level": 1, "content": "Hi"},  # Too short
            {"heading": "Normal", "level": 1, "content": "This is normal length content."},
        ],
    )

    chunks = chunker.chunk(doc)
    headings = [c.metadata.get("heading") for c in chunks]
    assert "Short" not in headings
    assert "Normal" in headings
