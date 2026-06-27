# Hybrid Data Ingestion & Retrieval Pipeline — Design

**Phase**: 4–5
**Status**: Design

---

## Overview

This document defines the architecture for AuditAtlas's hybrid knowledge base — combining structured metadata storage with vector embeddings for accurate, citable, and semantically searchable audit responses.

---

## Architecture

```
                    ┌─────────────────────────────────────────────────────────────┐
                    │                      INGESTION (Phase 4)                     │
                    └─────────────────────────────────────────────────────────────┘

    Source C (Markdown)                          Source A (PDF)                    Source B (PDF)
    ┌─────────────┐                             ┌─────────────┐                    ┌─────────────┐
    │  Documents  │                             │  Documents  │                    │  Documents  │
    └──────┬──────┘                             └──────┬──────┘                    └──────┬──────┘
           │                                           │                                  │
           ▼                                           ▼                                  ▼
    ┌─────────────┐                             ┌─────────────┐                    ┌─────────────┐
    │   Parser    │                             │   Parser    │                    │   Parser    │
    │ (Markdown)  │                             │   (PDF)     │                    │   (PDF)     │
    └──────┬──────┘                             └──────┬──────┘                    └──────┬──────┘
           │                                           │                                  │
           ▼                                           ▼                                  ▼
    ┌─────────────┐                             ┌─────────────┐                    ┌─────────────┐
    │  Extracted  │                             │  Extracted  │                    │  Extracted  │
    │  Document   │                             │  Document   │                    │  Document   │
    └──────┬──────┘                             └──────┬──────┘                    └──────┬──────┘
           │                                           │                                  │
           └───────────────────┬──────────────────────┬┴──────────────────────────────────┘
                               │                      │
                               ▼                      ▼
                        ┌─────────────────────────────┐
                        │          CHUNKER            │
                        │                             │
                        │  Splits docs into chunks    │
                        │  Assigns chunk_id per       │
                        │  Phase 3 chunking strategy  │
                        └─────────────┬───────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
           ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
           │  JSON Store     │ │  ChromaDB       │ │   Metadata      │
           │                 │ │                 │ │   Index         │
           │  Full chunk    │ │  Embeddings     │ │   (SQLite)     │
           │  content +      │ │  + chunk_id     │ │                 │
           │  metadata       │ │  references    │ │  Source +       │
           │                 │ │                 │ │  temporal index │
           └─────────────────┘ └─────────────────┘ └─────────────────┘



                    ┌─────────────────────────────────────────────────────────────┐
                    │                     RETRIEVAL (Phase 5)                    │
                    └─────────────────────────────────────────────────────────────┘

           ┌─────────────────┐
           │    User Query   │
           └────────┬────────┘
                    │
                    ▼
           ┌─────────────────┐
           │     Router      │
           │   (Phase 3)     │
           │                 │
           │ Routes to:      │
           │ A / B / C /    │
           │ All sources     │
           └────────┬────────┘
                    │
                    ▼
           ┌─────────────────────────────────────────────────┐
           │              CHROMADB (Vector Search)            │
           │                                                  │
           │  1. Embed query                                 │
           │  2. Filter by source_type (from router)         │
           │  3. Return top-K chunks with similarity scores   │
           └────────────────────┬─────────────────────────────┘
                                │
                                ▼
           ┌─────────────────────────────────────────────────┐
           │              JSON STORE (Lookup)                │
           │                                                  │
           │  Join on chunk_id to get:                        │
           │  - Full content                                  │
           │  - Citation metadata                            │
           │  - Source-specific fields                       │
           └────────────────────┬─────────────────────────────┘
                                │
                                ▼
           ┌─────────────────────────────────────────────────┐
           │           RESPONSE GENERATOR                     │
           │                                                  │
           │  Builds answer + citations per Phase 3 format:   │
           │  [AS 1105 § .12] [AAPL 10-K, Item 1A (2025)]   │
           └─────────────────────────────────────────────────┘
```

---

## Storage Schema

### JSON Store — `data/knowledge_base/chunks.json`

One JSON object per line (JSONL format). Each chunk is a complete, citable unit.

```json
{
  "chunk_id": "IA-2026-004.3.1",
  "source_type": "C",
  "document_id": "IA-2026-004",
  "document_type": "InternalAuditReport",
  "chunk_index": 1,
  "content": "## Finding 2025-H-001: E-Commerce Payment Reconciliation Gap\n\nSeverity: High\n...",
  "metadata": {
    "section": "3.1",
    "heading": "Finding 2025-H-001: E-Commerce Payment Reconciliation Gap",
    "classification": "InternalConfidential",
    "effective_date": "2026-01-15",
    "owner": "Margaret Thornton",
    "company": "Northwind Retail Solutions Ltd."
  },
  "citation": {
    "format": "[InternalAuditReport:2025-H-001]",
    "type": "synthetic"
  }
}
```

**Source A chunk example:**

```json
{
  "chunk_id": "AS1105.12",
  "source_type": "A",
  "document_id": "AS1105",
  "document_type": "Standard",
  "chunk_index": 12,
  "content": "The auditor should obtain sufficient appropriate audit evidence...",
  "metadata": {
    "paragraph": ".12",
    "standard_title": "Audit Evidence",
    "effective_date": "2024-12-15",
    "status": "Effective"
  },
  "citation": {
    "format": "[AS 1105 § .12]",
    "type": "pcaob"
  }
}
```

**Source B chunk example:**

```json
{
  "chunk_id": "AAPL.2025.Item1A.3",
  "source_type": "B",
  "document_id": "AAPL",
  "document_type": "10-K",
  "chunk_index": 3,
  "content": "Our business is subject to a variety of risks, including...",
  "metadata": {
    "ticker": "AAPL",
    "company_name": "Apple Inc.",
    "fiscal_year": 2025,
    "item": "Item 1A",
    "risk_factor_index": 3
  },
  "citation": {
    "format": "[AAPL 10-K, Item 1A (2025)]",
    "type": "sec"
  }
}
```

### ChromaDB Collection — `audit_chunks`

| Field | Type | Description |
|-------|------|-------------|
| `id` | `chunk_id` | Primary key (references JSON) |
| `embedding` | `float[384]` | Sentence-transformer embedding |
| `document` | `chunk_id` | Reference only (no duplicate content) |
| `metadata.source_type` | `str` | "A", "B", or "C" |
| `metadata.document_type` | `str` | Standard, 10-K, InternalAuditReport, etc. |
| `metadata.ticker` | `str` | Optional (Source B only) |
| `metadata.standard_id` | `str` | Optional (Source A only) |

### SQLite Index — `data/knowledge_base/index.db`

Lightweight index for metadata filtering without loading JSON.

```sql
CREATE TABLE chunks (
  chunk_id TEXT PRIMARY KEY,
  source_type TEXT NOT NULL,
  document_type TEXT NOT NULL,
  document_id TEXT NOT NULL,
  effective_date TEXT,
  ticker TEXT,
  standard_id TEXT,
  classification TEXT
);

CREATE INDEX idx_source_type ON chunks(source_type);
CREATE INDEX idx_ticker ON chunks(ticker);
CREATE INDEX idx_standard_id ON chunks(standard_id);
```

---

## Ingestion Pipeline (Phase 4)

### Components

| Component | Responsibility |
|-----------|---------------|
| `parsers/` | Extract text and metadata from source documents |
| `chunkers/` | Split documents into chunks per Phase 3 strategy |
| `embedder/` | Generate vector embeddings for chunks |
| `storage/` | Write to JSON store, ChromaDB, SQLite index |

### Parsers

| Parser | Input | Output |
|--------|-------|--------|
| `MarkdownParser` | Source C `.md` files | Extracted document with frontmatter + content |
| `PDFParser` | Source A/B `.pdf` files | Extracted document with sections + metadata |

### Chunkers

Each source type uses its Phase 3 chunking strategy:

| Source | Chunk Unit | Chunk ID Format |
|--------|-----------|-----------------|
| A (PCAOB) | Paragraph | `{standard_id}.{paragraph}` → `AS1105.12` |
| B (SEC 10-K) | Section + paragraph | `{ticker}.{year}.{item}` → `AAPL.2025.Item1A` |
| C (Synthetic) | Heading section | `{doc_id}.{section}` → `IA-2026-004.3.1` |

### Embedder

```
Chunk Content Text
       │
       ▼
┌──────────────────┐
│ Embedding Model  │
│                  │
│ all-MiniLM-L6-v2 │  (384-dim, local, no API key)
└────────┬─────────┘
         │
         ▼
   [0.1, -0.3, 0.5, ...]
         │
         ▼
   ChromaDB.add(embedding, chunk_id)
```

### Ingestion Order

1. **Source C first** — simplest documents, validate pipeline
2. **Source A second** — complex PDF structure, smaller set
3. **Source B third** — large PDFs, standardized structure

---

## Retrieval Pipeline (Phase 5)

### Components

| Component | Responsibility |
|-----------|---------------|
| `router/` | Classify query, determine source(s) |
| `embedder/` | Embed query text |
| `vector_store/` | ChromaDB lookup with filters |
| `json_store/` | Fetch full chunk by chunk_id |
| `response/` | Format answer + citations |

### Retrieval Flow

```
User Query
    │
    ▼
┌──────────────────┐
│   Router         │─── determines source_type ───┐
│  (Phase 3)       │                             │
└────────┬─────────┘                             │
         │                                       │
         ▼                                       │
┌──────────────────┐                            │
│ Embedder          │                            │
│ (same model)     │                            │
└────────┬─────────┘                            │
         │                                       │
         ▼                                       │
┌──────────────────────────────────────────┐     │
│ ChromaDB.similarity_search                │     │
│   query_vector                            │     │
│   n_results=10                            │     │
│   where={source_type: routed_source}      │     │
└────────┬─────────────────────────────────┘     │
         │                                       │
         ▼                                       │
    Top-K chunk_ids                              │
    with similarity scores                       │
         │                                       │
         ▼                                       │
┌──────────────────────────────────────────┐     │
│ JSON Store lookup                          │     │
│   Get full content + citation for          │     │
│   each chunk_id                            │     │
└────────┬─────────────────────────────────┘     │
         │                                       │
         ▼                                       │
┌──────────────────┐                            │
│ Citation Formatter│                            │
│  [AS 1105 § .12] │                            │
│  [AAPL 10-K, ...]│                            │
└──────────────────┘
```

---

## API Interface

### Ingestion (Phase 4)

```bash
# Ingest all sources
python -m src.ingestion run --all

# Ingest by source
python -m src.ingestion run --source C
python -m src.ingestion run --source A
python -m src.ingestion run --source B

# Ingest single document
python -m src.ingestion run --file data/raw/synthetic_company_docs/01-Internal-Audit-Report.md
```

### Retrieval (Phase 5)

```python
from src.retrieval import Retriever

retriever = Retriever()

result = retriever.search(
    query="What are the risk factors for Apple?",
    top_k=5
)

# result.chunks[0].content
# result.chunks[0].citation  # "[AAPL 10-K, Item 1A (2025)]"
```

---

## Directory Structure

```
src/
├── ingestion/
│   ├── __init__.py
│   ├── run_ingestion.py      # CLI entry point
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── base_parser.py    # Abstract base
│   │   ├── markdown_parser.py
│   │   └── pdf_parser.py
│   ├── chunkers/
│   │   ├── __init__.py
│   │   └── chunker.py         # Phase 3 chunking strategy
│   ├── embedder/
│   │   ├── __init__.py
│   │   └── embedder.py        # Sentence-transformer wrapper
│   └── storage/
│       ├── __init__.py
│       ├── json_store.py
│       ├── chroma_store.py
│       └── sqlite_index.py
│
└── retrieval/
    ├── __init__.py
    ├── retriever.py           # Main search interface
    ├── router.py              # Phase 3 router
    ├── embedder.py            # Query embedding
    └── citation.py            # Phase 3 citation formatter

data/
├── knowledge_base/
│   ├── chunks.jsonl           # JSON store
│   ├── index.db               # SQLite index
│   └── chroma/                # ChromaDB persistence
```

---

## Dependencies

| Package | Purpose | Notes |
|---------|---------|-------|
| `chromadb` | Vector database | Local, no API key |
| `sentence-transformers` | Embedding model | all-MiniLM-L6-v2 |
| `pypdf` | PDF parsing | Source A & B |
| `python-frontmatter` | Markdown frontmatter | Source C |
| `pydantic` | Data validation | Phase 3 schemas reused |

---

## Out of Scope for MVP

- **Incremental ingestion** — full re-ingest only
- **Document updates/deletes** — version management
- **Embedding model selection** — fixed to all-MiniLM-L6-v2
- **Hybrid ranking tuning** — simple weighted fusion post-MVP
- **Caching** — query embedding caching
