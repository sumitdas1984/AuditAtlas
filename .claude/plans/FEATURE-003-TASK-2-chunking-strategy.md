# Plan: FEATURE-003-TASK-2 — Chunking Strategy

## Context

TASK-2 defines how documents are split into retrievable chunks while preserving citation anchors, cross-reference context, and self-contained meaning for RAG.

Building on TASK-1 schema:
- Source A (PCAOB): documents have numbered sections (.01, .10A), Roman numeral parts, appendix structure
- Source B (SEC 10-K): documents have standardized sections (Item 1A, Item 7, etc.), risk factors by paragraph
- Source C (Synthetic): documents have H1/H2 heading sections, tables with IDs (finding, control, risk)

## Approach

### Source A — PCAOB Standards

**Chunk by paragraph** — each numbered paragraph (`.01`, `.02`, `.10A`) is one chunk.

Why: Paragraphs are the atomic unit of PCAOB citation. Standards cite "paragraph .12" not "page 5." Keeping paragraph boundaries preserves the exact citation anchor.

- Each chunk gets ID: `{standard_id}.{paragraph_number}` (e.g., `AS1105.12`)
- Multiple paragraphs on the same topic can be grouped into a "section chunk" if they consistently appear together in citations
- Tables and figures become separate chunks with their own IDs
- Appendices chunked by section number

**Edge case:** When a paragraph is very long (>500 words), split at sub-paragraph boundaries (`.10A`, `.10B`) or sentence breaks.

### Source B — SEC 10-K

**Chunk by section + paragraph** — each Item (1A, 7, 8, 9A) is a section chunk, subdivided by topic paragraphs within the section.

Why: 10-K queries typically target a specific section ("risk factors" or "MD&A"). Chunking by section keeps context while allowing targeted retrieval.

- Each chunk gets ID: `{ticker}.{fiscal_year}.{item}` (e.g., `AAPL.2025.Item1A`)
- Within Item 1A (Risk Factors), chunk by individual risk factor paragraph
- Tables (risk matrices, financial tables) become separate chunks with captions
- Item numbers are stable citation anchors

**Edge case:** Risk factors are often multi-paragraph narratives. Chunk at paragraph boundaries, keeping paragraph as atomic unit.

### Source C — Synthetic Documents

**Chunk by H1/H2 heading section** — each heading (and its content) is one chunk.

Why: Each section in synthetic docs is semantically self-contained. A heading like "Finding 2025-H-001: E-Commerce Payment Reconciliation Gap" is a complete unit of meaning.

- Each chunk gets ID: `{document_id}.{section_ref}` (e.g., `IA-2026-004.3.2`)
- Tables become separate chunks with caption and column headers preserved
- Finding IDs, control IDs, risk IDs appear in heading text and are preserved as anchors

**Edge case:** Tables — extract as structured chunks with: table caption, column headers, row data, and table ID for citation.

## Output

Create `docs/knowledge_engineering/06_chunking_strategy.md` with:
1. Chunking approach per source type (A, B, C)
2. Chunk ID format per source type
3. Edge cases (long paragraphs, tables)
4. Overlap strategy (if any)

## Verification

- Each chunk ID maps to a stable location in the source document
- Chunks are self-contained (can answer a question independently)
- Citation format in TASK-3 can reference chunk IDs defined here
