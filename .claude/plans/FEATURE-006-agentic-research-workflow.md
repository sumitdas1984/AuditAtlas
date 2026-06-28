# Plan: FEATURE-006 — Agentic Research Workflow (Phase 6)

## Context

Phase 5 (Retrieval System) is complete. Users can run a query through the `Retriever` and get back relevant, cited chunks from any of the three sources. But that's only half the picture — the user is still left to read all the chunks and synthesize an answer themselves.

Phase 6 closes the loop: feed the retrieved chunks to an LLM and produce a coherent, citation-supported answer. The agentic workflow coordinates `Retriever` (Phase 5) + `AnswerGenerator` (new) into a single `ResearchWorkflow` API.

**Decisions made with the user:**
- **LLM**: Claude API (`claude-haiku-4-5`) — high quality, low latency
- **Workflow shape**: Single-pass synthesis — retrieve chunks → prompt LLM → return cited answer
- **HTTP API**: Deferred to a later phase (Phase 6 ships programmatic API + CLI only)

## Approach

Three sub-tasks, matching the established Phase 4/5 pattern. Phase 6 has a smaller surface area than Phase 5 (no embedding work, no storage work) so 3 tasks is sufficient.

| # | Title | Builds | Depends on |
|---|-------|--------|------------|
| 6-1 | LLM Client & Answer Generator | `LLMClient` (Anthropic SDK wrapper + mock), prompt template, `AnswerGenerator` (SearchResult → cited answer), citation validation/resolution | — |
| 6-2 | Research Workflow Orchestration | `ResearchWorkflow` coordinates `Retriever` + `AnswerGenerator`, returns `ResearchResult`, error handling, logging/tracing | 6-1 |
| 6-3 | CLI, Integration Tests, Docs | `python -m src.research workflow "query"`, end-to-end tests with mock LLM, doc updates | 6-2 |

### TASK-6-1: LLM Client & Answer Generator

**New files:**
- `src/research/__init__.py`
- `src/research/llm_client.py` — `LLMClient` protocol + `AnthropicClient` implementation + `MockClient` (deterministic, for tests)
- `src/research/prompts.py` — prompt template(s) for cited answer generation
- `src/research/answer_generator.py` — `AnswerGenerator` takes `SearchResult` → returns cited answer text
- `src/research/models.py` — `CitedAnswer`, `ResearchResult` dataclasses

**`LLMClient` design** (protocol-based for testability):
```python
class LLMClient(Protocol):
    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str: ...
```

Implementations:
- `AnthropicClient(LLMClient)` — wraps `anthropic.Anthropic().messages.create(...)`; uses `ANTHROPIC_API_KEY` env var
- `MockClient(LLMClient)` — returns a deterministic templated response (echoes chunks with citations)

**`AnswerGenerator` design:**
- Input: `SearchResult` (chunks + routing + sources_searched)
- Output: `CitedAnswer` dataclass:
  - `text: str` — the generated answer with inline citations like `[1]`, `[2]`
  - `citations: list[Citation]` — mapping of citation markers `[1]`, `[2]` to `RetrievedChunk` (so callers can render formal citations)
  - `model: str` — LLM model used
  - `usage: dict` — token counts (for monitoring)

**Citation resolution** — The LLM is instructed (in the prompt) to cite chunks by their `[chunk_id]`. The AnswerGenerator scans the answer text for `[[chunk_id]]` patterns and builds the `Citation` list. If the LLM mentions a chunk that wasn't retrieved, the AnswerGenerator silently drops it (don't surface unretrieved citations — they're ungrounded).

**Prompt template** (`prompts.py`):
```
You are an audit research assistant. Use the provided source chunks to answer the
user's question. Cite each claim by wrapping the chunk_id in double brackets,
e.g. [[AS1105.12]]. If the chunks don't contain enough information, say so —
do not invent.

Question: {query}

Source chunks:
1. [AS1105.12] "The auditor must obtain sufficient appropriate audit evidence..."
2. [AAPL.2025.Item1A.1] "Risk factors include supply chain disruption..."

Answer:
```

**Reuse:**
- `Retriever`, `SearchResult`, `RetrievedChunk` from `src/retrieval/`
- `format_citation` from `src/knowledge_engineering/citation.py` (for the Citation mapping)

**Tests** (`tests/test_research/test_answer_generator.py`):
- `test_answer_generator_with_mock_client_produces_cited_answer`
- `test_answer_generator_handles_empty_chunks` (no results → "I don't have enough information to answer")
- `test_answer_generator_resolves_citation_markers` (verifies `[[chunk_id]]` → Citation mapping)
- `test_answer_generator_drops_unknown_chunk_citations` (LLM hallucinates chunk_id → silently dropped)
- `test_anthropic_client_uses_api_key_from_env` (mock the anthropic SDK)
- `test_mock_client_is_deterministic`
- `test_prompt_includes_all_retrieved_chunks` (no truncation)

### TASK-6-2: Research Workflow Orchestration

**New files:**
- `src/research/workflow.py` — `ResearchWorkflow` class
- Tests in `tests/test_research/test_workflow.py`

**`ResearchWorkflow` design:**
```python
class ResearchWorkflow:
    def __init__(self, retriever: Retriever, answer_generator: AnswerGenerator): ...
    def run(self, query: str, top_k: int = 5, **retriever_kwargs) -> ResearchResult: ...
```

**`ResearchResult` dataclass:**
- `query: str`
- `answer: CitedAnswer`
- `chunks: list[RetrievedChunk]` — what was retrieved (for transparency)
- `routing: Optional[RoutingResult]` — routing decision (passed through)
- `sources_searched: list[str]`
- `latency_ms: float` — wall-clock time

**Flow:**
1. Log: "Starting research for query='{query}'"
2. `t0 = time.monotonic()`
3. `search_result = self.retriever.search(query, top_k=top_k, **kwargs)` — Phase 5
4. `answer = self.answer_generator.generate(search_result)` — new in 6-1
5. `latency_ms = (time.monotonic() - t0) * 1000`
6. Log: "Research complete in {latency_ms}ms; {n} chunks used"
7. Return `ResearchResult(...)`

**Error handling:**
- Retrieval failure → `WorkflowError` with retriever exception message
- LLM failure → `WorkflowError` with LLM exception message + "the search results are still available, you can re-run answer generation later"
- Empty chunks → workflow still succeeds; answer is "I don't have enough information to answer '{query}'"

**Logging:**
- Use `logging.getLogger(__name__)`
- INFO at start/end of each step
- DEBUG: query, retrieved chunk_ids, prompt summary, answer length
- WARNING: empty chunks, dropped citations

**Reuse:**
- All of `Retriever` (Phase 5)
- `AnswerGenerator` (6-1)
- `RoutingResult` (Phase 3)

**Tests** (`tests/test_research/test_workflow.py`):
- `test_workflow_run_returns_research_result` — happy path
- `test_workflow_propagates_retriever_error` — retriever raises → `WorkflowError`
- `test_workflow_propagates_llm_error` — LLM raises → `WorkflowError`
- `test_workflow_handles_empty_chunks` — empty SearchResult → answer with "I don't have enough information"
- `test_workflow_latency_is_measured` — `latency_ms > 0`
- `test_workflow_uses_default_retriever_and_generator` — `ResearchWorkflow()` works out-of-box
- `test_workflow_passes_kwargs_to_retriever` — `ticker=`, `standard_id=` flow through

### TASK-6-3: CLI, Integration Tests, Docs

**New files:**
- `src/research/cli.py` — `run_research` handler + output formatters
- `src/research/__main__.py` — argparse entry point
- `tests/test_research/test_integration.py` — end-to-end tests with mock LLM

**CLI** (matches Phase 5 pattern):
```bash
python -m src.research workflow "What does PCAOB say about audit evidence?" --top-k 5
python -m src.research workflow "risk factors" --ticker AAPL --format json
```

Output:
- **Text format (default)**: answer text followed by formal citations
- **JSON format**: `ResearchResult` serialized (answer + chunks + routing + latency)
- `--no-citations` to suppress citation rendering
- `--use-mock-llm` for testing (uses `MockClient` instead of `AnthropicClient`)

**Exit codes** (match Phase 5):
- 0 = success
- 2 = empty query
- 3 = uninit KB
- 4 = bad `--where` JSON
- 5 = runtime error (incl. LLM failure, retrieval failure)

**Integration tests** with mock LLM:
- `test_research_workflow_e2e_compliance_query` — full pipeline
- `test_research_workflow_e2e_with_ticker_filter` — filter flows through
- `test_research_workflow_handles_empty_kb` — graceful
- `test_research_cli_text_format` — subprocess runs, output contains answer
- `test_research_cli_json_format` — valid JSON
- `test_research_cli_exit_codes` — each error path

**Docs:**
- New: `docs/agentic_workflow/` directory with:
  - `01_workflow_architecture.md` — block diagram + flow
  - `02_prompt_templates.md` — current prompt template + how to tune
- Update `CLAUDE.md` — add `src/research/` row, mark Phase 6 status
- Update `docs/03_project_plan.md` — Phase 6 status

### Critical files to be modified

- `src/research/` (new directory) — ~10 new files
- `tests/test_research/` (new directory) — ~3 test files
- `pyproject.toml` — add `anthropic` dependency
- `docs/agentic_workflow/` (new) — design docs
- `CLAUDE.md` — phase status, src/research/ row

### Reuse map

| Component | Path | What we use |
|-----------|------|-------------|
| `Retriever` | `src/retrieval/retriever.py` | `search()` — Phase 5 output |
| `SearchResult`, `RetrievedChunk` | `src/retrieval/models.py` | workflow input |
| `format_citation` | `src/knowledge_engineering/citation.py` | render formal citations |
| `RoutingResult` | `src/knowledge_engineering/router.py` | pass through to user |
| `SourceType` | `src/knowledge_engineering/citation.py` | source attribution |

## Verification

1. `pytest tests/test_research/ -v` → all 6-1/6-2/6-3 tests pass
2. `pytest tests/` → full suite green, ≥245 tests (222 + 23 new estimated)
3. Manual smoke (mock LLM, no API key needed): `python -m src.research workflow "What are risk factors?" --use-mock-llm` returns formatted answer with citations
4. Manual smoke (real LLM, requires `ANTHROPIC_API_KEY`): `python -m src.research workflow "What are the risk factors for Apple?" --ticker AAPL` returns LLM-generated answer citing AAPL chunks
5. Latency check: < 5s end-to-end for mock; < 10s for real LLM (rough)

## Out of Scope (deferred to future phases)

- **Multi-step / ReAct agents** — Phase 6 is single-pass only; revisit if simple synthesis quality is insufficient
- **Conversation / context memory** — each query is independent
- **HTTP API** — Phase 7 or 8
- **Streaming responses** — out of scope; the answer is returned as a single text block
- **Custom prompt tuning per user** — single template for MVP
- **Citation quality evaluation** — Phase 7 (Evaluation)
- **Other LLM providers** (OpenAI, local) — extend the LLMClient protocol in a future task if needed

## Sub-tasks to file on GitHub

Create 3 child issues on `#7` using `sub_issue_write`:
- FEATURE-006-TASK-1: LLM Client & Answer Generator
- FEATURE-006-TASK-2: Research Workflow Orchestration
- FEATURE-006-TASK-3: CLI, Integration Tests, Docs

## Estimated test count after Phase 6

| Task | New tests | Cumulative |
|------|-----------|------------|
| 6-1 | ~7 | 229 |
| 6-2 | ~7 | 236 |
| 6-3 | ~9 | 245 |
| **Total** | **~23** | **~245** |