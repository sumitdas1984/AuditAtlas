# Plan: FEATURE-004-TASK-2 — Source C (Markdown) Ingestion

## Context

Issue: FEATURE-004-TASK-2 (#18)
Source: Design doc `docs/data_ingestion/09_hybrid_ingestion_and_retrieval_pipeline.md`
Task: Build complete ingestion pipeline for Source C (Markdown synthetic documents)

## Goal

Ingest 5 synthetic company documents from `data/raw/synthetic_company_docs/` into the hybrid knowledge base:
- `data/knowledge_base/chunks.jsonl` (JSONL store)
- `data/knowledge_base/index.db` (SQLite metadata index)
- `data/knowledge_base/chroma/` (ChromaDB vector store)

## Implementation Steps

### Step 1 — Create directory structure

```
src/ingestion/
├── __init__.py
├── run_ingestion.py      # CLI entry point
├── parsers/
│   ├── __init__.py
│   ├── base_parser.py    # Abstract base class
│   └── markdown_parser.py
├── chunkers/
│   ├── __init__.py
│   └── chunker.py        # Source C chunking strategy
├── embedder/
│   ├── __init__.py
│   └── embedder.py       # Sentence-transformer wrapper
└── storage/
    ├── __init__.py
    ├── json_store.py
    ├── chroma_store.py
    └── sqlite_index.py
```

### Step 2 — Markdown Parser (`parsers/markdown_parser.py`)

- Use `python-frontmatter` to extract YAML frontmatter
- Parse document content into heading sections
- Extract metadata: document_id, document_type, version, effective_date, review_date, classification, owner, company, file_path
- Return: `ParsedDocument` dataclass with frontmatter dict + content blocks

### Step 3 — Source C Chunker (`chunkers/chunker.py`)

- Split document by heading sections (H1, H2, H3)
- Chunk ID format: `{doc_id}.{section}` → e.g., `IA-2026-004.3.1`
- Each chunk is a complete, citable unit with heading + content
- Return: list of `Chunk` dataclasses

### Step 4 — Embedder (`embedder/embedder.py`)

- Use `sentence-transformers.AllMiniLM-L6-v2`
- Generate 384-dim embeddings for chunk content text
- Cache model in memory after first load
- Method: `embed(text: str) -> list[float]`

### Step 5 — Storage Layer

**json_store.py:**
- Append chunks to `data/knowledge_base/chunks.jsonl` (JSONL format)
- One JSON object per line per design schema

**sqlite_index.py:**
- Create `data/knowledge_base/index.db`
- `CREATE TABLE chunks` with: chunk_id, source_type, document_type, document_id, effective_date, classification
- Create indexes on source_type, document_id

**chroma_store.py:**
- Initialize ChromaDB client with persistence at `data/knowledge_base/chroma/`
- Collection: `audit_chunks`
- Fields: id (chunk_id), embedding (384-dim), metadata (source_type, document_type, chunk_id)

### Step 6 — CLI Entry Point (`run_ingestion.py`)

```bash
# Ingest Source C (all markdown files)
python -m src.ingestion run --source C

# Ingest single file
python -m src.ingestion run --file data/raw/synthetic_company_docs/01-Risk-Register.md
```

Commands:
- `--source C` — ingest all Source C files
- `--file <path>` — ingest single file
- `--all` — ingest all sources (A, B, C) — deferred to TASK-3/TASK-4

### Step 7 — Tests

- `tests/test_ingestion/` directory
- Test markdown parser with sample document
- Test chunker splits correctly
- Test embedder generates valid embedding
- Test storage round-trip (write + read chunk by ID)

## Files to Create/Modify

| File | Action |
|------|--------|
| `src/ingestion/__init__.py` | Create |
| `src/ingestion/run_ingestion.py` | Create |
| `src/ingestion/parsers/__init__.py` | Create |
| `src/ingestion/parsers/base_parser.py` | Create |
| `src/ingestion/parsers/markdown_parser.py` | Create |
| `src/ingestion/chunkers/__init__.py` | Create |
| `src/ingestion/chunkers/chunker.py` | Create |
| `src/ingestion/embedder/__init__.py` | Create |
| `src/ingestion/embedder/embedder.py` | Create |
| `src/ingestion/storage/__init__.py` | Create |
| `src/ingestion/storage/json_store.py` | Create |
| `src/ingestion/storage/chroma_store.py` | Create |
| `src/ingestion/storage/sqlite_index.py` | Create |
| `data/knowledge_base/` | Create directory |
| `tests/test_ingestion/` | Create |
| `pyproject.toml` | Add dependencies |

## Dependencies to Add

```toml
[project.dependencies]
chromadb = ">=0.4.0"
sentence-transformers = ">=2.0.0"
python-frontmatter = ">=1.0.0"
pypdf = ">=3.0.0"
pydantic = ">=2.0"
```

## Verification

1. Run `python -m src.ingestion run --source C`
2. Check `data/knowledge_base/chunks.jsonl` has 5+ chunks
3. Check `data/knowledge_base/index.db` has records
4. Check ChromaDB collection has embeddings
5. Run pytest — all tests pass
