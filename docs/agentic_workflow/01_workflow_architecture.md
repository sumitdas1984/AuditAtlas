# Agentic Research Workflow — Architecture

**Phase**: 6 — Agentic Research Workflow
**Status**: Implemented (TASK-6-1, 6-2, 6-3 done)
**Issue**: FEATURE-006 (#7)

---

## Overview

The agentic research workflow coordinates the Phase 5 `Retriever` with the Phase 6 `AnswerGenerator` to produce evidence-backed, citation-supported answers. A single user query flows through retrieval, prompt construction, LLM generation, and citation resolution — all in one `ResearchWorkflow.run()` call.

## Architecture

```
┌──────────────────┐
│   User Query     │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│  ResearchWorkflow.run(query, top_k, ...)  │
│  (src/research/workflow.py)               │
└────────┬────────────────────────┬────────┘
         │                        │
         ▼                        ▼
┌──────────────────────┐  ┌─────────────────────────┐
│  Retriever           │  │  AnswerGenerator         │
│  (src/retrieval/)    │  │  (src/research/)         │
│                      │  │                          │
│  - Router            │  │  - LLMClient             │
│  - ChromaDB          │  │  - prompt template       │
│  - JsonStore         │  │  - citation resolution   │
│  - Embedder          │  │  - hallucination guard   │
└────────┬─────────────┘  └──────────┬────────────────┘
         │                           │
         ▼                           ▼
   SearchResult                CitedAnswer
         │                           │
         └──────────┬────────────────┘
                    ▼
            ┌──────────────────┐
            │ ResearchResult   │
            │ - query          │
            │ - answer         │
            │ - chunks         │
            │ - routing        │
            │ - sources_searched │
            │ - latency_ms     │
            └──────────────────┘
```

## Components

| Component | Path | Role |
|-----------|------|------|
| `ResearchWorkflow` | `src/research/workflow.py` | Orchestrator; `run(query, **kwargs) → ResearchResult` |
| `Retriever` | `src/retrieval/retriever.py` | Phase 5; `search(query, top_k, **kwargs) → SearchResult` |
| `AnswerGenerator` | `src/research/answer_generator.py` | Phase 6-1; `generate(SearchResult) → CitedAnswer` |
| `LLMClient` (Protocol) | `src/research/llm_client.py` | Pluggable LLM backend |
| `AnthropicClient` | same | Real Claude API implementation |
| `MockClient` | same | Deterministic, for tests |
| `RetrievedChunk`, `SearchResult` | `src/retrieval/models.py` | Retrieval output models |
| `Citation`, `CitedAnswer`, `ResearchResult` | `src/research/models.py` | Answer / workflow output models |
| `Router` | `src/knowledge_engineering/router.py` | Phase 3; multi-source routing |
| `format_citation` | `src/knowledge_engineering/citation.py` | Phase 3; formal citation rendering |

## Flow

1. **Input** — User calls `workflow.run(query, top_k=5, ticker=..., standard_id=..., where=..., use_router=True)`.

2. **Retrieval** (Phase 5):
   - `Retriever.search()` either routes the query via `Router` (multi-source) or uses a single `where` filter
   - Returns `SearchResult` with chunks ordered by ChromaDB distance

3. **Answer Generation** (Phase 6-1):
   - Empty chunks → return graceful "I don't have enough information" message (no LLM call)
   - Otherwise: build prompt with system + user messages, call LLM, parse `[[chunk_id]]` markers into `Citation` list
   - Hallucinated chunk_ids (not in retrieved chunks) are silently dropped

4. **Bundle** — `ResearchResult` combines:
   - The original query
   - `CitedAnswer` (text + citations)
   - Retrieved chunks (for callers that want full context)
   - Routing decision (if Router was used)
   - `sources_searched` (which source types were queried)
   - `latency_ms` (wall-clock)

5. **Return** — Caller gets a structured `ResearchResult` they can render however they like (text via CLI, JSON via API, etc.).

## Error Handling

Both `Retriever.search()` and `LLMClient.complete()` can raise. The workflow wraps both in a single `WorkflowError(RuntimeError)` so callers have one exception type to handle:

- Retrieval fails → `WorkflowError("retrieval failed: ...")` with original chained via `__cause__`
- LLM fails → `WorkflowError("answer generation failed: ...")` with original chained
- Empty KB → graceful answer, no error
- Empty chunks → graceful "I don't have enough information" message, no LLM call

The workflow logs every error at `ERROR` level via `logger.exception(...)` so the traceback is preserved for debugging.

## CLI Exposure

See `src/research/cli.py` and `__main__.py`:

```bash
python -m src.research workflow "What does PCAOB say about audit evidence?" --top-k 5
python -m src.research workflow "risk factors" --ticker AAPL --format json
python -m src.research workflow "anything" --use-mock-llm  # for testing without API key
```

CLI exit codes match the Phase 5 pattern:
- 0 = success (including "no results")
- 2 = empty query
- 3 = uninitialized KB
- 4 = bad `--where` JSON
- 5 = runtime error (incl. LLM failure, retrieval failure)

## Design Decisions

### Single-pass synthesis (not multi-step agent)

The current workflow is single-pass: one retrieval call + one LLM call per query. We deliberately did NOT build a multi-step ReAct-style agent with replanning, tool use, or multi-hop reasoning. Reasons:

- Simpler to test and evaluate
- Faster end-to-end (typically <2s for mock LLM, ~5-10s for real Claude)
- Most audit queries don't need multi-hop — they ask "what does PCAOB say about X" or "what are AAPL's risk factors", not "compare X across all sources and synthesize"

If a query needs more depth, callers can chain multiple `workflow.run()` calls with refined queries (Phase 7+ evaluation).

### Pluggable LLM backend

The `LLMClient` Protocol means we can add other LLM providers (OpenAI, local models via Ollama, etc.) without changing the workflow. The MVP ships with `AnthropicClient` (Claude API) and `MockClient` (for tests).

### Citation format `[[chunk_id]]`

We use `[[chunk_id]]` (double brackets) instead of `[1]` numeric markers because:
- Numeric markers require a post-processing step to map them back to chunks
- `[[chunk_id]]` is self-describing — the LLM cites by the actual ID, which the user can verify
- The regex `\[\[([^\]\s]+)\]\]` extracts them reliably
- It survives markdown rendering (won't be confused with link syntax)

## Out of Scope

- Multi-step / ReAct agents
- Streaming responses
- Conversation / context memory
- HTTP API
- Citation quality evaluation (Phase 7)
