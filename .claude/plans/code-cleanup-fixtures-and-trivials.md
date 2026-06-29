# Plan: Test Suite Cleanup — Fixtures & Trivial Tests

## Context

Redundancy analysis (3 parallel agents) found ~25 candidates across 19 test files. This plan covers **Items 1+2** from the prioritized list:

- **Item 1**: Lift duplicated fixtures into shared `conftest.py` files
- **Item 2**: Delete trivial test classes that test stdlib / dataclass behavior

Items 3-5 (parametrize opportunities, overlapping tests, `test_integration.py` trim) are deferred to a follow-up — they have higher refactor risk and we want a clean baseline first.

## Approach

### Item 1 — Fixtures

#### A) `tests/test_ingestion/conftest.py` (new file)

Currently 4 files each redefine `embedder` and 2 files redefine `sample_chunk`. Move to a shared conftest.

**Note on `sample_chunk` divergence**: the existing fixtures differ (one is `RiskRegister/TEST-001`, the other is `InternalAuditReport/IA-2026-004`). Two options:
- (a) Pick one canonical chunk shape and update tests that reference the other shape
- (b) Provide both as named fixtures (`sample_chunk_a` for RiskRegister, `sample_chunk_b` for InternalAuditReport)

→ **Pick (b) — lower risk.** No test currently asserts on the specific document_id/document_type of these fixtures, so the *shape* is what matters. Tests that need a different shape build inline (as they already do).

Conftest content:
```python
"""Shared fixtures for ingestion tests."""

import pytest
from src.ingestion.chunkers.chunker import Chunk
from src.ingestion.embedder.embedder import Embedder


@pytest.fixture
def embedder():
    return Embedder()


@pytest.fixture
def sample_chunk():
    """Source-C RiskRegister chunk (used by ChromaStore + storage tests)."""
    return Chunk(
        chunk_id="TEST-001.1",
        source_type="C",
        document_id="TEST-001",
        document_type="RiskRegister",
        chunk_index=1,
        content="## Risk Overview\n\nThis is a risk overview section.",
        metadata={
            "heading": "Risk Overview",
            "level": 1,
            "classification": "InternalConfidential",
            "effective_date": "2026-01-15",
        },
        citation={"format": "[RiskRegister:TEST-001]", "type": "synthetic"},
    )
```

Files to modify (remove local fixtures, rely on conftest):
- `tests/test_ingestion/test_chroma_store.py` — delete local `sample_chunk` (lines 10-30) and `embedder` (lines 33-36)
- `tests/test_ingestion/test_embedder.py` — delete local `embedder` (lines 5-8)
- `tests/test_ingestion/test_storage.py` — delete local `sample_chunk` (lines 12-34); keep test-specific fixtures (temp_store, temp_db)
- `tests/test_ingestion/test_run_ingestion.py` — no fixture to lift (uses only `temp_source_dir`)

Net result: −3 duplicate fixture definitions, +1 conftest.

#### B) `tests/test_research/conftest.py` already exists

The conftest (lines 32-57) has `_make_chunk` + `sample_chunks` + `mock_llm` + `mock_answer_generator` + `mock_retriever*`.

`tests/test_research/test_answer_generator.py:23-48` redefines `_make_chunk` + `sample_chunks` identically. Delete lines 23-48.

Tests in `test_answer_generator.py` use these fixtures with the `sample_chunks` parameter (pytest auto-discovers the conftest fixture).

#### C) `tests/test_retrieval/conftest.py` already exists

Conftest has `temp_dir`, `embedder`, `populated_stores`. The `_make_chunk` factory in:
- `tests/test_retrieval/test_router_integration.py:417-429` (3-arg variant) — used by tests in that file
- `tests/test_retrieval/test_cli_formatters.py:25-44` (8-arg variant) — used by tests in that file

**Decision**: keep the local `_make_chunk` in each file because the variants are different (one builds RetrievedChunk with 3 fields, the other with 8 fields for JSON serialization tests). Lifting these adds an import for marginal cleanup. **Skip.**

### Item 2 — Delete trivial test classes

#### A) `tests/test_research/test_workflow.py`

| Class / lines | Tests | Why delete |
|---|---|---|
| `TestResearchResultDataclass` (292-335) | 3 | Pure `ResearchResult` dataclass round-trip (`__init__`, `__eq__`); covered by every workflow test transitively |
| `TestWorkflowError` (342-370) | 4 | Tests `RuntimeError` inheritance, `raise/except`, `from exc`, `from x import x is x` — stdlib behavior |

Delete both classes entirely (lines 292-370). `TestResearchWorkflowErrors` (lines 104-141) already verifies WorkflowError inheritance-via-usage and `__cause__` chaining — keeps the meaningful coverage.

#### B) `tests/test_research/test_answer_generator.py:317-333`

`TestCitationDataclass` (2 tests): `__init__` round-trip + dataclass equality on `Citation`. Delete the class. Citation behavior is exercised by every TestAnswerGenerator test.

#### C) `tests/test_retrieval/test_retriever.py:143-165`

Two tests:
- `test_search_result_default_fields` (143-149) — `SearchResult(query="q")` defaults
- `test_retrieved_chunk_construction` (151-165) — `RetrievedChunk(...)` field round-trip

Both are pure dataclass exercises. Delete both. (`SearchResult` is exercised by every retriever test; `RetrievedChunk` is exercised by every retrieval test that builds chunks.)

#### D) `tests/test_research/test_workflow.py:217-222`

`test_default_top_k_is_5`: asserts the default value 5. The default is a documented contract in `workflow.py:64`; behavior is covered by `test_run_passes_query_and_top_k_to_retriever` (lines 35-46). Delete.

#### E) `tests/test_research/test_workflow.py:69-82`

`test_run_latency_is_measured`: lower bound `latency_ms > 0` is already asserted in `test_run_returns_research_result:33`; upper bound `latency_ms < 10_000` is the only unique signal (regression catcher for hang). **Merge** by adding the upper-bound assertion into `test_run_returns_research_result` (line 33), then delete the standalone test.

## Files modified

| File | Change | Net lines |
|---|---|---|
| `tests/test_ingestion/conftest.py` | NEW | +35 |
| `tests/test_ingestion/test_chroma_store.py` | delete local fixtures | −28 |
| `tests/test_ingestion/test_embedder.py` | delete local fixture | −4 |
| `tests/test_ingestion/test_storage.py` | delete local fixture | −23 |
| `tests/test_research/test_answer_generator.py` | delete duplicate `_make_chunk`/`sample_chunks` + `TestCitationDataclass` | −50 |
| `tests/test_research/test_workflow.py` | delete 3 classes + 2 tests, fold upper-bound into existing test | −110 |
| `tests/test_retrieval/test_retriever.py` | delete 2 tests | −23 |

**Net: ~−200 lines, ~−15 tests, zero coverage loss.**

## Verification

1. `pytest tests/test_ingestion/ -v` — all 57 tests pass (conftest fixtures available via auto-discovery)
2. `pytest tests/test_research/ -v` — all tests pass; `sample_chunks` fixture picked up from conftest
3. `pytest tests/test_retrieval/ -v` — all tests pass
4. `pytest tests/ -q` — full suite green; total ~318 tests (was 333); line-count report shows reduction
5. Confirm no import errors from removed fixtures (`grep` for `sample_chunk` and `embedder` should only show conftest definitions + valid usages)
6. Coverage report (`pytest --cov=src`) shows no source line newly uncovered

## Out of scope (deferred to follow-up)

- Item 3: parametrize opportunities (`test_citation.py`, `test_pdf_parser.py`, etc.)
- Item 4: overlap trims (`test_retrieval/test_integration.py`, `TestResearchCliSubprocess`)
- Item 5: speed wins (subprocess marker, module-scoped embedder in research tests)
- Marking tests with custom pytest markers

## Why a separate PR

This PR is pure deletion/lift with zero behavior change. Easy review, low risk, no CI signal noise. Items 3-5 can follow as a separate PR that touches test bodies (parametrize, deletions of overlapping cases).