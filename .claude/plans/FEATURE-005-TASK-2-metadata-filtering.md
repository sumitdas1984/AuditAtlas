# Plan: FEATURE-005-TASK-2 — Metadata Filtering

## Context

Issue #26: TASK-5-1 (Core Retriever, PR #27) is merged on `main`. The `Retriever.search()` method accepts a raw `where: dict` for ChromaDB filtering, but consumers have to know ChromaDB's metadata field names and dict shape.

This task adds source-specific filter kwargs (`ticker=`, `standard_id=`) on `Retriever.search()` and the matching lookup methods on `SqliteIndex`, so callers can filter intuitively without coupling to ChromaDB internals.

Out of scope for this task: `classification` filtering (Source C field is not in ChromaDB metadata — only in JSON store; would need post-search filtering or re-ingestion to wire into ChromaDB where clauses. Deferred until a use case demands it).

## Approach

### Modify `src/ingestion/storage/sqlite_index.py`

Add two query methods alongside the existing `query_by_source` / `query_by_document`:

```python
def query_by_ticker(self, ticker: str) -> list[str]:
    """Get all chunk_ids for a given ticker (Source B)."""
    with sqlite3.connect(self.db_path) as conn:
        cursor = conn.execute(
            "SELECT chunk_id FROM chunks WHERE ticker = ?", (ticker,)
        )
        return [row[0] for row in cursor.fetchall()]

def query_by_standard_id(self, standard_id: str) -> list[str]:
    """Get all chunk_ids for a given PCAOB standard ID (Source A)."""
    with sqlite3.connect(self.db_path) as conn:
        cursor = conn.execute(
            "SELECT chunk_id FROM chunks WHERE standard_id = ?", (standard_id,)
        )
        return [row[0] for row in cursor.fetchall()]
```

These reuse the existing `idx_ticker` and `idx_standard_id` indexes created in `_init_db` — no schema change needed.

### Modify `src/retrieval/retriever.py`

Extend `Retriever.search()` with two new kwargs that build up the ChromaDB `where` clause. Keep the raw `where=` kwarg for callers that need full control.

```python
def search(
    self,
    query: str,
    top_k: int = 5,
    where: Optional[dict] = None,
    ticker: Optional[str] = None,
    standard_id: Optional[str] = None,
) -> SearchResult:
```

**Filter logic:**
- Build a `where` dict starting from the caller's `where` (or `{}`).
- If `ticker` is set, `where["ticker"] = ticker`.
- If `standard_id` is set, `where["standard_id"] = standard_id`.
- Pass the merged dict to `chroma_store.search(...)`.

Both fields are already in ChromaDB metadata (see `ChromaStore.add()` at `chroma_store.py:66-80`), so this is a pure metadata push-down — no post-search filtering needed.

The existing `where` kwarg stays so callers can still filter on `source_type`, `document_type`, or combine filters explicitly.

### Reuse

| Component | Path | What we use |
|-----------|------|-------------|
| `SqliteIndex` | `src/ingestion/storage/sqlite_index.py` | `query_by_ticker`, `query_by_standard_id` (added) |
| `ChromaStore.search` | `src/ingestion/storage/chroma_store.py` | `where` clause push-down (existing) |
| `Retriever.search` | `src/retrieval/retriever.py` | extended signature (modified) |

### Tests

**`tests/test_ingestion/test_storage.py` — extend `TestSqliteIndex`:**
- `test_insert_and_query_by_ticker` — insert chunks with different tickers; verify `query_by_ticker("AAPL")` returns only AAPL chunk_ids
- `test_insert_and_query_by_standard_id` — insert chunks with different standard_ids; verify `query_by_standard_id("AS1105")` returns only AS1105 chunk_ids
- `test_query_by_ticker_no_match` — query for non-existent ticker → empty list
- `test_query_by_standard_id_no_match` — query for non-existent standard_id → empty list

**`tests/test_retrieval/test_retriever.py` — extend `TestRetriever`:**
- `test_search_filter_by_ticker` — `search(..., ticker="AAPL")` returns only Source B chunks with `ticker == "AAPL"`; `sources_searched` reflects Source B
- `test_search_filter_by_standard_id` — `search(..., standard_id="AS1105")` returns only the AS1105 chunk
- `test_search_filter_combined_with_where` — `search(..., where={"source_type": "A"}, standard_id="AS1105")` narrows to AS1105 only (not AS2110)
- `test_search_filter_no_match` — `search(..., ticker="XYZ")` returns empty `SearchResult` without raising
- `test_search_filter_kwarg_only` — `search(..., standard_id="AS2110")` (no explicit `where`) translates to where-clause and works

Use the existing `populated_stores` fixture from TASK-5-1 (covers Source A, B, C with known chunk_ids) — no new fixture needed.

## Critical files to be modified

- `src/ingestion/storage/sqlite_index.py` — add 2 query methods (~12 lines)
- `src/retrieval/retriever.py` — extend `search()` signature and merge kwargs into `where` (~6 lines added, 3 lines modified)
- `tests/test_ingestion/test_storage.py` — add 4 tests for new `SqliteIndex` methods
- `tests/test_retrieval/test_retriever.py` — add 5 tests for new filter kwargs

## Verification

1. `pytest tests/test_ingestion/test_storage.py -v` — all SqliteIndex tests pass (existing 4 + new 4)
2. `pytest tests/test_retrieval/test_retriever.py -v` — all Retriever tests pass (existing 12 + new 5)
3. `pytest tests/` — full suite green, ≥120 tests
4. Manual smoke (after re-ingestion): `python -c "from src.retrieval import Retriever; r = Retriever(); print(r.search('risk factors', ticker='AAPL').chunks[:3])"` returns AAPL 10-K chunks only

## Out of Scope (handled in later tasks or follow-ups)

- `classification` filter (Source C) — field not in ChromaDB metadata; would require either re-ingestion or a SQLite pre-filter + `chunk_id $in [...]` pattern. Not in the parent plan for TASK-5-2. Revisit if a use case emerges.
- Combined BM25 + vector hybrid ranking — post-MVP per parent plan
- Router-driven multi-source aggregation — TASK-5-3