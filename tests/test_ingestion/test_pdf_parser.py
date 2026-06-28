import pytest
from pathlib import Path
from src.ingestion.parsers.pdf_parser import PDFParser


class TestPDFParser:
    """Tests for PDF parser."""

    def test_extract_document_info_as_standard(self):
        """Test extraction of AS/QC standard IDs."""
        parser = PDFParser()

        result = parser._extract_document_info("2024-004-as1000.pdf")
        assert result["document_id"] == "AS1000"
        assert result["document_type"] == "Standard"

        result = parser._extract_document_info("2024-005-qc1000.pdf")
        assert result["document_id"] == "QC1000"

        result = parser._extract_document_info("AS2110-release.pdf")
        assert result["document_id"] == "AS2110"

    def test_extract_document_info_release(self):
        """Test extraction of release numbers."""
        parser = PDFParser()

        result = parser._extract_document_info("pcaob-release-no-2025-004.pdf")
        assert result["document_id"] == "PCAOB-2025-004"

        result = parser._extract_document_info("release_2010-004.pdf")
        assert result["document_id"] == "PCAOB-2010-004"

    def test_extract_document_info_staff_guidance(self):
        """Test staff guidance document ID."""
        parser = PDFParser()

        result = parser._extract_document_info("staff-guidance-evaluating.pdf")
        assert result["document_id"] == "STAFF-GUIDANCE"

    def test_extract_document_info_source_b(self):
        """Test extraction of Source B (10-K) ticker and fiscal year."""
        parser = PDFParser()

        result = parser._extract_document_info("aapl-20250927.pdf")
        assert result["document_id"] == "AAPL"
        assert result["document_type"] == "10-K"
        assert result["extra_metadata"]["ticker"] == "AAPL"
        assert result["extra_metadata"]["fiscal_year"] == "2025"

        result = parser._extract_document_info("msft.pdf")
        assert result["document_id"] == "MSFT"
        assert result["document_type"] == "10-K"
        assert result["extra_metadata"]["ticker"] == "MSFT"
        assert result["extra_metadata"]["fiscal_year"] == ""

    def test_split_into_paragraphs(self):
        """Test paragraph splitting."""
        parser = PDFParser()

        text = """
        This is the first paragraph. It has multiple sentences.

        This is the second paragraph. It also has multiple sentences.

        Short.
        """

        paragraphs = parser._split_into_paragraphs(text)

        # Should have 2+ paragraphs (short ones filtered out)
        assert len(paragraphs) >= 2
        assert all(p["heading"] == "" for p in paragraphs)
        assert all(p["level"] == 0 for p in paragraphs)

    def test_split_filters_short_paragraphs(self):
        """Test that very short paragraphs are filtered."""
        parser = PDFParser()

        text = """
        This is a valid paragraph with enough words to pass the filter.

        Short.
        """

        paragraphs = parser._split_into_paragraphs(text)
        contents = [p["content"] for p in paragraphs]

        assert "Short." not in contents
        assert len(paragraphs) == 1
