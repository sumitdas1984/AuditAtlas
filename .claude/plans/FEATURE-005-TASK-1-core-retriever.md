# Plan: FEATURE-005-TASK-1 — Core Retriever & SearchResult Schema

## Context

Issue #25: Build the foundation of the retrieval layer. Phase 4 ingestion is complete (parsers, chunkers, embedder, storage all working). Phase 3 produced a `Router` and `citation.py`. There is no `src/retrieval/` directory yet.

The design doc `docs/data_ingestion/09_hybrid_ingestion_and_retrieval_pipeline.md` specifies the retrieval flow (Router → Embedder → ChromaDB → JSON Store → Citation Formatter), but no code wires these together.

This task creates the `Retriever` class with `SearchResult`/`RetrievedChunk` schemas and a single-source `search()` API. Multi-source aggregation, metadata filtering, and the CLI come in later tasks.

## Approach

### New files

- `src/retrieval/__init__.py` — exports `Retriever`, `SearchResult`, `RetrievedChunk`
- `src/retrieval/models.py` — `SearchResult`, `RetrievedChunk` dataclasses
- `src/retrieval/retriever.py` — `Retriever` class with `search(query, top_k, where)` method

### `Retriever.__init__`

```python
def __init__(
    self,
    chroma_store: ChromaStore | None = None,
    json_store: JsonStore | None = None,
    embedder: Embedder | None = None,
):
    self.chroma_store = chroma_store or ChromaStore()
    self.json_store = json_store or JsonStore()
    self.embedder = embedder or Embedder()
```

Defaults wire to the existing `data/knowledge_base/` paths so `Retriever()` works out-of-the-box after `python -m src.ingestion run --all`.

### `Retriever.search(query, top_k=5, where=None) -> SearchResult`

1. Call `chroma_store.search(query, embedder, n_results=top_k, where=where)` → raw ChromaDB result
2. Extract `ids`, `distances`, `metadatas` from the result (ChromaDB returns lists-of-lists for query API; take `[0]`)
3. For each `chunk_id` returned, lookup full content via `json_store.read(chunk_id)`
4. Format citation via `format_citation(chunk_id, source_type)`
5. Build `RetrievedChunk` for each result
6. Return `SearchResult(query=..., chunks=[...])`

### Models

```python
@dataclass
class RetrievedChunk:
    chunk_id: str
    source_type: str         # "A", "B", "C"
    document_id: str
    document_type: str
    content: str
    metadata: dict
    citation: str            # formatted via format_citation()
    distance: float          # ChromaDB similarity distance (lower = better)

@dataclass
class SearchResult:
    query: str
    chunks: list[RetrievedChunk]
    routing: RoutingResult | None = None  # set by TASK-5-3
```

### Reuse

| Component | Path | What we use |
|-----------|------|-------------|
| `Embedder` | `src/ingestion/embedder/embedder.py` | `embed(query)`, `embed_batch(texts)` |
| `ChromaStore` | `src/ingestion/storage/chroma_store.py` | `search(query_text, embedder, n_results, where)` |
| `JsonStore` | `src/ingestion/storage/json_store.py` | `read(chunk_id)` |
| `format_citation` | `src/knowledge_engineering/citation.py` | citation formatter |
| `SourceType` | `src/knowledge_engineering/citation.py` | source type enum |

### Tests (`tests/test_retrieval/test_retriever.py`)

- `test_search_returns_search_result` — single-source search returns structured `SearchResult`
- `test_search_includes_content_and_citation` — each `RetrievedChunk` has non-empty content and a formatted citation
- `test_search_respects_top_k` — `top_k=3` returns at most 3 chunks
- `test_search_with_where_filter` — `where={"source_type": "A"}` only returns Source A chunks
- `test_search_empty_kb_returns_empty_chunks` — empty ChromaDB returns empty `chunks` list (no error)
- `test_search_handles_missing_json_entry` — if ChromaDB returns a chunk_id not in JSON store, skip gracefully
- `test_citation_format_for_each_source` — citations are formatted per source type

Tests use a temp directory for storage to avoid polluting `data/knowledge_base/`.

## Verification

1. All 7 new tests pass
2. Full suite passes: `pytest tests/` ≥100 tests
3. Manual smoke test: ingest a sample, then `Retriever().search("risk factors")` returns chunks with content + citations

## Out of Scope (handled in later tasks)

- Metadata filter helpers on `SqliteIndex` — TASK-5-2
- Router integration / multi-source aggregation — TASK-5-3
- CLI entry point — TASK-5-4
- Hybrid ranking / BM25 — post-MVP