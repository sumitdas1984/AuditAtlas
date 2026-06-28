import pytest
import tempfile
import os
from pathlib import Path
from src.ingestion.parsers.markdown_parser import MarkdownParser


@pytest.fixture
def sample_markdown():
    """Sample Markdown document with frontmatter."""
    return """---
document_id: IA-2026-004
document_type: InternalAuditReport
version: "3.2"
effective_date: 2026-01-15
review_date: 2026-12-31
classification: InternalConfidential
owner: Margaret Thornton
company: Northwind Retail Solutions Ltd.
---

# Internal Audit Report

## Executive Summary

This is the executive summary content. It provides an overview of the audit
findings and key recommendations for management consideration.

## Finding 2025-H-001

### E-Commerce Payment Reconciliation Gap

Severity: High

A gap was identified in the e-commerce payment reconciliation process.
"""

@pytest.fixture
def temp_md_file(sample_markdown):
    """Create a temporary Markdown file."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".md",
        delete=False,
        encoding="utf-8"
    ) as f:
        f.write(sample_markdown)
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    os.unlink(temp_path)


def test_parser_extracts_frontmatter(temp_md_file):
    """Test that parser extracts YAML frontmatter correctly."""
    parser = MarkdownParser()
    doc = parser.parse(temp_md_file)

    assert doc.document_id == "IA-2026-004"
    assert doc.document_type == "InternalAuditReport"
    assert doc.metadata["owner"] == "Margaret Thornton"
    assert doc.metadata["classification"] == "InternalConfidential"


def test_parser_splits_by_headings(temp_md_file):
    """Test that parser splits content into heading blocks."""
    parser = MarkdownParser()
    doc = parser.parse(temp_md_file)

    # Should have blocks for: Executive Summary, Finding 2025-H-001, E-Commerce...
    headings = [b["heading"] for b in doc.content_blocks]
    assert "Executive Summary" in headings
    assert "E-Commerce Payment Reconciliation Gap" in headings


def test_parser_content_not_empty(temp_md_file):
    """Test that content blocks have actual content."""
    parser = MarkdownParser()
    doc = parser.parse(temp_md_file)

    for block in doc.content_blocks:
        if block["heading"] and block["content"]:
            assert len(block["content"]) > 0


def test_infer_document_type():
    """Test document type inference from filename."""
    parser = MarkdownParser()

    assert parser._infer_document_type("01-Internal-Audit-Report") == "InternalAuditReport"
    assert parser._infer_document_type("01-Risk-Register") == "RiskRegister"
    assert parser._infer_document_type("01-Control-Matrix") == "ControlMatrix"
    assert parser._infer_document_type("01-Policy") == "Policy"
    assert parser._infer_document_type("01-SOP-for-Vendor-Onboarding") == "SOP"
