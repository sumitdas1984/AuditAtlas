# Plan: FEATURE-004 — Data Ingestion

**Issue**: https://github.com/sumitdas1984/AuditAtlas/issues/5
**Phase**: 4
**Status**: In Progress — TASK-1 ⏳ TASK-2 ⏳ TASK-3 ⏳ TASK-4 ⏳

## Objective

Build the ingestion pipeline to parse, chunk, embed, and store documents from all three source types into a hybrid knowledge base (JSONL + ChromaDB + SQLite).

---

## Background

Phase 4 transforms source documents into a structured, queryable knowledge base using the schemas and chunking strategies from Phase 3.

| Source | Format | Chunk Strategy | Example Chunk ID |
|--------|--------|----------------|------------------|
| A — PCAOB Standards | PDF | Paragraph | `AS1105.12` |
| B — SEC 10-K | PDF | Item section | `AAPL.2025.Item1A` |
| C — Synthetic Docs | Markdown | Heading section | `IA-2026-004.3.1` |

**Hybrid Storage**:
- JSONL (`chunks.jsonl`) — Full chunk content + metadata, source of truth
- ChromaDB — Vector embeddings for semantic search
- SQLite (`index.db`) — Metadata index for filtering

---

## Tasks

### Task 1: Hybrid Pipeline Design

Document the architecture for the hybrid knowledge base combining structured storage with vector embeddings.

**Scope**:
- Architecture diagram (ingestion + retrieval pipelines)
- Storage schema (JSONL, ChromaDB, SQLite)
- API interface (CLI for ingestion, Python for retrieval)
- Directory structure
- Dependencies

**Deliverable**: `docs/data_ingestion/09_hybrid_ingestion_and_retrieval_pipeline.md`

---

### Task 2: Source C (Markdown) Ingestion

Build the complete ingestion pipeline using Source C (Markdown) documents as the first source.

**Scope**:
- Markdown parser for Source C documents
- Chunker using Phase 3 strategy (H1/H2 sections)
- Embedder using sentence-transformers (all-MiniLM-L6-v2)
- Storage to JSONL + ChromaDB + SQLite
- CLI entry point

**Implementation Order**:
1. Create `src/ingestion/` directory structure
2. Base parser abstract class
3. Markdown parser — extract frontmatter + H1/H2 sections
4. Source C chunker — `{doc_id}.{section}`
5. Embedder — sentence-transformer wrapper
6. Storage layer — JSONL writer, ChromaDB client, SQLite indexer
7. CLI entry point — `python -m src.ingestion run --source C`
8. Test with all 5 Source C documents

**Deliverable**: `src/ingestion/` with parsers, chunkers, embedder, storage + `data/knowledge_base/` with Source C chunks

---

### Task 3: Source A (PCAOB PDF) Ingestion

Extend the pipeline to handle PCAOB standards PDFs.

**Scope**:
- PDF parser for Source A documents
- Chunker using Phase 3 strategy (paragraph-level)
- Ingest into existing knowledge base

**Implementation Order**:
1. PDF parser — extract paragraphs + metadata (standard_id, title, effective_date)
2. Source A chunker — paragraph-level chunks (`{standard_id}.{paragraph}`)
3. Reuse embedder and storage from TASK-2
4. CLI extension — `python -m src.ingestion run --source A`
5. Test with Source A PDFs

**Deliverable**: Source A parser + Source A chunks in `data/knowledge_base/`

---

### Task 4: Source B (SEC 10-K PDF) Ingestion

Extend the pipeline to handle SEC 10-K filings.

**Scope**:
- PDF parser for Source B documents
- Chunker using Phase 3 strategy (Item sections)
- Ingest into existing knowledge base

**Implementation Order**:
1. PDF parser — extract Item sections (1A, 7, 8, 9A) + metadata
2. Source B chunker — Item-section chunks (`{ticker}.{year}.{item}`)
3. Reuse embedder and storage from TASK-2
4. CLI extension — `python -m src.ingestion run --source B`
5. Test with Source B PDFs

**Deliverable**: Source B parser extensions + Source B chunks in `data/knowledge_base/`

---

## Output Summary

| Task | Output | Status |
|------|--------|--------|
| 1. Hybrid Pipeline Design | `docs/data_ingestion/09_hybrid_ingestion_and_retrieval_pipeline.md` | ⏳ |
| 2. Source C Ingestion | `src/ingestion/` + Source C chunks | ⏳ |
| 3. Source A Ingestion | Source A chunks | ⏳ |
| 4. Source B Ingestion | Source B chunks | ⏳ |

---

## Dependencies

- Phase 3 schemas and chunking strategy — ✅ Complete
- Phase 3 citation and routing — ✅ Complete
- Source data files in `data/` directories

---

## Next Steps After Phase 4

Phase 5 (Retrieval System) will consume the knowledge base built here:
- Query embedding
- ChromaDB similarity search with metadata filtering
- JSON store lookup for full chunk content
- Citation formatting per Phase 3