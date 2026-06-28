# Plan: FEATURE-004-TASK-3 — Source A (PCAOB PDF) Ingestion

## Context

Issue: FEATURE-004-TASK-3 (#19)
Source: Design doc `docs/data_ingestion/09_hybrid_ingestion_and_retrieval_pipeline.md`
Task: Extend ingestion pipeline to handle PCAOB standards PDFs (Source A)

## Goal

Ingest 6 PCAOB PDF documents from `data/raw/pcaob_standards/` into the hybrid knowledge base.

## Source A Files

```
data/raw/pcaob_standards/
├── 2024-004-as1000.pdf                      # AS 1000 - General Responsibilities
├── 2024-005-qc1000.pdf                      # QC 1000 - Quality Control
├── pcaob-2025-001-qc1000-delay.pdf          # QC 1000 Delay
├── pcaob-release-no-2025-004.pdf            # Rulemaking Release
├── release_2010-004_risk_assessment.pdf      # AS 2110 Risk Assessment
└── staff-guidance-*.pdf                     # Staff Guidance
```

## Implementation Steps

### Step 1 — Extend CLI to support `--source A`

Modify `src/ingestion/run_ingestion.py`:
- Add `--source A` option
- Route to Source A ingestion path
- Use existing parser/chunker/storage structure

### Step 2 — Create PDF Parser (`src/ingestion/parsers/pdf_parser.py`)

- Use `pypdf` to extract text from PDFs
- Parse into sections (paragraph-level)
- Extract metadata: standard_id, title, issue_date, effective_date, status
- Return: `ParsedDocument` dataclass

### Step 3 — Create Source A Chunker (`chunkers/chunker.py`)

Add Source A chunking method:
- **Chunk unit:** Paragraph
- **Chunk ID format:** `{standard_id}.{paragraph}` → `AS1105.12`
- Each paragraph becomes a distinct chunk

### Step 4 — Update Storage Layer

Ensure ChromaDB, SQLite, JSONL handle Source A chunks:
- `source_type = "A"`
- `document_type = "Standard"`
- Include `standard_id`, `paragraph` in metadata

### Step 5 — Tests

- `tests/test_ingestion/test_pdf_parser.py` — parse sample PDF
- `tests/test_ingestion/test_source_a_chunker.py` — paragraph-level chunking

## Files to Modify/Create

| File | Action |
|------|--------|
| `src/ingestion/parsers/pdf_parser.py` | Create |
| `src/ingestion/run_ingestion.py` | Modify |
| `src/ingestion/chunkers/chunker.py` | Modify (add Source A method) |
| `tests/test_ingestion/test_pdf_parser.py` | Create |
| `tests/test_ingestion/test_source_a_chunker.py` | Create |

## Verification

1. Run `python -m src.ingestion run --source A`
2. Check `data/knowledge_base/chunks.jsonl` has Source A chunks
3. Check chunk IDs follow `{standard_id}.{paragraph}` format
4. Run pytest — all tests pass
