# Plan: FEATURE-003-TASK-3 — Citation and Referencing Strategy

## Context

TASK-3 defines how retrieved chunks are cited in generated answers. Citations must be traceable to specific chunks (not just documents), readable, and support compound citations.

Building on TASK-2 chunking:
- Source A chunk ID: `{standard_id}.{paragraph}` (e.g., `AS1105.12`)
- Source B chunk ID: `{ticker}.{year}.{item}` (e.g., `AAPL.2025.Item1A`)
- Source C chunk ID: `{doc_id}.{section}` (e.g., `IA-2026-004.3.1`)

## Approach

### Citation Format

Each source type has a human-readable citation format that maps to its chunk ID.

**Source A — PCAOB Standards**

```
[AS {id} § {paragraph}]
```

Example: `[AS 1105 § .12]`

Extends to: `[AS {id} § {paragraph}-{end_paragraph}]` for ranges (e.g., `[AS 1105 § .10-.15]`)

**Source B — SEC 10-K**

```
[{ticker} 10-K, {item} ({year})]
```

Example: `[AAPL 10-K, Item 1A (2025)]`

**Source C — Synthetic Documents**

```
[{doc_type}:{reference_id}]
```

Example: `[InternalAuditReport:2025-H-001]`

For section-level citations without a specific reference ID:
```
[{doc_type}:{doc_id}.{section}]
```

Example: `[ControlMatrix:NSRL-CTL-2026-001.4.2]`

### Compound Citations

When an answer draws from multiple chunks, citations are combined with semicolons:

```
[AS 1105 § .12]; [AAPL 10-K, Item 1A (2025)]; [InternalAuditReport:2025-H-001]
```

### Citation Requirements

- Every cited claim in a generated answer must have a corresponding citation
- Citations must reference a specific chunk, not an entire document
- Citation must be traceable back to the exact text in the source chunk
- Citation text must be human-readable (not a URL or chunk ID string)

## Output

Create `docs/knowledge_engineering/07_citation_strategy.md` with:
1. Citation format per source type
2. Citation examples per source type
3. Compound citation format
4. Citation requirements (traceability, specificity, readability)

## Verification

- Each citation format maps directly to a chunk ID from TASK-2
- Citation examples match the chunk ID formats defined in chunking strategy
- Compound citations support multi-source answers
