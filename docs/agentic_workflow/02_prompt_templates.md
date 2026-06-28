# Prompt Templates — Agentic Research Workflow

**Phase**: 6 — Agentic Research Workflow
**Status**: Implemented

---

## Overview

The `AnswerGenerator` (Phase 6-1) builds two prompt components — a **system** prompt and a **user** prompt — from the user's query and the retrieved chunks. The LLM is instructed to cite sources by wrapping the chunk_id in `[[chunk_id]]` markers, which the `AnswerGenerator` parses back into a structured `Citation` list.

## Current Template

### System prompt

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

### User prompt

```
Question: {query}

Source chunks:
1. [{chunk_id_1}] "{content_1}"
2. [{chunk_id_2}] "{content_2}"
3. [{chunk_id_3}] "{content_3}"
...

Answer:
```

## Where the Template Lives

| File | Contents |
|------|----------|
| `src/research/prompts.py` | `SYSTEM_PROMPT` constant + `build_cited_answer_prompt(query, chunks)` function |

The system prompt is a module-level string constant. The user prompt is built by `build_cited_answer_prompt`, which:
- Truncates chunk content to fit the prompt budget
- Collapses whitespace in chunk content (newlines/tabs become single spaces)
- Numbers each chunk for reference
- Wraps each chunk_id in `[{chunk_id}]` for the LLM to see

## How to Tune the Prompts

### Change the system prompt

Edit `SYSTEM_PROMPT` in `src/research/prompts.py`. Common reasons to tune:
- Add domain-specific language (e.g., "Use COSO framework terminology")
- Tighten the citation rule (e.g., require every sentence to have a citation)
- Add style guidance (e.g., "Reply in formal English suitable for an audit memo")

After editing, re-run tests to verify nothing broke.

### Change the citation format

If you want the LLM to use a different citation format (e.g., `[1]` numeric markers or `[source: PCAOB AS 1105]`), update both the system prompt AND the regex in `src/research/answer_generator.py`:

```python
_CITATION_PATTERN = re.compile(r"\[\[([^\]\s]+)\]\]")
```

For example, to switch to `[1]` numeric markers:
1. System prompt: "Cite by source number, e.g. [1] for the first source, [2] for the second"
2. `_CITATION_PATTERN`: capture the number, then look up the chunk by position in the input list
3. Update the `Citation` dataclass to include the marker

This is a non-trivial change; consider keeping the current `[[chunk_id]]` format.

### Change the model

Default model is `claude-haiku-4-5` (in `AnswerGenerator.__init__`). To use a different model:

```python
from src.research import AnswerGenerator, AnthropicClient
gen = AnswerGenerator(
    llm_client=AnthropicClient(model="claude-sonnet-4-6"),
)
```

For higher quality at higher cost/latency, use `claude-sonnet-4-6`. For lower latency at lower cost, stick with `claude-haiku-4-5`.

### Add a custom prompt for a specific use case

Create a new function in `src/research/prompts.py` and reference it from a custom `AnswerGenerator` subclass:

```python
# src/research/prompts.py
DEFINITION_SYSTEM_PROMPT = "..."  # your custom prompt
def build_definition_prompt(query, chunks): ...

# src/research/answer_generator.py (or new file)
class DefinitionAnswerGenerator(AnswerGenerator):
    def generate(self, search_result):
        sys_p, usr_p = build_definition_prompt(...)
        text = self.llm_client.complete(sys_p, usr_p, max_tokens=...)
        citations = self._resolve_citations(text, search_result.chunks)
        return CitedAnswer(text=text, citations=citations, model=self.model, usage={})
```

## Testing Prompts

The test suite covers:
- All retrieved chunks appear in the user prompt (`test_prompt_includes_all_retrieved_chunks`)
- The query is included (`test_prompt_includes_query`)
- The system prompt instructs the `[[chunk_id]]` format (`test_prompt_system_instructs_citation_format`)
- Chunks are numbered (`test_prompt_chunks_are_numbered`)
- Newlines in chunk content are collapsed (`test_prompt_handles_newlines_in_chunk_content`)

After tuning the prompt, run `pytest tests/test_research/test_answer_generator.py` to confirm.

## Limitations

- **No streaming**: The full answer is returned as a single text block after the LLM call completes.
- **No multi-step reasoning**: One prompt, one response. For multi-hop queries, the caller must chain multiple `run()` calls.
- **No few-shot examples**: The prompt is zero-shot. Adding 1-2 example answers (with `[[chunk_id]]` citations) could improve citation quality — easy to add as a follow-up.
- **No temperature tuning**: The Anthropic API uses its default sampling parameters. For more deterministic answers, consider passing `temperature=0` (requires extending `AnthropicClient.complete()` to accept extra kwargs).
- **No token counting / budget enforcement**: If the prompt gets very long (many chunks), it may exceed the model's context window. Add a token-budget check if you expect >10 chunks per query.

## Future Improvements

- Add few-shot examples to the system prompt
- Support temperature and other Anthropic API parameters
- Add prompt variants for different query intents (definition vs comparison vs finding)
- Track token usage in `CitedAnswer.usage` (currently always `{}` — would require extending `LLMClient.complete()` to return a `(text, usage_dict)` tuple)
