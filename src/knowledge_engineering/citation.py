import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SourceType(str, Enum):
    SOURCE_A = "A"  # PCAOB Standards
    SOURCE_B = "B"  # SEC 10-K
    SOURCE_C = "C"  # Synthetic Documents


@dataclass
class CitationResult:
    citation: str
    source_type: SourceType
    chunk_id: str


def format_citation(chunk_id: str, source_type: SourceType) -> str:
    """
    Convert a chunk_id to a human-readable citation.

    Examples:
        AS1105.12 -> [AS 1105 § .12]
        AAPL.2025.Item1A -> [AAPL 10-K, Item 1A (2025)]
        IA-2026-004.3.1 -> [InternalAuditReport:2025-H-001]
    """
    if source_type == SourceType.SOURCE_A:
        return _format_source_a_citation(chunk_id)
    elif source_type == SourceType.SOURCE_B:
        return _format_source_b_citation(chunk_id)
    elif source_type == SourceType.SOURCE_C:
        return _format_source_c_citation(chunk_id)
    else:
        raise ValueError(f"Unknown source type: {source_type}")


def _format_source_a_citation(chunk_id: str) -> str:
    """
    Format: [AS {id} § {paragraph}]
    Examples: [AS 1105 § .12], [AS 1105 § .10-.15]
    """
    match = re.match(r"(AS|QC|EI)(\d+)\.(.+)", chunk_id)
    if not match:
        return f"[{chunk_id}]"

    prefix, number, paragraph = match.groups()
    # Strip leading zeros from standard number
    standard_number = str(int(number))
    standard_id = f"{prefix} {standard_number}"

    # Add leading dot if not present (chunk_id format AS1105.12 -> paragraph 12)
    if not paragraph.startswith("."):
        paragraph = "." + paragraph

    if "-" in paragraph:
        start, end = paragraph.split("-", 1)
        return f"[{standard_id} § {start}-{end}]"

    return f"[{standard_id} § {paragraph}]"


def _format_source_b_citation(chunk_id: str) -> str:
    """
    Format: [{ticker} 10-K, {item} ({year})]
    Examples: [AAPL 10-K, Item 1A (2025)]
    """
    match = re.match(r"([A-Z]+)\.(\d+)\.(Item)(\d+[A-Z]?)(?:\.(\d+))?", chunk_id)
    if not match:
        return f"[{chunk_id}]"

    ticker, year, item_prefix, item_number = match.group(1), match.group(2), match.group(3), match.group(4)
    return f"[{ticker} 10-K, {item_prefix} {item_number} ({year})]"


def _format_source_c_citation(chunk_id: str) -> str:
    """
    Format: [{doc_type}:{reference_id}]
    Examples: [InternalAuditReport:2025-H-001]
    """
    if ":" in chunk_id:
        return f"[{chunk_id}]"

    parts = chunk_id.split(".")
    if len(parts) < 2:
        return f"[{chunk_id}]"

    doc_id = parts[0]

    doc_type_map = {
        "IA": "InternalAuditReport",
        "NSRL-CTL": "ControlMatrix",
        "NS-RISK": "RiskRegister",
        "NS-POL": "Policy",
        "NS-SOP": "SOP",
    }

    # Match prefixes of varying lengths
    doc_type = "Unknown"
    for prefix, dtype in doc_type_map.items():
        if doc_id.startswith(prefix):
            doc_type = dtype
            break

    # Use full chunk_id as reference_id
    return f"[{doc_type}:{chunk_id}]"


def parse_citation(citation: str) -> Optional[CitationResult]:
    """
    Parse a citation string back to its components.
    Returns None if the citation format is unrecognized.
    """
    citation = citation.strip()
    if not (citation.startswith("[") and citation.endswith("]")):
        return None

    inner = citation[1:-1]

    result = _parse_source_a_citation(inner)
    if result:
        return result

    result = _parse_source_b_citation(inner)
    if result:
        return result

    result = _parse_source_c_citation(inner)
    if result:
        return result

    return None


def _parse_source_a_citation(inner: str):
    match = re.match(r"(AS|QC|EI)\s+(\d+)\s+§\s+(.+)", inner)
    if match:
        prefix, number, paragraph = match.groups()
        # Remove leading dot from paragraph (chunk_id format uses dot as separator)
        paragraph_clean = paragraph.lstrip(".")
        chunk_id = f"{prefix}{number}.{paragraph_clean}"
        return CitationResult(citation=f"[{inner}]", source_type=SourceType.SOURCE_A, chunk_id=chunk_id)
    return None


def _parse_source_b_citation(inner: str):
    match = re.match(r"([A-Z]+)\s+10-K,\s+(Item)\s+(\d+[A-Z]?)\s+\((\d+)\)", inner)
    if match:
        ticker, item, item_number, year = match.groups()
        chunk_id = f"{ticker}.{year}.{item}{item_number}"
        return CitationResult(citation=f"[{inner}]", source_type=SourceType.SOURCE_B, chunk_id=chunk_id)
    return None


def _parse_source_c_citation(inner: str):
    match = re.match(r"(\w+):(.+)", inner)
    if match:
        doc_type, ref_id = match.groups()
        chunk_id = ref_id
        return CitationResult(citation=f"[{inner}]", source_type=SourceType.SOURCE_C, chunk_id=chunk_id)
    return None


def format_compound(citations: list[str]) -> str:
    """
    Join multiple citations with semicolons.
    Example: [AS 1105 § .12]; [AAPL 10-K, Item 1A (2025)]
    """
    return "; ".join(citations)
