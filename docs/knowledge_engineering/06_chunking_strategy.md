# Chunking Strategy — Knowledge Engineering

**Phase**: 3 — Knowledge Engineering
**Issue**: FEATURE-003-TASK-2 (#12)
**Status**: Complete

---

## Overview

Chunking defines how documents are split into retrievable units. Each chunk must be:
- Self-contained enough to answer a question independently
- Identifiable by a stable citation anchor
- Small enough to be relevant, large enough to have context

---

## Source A — PCAOB Standards

### Chunk Unit: Paragraph

Each numbered paragraph (`.01`, `.02`, `.10A`) is one chunk.

Paragraphs are the atomic unit of PCAOB citation. Standards cite "see paragraph .12" not "page 5" — paragraph boundaries preserve the exact citation anchor.

### Chunk ID Format

```
{standard_id}.{paragraph}
```

**Examples:**
- `AS1105.01`
- `AS1105.10A`
- `QC1000.34`

### Rules

- Tables and figures become separate chunks with their own IDs
- Appendices chunked by section number (e.g., `AS1105.Appendix1.3`)
- Roman numeral sections (I, II, III) are metadata only, not chunk boundaries

### Edge Cases

- Paragraphs longer than 500 words: split at sub-paragraph boundaries (`.10A`, `.10B`) or sentence breaks
- Introductory paragraphs without paragraph numbers: assign section prefix + sequential number (e.g., `AS1105.Intro.1`)

---

## Source B — SEC 10-K Filings

### Chunk Unit: Section + Paragraph

Each standardized Item (Item 1A, Item 7, Item 8, Item 9A) is the section boundary. Within each section, chunk by topic paragraph.

Why: 10-K queries typically target a specific section ("risk factors" or "MD&A"). Chunking by section keeps context while allowing targeted retrieval.

### Chunk ID Format

```
{ticker}.{fiscal_year}.{item}
```

**Examples:**
- `AAPL.2025.Item1A`
- `JPM.2025.Item7`
- `MSFT.2025.Item9A`

For sub-chunks within a section:

```
{ticker}.{fiscal_year}.{item}.{paragraph_index}
```

**Example:**
- `AAPL.2025.Item1A.3` (third risk factor paragraph in Apple's 2025 filing)

### Rules

- Tables (risk matrices, financial tables) become separate chunks with captions preserved
- Item numbers are stable citation anchors from the SEC EDGAR standard
- Cross-references to other Items are preserved as metadata on the chunk

### Edge Cases

- Risk Factors (Item 1A) are multi-paragraph narratives — chunk at paragraph boundaries, treating each paragraph as atomic
- Very short Items (Item 1B, Item 2): treat entire Item as one chunk

---

## Source C — Synthetic Documents

### Chunk Unit: H1/H2 Heading Section

Each heading (H1 or H2) and its content is one chunk.

Each section in synthetic docs is semantically self-contained. A heading like "Finding 2025-H-001: E-Commerce Payment Reconciliation Gap" is a complete unit of meaning.

### Chunk ID Format

```
{document_id}.{section}
```

**Examples:**
- `IA-2026-004.3.1` (Finding 2025-H-001 — High-Risk Observation)
- `NSRL-CTL-2026-001.4.2` (Revenue and Sales Processing Controls)
- `NS-RISK-2026-001.3.4` (Compliance and Regulatory Risks)

### Rules

- Tables become separate chunks with caption and column headers preserved
- Finding IDs, control IDs, risk IDs appear in heading text and are preserved as anchors
- Multiple H2s under one H1: each H2 gets its own chunk with H1 prefix

### Edge Cases

- Tables: extract as structured chunks with table ID, caption, column headers, and row data
- Sections without clear headings: assign sequential section number based on document structure

---

## Summary

| Source | Chunk Unit | Chunk ID Format | Example |
|--------|-----------|-----------------|---------|
| A — PCAOB | Paragraph | `{standard_id}.{paragraph}` | `AS1105.12` |
| B — SEC 10-K | Section + paragraph | `{ticker}.{year}.{item}` | `AAPL.2025.Item1A` |
| C — Synthetic | Heading section | `{doc_id}.{section}` | `IA-2026-004.3.1` |

---

## Out of Scope for MVP

- **Hierarchical chunking** — grouping related chunks into larger context windows
- **Overlap between chunks** — for preserving cross-reference context
- **Dynamic chunk sizing** — adjusting chunk size based on semantic density
