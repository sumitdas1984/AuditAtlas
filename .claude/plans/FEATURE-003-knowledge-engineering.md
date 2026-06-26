# Plan: FEATURE-003 — Knowledge Engineering

**Issue**: https://github.com/sumitdas1984/AuditAtlas/issues/4
**Phase**: 3
**Status**: In Progress — TASK-1 ✅ Complete

## Phase Folder Structure

All Phase 3 outputs are stored in `docs/knowledge_engineering/`

## Objective

Design the knowledge engineering foundation that enables traceable, citeable answers in downstream phases. This bridges data acquisition (Phase 2) and ingestion (Phase 4).

---

## Background

Three source types with different structures:

| Source | Format | Sample Documents | Key Structural Elements |
|--------|--------|-----------------|----------------------|
| A — PCAOB Standards | PDF | AS 1000, AS 1105, AS 2110, AS 2201, AS 2301 | Numbered sections, authoritative text, effective dates |
| B — SEC 10-K | PDF | AAPL, AMZN, JPM, MSFT, TSLA filings | Standardized sections (Item 1A, 7, 8, 9A), risk factors, financial statements |
| C — Synthetic Docs | Markdown | Internal Audit Report, Risk Register, Control Matrix, Policies & Procedures, SOP | Hierarchical headings, tables, finding IDs, risk ratings, distribution lists |

---

## Tasks

### Task 1: Schema Design for Each Source Type

Define a metadata schema for each source that supports:
- Source identification and versioning
- Temporal queries (e.g., "latest effective date")
- Topic/keyword filtering
- Citation traceability back to source

**Source A — PCAOB Standards**
- Standard ID (e.g., AS 1105)
- Full title
- Effective date
- PCAOB source URL
- Topics covered (array)
- Section structure (for chunking)

**Source B — SEC 10-K**
- Company name and ticker
- Filing date and fiscal year end
- SEC EDGAR filing number
- Sections present (Item 1A, 7, 8, 9A, etc.)
- Topics covered (array — extracted from risk factors)

**Source C — Synthetic Documents**
- Document type (Internal Audit Report, Risk Register, Control Matrix, Policy, SOP)
- Company name (Northwind Retail Solutions Ltd.)
- Document reference number
- Effective date and review date
- Classification (Internal Use – Confidential)
- Distribution list
- Topics covered (array)

**Deliverable**: `docs/knowledge_engineering/05_schema_design.md` — Schema definitions for all three source types ✅

---

### Task 2: Chunking Strategy

Define how documents are split into retrievable chunks while preserving context.

**Principles**:
- Chunks must be self-contained enough to answer a question independently
- Preserve citation anchors (section IDs, finding IDs, table references)
- Overlap where necessary to maintain cross-reference context

**Approach by source**:

- **Source A (Standards)**: Chunk by section (e.g., AS 1105.10, AS 1105.15). Each chunk retains section number as citation anchor. Larger sections split by paragraph with sub-anchors.

- **Source B (10-K)**: Chunk by section (Item 1A, Item 7, etc.). Within sections, chunk by topic paragraph or risk factor. Retain item number and page reference.

- **Source C (Synthetic)**: Chunk by heading section (H1/H2 level). Tables extracted as structured chunks with caption and column headers. Findings, risk entries, and control IDs become named anchors.

**Deliverable**: `docs/knowledge_engineering/06_chunking_strategy.md` — Chunking approach per source type, including edge cases

---

### Task 3: Citation and Referencing Strategy

Define how retrieved chunks are cited in generated answers.

**Requirements**:
- Each citation must point back to a specific chunk, not just a document
- Citation format should be readable: `AS 1105 § 12` or `10-K Item 1A (p.3)`
- Citations must be traceable to the exact source text
- Support for compound citations (multiple sources in one answer)

**Proposed citation format**:
- PCAOB: `[AS <ID> § <section-number>]`
- SEC 10-K: `[<Ticker> 10-K, <Item> (<fiscal-year>)]`
- Synthetic: `[<Doc-Type>:<Reference-ID>]`

**Deliverable**: `docs/knowledge_engineering/07_citation_strategy.md` — Citation format definitions and examples

---

### Task 4: Multi-Source Query Routing

Define how a user query routes to relevant sources and how results are aggregated.

**Query classification axes**:
- Topic: audit standards, SEC filings, internal controls, risk, policy, procedure
- Intent: definition, finding, requirement, example, comparison
- Scope: specific company/standard vs. general guidance

**Routing rules** (initial):
- "What does PCAOB say about X?" → Source A only
- "What are the risk factors for X?" → Source B only
- "How does company X handle Y?" → Source B + C
- "What controls exist for X?" → Source C (Control Matrix)
- "Show me audit findings for X" → Source C (Internal Audit Report)
- Unclassified → all sources, ranked by relevance

**Deliverable**: `docs/knowledge_engineering/08_query_routing.md` — Query classification taxonomy and routing logic

---

### Task 5: Implement Schema and Routing as Code

- Create schema definitions in code (YAML or JSON)
- Implement query classifier/router
- Implement citation formatter
- No ingestion yet (Phase 4) — this is design-only implementation

**Deliverable**: `src/knowledge_engineering/` directory with:
- `schemas/` — YAML schema definitions per source type
- `router.py` — Query classification and routing logic
- `citation.py` — Citation formatting utilities

---

## Output Summary

| Task | Output File | Status |
|------|------------|--------|
| 1. Schema Design | `docs/knowledge_engineering/05_schema_design.md` | ✅ |
| 2. Chunking Strategy | `docs/knowledge_engineering/06_chunking_strategy.md` | |
| 3. Citation Strategy | `docs/knowledge_engineering/07_citation_strategy.md` | |
| 4. Query Routing | `docs/knowledge_engineering/08_query_routing.md` | |
| 5. Code Implementation | `src/knowledge_engineering/` | |

---

## Dependencies

- Phase 2 (Source C synthetic docs) — ✅ Complete
- Phase 4 (Data Ingestion) — depends on schemas from this phase

## Next Steps After This Phase

Phase 4 (Data Ingestion) will use the schemas and chunking strategies defined here to parse, validate, and store documents in the knowledge base.
