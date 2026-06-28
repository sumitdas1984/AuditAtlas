import pytest
from pathlib import Path
from src.ingestion.parsers.pdf_parser import PDFParser


class TestPDFParser:
    """Tests for PDF parser."""

    def test_extract_document_id_as_standard(self):
        """Test extraction of AS/QC standard IDs."""
        parser = PDFParser()

        assert parser._extract_document_id("2024-004-as1000.pdf") == "AS1000"
        assert parser._extract_document_id("2024-005-qc1000.pdf") == "QC1000"
        assert parser._extract_document_id("AS2110-release.pdf") == "AS2110"

    def test_extract_document_id_release(self):
        """Test extraction of release numbers."""
        parser = PDFParser()

        assert parser._extract_document_id("pcaob-release-no-2025-004.pdf") == "PCAOB-2025-004"
        assert parser._extract_document_id("release_2010-004.pdf") == "PCAOB-2010-004"

    def test_extract_document_id_staff_guidance(self):
        """Test staff guidance document ID."""
        parser = PDFParser()

        assert parser._extract_document_id("staff-guidance-evaluating.pdf") == "STAFF-GUIDANCE"

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
