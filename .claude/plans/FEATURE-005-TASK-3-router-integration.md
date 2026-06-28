# Plan: FEATURE-005-TASK-3 — Router Integration & Multi-Source Search

## Context

Issue #27: TASK-5-1 (Core Retriever) and TASK-5-2 (Metadata Filtering) are merged. The `Retriever` runs a single ChromaDB search with one `where` clause and returns results. But the existing Phase 3 `Router` (`src/knowledge_engineering/router.py`) classifies queries by topic/intent/scope and produces a `RoutingResult.sources: list[SourceType]` — currently the Retriever doesn't consult it.

This task wires `Router` into `Retriever.search()` so:
- A compliance query (`"What are the compliance requirements?"`) routes to A+B+C and returns mixed-source results sorted by distance.
- A requirement-intent query (`"What must auditors do?"`) routes to A only.
- A ticker-specific query stays scoped to that company.
- `SearchResult.routing` is populated so downstream consumers (Phase 6 agent, CLI) can see the routing decision.

## Approach

### Modify `src/retrieval/retriever.py`

**1. `Retriever.__init__` — accept optional `router`:**

```python
def __init__(
    self,
    chroma_store: Optional[ChromaStore] = None,
    json_store: Optional[JsonStore] = None,
    embedder: Optional[Embedder] = None,
    router: Optional[Router] = None,
):
    self.chroma_store = chroma_store or ChromaStore()
    self.json_store = json_store or JsonStore()
    self.embedder = embedder or Embedder()
    self.router = router  # may be None; search() decides whether to use it
```

Default to `None` (not auto-instantiated) so the dependency is explicit. `search()` will check `self.router is not None` and `use_router=True`.

**2. `Retriever.search()` — accept `use_router: bool = True`:**

```python
def search(
    self,
    query: str,
    top_k: int = 5,
    where: Optional[dict] = None,
    ticker: Optional[str] = None,
    standard_id: Optional[str] = None,
    use_router: bool = True,
) -> SearchResult:
```

**Routing decision logic** (clear precedence):
- If `use_router=True` AND `self.router is not None` AND caller did NOT pass `where`, `ticker`, or `standard_id` → **use router**.
- Otherwise → **single search with merged where clause** (current behavior, fully backwards-compatible).

Rationale for "explicit filters skip router": if the caller says `ticker="AAPL"`, they've already made a routing decision (Source B). Re-routing would be confusing and could narrow results the caller explicitly wanted.

**3. Multi-source search helper:**

When routing, run one ChromaDB call per source with `where={"source_type": source.value}`, over-fetch slightly per source (`n_results=top_k`) so the merged result has enough material:

```python
all_raw = []
for source in routing.sources:
    raw = self.chroma_store.search(
        query_text=query,
        embedder=self.embedder,
        n_results=top_k,  # per source — gives cross-source diversity
        where={"source_type": source.value},
    )
    all_raw.append((source, raw))

# Merge + sort by distance, dedupe by chunk_id (shouldn't collide but defensive)
chunks = self._merge_multi_source_results(all_raw)
```

This gives the user up to `top_k * len(sources)` candidates, sorted by ChromaDB distance, then truncated to `top_k` overall. Distance-based sorting naturally balances across sources — a very relevant Source B chunk can outrank a mediocre Source A chunk.

**4. Refactor: extract `_hydrate_chunks()` helper:**

The "ChromaDB result → list[RetrievedChunk]" logic (JSON hydration + citation formatting) is repeated in single-search and multi-search paths. Extract:

```python
def _hydrate_chunks(
    self,
    ids: list[str],
    distances: list[float],
    metadatas: list[dict],
) -> list[RetrievedChunk]:
    """Turn raw ChromaDB result tuples into hydrated RetrievedChunks."""
```

Used by both single-search and multi-search paths.

### `SearchResult.routing` field

Already exists in `src/retrieval/models.py` as `routing: Optional[object] = None` — just populate it with the `RoutingResult` when routing is used. Type stays loose (`Optional[object]`) to avoid an import cycle with `knowledge_engineering`.

### Reuse

| Component | Path | What we use |
|-----------|------|-------------|
| `Router` | `src/knowledge_engineering/router.py` | `route(query)` returns `RoutingResult` |
| `RoutingResult` | `src/knowledge_engineering/router.py` | `.sources: list[SourceType]`, `.confidence`, `.reasoning` |
| `SourceType` | `src/knowledge_engineering/citation.py` | enum value for ChromaDB where filter |
| `ChromaStore.search` | `src/ingestion/storage/chroma_store.py` | existing `where` push-down |

### Tests — `tests/test_retrieval/test_router_integration.py` (new file)

**Routing tests (using `populated_stores` fixture pattern from TASK-5-1):**
- `test_router_compliance_routes_to_all_sources` — `"compliance requirements"` → chunks from A, B, C
- `test_router_requirement_intent_routes_to_source_a` — `"What must auditors do?"` → only Source A chunks
- `test_router_finding_intent_routes_to_source_c` — `"Show me audit findings"` → only Source C chunks
- `test_router_audit_standards_routes_to_source_a` — `"What does PCAOB say..."` → only Source A
- `test_router_risk_factors_routes_to_source_b` — `"What are Apple's risk factors?"` → only Source B
- `test_router_unclassified_routes_to_all_sources` — gibberish query → all 3 sources

**Multi-source aggregation tests:**
- `test_multi_source_results_sorted_by_distance_global` — mixed-source chunks, distances ascending across sources
- `test_multi_source_respects_top_k_after_merge` — total chunks ≤ top_k even when 3 sources contribute
- `test_multi_source_preserves_source_attribution` — each chunk's `source_type` matches one of the routed sources
- `test_multi_source_populates_routing_field` — `SearchResult.routing` is the `RoutingResult` from Router
- `test_multi_source_populates_sources_searched` — `sources_searched` matches routed sources

**Router bypass tests:**
- `test_explicit_where_bypasses_router` — `where={"source_type": "A"}` → only Source A, `routing=None`
- `test_explicit_ticker_bypasses_router` — `ticker="AAPL"` → only Source B, `routing=None`
- `test_explicit_standard_id_bypasses_router` — `standard_id="AS1105"` → only Source A, `routing=None`
- `test_use_router_false_skips_routing` — `use_router=False` → single search, `routing=None`
- `test_no_router_instance_skips_routing` — `Retriever(router=None).search(...)` → no error, `routing=None`

**Backwards compatibility:**
- All TASK-5-1 tests (single-source search, citations, empty KB) still pass.
- All TASK-5-2 tests (filter kwargs) still pass.

### Critical files to be modified

- `src/retrieval/retriever.py` — add `router=` to `__init__`, add `use_router=` to `search()`, extract `_hydrate_chunks()`, add `_merge_multi_source_results()` (~80 lines added/changed)
- `tests/test_retrieval/test_router_integration.py` — new file, ~15 tests

### Reuse of existing fixtures

The `populated_stores` fixture in `tests/test_retrieval/test_retriever.py` has chunks from all 3 sources. Move it to a `conftest.py` so the new test file can share it. Conftest only if needed — alternatively, duplicate the small fixture (~50 lines) for self-containment.

**Decision**: move to `tests/test_retrieval/conftest.py` for DRY.

## Verification

1. `pytest tests/test_retrieval/ -v` → all TASK-5-1, TASK-5-2, and new TASK-5-3 tests pass (target: 17 existing + 15 new = 32 in retrieval folder)
2. `pytest tests/` → full suite green, ≥155 tests
3. Manual smoke: `r = Retriever(); print(r.search("compliance requirements").sources_searched)` → `["A", "B", "C"]` and `r.routing` populated
4. Manual smoke: `r.search("risk factors", ticker="AAPL")` → only AAPL chunks, `r.routing is None` (explicit filter bypassed router)

## Out of Scope (handled in later tasks or follow-ups)

- CLI entry point — TASK-5-4
- Integration tests against real knowledge base — TASK-5-4
- `classification` filter — deferred per TASK-5-2 TODO comment
- Per-source top-k distribution (e.g., proportional to source size) — naive `top_k * len(sources)` works for MVP
- Cross-source re-ranking beyond ChromaDB distance — distance is sufficient for MVP