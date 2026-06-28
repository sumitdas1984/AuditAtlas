"""AuditAtlas research (answer generation) layer.

Phase 6: orchestrates the Phase 5 Retriever with an LLM to produce
evidence-backed, citation-supported answers.

Public API:
- `ResearchWorkflow` — end-to-end research API (retrieval + generation)
- `AnswerGenerator` — generates CitedAnswer from a SearchResult
- `CitedAnswer`, `Citation`, `ResearchResult` — data models
- `LLMClient` (Protocol), `AnthropicClient`, `MockClient` — LLM backends
"""

from .answer_generator import AnswerGenerator
from .llm_client import AnthropicClient, LLMClient, MockClient
from .models import Citation, CitedAnswer, ResearchResult
from .prompts import build_cited_answer_prompt
from .workflow import ResearchWorkflow, WorkflowError

__all__ = [
    "AnswerGenerator",
    "AnthropicClient",
    "Citation",
    "CitedAnswer",
    "LLMClient",
    "MockClient",
    "ResearchResult",
    "ResearchWorkflow",
    "WorkflowError",
    "build_cited_answer_prompt",
]
