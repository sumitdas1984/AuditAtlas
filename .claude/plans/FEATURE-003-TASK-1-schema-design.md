# Plan: FEATURE-003-TASK-1 — Schema Design for All Source Types

## Context

Issue #11 requires designing a metadata schema for all three source types.

## Approach

**Source A — PCAOB Standards Schema**

| Field | Type | Example |
|-------|------|---------|
| `standard_id` | string | AS 1000, QC 1000 |
| `title` | string | General Responsibilities of the Auditor |
| `document_type` | enum | Standard, RulemakingRelease, StaffGuidance |
| `issue_date` | date | 2024-05-13 |
| `effective_date` | date | 2024-12-15 |
| `status` | enum | Effective, Proposed, Delayed |
| `source_url` | string | https://pcaobus.org/... |
| `file_path` | string | data/pcaob_standards/... |

**Source B — SEC 10-K Schema**

| Field | Type | Example |
|-------|------|---------|
| `company_name` | string | Apple Inc. |
| `ticker` | string | AAPL |
| `filing_date` | date | 2025-09-27 |
| `fiscal_year` | integer | 2025 |
| `sections_present` | string[] | Item 1A, Item 7, Item 8, Item 9A |
| `source_url` | string | https://www.sec.gov/... |
| `file_path` | string | data/sec_10k/... |

**Source C — Synthetic Documents (Flat)**

All fields apply to every synthetic doc. Fields not applicable to a document are omitted.

| Field | Type | Example |
|-------|------|---------|
| `document_id` | string | IA-2026-004 |
| `document_type` | enum | InternalAuditReport, ControlMatrix, RiskRegister, SOP, Policy |
| `version` | string | 3.2 |
| `effective_date` | date | 2026-01-15 |
| `review_date` | date | 2026-12-31 |
| `classification` | enum | Internal, Confidential |
| `owner` | string | Chief Risk Officer |
| `company` | string | Northwind Retail Solutions Ltd. |
| `file_path` | string | data/synthetic_company_docs/... |

## Output

Create `docs/knowledge_engineering/05_schema_design.md`
