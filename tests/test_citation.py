import pytest
from src.knowledge_engineering.citation import (
    format_citation,
    parse_citation,
    format_compound,
    SourceType,
)


class TestFormatCitation:
    def test_source_a_simple_paragraph(self):
        assert format_citation("AS1105.12", SourceType.SOURCE_A) == "[AS 1105 § .12]"

    def test_source_a_paragraph_range(self):
        assert format_citation("AS1105.10-.15", SourceType.SOURCE_A) == "[AS 1105 § .10-.15]"

    def test_source_a_qc_standard(self):
        assert format_citation("QC1000.34", SourceType.SOURCE_A) == "[QC 1000 § .34]"

    def test_source_a_ei_standard(self):
        assert format_citation("EI0015.05", SourceType.SOURCE_A) == "[EI 15 § .05]"

    def test_source_a_with_letter_suffix(self):
        assert format_citation("AS1105.10A", SourceType.SOURCE_A) == "[AS 1105 § .10A]"

    def test_source_b_item1a(self):
        assert format_citation("AAPL.2025.Item1A", SourceType.SOURCE_B) == "[AAPL 10-K, Item 1A (2025)]"

    def test_source_b_item7(self):
        assert format_citation("JPM.2025.Item7", SourceType.SOURCE_B) == "[JPM 10-K, Item 7 (2025)]"

    def test_source_b_item9a(self):
        assert format_citation("MSFT.2025.Item9A", SourceType.SOURCE_B) == "[MSFT 10-K, Item 9A (2025)]"

    def test_source_b_with_subparagraph(self):
        assert format_citation("AAPL.2025.Item1A.3", SourceType.SOURCE_B) == "[AAPL 10-K, Item 1A (2025)]"

    def test_source_c_internal_audit_report(self):
        assert format_citation("IA-2026-004.3.1", SourceType.SOURCE_C) == "[InternalAuditReport:IA-2026-004.3.1]"

    def test_source_c_control_matrix(self):
        assert format_citation("NSRL-CTL-2026-001.4.2", SourceType.SOURCE_C) == "[ControlMatrix:NSRL-CTL-2026-001.4.2]"

    def test_source_c_risk_register(self):
        assert format_citation("NS-RISK-2026-001.3.4", SourceType.SOURCE_C) == "[RiskRegister:NS-RISK-2026-001.3.4]"


class TestParseCitation:
    def test_parse_source_a(self):
        result = parse_citation("[AS 1105 § .12]")
        assert result is not None
        assert result.source_type == SourceType.SOURCE_A
        assert result.chunk_id == "AS1105.12"

    def test_parse_source_a_range(self):
        result = parse_citation("[AS 1105 § .10-.15]")
        assert result is not None
        assert result.source_type == SourceType.SOURCE_A

    def test_parse_source_b(self):
        result = parse_citation("[AAPL 10-K, Item 1A (2025)]")
        assert result is not None
        assert result.source_type == SourceType.SOURCE_B
        assert result.chunk_id == "AAPL.2025.Item1A"

    def test_parse_source_c(self):
        result = parse_citation("[InternalAuditReport:2025-H-001]")
        assert result is not None
        assert result.source_type == SourceType.SOURCE_C

    def test_parse_invalid_returns_none(self):
        assert parse_citation("not a citation") is None
        assert parse_citation("[invalid") is None


class TestFormatCompound:
    def test_compound_two_citations(self):
        result = format_compound(["[AS 1105 § .12]", "[AAPL 10-K, Item 1A (2025)]"])
        assert result == "[AS 1105 § .12]; [AAPL 10-K, Item 1A (2025)]"

    def test_compound_three_citations(self):
        result = format_compound([
            "[AS 1105 § .12]",
            "[AAPL 10-K, Item 1A (2025)]",
            "[InternalAuditReport:2025-H-001]"
        ])
        assert result == "[AS 1105 § .12]; [AAPL 10-K, Item 1A (2025)]; [InternalAuditReport:2025-H-001]"

    def test_compound_empty_returns_empty(self):
        assert format_compound([]) == ""
