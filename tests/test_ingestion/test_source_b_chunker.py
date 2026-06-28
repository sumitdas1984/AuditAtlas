import pytest
from src.ingestion.parsers.base_parser import ParsedDocument
from src.ingestion.chunkers.chunker import SourceBChunker


class TestSourceBChunker:
    """Tests for Source B (SEC 10-K) chunker."""

    @pytest.fixture
    def sample_parsed_doc(self):
        """Sample parsed 10-K document."""
        return ParsedDocument(
            file_path="data/raw/sec_10k/aapl-20250927.pdf",
            document_id="AAPL",
            document_type="10-K",
            metadata={
                "ticker": "AAPL",
                "fiscal_year": "2025",
                "company_name": "Apple Inc.",
            },
            content_blocks=[
                {
                    "heading": "",
                    "content": "Item 1A. Risk Factors\n\nOur business is subject to risks...",
                    "level": 0,
                    "paragraph_num": 1,
                },
                {
                    "heading": "",
                    "content": "Some more content for risk factors that continues here.",
                    "level": 0,
                    "paragraph_num": 2,
                },
                {
                    "heading": "",
                    "content": "Item 7. Management's Discussion\n\nManagement discussion content here.",
                    "level": 0,
                    "paragraph_num": 3,
                },
                {
                    "heading": "",
                    "content": "Item 8. Financial Statements\n\nFinancial statements content here.",
                    "level": 0,
                    "paragraph_num": 4,
                },
            ],
        )

    def test_split_at_item_boundaries(self):
        """Test splitting content blocks at Item section boundaries."""
        chunker = SourceBChunker()

        # No Item headers — single segment with item=None
        result = chunker._split_at_item_boundaries("Just some text without any item markers.")
        assert len(result) == 1
        assert result[0][0] is None
        assert "Just some text" in result[0][1]

        # Single Item header at start
        result = chunker._split_at_item_boundaries("Item 1A. Risk Factors Some content here.")
        assert len(result) == 1
        assert result[0][0] == "Item 1A"
        assert "Risk Factors" in result[0][1]

        # Multiple Item headers in one block (e.g., AMZN's TOC layout)
        content = "Item 1. Business 3 Item 1A. Risk Factors 6 Item 7. Management's Discussion 20"
        result = chunker._split_at_item_boundaries(content)
        item_ids = [r[0] for r in result if r[0]]
        assert "Item 1" in item_ids
        assert "Item 1A" in item_ids
        assert "Item 7" in item_ids

        # Item header embedded mid-content (e.g., AMZN real sections)
        content = "Wendell P. Weeks Chairman Corning Item 1A. Risk Factors Please carefully consider"
        result = chunker._split_at_item_boundaries(content)
        item_ids = [r[0] for r in result if r[0]]
        assert "Item 1A" in item_ids

    def test_chunker_creates_chunks_per_item(self, sample_parsed_doc):
        """Test that chunker creates one chunk per Item section."""
        chunker = SourceBChunker()
        chunks = chunker.chunk(sample_parsed_doc)

        # Should have chunks for Item 1A, Item 7, and Item 8
        assert len(chunks) == 3

    def test_chunk_id_format(self, sample_parsed_doc):
        """Test chunk ID follows {ticker}.{year}.{item}.{paragraph} format."""
        chunker = SourceBChunker()
        chunks = chunker.chunk(sample_parsed_doc)

        for chunk in chunks:
            assert "." in chunk.chunk_id
            assert chunk.chunk_id.startswith("AAPL.2025.Item")
            assert chunk.metadata["ticker"] == "AAPL"
            assert chunk.metadata["fiscal_year"] == "2025"

    def test_source_type_is_b(self, sample_parsed_doc):
        """Test that chunks have source_type = 'B'."""
        chunker = SourceBChunker()
        chunks = chunker.chunk(sample_parsed_doc)

        for chunk in chunks:
            assert chunk.source_type == "B"

    def test_citation_format(self, sample_parsed_doc):
        """Test SEC 10-K citation format."""
        chunker = SourceBChunker()
        chunks = chunker.chunk(sample_parsed_doc)

        for chunk in chunks:
            citation = chunk.citation
            assert "format" in citation
            assert citation["type"] == "sec"
            assert "AAPL" in citation["format"]
            assert "10-K" in citation["format"]

    def test_metadata_preserved(self, sample_parsed_doc):
        """Test that metadata is correctly passed to chunks."""
        chunker = SourceBChunker()
        chunks = chunker.chunk(sample_parsed_doc)

        for chunk in chunks:
            assert chunk.metadata["ticker"] == "AAPL"
            assert chunk.metadata["fiscal_year"] == "2025"
            assert "Item" in chunk.metadata["item"]

    def test_combines_paragraphs_within_item(self, sample_parsed_doc):
        """Test that multiple paragraphs within same Item are combined."""
        chunker = SourceBChunker()
        chunks = chunker.chunk(sample_parsed_doc)

        # Find the Item 1A chunk
        item_1a_chunk = next(c for c in chunks if "Item1A" in c.chunk_id)
        # Should contain both paragraphs about risk factors
        assert "Risk Factors" in item_1a_chunk.content
        assert "Our business is subject to risks" in item_1a_chunk.content

    def test_handles_no_items(self):
        """Test chunker handles document with no clear Item sections."""
        chunker = SourceBChunker()
        doc = ParsedDocument(
            file_path="test.pdf",
            document_id="TEST",
            document_type="10-K",
            metadata={"ticker": "TEST", "fiscal_year": "2025"},
            content_blocks=[
                {"heading": "", "content": "This is some content without item markers.", "level": 0, "paragraph_num": 1},
            ],
        )

        chunks = chunker.chunk(doc)
        # 10-K without Item sections produces no chunks
        # This is expected behavior - valid 10-Ks have Item sections
        assert len(chunks) == 0

    def test_is_cross_reference_detects_part_reference(self):
        """Cross-references like 'Item 7 of Part II' should be filtered."""
        chunker = SourceBChunker()

        # Real sections — NOT cross-references
        assert chunker._is_cross_reference("Item 7. Management's Discussion") is False
        assert chunker._is_cross_reference("Item 1A. Risk Factors content here") is False

        # Cross-references — should be detected
        assert chunker._is_cross_reference("Item 7 of Part II, Management's Discussion") is True
        assert chunker._is_cross_reference("Item 1A of Part I, Risk Factors") is True
        assert chunker._is_cross_reference("See Item 8 of Part II for details") is True

    def test_dedupe_by_longest_keeps_longest_chunk(self):
        """Dedup keeps the longest chunk per chunk_id when duplicates exist."""
        from src.ingestion.chunkers.chunker import Chunk

        chunker = SourceBChunker()

        short = Chunk(
            chunk_id="AMZN.2025.Item1A.1",
            source_type="B",
            document_id="AMZN",
            document_type="10-K",
            chunk_index=1,
            content="Item 1A. Risk Factors 6",  # TOC entry — short
            metadata={"ticker": "AMZN", "fiscal_year": "2025", "item": "Item 1A"},
            citation={"format": "[AMZN 10-K, Item 1A (2025)]", "type": "sec"},
        )
        long = Chunk(
            chunk_id="AMZN.2025.Item1A.1",
            source_type="B",
            document_id="AMZN",
            document_type="10-K",
            chunk_index=1,
            content="Item 1A. Risk Factors Our business is subject to risks that could..." * 5,
            metadata={"ticker": "AMZN", "fiscal_year": "2025", "item": "Item 1A"},
            citation={"format": "[AMZN 10-K, Item 1A (2025)]", "type": "sec"},
        )

        result = chunker._dedupe_by_longest([short, long])
        assert len(result) == 1
        assert len(result[0].content) > len(short.content)

    def test_chunk_handles_mid_block_item_headers(self):
        """AMZN-style PDFs embed Item headers mid-block; chunker must split them."""
        chunker = SourceBChunker()

        # Simulates AMZN PDF layout: a single block with multiple Items
        doc = ParsedDocument(
            file_path="data/raw/sec_10k/amzn-20251231.pdf",
            document_id="AMZN",
            document_type="10-K",
            metadata={"ticker": "AMZN", "fiscal_year": "2025"},
            content_blocks=[
                {
                    "heading": "",
                    "content": "Item 1. Business 3 Item 1A. Risk Factors 6 Item 7. Management's Discussion 20",
                    "level": 0,
                    "paragraph_num": 1,
                },
                {
                    "heading": "",
                    "content": "Wendell P. Weeks Chairman Corning Item 1A. Risk Factors Please carefully consider the risks.",
                    "level": 0,
                    "paragraph_num": 2,
                },
            ],
        )

        chunks = chunker.chunk(doc)
        # Should produce chunks for Item 1, 1A, 7 — and dedup Item 1A to keep longest
        item_ids = [c.metadata["item"] for c in chunks]
        assert "Item 1" in item_ids
        assert "Item 1A" in item_ids
        assert "Item 7" in item_ids
        # Item 1A appears only once after dedup
        assert item_ids.count("Item 1A") == 1

    def test_chunk_filters_cross_reference_chunks(self):
        """End-to-end: cross-references like 'Item X of Part Y' should not appear as chunks."""
        chunker = SourceBChunker()

        doc = ParsedDocument(
            file_path="test.pdf",
            document_id="TEST",
            document_type="10-K",
            metadata={"ticker": "TEST", "fiscal_year": "2025"},
            content_blocks=[
                {
                    "heading": "",
                    "content": "Item 1. Business Overview We are a test company.",
                    "level": 0,
                    "paragraph_num": 1,
                },
                {
                    "heading": "",
                    "content": "Item 7 of Part II, Management's Discussion, is incorporated by reference.",
                    "level": 0,
                    "paragraph_num": 2,
                },
            ],
        )

        chunks = chunker.chunk(doc)
        item_ids = [c.metadata["item"] for c in chunks]
        # Item 7 should be filtered as cross-reference
        assert "Item 7" not in item_ids
        # Item 1 (real section) should remain
        assert "Item 1" in item_ids
