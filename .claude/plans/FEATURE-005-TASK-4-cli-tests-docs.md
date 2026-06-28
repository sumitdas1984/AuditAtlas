# Plan: FEATURE-005-TASK-4 — CLI, Integration Tests, Docs

## Context

Issue #28: TASK-5-1 through TASK-5-3 are merged. The `Retriever` API is complete (single-source + multi-source + metadata filtering) but only callable from Python. There's no command-line interface, no end-to-end integration test, and the retrieval pipeline doc has inaccuracies (e.g., `chunks.json` should be `chunks.jsonl`) and missing usage examples.

This is the final Phase 5 sub-task. It wraps the retrieval layer so it's usable by humans (CLI) and by CI (integration tests), and the docs reflect the actual implementation.

## Approach

### 1. CLI — `src/retrieval/cli.py` + `src/retrieval/__main__.py`

Match the Phase 4 ingestion CLI pattern (`src/ingestion/run_ingestion.py`):
- `__main__.py`: argparse entry point with `search` subcommand
- `cli.py`: command handler functions (testable in isolation)

**Invocation:**
```bash
python -m src.retrieval search "risk factors" --top-k 3
python -m src.retrieval search "audit evidence" --ticker AAPL --format json
python -m src.retrieval search "AS 1105" --standard-id AS1105 --use-router false
```

**Arguments (under `search` subcommand):**
| Flag | Type | Default | Purpose |
|------|------|---------|---------|
| `query` (positional) | str | required | The search query |
| `--top-k` | int | 5 | Number of chunks to return |
| `--ticker` | str | None | Source B ticker filter |
| `--standard-id` | str | None | Source A standard ID filter |
| `--where` | str | None | Raw ChromaDB where clause as JSON (e.g., `'{"source_type":"A"}'`) |
| `--use-router` | bool | True | Enable router-based multi-source search |
| `--format` | choice | "table" | "table" (human) or "json" (machine) |
| `--show-content` | bool | True | Include content snippet in output |

**Output formats:**
- **Table** (default, human-readable): rows of `chunk_id | source_type | distance | citation | content_preview` (first 200 chars)
- **JSON**: full `SearchResult` serialized (chunks + routing + sources_searched)

**Error handling — graceful with exit codes:**
| Error | Exit code | Message |
|-------|-----------|---------|
| Empty query | 2 | `Error: query cannot be empty` |
| Knowledge base not initialized | 3 | `Error: no knowledge base found. Run 'python -m src.ingestion run --all' first.` |
| Empty KB (no chunks match) | 0 (success, no results) | "No results found." (table) / `"chunks": []` (json) |
| Invalid `--where` JSON | 4 | `Error: --where must be valid JSON` |
| ChromaDB / embedding model failure | 5 | `Error: <exception message>` |

Exit code 0 = success even when no results (CLI success = command completed, not "found something").

### 2. Integration test — `tests/test_retrieval/test_integration.py`

End-to-end test that:
1. Builds a populated knowledge base in a temp directory (uses sample documents from all 3 sources)
2. Runs `Retriever(router=Router()).search(query)` against it
3. Asserts retrieved chunks have content, citation, and correct source_type per routing

Also add a CLI smoke test that:
- Invokes `python -m src.retrieval search "..."` via `subprocess.run`
- Asserts exit code 0 and expected output structure

**Tests:**
- `test_integration_search_returns_hydrated_chunks` — full pipeline: chunk → embed → store → search → assert
- `test_integration_routing_to_all_sources` — compliance query → mixed sources
- `test_integration_ticker_filter_narrows_to_source_b`
- `test_integration_standard_id_filter_narrows_to_source_a`
- `test_integration_empty_kb_returns_empty_search_result` — graceful
- `test_integration_multi_source_aggregates_by_distance`
- `test_cli_search_basic_invocation` — subprocess runs successfully
- `test_cli_search_json_output_is_valid` — parses as JSON
- `test_cli_search_with_ticker_filter` — `--ticker` flag works
- `test_cli_search_empty_query_exits_with_error` — exit code 2
- `test_cli_search_invalid_where_exits_with_error` — exit code 4
- `test_cli_search_uninitialized_kb_exits_with_error` — exit code 3

### 3. Docs

**`docs/data_ingestion/09_hybrid_ingestion_and_retrieval_pipeline.md`:**
- Fix `chunks.json` → `chunks.jsonl` (line 113)
- Add new section: "Retrieval Usage — Programmatic API" with code examples:
  - Basic search
  - Search with metadata filter
  - Search with router (default) vs without
  - Accessing `SearchResult.routing` for routing visibility
- Add new section: "Retrieval Usage — CLI" with command examples
- Update the retrieval flow ASCII diagram to show router branch (if it currently doesn't)

**`CLAUDE.md`:** Already has `src/retrieval/` row. Verify it's still accurate. May add Slash Command row for `/search` if we want a wrapper later (out of scope for this task).

### Critical files to be modified

- `src/retrieval/cli.py` (new) — command handlers
- `src/retrieval/__main__.py` (new) — argparse entry point
- `tests/test_retrieval/test_integration.py` (new) — ~12 integration + CLI tests
- `docs/data_ingestion/09_hybrid_ingestion_and_retrieval_pipeline.md` — fix path + add usage sections
- `CLAUDE.md` — verify `src/retrieval/` row; add note about CLI

### Reuse

- `Retriever`, `SearchResult`, `RetrievedChunk` from `src/retrieval/`
- `Router` from `src/knowledge_engineering/router.py`
- `format_citation` from `src/knowledge_engineering/citation.py`
- Argparse pattern from `src/ingestion/run_ingestion.py:185-222`

## Verification

1. `pytest tests/test_retrieval/ -v` → all TASK-5-1 through TASK-5-3 tests still pass, new integration tests pass
2. `pytest tests/` → full suite green, ≥186 tests (174 + 12 new)
3. Manual smoke: `python -m src.retrieval search "compliance requirements" --top-k 3` → 3 chunks from A+B+C with table output
4. Manual smoke: `python -m src.retrieval search "audit evidence" --ticker AAPL --format json` → valid JSON with AAPL chunks
5. Manual smoke: `python -m src.retrieval search ""` → exit code 2 + error message
6. Manual smoke: `python -m src.retrieval search "x" --where 'not json'` → exit code 4 + error message

## Out of Scope

- Slash command wrapper (`/search`) — separate task if desired
- Interactive REPL mode — out of scope for MVP
- Query result caching — deferred per design doc
- Async / parallel ChromaDB queries — out of scope for MVP (would speed up multi-source)
- Color output / TTY detection — keep it plain text, can add later