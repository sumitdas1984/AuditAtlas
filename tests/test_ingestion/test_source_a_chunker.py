import pytest
from src.ingestion.parsers.base_parser import ParsedDocument
from src.ingestion.chunkers.chunker import SourceAChunker


class TestSourceAChunker:
    """Tests for Source A (PCAOB) chunker."""

    @pytest.fixture
    def sample_parsed_doc(self):
        """Sample parsed PCAOB document."""
        return ParsedDocument(
            file_path="data/raw/pcaob_standards/2024-004-as1000.pdf",
            document_id="AS1000",
            document_type="Standard",
            metadata={
                "title": "General Responsibilities of the Auditor",
                "effective_date": "2024-12-15",
                "status": "Effective",
            },
            content_blocks=[
                {
                    "heading": "",
                    "content": "Paragraph one content here. This is the first paragraph with sufficient length.",
                    "level": 0,
                    "paragraph_num": 1,
                },
                {
                    "heading": "",
                    "content": "Paragraph two content here. This is the second paragraph with sufficient length.",
                    "level": 0,
                    "paragraph_num": 2,
                },
                {
                    "heading": "",
                    "content": "Paragraph three content here. This is the third paragraph.",
                    "level": 0,
                    "paragraph_num": 3,
                },
            ],
        )

    def test_chunker_creates_chunks(self, sample_parsed_doc):
        """Test that chunker creates correct number of chunks."""
        chunker = SourceAChunker()
        chunks = chunker.chunk(sample_parsed_doc)

        # All 3 paragraphs should become chunks
        assert len(chunks) == 3

    def test_chunk_id_format(self, sample_parsed_doc):
        """Test chunk ID follows {standard_id}.{paragraph} format."""
        chunker = SourceAChunker()
        chunks = chunker.chunk(sample_parsed_doc)

        for chunk in chunks:
            assert "." in chunk.chunk_id
            assert chunk.chunk_id.startswith("AS1000.")
            assert chunk.metadata["standard_id"] == "AS1000"

    def test_source_type_is_a(self, sample_parsed_doc):
        """Test that chunks have source_type = 'A'."""
        chunker = SourceAChunker()
        chunks = chunker.chunk(sample_parsed_doc)

        for chunk in chunks:
            assert chunk.source_type == "A"

    def test_citation_format(self, sample_parsed_doc):
        """Test PCAOB citation format."""
        chunker = SourceAChunker()
        chunks = chunker.chunk(sample_parsed_doc)

        # Citation should be like [AS 1000 § .1]
        for chunk in chunks:
            citation = chunk.citation
            assert "format" in citation
            assert citation["type"] == "pcaob"
            assert "AS" in citation["format"]
            assert "§" in citation["format"]

    def test_metadata_preserved(self, sample_parsed_doc):
        """Test that metadata is correctly passed to chunks."""
        chunker = SourceAChunker()
        chunks = chunker.chunk(sample_parsed_doc)

        for chunk in chunks:
            assert chunk.metadata["standard_id"] == "AS1000"
            assert chunk.metadata["effective_date"] == "2024-12-15"
            assert chunk.metadata["status"] == "Effective"

    def test_filters_short_content(self):
        """Test that short paragraphs are skipped."""
        chunker = SourceAChunker()
        doc = ParsedDocument(
            file_path="test.pdf",
            document_id="TEST",
            document_type="Standard",
            metadata={},
            content_blocks=[
                {"heading": "", "content": "Short", "level": 0, "paragraph_num": 1},
                {"heading": "", "content": "This is a longer paragraph with enough words.", "level": 0, "paragraph_num": 2},
            ],
        )

        chunks = chunker.chunk(doc)
        assert len(chunks) == 1
        assert chunks[0].chunk_index == 2
