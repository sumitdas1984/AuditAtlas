"""Tests for the LLM client + answer generator (FEATURE-006-TASK-1)."""

import os
from unittest.mock import patch

import pytest

from src.research import (
    AnswerGenerator,
    AnthropicClient,
    Citation,
    CitedAnswer,
    MockClient,
    build_cited_answer_prompt,
)
from src.retrieval import RetrievedChunk, SearchResult


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

def _make_chunk(
    chunk_id: str,
    content: str = "Sample content",
    source_type: str = "A",
    document_id: str = "DOC",
    metadata: dict | None = None,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        source_type=source_type,
        document_id=document_id,
        document_type="Standard",
        content=content,
        metadata=metadata if metadata is not None else {"paragraph": ".1"},
        citation=f"[{chunk_id}]",
        distance=0.1,
    )


@pytest.fixture
def sample_chunks() -> list[RetrievedChunk]:
    return [
        _make_chunk("AS1105.12", content="Audit evidence requirements.", source_type="A"),
        _make_chunk("AAPL.2025.Item1A.1", content="Apple risk factors.", source_type="B"),
        _make_chunk("IA-2026-004.3.1", content="Internal audit finding.", source_type="C"),
    ]


# ---------------------------------------------------------------------------
# TestAnswerGenerator
# ---------------------------------------------------------------------------

class TestAnswerGenerator:
    def test_with_mock_client_produces_cited_answer(self, sample_chunks):
        mock = MockClient(response="See [[AS1105.12]] for the requirements.")
        gen = AnswerGenerator(llm_client=mock)
        result = SearchResult(query="What does AS 1105 require?", chunks=sample_chunks)

        answer = gen.generate(result)

        assert isinstance(answer, CitedAnswer)
        assert answer.text == "See [[AS1105.12]] for the requirements."
        assert len(answer.citations) == 1
        assert answer.citations[0].chunk_id == "AS1105.12"
        assert answer.citations[0].chunk is sample_chunks[0]
        assert answer.model == "claude-haiku-4-5"

    def test_handles_empty_chunks(self):
        mock = MockClient(response="ignored")
        gen = AnswerGenerator(llm_client=mock)
        result = SearchResult(query="What is X?", chunks=[])

        answer = gen.generate(result)

        # Mock should NOT have been called for empty chunks
        assert mock.calls == []
        assert "don't have enough information" in answer.text.lower()
        assert "what is x?" in answer.text.lower()  # query echoed
        assert answer.citations == []

    def test_resolves_multiple_citations(self, sample_chunks):
        mock = MockClient(
            response="Per [[AS1105.12]] and [[AAPL.2025.Item1A.1]], this is true."
        )
        gen = AnswerGenerator(llm_client=mock)
        result = SearchResult(query="q", chunks=sample_chunks)

        answer = gen.generate(result)

        assert len(answer.citations) == 2
        chunk_ids = [c.chunk_id for c in answer.citations]
        assert chunk_ids == ["AS1105.12", "AAPL.2025.Item1A.1"]

    def test_deduplicates_citations(self, sample_chunks):
        mock = MockClient(
            response="[[AS1105.12]] says X. [[AS1105.12]] also says Y. [[AAPL.2025.Item1A.1]] too."
        )
        gen = AnswerGenerator(llm_client=mock)
        result = SearchResult(query="q", chunks=sample_chunks)

        answer = gen.generate(result)

        # AS1105.12 appears twice in text → 1 citation
        # AAPL.2025.Item1A.1 appears once → 1 citation
        assert len(answer.citations) == 2
        assert answer.citations[0].chunk_id == "AS1105.12"
        assert answer.citations[1].chunk_id == "AAPL.2025.Item1A.1"

    def test_drops_unknown_citations(self, sample_chunks, caplog):
        """If LLM cites a chunk_id that wasn't retrieved, silently drop it."""
        mock = MockClient(
            response="[[AS1105.12]] is real but [[FAKE.123]] is hallucinated."
        )
        gen = AnswerGenerator(llm_client=mock)
        result = SearchResult(query="q", chunks=sample_chunks)

        with caplog.at_level("DEBUG", logger="src.research.answer_generator"):
            answer = gen.generate(result)

        # Only AS1105.12 in citations; FAKE.123 silently dropped
        assert len(answer.citations) == 1
        assert answer.citations[0].chunk_id == "AS1105.12"
        assert "FAKE.123" in caplog.text  # logged at debug

    def test_preserves_citation_order(self, sample_chunks):
        """Citation order = order of first appearance in the text."""
        mock = MockClient(
            response="[[IA-2026-004.3.1]] first, then [[AS1105.12]], then [[AAPL.2025.Item1A.1]]."
        )
        gen = AnswerGenerator(llm_client=mock)
        result = SearchResult(query="q", chunks=sample_chunks)

        answer = gen.generate(result)

        assert [c.chunk_id for c in answer.citations] == [
            "IA-2026-004.3.1",
            "AS1105.12",
            "AAPL.2025.Item1A.1",
        ]

    def test_passes_max_tokens_to_llm(self, sample_chunks):
        mock = MockClient(response="answer")
        gen = AnswerGenerator(llm_client=mock, max_tokens=512)
        result = SearchResult(query="q", chunks=sample_chunks)

        gen.generate(result)

        assert mock.calls[0]["max_tokens"] == 512


# ---------------------------------------------------------------------------
# TestPromptTemplate
# ---------------------------------------------------------------------------

class TestPromptTemplate:
    def test_prompt_includes_all_retrieved_chunks(self, sample_chunks):
        system, user = build_cited_answer_prompt("What is X?", sample_chunks)

        # Every chunk_id should appear in the user prompt
        for chunk in sample_chunks:
            assert chunk.chunk_id in user

    def test_prompt_includes_query(self, sample_chunks):
        system, user = build_cited_answer_prompt("What are the risk factors?", sample_chunks)
        assert "What are the risk factors?" in user

    def test_prompt_system_instructs_citation_format(self, sample_chunks):
        system, _ = build_cited_answer_prompt("q", sample_chunks)

        # System prompt should mention the [[chunk_id]] citation format
        assert "[[" in system and "]]" in system
        # And should tell the LLM not to invent chunk_ids
        assert "invent" in system.lower() or "not" in system.lower()

    def test_prompt_chunks_are_numbered(self, sample_chunks):
        _, user = build_cited_answer_prompt("q", sample_chunks)

        # Each chunk should be prefixed with a number
        for i, chunk in enumerate(sample_chunks, 1):
            assert f"{i}. [{chunk.chunk_id}]" in user

    def test_prompt_handles_newlines_in_chunk_content(self):
        chunk = _make_chunk("X.1", content="line one\n\nline two")
        _, user = build_cited_answer_prompt("q", [chunk])

        # Newlines should be collapsed so they don't break the prompt
        assert "line one line two" in user
        # No raw double-newlines in the chunk line
        chunk_line = [l for l in user.split("\n") if "[X.1]" in l][0]
        assert "\n" not in chunk_line


# ---------------------------------------------------------------------------
# TestMockClient
# ---------------------------------------------------------------------------

class TestMockClient:
    def test_returns_configured_string(self):
        mock = MockClient(response="hello world")
        assert mock.complete(system="s", user="u") == "hello world"

    def test_uses_callable_for_dynamic_responses(self):
        mock = MockClient(response=lambda s, u, t: f"echo: {u}")
        assert mock.complete(system="s", user="hi") == "echo: hi"

    def test_records_every_call(self):
        mock = MockClient(response="r")
        mock.complete("s1", "u1", max_tokens=100)
        mock.complete("s2", "u2", max_tokens=200)

        assert len(mock.calls) == 2
        assert mock.calls[0] == {"system": "s1", "user": "u1", "max_tokens": 100}
        assert mock.calls[1] == {"system": "s2", "user": "u2", "max_tokens": 200}

    def test_raises_when_configured(self):
        mock = MockClient(response="r", raise_on_call=RuntimeError("boom"))
        with pytest.raises(RuntimeError, match="boom"):
            mock.complete("s", "u")


# ---------------------------------------------------------------------------
# TestAnthropicClientEnvVar
# ---------------------------------------------------------------------------

class TestAnthropicClientEnvVar:
    def test_raises_when_no_api_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            AnthropicClient(api_key=None)

    def test_accepts_explicit_api_key(self, monkeypatch):
        """When api_key is passed explicitly, don't need env var."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        # Should not raise on construction (only on actual API call)
        client = AnthropicClient(api_key="test-key-123")
        assert client.model == AnthropicClient.DEFAULT_MODEL

    def test_uses_env_var_api_key(self, monkeypatch):
        """When env var is set, use it."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key-456")
        client = AnthropicClient()
        assert client.model == AnthropicClient.DEFAULT_MODEL
