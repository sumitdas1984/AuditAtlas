# Plan: FEATURE-004-TASK-4 — Source B (SEC 10-K PDF) Ingestion

## Context

Issue: FEATURE-004-TASK-4 (#20)
Source: Design doc `docs/data_ingestion/09_hybrid_ingestion_and_retrieval_pipeline.md`
Task: Extend ingestion pipeline to handle SEC 10-K filings (Source B)

## Goal

Ingest 5 SEC 10-K PDF documents from `data/raw/sec_10k/` into the hybrid knowledge base.

## Source B Files

```
data/raw/sec_10k/
├── aapl-20250927.pdf     # Apple Inc. 10-K
├── amzn-20251231.pdf     # Amazon.com 10-K
├── jpm-20251231.pdf      # JPMorgan Chase 10-K
├── msft.pdf              # Microsoft 10-K
└── tsla-20251231.pdf    # Tesla 10-K
```

## Implementation Steps

### Step 1 — Extend CLI to support `--source B`

Modify `src/ingestion/run_ingestion.py`:
- Add `--source B` option
- Route to Source B ingestion path
- Use PDFParser + Source B specific chunking

### Step 2 — Create Source B Chunker

Add Source B chunking method to `chunkers/chunker.py`:
- **Chunk unit:** Section + paragraph
- **Chunk ID format:** `{ticker}.{year}.{item}` → `AAPL.2025.Item1A.3`
- Extract ticker from filename (e.g., `aapl-20250927.pdf` → `AAPL`)
- Extract fiscal year from filename or content
- Split by Item sections (Item 1A, Item 7, Item 8, etc.)

### Step 3 — Build Citation

Citation format: `[AAPL 10-K, Item 1A (2025)]`

### Step 4 — Tests

- `tests/test_ingestion/test_source_b_chunker.py` — section-level chunking

## Files to Modify/Create

| File | Action |
|------|--------|
| `src/ingestion/run_ingestion.py` | Modify (add `--source B`) |
| `src/ingestion/chunkers/chunker.py` | Modify (add SourceBChunker) |
| `tests/test_ingestion/test_source_b_chunker.py` | Create |

## Verification

1. Run `python -m src.ingestion run --source B`
2. Check `data/knowledge_base/chunks.jsonl` has Source B chunks
3. Check chunk IDs follow `{ticker}.{year}.{item}` format
4. Run pytest — all tests pass
