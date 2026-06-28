"""AuditAtlas research (answer generation) layer.

Phase 6: orchestrates the Phase 5 Retriever with an LLM to produce
evidence-backed, citation-supported answers.

Public API:
- `AnswerGenerator` — generates CitedAnswer from a SearchResult
- `CitedAnswer`, `Citation` — answer data models
- `LLMClient` (Protocol), `AnthropicClient`, `MockClient` — LLM backends
"""

from .answer_generator import AnswerGenerator
from .llm_client import AnthropicClient, LLMClient, MockClient
from .models import Citation, CitedAnswer
from .prompts import build_cited_answer_prompt

__all__ = [
    "AnswerGenerator",
    "AnthropicClient",
    "Citation",
    "CitedAnswer",
    "LLMClient",
    "MockClient",
    "build_cited_answer_prompt",
]
