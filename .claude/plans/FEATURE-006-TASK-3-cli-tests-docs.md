# Plan: FEATURE-006-TASK-3 — CLI, Integration Tests, Docs

## Context

Issue #35: TASK-6-1 (LLM Client & Answer Generator) and TASK-6-2 (ResearchWorkflow) are merged. The `ResearchWorkflow.run()` API works programmatically but isn't accessible from a shell. Phase 6 ships without a CLI; users have to write Python to use the system.

TASK-6-3 exposes the workflow via CLI, adds end-to-end integration tests, and creates design docs for the agentic workflow. Final Phase 6 sub-task.

## Approach

### 1. CLI — `src/research/cli.py` + `src/research/__main__.py`

Match the Phase 5 retrieval CLI pattern (`src/retrieval/cli.py`):
- `__main__.py`: argparse entry point
- `cli.py`: command handlers + output formatters (testable in isolation)

**Invocation:**
```bash
python -m src.research workflow "What does PCAOB say about audit evidence?" --top-k 5
python -m src.research workflow "risk factors" --ticker AAPL --format json
python -m src.research workflow "anything" --use-mock-llm  # for testing
```

**Arguments (under `workflow` subcommand):**
| Flag | Type | Default | Purpose |
|------|------|---------|---------|
| `query` (positional) | str | required | The research question |
| `--top-k` | int | 5 | Number of chunks to retrieve |
| `--ticker` | str | None | Source B ticker filter |
| `--standard-id` | str | None | Source A standard ID filter |
| `--where` | str | None | Raw ChromaDB where clause as JSON |
| `--use-router` | bool | True | Enable router-based multi-source search |
| `--format` | choice | "text" | "text" (human) or "json" (machine) |
| `--use-mock-llm` | flag | False | Use MockClient (no API key needed) |
| `--chroma-dir` | str | None | Override ChromaDB persist directory |
| `--collection-name` | str | None | Override ChromaDB collection name |
| `--jsonl-path` | str | None | Override JSONL store path |

**Output formats:**
- **Text (default)**: answer text + numbered citations `[1] [AS 1105 § .12] [2] [AAPL 10-K, Item 1A (2025)]` rendered via `format_citation()` + a footer with sources searched and latency
- **JSON**: full `ResearchResult` serialized

**Exit codes** (match Phase 5):
| Code | Meaning |
|------|---------|
| 0 | Success (including "no results found") |
| 2 | Empty query |
| 3 | Uninitialized knowledge base |
| 4 | Invalid `--where` JSON |
| 5 | Runtime error (incl. LLM failure, retrieval failure — `WorkflowError`) |

### 2. Implementation details

**`run_research()` handler signature:**
```python
def run_research(
    query: str,
    top_k: int = 5,
    ticker: str | None = None,
    standard_id: str | None = None,
    where: str | None = None,
    use_router: bool = True,
    output_format: str = "text",
    use_mock_llm: bool = False,
    chroma_dir: str | None = None,
    collection_name: str | None = None,
    jsonl_path: str | None = None,
) -> tuple[int, str]:
```

**Flow:**
1. Input validation (empty query, bad --where JSON, unknown format)
2. KB health check via `ChromaStore.collection.count()` (same pattern as Phase 5)
3. Build retriever (with optional `chroma_dir` / `collection_name` / `jsonl_path` overrides)
4. Build answer generator:
   - If `use_mock_llm=True`: `AnswerGenerator(llm_client=MockClient())`
   - Else: `AnswerGenerator(llm_client=AnthropicClient())` (will raise if no API key)
5. Build `ResearchWorkflow(retriever, answer_generator)`
6. `result = workflow.run(query, top_k, ticker=..., standard_id=..., where=..., use_router=...)`
   - Catch `WorkflowError` → return exit 5 with error message
7. Format output (text or JSON)
8. Return (0, output)

**Citation rendering** (text format):
```python
def _format_text(result: ResearchResult) -> str:
    lines = []
    lines.append(result.answer.text)
    lines.append("")
    lines.append("Sources:")
    for i, citation in enumerate(result.answer.citations, 1):
        # format_citation takes a chunk_id and SourceType
        # We need to derive SourceType from the chunk's source_type
        source_type = SourceType(citation.chunk.source_type)
        formal = format_citation(citation.chunk_id, source_type)
        lines.append(f"  [{i}] {formal}")
    if result.sources_searched:
        lines.append("")
        lines.append(f"Sources searched: {result.sources_searched}")
    if result.latency_ms:
        lines.append(f"Latency: {result.latency_ms:.0f}ms")
    return "\n".join(lines)
```

**JSON format** (mirrors Phase 5):
```json
{
  "query": "...",
  "answer": {"text": "...", "citations": [...], "model": "..."},
  "chunks": [...],
  "routing": {"sources": ["A", "B"], "confidence": 0.9, "reasoning": "..."} | null,
  "sources_searched": ["A", "B"],
  "latency_ms": 1234.5
}
```

Use `json.dumps(..., indent=2, default=str, ensure_ascii=False)`.

### 3. Integration tests — `tests/test_research/test_integration.py`

**End-to-end tests** (with `MockClient` for LLM):
- `test_research_workflow_e2e_compliance_query` — full pipeline: build KB → workflow.run → assert answer + citations
- `test_research_workflow_e2e_with_ticker_filter` — filter flows through
- `test_research_workflow_handles_empty_kb` — graceful "I don't have enough information"
- `test_research_cli_text_format` — subprocess runs, output contains answer
- `test_research_cli_json_format` — valid JSON
- `test_research_cli_exit_codes` — each error path (2/3/4/5)
- `test_research_cli_use_mock_llm` — no API key needed
- `test_research_cli_passes_retriever_kwargs` — `--ticker` etc. flow through
- `test_research_cli_with_chroma_dir_override` — uses test-isolated temp dirs

**Total: ~9 tests**

### 4. Design docs

**New files:**
- `docs/agentic_workflow/01_workflow_architecture.md` — block diagram + flow description
- `docs/agentic_workflow/02_prompt_templates.md` — current prompt template + tuning guide

**Architecture doc content:**
```
┌──────────────────┐
│   User Query     │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│  ResearchWorkflow.run(query, top_k, ...)  │
└────────┬────────────────────────┬────────┘
         │                        │
         ▼                        ▼
┌──────────────────┐    ┌────────────────────┐
│   Retriever      │    │  AnswerGenerator   │
│   (Phase 5)      │    │  (Phase 6-1)        │
│                  │    │                     │
│ - Router         │    │ - LLMClient         │
│ - ChromaDB       │    │ - prompt template   │
│ - JsonStore      │    │ - citation resolve  │
└────────┬─────────┘    └──────────┬──────────┘
         │                        │
         ▼                        ▼
   SearchResult            CitedAnswer
         │                        │
         └────────┬───────────────┘
                  ▼
        ┌──────────────────┐
        │ ResearchResult   │
        │ - answer         │
        │ - chunks         │
        │ - routing        │
        │ - sources_searched│
        │ - latency_ms     │
        └──────────────────┘
```

**Prompt template doc:** copy of the current system prompt + the user prompt template, with notes on:
- How to swap models
- How to tune the citation format
- How to test with a custom prompt
- Limitations (no streaming, single-pass only)

**`CLAUDE.md`:** add `docs/agentic_workflow/` row, update status line.

### Critical files to be modified

**New:**
- `src/research/cli.py` — CLI handlers (~200 lines)
- `src/research/__main__.py` — argparse entry (~30 lines)
- `tests/test_research/test_integration.py` — 9 tests
- `docs/agentic_workflow/01_workflow_architecture.md`
- `docs/agentic_workflow/02_prompt_templates.md`

**Modified:**
- `CLAUDE.md` — add `docs/agentic_workflow/` row, update status

### Reuse

- `ResearchWorkflow`, `ResearchResult`, `CitedAnswer` from `src/research/`
- `AnswerGenerator`, `MockClient`, `AnthropicClient` from `src/research/`
- `Retriever`, `ChromaStore`, `JsonStore` from `src/retrieval/`
- `format_citation`, `SourceType` from `src/knowledge_engineering/citation.py`
- CLI pattern from `src/retrieval/cli.py`

## Verification

1. `pytest tests/test_research/test_integration.py -v` → 9 new tests pass
2. `pytest tests/` → full suite green, ≥297 tests (288 + 9 new)
3. Manual smoke (mock LLM, no API key needed):
   `python -m src.research workflow "What are the risk factors?" --use-mock-llm --top-k 3` returns formatted text with answer + numbered citations
4. Manual smoke (JSON):
   `python -m src.research workflow "audit evidence" --use-mock-llm --format json` returns valid JSON
5. Manual smoke (error paths):
   - `python -m src.research workflow ""` → exit 2
   - `python -m src.research workflow "x" --where 'not json'` → exit 4

## Out of Scope (deferred to later phases)

- HTTP API → deferred to Phase 7 or 8
- Streaming responses
- Conversation / context memory
- Citation quality evaluation → Phase 7
- Custom prompt tuning per user
- Other LLM providers (OpenAI, local)
