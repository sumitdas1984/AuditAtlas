# Plan: FEATURE-006-TASK-1 — LLM Client & Answer Generator

## Context

Issue #33: Phase 5 (Retrieval) is complete — `Retriever.search()` returns ranked, hydrated chunks with citations. But the user still has to read those chunks and synthesize an answer themselves.

TASK-6-1 builds the foundation for the answer-generation layer:
- An **LLM client** abstraction (Anthropic SDK wrapper + deterministic mock for tests)
- A **prompt template** that instructs the LLM to cite chunks via `[[chunk_id]]` markers
- An **AnswerGenerator** that takes a `SearchResult`, calls the LLM, and returns a `CitedAnswer` with the answer text + a structured `Citation` list mapping markers back to `RetrievedChunk` objects
- A **hallucination guard**: if the LLM mentions a chunk_id that wasn't retrieved, silently drop it (don't surface ungrounded citations)

This is the building block for `ResearchWorkflow` (TASK-6-2) and the CLI (TASK-6-3).

## Approach

### New files

- `src/research/__init__.py` — exports `AnswerGenerator`, `CitedAnswer`, `Citation`, `LLMClient`, `AnthropicClient`, `MockClient`
- `src/research/models.py` — dataclasses: `Citation`, `CitedAnswer`
- `src/research/llm_client.py` — `LLMClient` protocol + `AnthropicClient` + `MockClient`
- `src/research/prompts.py` — `build_cited_answer_prompt(query, chunks)` function
- `src/research/answer_generator.py` — `AnswerGenerator` class
- `tests/test_research/__init__.py` — empty
- `tests/test_research/test_answer_generator.py` — ~7 tests
- `pyproject.toml` — add `anthropic` dependency

### `models.py` — data classes

```python
@dataclass
class Citation:
    """A citation marker in the answer text, mapped back to a chunk."""
    marker: str           # "[[AS1105.12]]"
    chunk_id: str         # "AS1105.12"
    chunk: RetrievedChunk # the full chunk for rendering

@dataclass
class CitedAnswer:
    """An LLM-generated answer with grounded citations."""
    text: str                         # answer text with [[chunk_id]] markers
    citations: list[Citation]         # ordered, deduped
    model: str                        # e.g., "claude-haiku-4-5"
    usage: dict                       # {"input_tokens": N, "output_tokens": M}
```

### `llm_client.py` — LLM client abstraction

**Protocol-based** for testability:
```python
from typing import Protocol

class LLMClient(Protocol):
    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str: ...
```

**`AnthropicClient`** — real implementation:
- Reads `ANTHROPIC_API_KEY` from env at `__init__`
- Calls `anthropic.Anthropic().messages.create(model="claude-haiku-4-5", system=..., messages=[{"role": "user", "content": user}], max_tokens=...)`
- Returns the response text + a usage dict
- Imports `anthropic` lazily so tests don't require it (only loaded when used)

**`MockClient`** — deterministic, for tests:
- Stores a pre-canned response or callable
- Records calls for test assertions
- No external dependencies

### `prompts.py` — prompt template

Single function `build_cited_answer_prompt(query: str, chunks: list[RetrievedChunk]) -> tuple[str, str]` that returns `(system_prompt, user_prompt)`.

**System prompt** (defines the LLM's role):
```
You are an audit research assistant. You help audit professionals by
answering questions using authoritative sources: PCAOB auditing standards,
SEC 10-K filings, and internal company documents.

When answering:
- Cite every claim by wrapping the chunk_id in double brackets,
  e.g. [[AS1105.12]] or [[AAPL.2025.Item1A.1]].
- Use only information from the provided source chunks. If the chunks
  don't contain enough information to answer, say so clearly.
- Be concise but complete. Use formal audit language.
- Never invent chunk_ids that aren't in the source chunks.
```

**User prompt** (the actual question + context):
```
Question: {query}

Source chunks:
1. [chunk_id] "{content}"
2. [chunk_id] "{content}"
...

Answer:
```

### `answer_generator.py` — main class

```python
class AnswerGenerator:
    def __init__(self, llm_client: LLMClient, model: str = "claude-haiku-4-5"):
        self.llm_client = llm_client
        self.model = model

    def generate(self, search_result: SearchResult) -> CitedAnswer:
        """Generate a cited answer from a SearchResult."""
```

**Flow:**
1. If `search_result.chunks` is empty → return `CitedAnswer(text="I don't have enough information to answer '{query}'.", citations=[], model=self.model, usage={})`
2. Build system + user prompts via `prompts.py`
3. Call `self.llm_client.complete(system, user, max_tokens=1024)` → raw LLM text
4. **Citation resolution**: scan the LLM text for `[[chunk_id]]` patterns (regex `\[\[([^\]]+)\]\]`)
5. For each `[[chunk_id]]` found:
   - If `chunk_id` matches a retrieved chunk → add to `citations` list (dedupe by `chunk_id`)
   - If `chunk_id` is unknown (LLM hallucination) → silently drop (log debug)
6. Return `CitedAnswer(text=llm_text, citations=ordered_list, model=self.model, usage={...})`

**Citation ordering**: preserve order of first appearance in the text.

**Hallucination logging**:
```python
logger.debug("Answer generator: dropped %d unknown citation(s): %s", count, ids)
```

### Reuse

- `SearchResult`, `RetrievedChunk` from `src/retrieval/models.py`
- Standard `logging` module

### `pyproject.toml` changes

Add `anthropic` to dependencies:
```toml
[project]
dependencies = [
    ...,
    "anthropic>=0.40.0",
]
```

### Tests (`tests/test_research/test_answer_generator.py`)

1. **`test_answer_generator_with_mock_client_produces_cited_answer`** — happy path; mock returns text with `[[AS1105.12]]`; assert Citation object built with correct chunk
2. **`test_answer_generator_handles_empty_chunks`** — empty SearchResult → "I don't have enough information..." with no citations
3. **`test_answer_generator_resolves_multiple_citations`** — text with 3 different `[[chunk_id]]` markers → 3 Citation objects
4. **`test_answer_generator_deduplicates_citations`** — same `[[chunk_id]]` appears twice → only 1 Citation object
5. **`test_answer_generator_drops_unknown_citations`** — text has `[[FAKE.1]]` (not retrieved) → not in citations
6. **`test_answer_generator_preserves_citation_order`** — citations appear in order of first mention in text
7. **`test_prompt_includes_all_retrieved_chunks`** — every chunk_id appears in the prompt
8. **`test_anthropic_client_uses_api_key_from_env`** — mock anthropic SDK, verify `__init__` reads env (and raises if missing)
9. **`test_mock_client_records_calls`** — calls list is populated

**Total: ~9 tests** (a couple more than the 7 estimated in the parent plan).

### Critical files to be modified

- `src/research/__init__.py` (new)
- `src/research/models.py` (new)
- `src/research/llm_client.py` (new)
- `src/research/prompts.py` (new)
- `src/research/answer_generator.py` (new)
- `tests/test_research/__init__.py` (new, empty)
- `tests/test_research/test_answer_generator.py` (new)
- `pyproject.toml` (modify: add anthropic)

## Verification

1. `pytest tests/test_research/ -v` → 9 new tests pass
2. `pytest tests/` → full suite green, ≥231 tests (222 + 9 new)
3. Manual smoke (mock): `from src.research.llm_client import MockClient; from src.research.answer_generator import AnswerGenerator; g = AnswerGenerator(MockClient(response="See [[AS1105.12]]."))` returns expected `CitedAnswer`

## Out of Scope (deferred to later tasks)

- Real LLM integration testing (requires `ANTHROPIC_API_KEY`; covered manually in TASK-6-3)
- `ResearchWorkflow` orchestration → TASK-6-2
- CLI exposure → TASK-6-3
- Citation rendering (converting `Citation` to formatted text like `[1] [AS 1105 § .12]`) → TASK-6-3
- Streaming responses
- Token usage tracking integration with monitoring