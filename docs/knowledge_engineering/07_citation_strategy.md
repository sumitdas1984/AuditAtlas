# Citation and Referencing Strategy — Knowledge Engineering

**Phase**: 3 — Knowledge Engineering
**Issue**: FEATURE-003-TASK-3 (#13)
**Status**: Complete

---

## Overview

Citations make answers traceable. Every claim in a generated answer must cite the specific chunk it came from. Citations must be human-readable, source-specific, and traceable to the exact text.

---

## Source A — PCAOB Standards

### Citation Format

```
[AS {id} § {paragraph}]
```

### Examples

| Citation | Meaning |
|----------|---------|
| `[AS 1105 § .01]` | Paragraph .01 of AS 1105 |
| `[AS 1105 § .10A]` | Paragraph .10A of AS 1105 |
| `[AS 1105 § .10-.15]` | Paragraphs .10 through .15 of AS 1105 |
| `[QC 1000 § .34]` | Paragraph .34 of QC 1000 |

### Notes

- Standard ID uses abbreviation (AS, QC, EI) without spaces
- Paragraph number includes leading dot (`.01`, `.10A`)
- Ranges use hyphen with spaces on either side (`§ .10-.15`)

---

## Source B — SEC 10-K Filings

### Citation Format

```
[{ticker} 10-K, {item} ({year})]
```

### Examples

| Citation | Meaning |
|----------|---------|
| `[AAPL 10-K, Item 1A (2025)]` | Item 1A (Risk Factors) from Apple's 2025 10-K |
| `[JPM 10-K, Item 7 (2025)]` | Item 7 (MD&A) from JPMorgan's 2025 10-K |
| `[MSFT 10-K, Item 9A (2025)]` | Item 9A (Controls) from Microsoft's 2025 10-K |

### Notes

- Item number is the SEC standard item identifier (Item 1A, Item 7, Item 8, Item 9A, etc.)
- Fiscal year is the filing year, not the fiscal year end date
- Ticker is uppercase

---

## Source C — Synthetic Documents

### Citation Format

```
[{doc_type}:{reference_id}]
```

### Examples

| Citation | Meaning |
|----------|---------|
| `[InternalAuditReport:2025-H-001]` | Finding 2025-H-001 from the Internal Audit Report |
| `[ControlMatrix:REV-007]` | Control REV-007 from the Control Matrix |
| `[RiskRegister:COMP-001]` | Risk COMP-001 from the Risk Register |
| `[SOP:SOP-PROC-005]` | SOP-PROC-005 (Vendor Onboarding SOP) |
| `[Policy:NRS-POL-001]` | Policy NRS-POL-001 |

### Section-Level Citations

When citing a specific section without a reference ID:

```
[{doc_type}:{doc_id}.{section}]
```

**Example:**
- `[ControlMatrix:NSRL-CTL-2026-001.4.2]` — Section 4.2 of the Control Matrix

### Notes

- `doc_type` is the schema enum value (InternalAuditReport, ControlMatrix, RiskRegister, SOP, Policy)
- No spaces in reference IDs

---

## Compound Citations

When an answer draws from multiple chunks across different sources:

### Format

```
[{source1_citation}]; [{source2_citation}]; [{source3_citation}]
```

### Example

```
[AS 1105 § .12]; [AAPL 10-K, Item 1A (2025)]; [InternalAuditReport:2025-H-001]
```

### Notes

- Each individual citation follows its source-specific format
- Citations separated by semicolons with single spaces
- Order does not imply priority

---

## Citation Requirements

1. **Every cited claim must have a citation** — no unsupported statements
2. **Citations must reference specific chunks** — not entire documents
3. **Citations must be traceable** — each citation maps to the exact source text
4. **Citations must be human-readable** — not URLs, not raw chunk IDs
5. **No hallucinated citations** — if no source supports a claim, the claim is not made
