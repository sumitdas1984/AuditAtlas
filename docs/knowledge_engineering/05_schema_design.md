# Schema Design — Knowledge Engineering

**Phase**: 3 — Knowledge Engineering
**Issue**: FEATURE-003-TASK-1 (#11)
**Status**: Complete

---

## Source A — PCAOB Auditing Standards

| Field | Type | Example |
|-------|------|---------|
| `standard_id` | string | `AS 1000` |
| `title` | string | General Responsibilities of the Auditor |
| `document_type` | enum | `Standard`, `RulemakingRelease`, `StaffGuidance` |
| `issue_date` | date | `2024-05-13` |
| `effective_date` | date | `2024-12-15` |
| `status` | enum | `Effective`, `Proposed`, `Delayed` |
| `source_url` | string | `https://pcaobus.org/...` |
| `file_path` | string | `data/raw/pcaob_standards/...` |

---

## Source B — SEC 10-K Filings

| Field | Type | Example |
|-------|------|---------|
| `company_name` | string | Apple Inc. |
| `ticker` | string | `AAPL` |
| `filing_date` | date | `2025-09-27` |
| `fiscal_year` | integer | `2025` |
| `sections_present` | string[] | `["Item 1A", "Item 7", "Item 8", "Item 9A"]` |
| `source_url` | string | `https://www.sec.gov/...` |
| `file_path` | string | `data/raw/sec_10k/...` |

---

## Source C — Synthetic Documents

All fields apply to every synthetic doc. Fields not applicable to a document are omitted.

| Field | Type | Example |
|-------|------|---------|
| `document_id` | string | `IA-2026-004` |
| `document_type` | enum | `InternalAuditReport`, `ControlMatrix`, `RiskRegister`, `SOP`, `Policy` |
| `version` | string | `3.2` |
| `effective_date` | date | `2026-01-15` |
| `review_date` | date | `2026-12-31` |
| `classification` | enum | `Internal`, `Confidential` |
| `owner` | string | Chief Risk Officer |
| `company` | string | Northwind Retail Solutions Ltd. |
| `file_path` | string | `data/raw/synthetic_company_docs/...` |

---

## Future Enhancements (Post-MVP)

These features are **intentionally deferred** — not forgotten. They require the MVP foundation before being viable.

| Feature | Description | Trigger |
|---------|-------------|---------|
| Cross-document chaining | Link findings → controls → risks across documents at query time | Phase 6+ evaluation |
| Machine-readable ID extraction | Extract and store `finding_ids[]`, `control_ids[]`, `risk_ids[]` as metadata | Phase 4+ when relationship queries surface |
| Knowledge graph | Structured entity relationships beyond document-level metadata | When cross-doc chaining proves valuable |

These will be revisited after Phase 8 (Evaluation) based on user research needs.
