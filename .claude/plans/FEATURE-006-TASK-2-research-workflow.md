# Plan: FEATURE-006-TASK-2 — Research Workflow Orchestration

## Context

Issue #34: TASK-6-1 (LLM Client & Answer Generator) is merged. The `AnswerGenerator.generate(SearchResult)` returns a `CitedAnswer`, but there's no end-to-end API that wires the existing `Retriever` (Phase 5) with the new `AnswerGenerator` (6-1).

TASK-6-2 builds the `ResearchWorkflow` class — a thin orchestrator that:
1. Calls `retriever.search(query, top_k, **kwargs)`
2. Hands the `SearchResult` to `answer_generator.generate(...)`
3. Bundles the answer + retrieved chunks + routing + latency into a `ResearchResult`
4. Wraps both retriever and LLM failures into a single `WorkflowError`

This is the building block for the CLI (TASK-6-3) and any future HTTP API.

## Approach

### New files

- `src/research/workflow.py` — `ResearchWorkflow` class + `WorkflowError` exception
- `src/research/models.py` — extend with `ResearchResult` dataclass
- `tests/test_research/test_workflow.py` — ~7 tests

### Modify

- `src/research/__init__.py` — export `ResearchWorkflow`, `ResearchResult`, `WorkflowError`

### `models.py` — `ResearchResult` dataclass

```python
@dataclass
class ResearchResult:
    """The outcome of a complete research workflow run.

    Attributes:
        query: The original user query.
        answer: The LLM-generated CitedAnswer.
        chunks: The retrieved chunks (mirrors answer.citations[].chunk — kept
            here for callers that want the full retrieval context).
        routing: The RoutingResult (if the router was used), else None.
        sources_searched: List of source types queried (e.g., ["A", "B", "C"]).
        latency_ms: Wall-clock time for the full workflow run, in milliseconds.
    """

    query: str
    answer: CitedAnswer
    chunks: list[RetrievedChunk]
    routing: Optional[RoutingResult] = None
    sources_searched: list[str] = field(default_factory=list)
    latency_ms: float = 0.0
```

### `workflow.py` — `WorkflowError` + `ResearchWorkflow`

```python
class WorkflowError(RuntimeError):
    """Raised when the research workflow fails (retrieval or LLM error).

    The original exception is chained via `__cause__` for debugging.
    """
```

```python
class ResearchWorkflow:
    """Orchestrates Retriever (Phase 5) + AnswerGenerator (6-1) into a single API.

    Args:
        retriever: Any object with a `.search(query, top_k, **kwargs) -> SearchResult` method.
        answer_generator: An `AnswerGenerator` instance.

    If both are omitted, defaults are constructed:
    - `Retriever()` — uses standard stores + a Router
    - `AnswerGenerator(AnthropicClient())` — requires ANTHROPIC_API_KEY
    """

    def __init__(
        self,
        retriever: Optional[Retriever] = None,
        answer_generator: Optional[AnswerGenerator] = None,
    ):
        self.retriever = retriever or Retriever()
        self.answer_generator = answer_generator or AnswerGenerator(AnthropicClient())

    def run(
        self,
        query: str,
        top_k: int = 5,
        **retriever_kwargs,
    ) -> ResearchResult:
        """Run end-to-end research: retrieve chunks, generate cited answer.

        Args:
            query: Natural-language question.
            top_k: Maximum number of chunks to retrieve (default 5).
            **retriever_kwargs: Extra kwargs forwarded to Retriever.search()
                (e.g., ticker, standard_id, where, use_router).

        Returns:
            ResearchResult with answer, chunks, routing, and latency.

        Raises:
            WorkflowError: If retrieval or LLM generation fails. The original
                exception is chained via __cause__.
        """
```

**Flow:**
1. Log INFO: "Research started for query='{query}', top_k={top_k}"
2. `t0 = time.monotonic()`
3. **Retrieval step** (try/except → WorkflowError):
   - `search_result = self.retriever.search(query, top_k=top_k, **retriever_kwargs)`
4. Log DEBUG: "Retrieved {n} chunks in {ms}ms"
5. **Generation step** (try/except → WorkflowError):
   - `answer = self.answer_generator.generate(search_result)`
6. Compute `latency_ms = (time.monotonic() - t0) * 1000`
7. Log INFO: "Research complete in {latency_ms}ms; {n_chunks} chunks used"
8. Build `ResearchResult(...)` with:
   - `query` from input
   - `answer` from generation
   - `chunks = search_result.chunks`
   - `routing = search_result.routing`
   - `sources_searched = search_result.sources_searched`
   - `latency_ms` measured

**Empty chunks** (no retrieval results): The `AnswerGenerator` already handles this — it returns the graceful "I don't have enough information" message without calling the LLM. The workflow passes through normally.

**Error wrapping:**
- `except Exception as exc: raise WorkflowError(f"retrieval failed: {exc}") from exc`
- `except Exception as exc: raise WorkflowError(f"answer generation failed: {exc}") from exc`
- Always log the full traceback at ERROR level before raising

### Reuse

- `Retriever`, `SearchResult`, `RetrievedChunk` from `src/retrieval/`
- `AnswerGenerator`, `CitedAnswer` from `src/research/`
- `RoutingResult` from `src/knowledge_engineering/router.py`
- `AnthropicClient` from `src/research/llm_client.py` (default LLM)
- `MockClient` for tests (so the default `ResearchWorkflow()` doesn't need an API key in tests)

### Tests (`tests/test_research/test_workflow.py`)

1. **`test_workflow_run_returns_research_result`** — happy path with `MockClient`
2. **`test_workflow_propagates_retriever_error`** — `Retriever.search()` raises → `WorkflowError` with chained cause
3. **`test_workflow_propagates_llm_error`** — `AnswerGenerator` raises (via `MockClient(raise_on_call=...)`) → `WorkflowError` with chained cause
4. **`test_workflow_handles_empty_chunks`** — empty `SearchResult.chunks` → workflow succeeds with graceful answer (no LLM call)
5. **`test_workflow_latency_is_measured`** — `latency_ms > 0` after run
6. **`test_workflow_passes_kwargs_to_retriever`** — `ticker=`, `standard_id=`, `where=`, `use_router=` flow through to retriever
7. **`test_workflow_logs_start_and_end`** — verify INFO log records with `caplog`

**Total: ~7 tests**

### Fixtures (in conftest.py for `tests/test_research/`)

Add `populated_stores` (a small in-memory KB) and `mock_retriever_with_chunks` so workflow tests can run without real retrieval.

### Critical files to be modified

- `src/research/models.py` (add `ResearchResult`)
- `src/research/workflow.py` (new, ~80 lines)
- `src/research/__init__.py` (extend exports)
- `tests/test_research/test_workflow.py` (new)
- `tests/test_research/conftest.py` (new, fixtures)

## Verification

1. `pytest tests/test_research/test_workflow.py -v` → 7 new tests pass
2. `pytest tests/` → full suite green, ≥268 tests (261 + 7 new)
3. Manual smoke: with `MockClient`, `ResearchWorkflow(...).run("query")` returns `ResearchResult` with `latency_ms > 0` and a non-empty answer

## Out of Scope (deferred to later tasks)

- CLI exposure → TASK-6-3
- HTTP API → deferred to a later phase
- Streaming responses
- Conversation / context memory
- Workflow metrics collection (Prometheus, etc.)
- Caching of LLM responses
