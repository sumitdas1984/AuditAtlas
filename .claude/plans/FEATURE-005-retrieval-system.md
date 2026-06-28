# Plan: FEATURE-005 — Retrieval System (Phase 5)

## Context

Phase 4 (Data Ingestion) is complete — all three sources (A: PCAOB PDFs, B: SEC 10-K PDFs, C: Synthetic Markdown) are parsed, chunked, embedded, and stored in JSONL + ChromaDB + SQLite. Phase 3 also produced a Router (`src/knowledge_engineering/router.py`) and a Citation formatter (`src/knowledge_engineering/citation.py`).

**What's missing**: there is no `src/retrieval/` directory. The retrieval flow (Router → Embedder → ChromaDB → JSON Store → Citation Formatter) is documented in `docs/data_ingestion/09_hybrid_ingestion_and_retrieval_pipeline.md` but no code wires these pieces together. Users have no way to query the knowledge base.

**Goal**: Build the retrieval layer so that a query returns relevant, ranked chunks with full content and citations, filtered by metadata, and routed to the right source(s) via the existing Phase 3 router.

## Approach

Four sub-tasks, matching Phase 4's decomposition pattern.

| # | Title | Builds | Depends on |
|---|-------|--------|------------|
| 5-1 | Core Retriever & SearchResult schema | `src/retrieval/` skeleton, `Retriever.search()`, result models, single-source search | — |
| 5-2 | Metadata filtering | Add `query_by_ticker` / `query_by_standard_id` to `SqliteIndex`; expose filters on `Retriever` | 5-1 |
| 5-3 | Router integration & multi-source search | Wire `Router` into `Retriever`; aggregate across sources | 5-1, 5-2 |
| 5-4 | CLI, integration tests, docs | `python -m src.retrieval search "..."`; end-to-end tests; doc-sync | 5-3 |

### TASK-5-1: Core Retriever & SearchResult schema

**New files:**
- `src/retrieval/__init__.py`
- `src/retrieval/retriever.py` — `Retriever` class with `search(query, top_k, where)` method
- `src/retrieval/models.py` — `SearchResult`, `RetrievedChunk` dataclasses

**Reuse:**
- `Embedder.embed(text)` from `src/ingestion/embedder/embedder.py`
- `ChromaStore.search(query_text, embedder, n_results, where)` from `src/ingestion/storage/chroma_store.py`
- `JsonStore.read(chunk_id)` from `src/ingestion/storage/json_store.py`
- `format_citation(chunk_id, source_type)` from `src/knowledge_engineering/citation.py`

**`Retriever.search()` flow:**
1. Embed query (delegated to Embedder)
2. Call `ChromaStore.search(...)` with `where` filter (single source for now)
3. For each returned `chunk_id`, lookup full content via `JsonStore.read()`
4. Format citation via `format_citation()`
5. Return `SearchResult(query=..., chunks=[RetrievedChunk(...)])`

**Tests:** `tests/test_retrieval/test_retriever.py` — basic single-source search, empty results, citation formatting.

### TASK-5-2: Metadata filtering

**Modify:**
- `src/ingestion/storage/sqlite_index.py` — add `query_by_ticker(ticker)`, `query_by_standard_id(standard_id)` methods
- `src/retrieval/retriever.py` — extend `search()` to accept `ticker=`, `standard_id=`, `classification=` keyword args; translate to `where` clauses

**Tests:** filter combinations, edge cases (no matches), and verify filter results joined with ChromaDB results.

### TASK-5-3: Router integration & multi-source search

**Modify:**
- `src/retrieval/retriever.py` — accept optional `router=` arg; when provided, route query to sources, run separate `ChromaStore.search()` per source, merge results
- Sort merged results by ChromaDB distance (lower = better)

**Reuse:**
- `Router.route(query)` from `src/knowledge_engineering/router.py` — already returns `RoutingResult.sources: list[SourceType]`

**Tests:** `tests/test_retrieval/test_router_integration.py` — compliance query routes to A+B+C, requirement intent routes to A only, ticker-specific query stays scoped.

### TASK-5-4: CLI, integration tests, docs

**New files:**
- `src/retrieval/__main__.py` — argparse CLI; `python -m src.retrieval search "query" --top-k 5`
- `src/retrieval/cli.py` — CLI helpers
- `tests/test_retrieval/test_integration.py` — end-to-end test: ingest sample → search → assert retrieved chunks

**Modify docs:**
- `docs/data_ingestion/09_hybrid_ingestion_and_retrieval_pipeline.md` — fix path mismatch (`chunks.json` → `chunks.jsonl`); add retrieval usage examples
- `CLAUDE.md` — add `src/retrieval/` to key files table

**Tests:** CLI smoke test, integration test against a populated knowledge base.

## Critical files to be modified

- `src/retrieval/retriever.py` (new)
- `src/retrieval/models.py` (new)
- `src/retrieval/__main__.py` (new)
- `src/retrieval/cli.py` (new)
- `src/ingestion/storage/sqlite_index.py` (extend)
- `docs/data_ingestion/09_hybrid_ingestion_and_retrieval_pipeline.md` (update)
- `CLAUDE.md` (update)

## Verification

End-to-end test for each sub-task:
1. **5-1**: Run a single-source search, assert `SearchResult.chunks` contains expected chunk_ids with non-empty content and citations
2. **5-2**: Run filtered search (e.g., `ticker="AAPL"`), assert only AAPL chunks returned; combined filter (`source_type="A", standard_id="AS1105"`) returns only AS1105 chunks
3. **5-3**: Run `"What does PCAOB say about audit evidence?"` (routes to A); assert only Source A chunks in result. Run `"compliance"` (routes to A+B+C); assert mixed sources, sorted by distance
4. **5-4**: `python -m src.retrieval search "risk factors" --top-k 3` prints results; full pytest suite passes (target: ≥110 tests)

Full test suite must remain green at every step (`pytest tests/`).

## Out of Scope for Phase 5

- Hybrid ranking (vector + BM25) — deferred post-MVP per design doc
- Query embedding caching — defer
- Learning-based routing / re-ranking — defer
- Document updates / version management — defer
- API server (HTTP endpoint) — Phase 6 (Agentic Workflow) may add this

## Sub-tasks to file on GitHub

Create 4 child issues on `#6` using `sub_issue_write`:
- FEATURE-005-TASK-1: Core Retriever & SearchResult Schema
- FEATURE-005-TASK-2: Metadata Filtering
- FEATURE-005-TASK-3: Router Integration & Multi-Source Search
- FEATURE-005-TASK-4: CLI, Integration Tests, Docs