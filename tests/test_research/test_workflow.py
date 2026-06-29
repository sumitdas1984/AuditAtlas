"""Tests for the ResearchWorkflow orchestrator (FEATURE-006-TASK-2)."""

import logging

import pytest

from src.research import (
    AnswerGenerator,
    MockClient,
    ResearchResult,
    ResearchWorkflow,
    WorkflowError,
)
from src.retrieval import RetrievedChunk


class TestResearchWorkflowRun:
    """Happy-path and basic shape tests."""

    def test_run_returns_research_result(self, mock_retriever, mock_answer_generator):
        wf = ResearchWorkflow(
            retriever=mock_retriever, answer_generator=mock_answer_generator
        )
        result = wf.run("What are the audit evidence requirements?")

        assert isinstance(result, ResearchResult)
        assert result.query == "What are the audit evidence requirements?"
        assert result.answer.text  # non-empty
        assert result.answer.citations  # has citations
        assert result.chunks  # has retrieved chunks
        # Latency is measured: positive, with a sane upper bound (regression
        # catcher for a hang — should be sub-second for mocked workflow).
        assert 0 < result.latency_ms < 10_000

    def test_run_passes_query_and_top_k_to_retriever(
        self, mock_retriever, mock_answer_generator
    ):
        wf = ResearchWorkflow(
            retriever=mock_retriever, answer_generator=mock_answer_generator
        )
        wf.run("What about AS1105?", top_k=7)

        assert len(mock_retriever.calls) == 1
        call = mock_retriever.calls[0]
        assert call["query"] == "What about AS1105?"
        assert call["top_k"] == 7

    def test_run_forwards_retriever_kwargs(
        self, mock_retriever, mock_answer_generator
    ):
        """ticker, standard_id, where, use_router all flow through to retriever."""
        wf = ResearchWorkflow(
            retriever=mock_retriever, answer_generator=mock_answer_generator
        )
        wf.run(
            "any query",
            ticker="AAPL",
            standard_id="AS1105",
            where={"source_type": "A"},
            use_router=False,
        )

        call = mock_retriever.calls[0]
        assert call["ticker"] == "AAPL"
        assert call["standard_id"] == "AS1105"
        assert call["where"] == {"source_type": "A"}
        assert call["use_router"] is False

    def test_run_preserves_routing_and_sources(
        self, mock_retriever, mock_answer_generator
    ):
        """Routing result and sources_searched are passed through from SearchResult."""
        from src.knowledge_engineering.router import RoutingResult, SourceType
        mock_retriever.routing = RoutingResult(
            sources=[SourceType.SOURCE_A, SourceType.SOURCE_B],
            confidence=0.9,
            reasoning="test routing",
        )
        mock_retriever.sources_searched = ["A", "B"]

        wf = ResearchWorkflow(
            retriever=mock_retriever, answer_generator=mock_answer_generator
        )
        result = wf.run("query")

        assert result.routing is mock_retriever.routing
        assert result.sources_searched == ["A", "B"]


class TestResearchWorkflowErrors:
    """Error propagation tests."""

    def test_propagates_retriever_error(self, mock_retriever_raises, mock_answer_generator):
        wf = ResearchWorkflow(
            retriever=mock_retriever_raises, answer_generator=mock_answer_generator
        )
        with pytest.raises(WorkflowError, match="retrieval failed"):
            wf.run("query")

    def test_retriever_error_chains_original(self, mock_retriever_raises, mock_answer_generator):
        wf = ResearchWorkflow(
            retriever=mock_retriever_raises, answer_generator=mock_answer_generator
        )
        with pytest.raises(WorkflowError) as exc_info:
            wf.run("query")
        # Original RuntimeError is chained via __cause__
        assert isinstance(exc_info.value.__cause__, RuntimeError)
        assert "retriever boom" in str(exc_info.value.__cause__)

    def test_propagates_llm_error(self, mock_retriever):
        # LLM raises on every call
        bad_llm = MockClient(response="ignored", raise_on_call=RuntimeError("llm boom"))
        bad_gen = AnswerGenerator(llm_client=bad_llm)
        wf = ResearchWorkflow(retriever=mock_retriever, answer_generator=bad_gen)

        with pytest.raises(WorkflowError, match="answer generation failed"):
            wf.run("query")

    def test_llm_error_chains_original(self, mock_retriever):
        bad_llm = MockClient(response="ignored", raise_on_call=RuntimeError("llm boom"))
        bad_gen = AnswerGenerator(llm_client=bad_llm)
        wf = ResearchWorkflow(retriever=mock_retriever, answer_generator=bad_gen)

        with pytest.raises(WorkflowError) as exc_info:
            wf.run("query")
        assert isinstance(exc_info.value.__cause__, RuntimeError)
        assert "llm boom" in str(exc_info.value.__cause__)


class TestResearchWorkflowEmptyResults:
    """Empty SearchResult handling."""

    def test_handles_empty_chunks(self, mock_retriever_empty, mock_answer_generator):
        """When retriever returns no chunks, workflow still succeeds with graceful answer."""
        wf = ResearchWorkflow(
            retriever=mock_retriever_empty, answer_generator=mock_answer_generator
        )
        result = wf.run("anything")

        # Answer is the graceful "I don't have enough information" message
        assert "don't have enough information" in result.answer.text.lower()
        assert result.answer.citations == []
        assert result.chunks == []
        # LLM was NOT called for empty chunks (AnswerGenerator short-circuits)
        # Verify by checking the answer doesn't have any [[chunk_id]] markers
        assert "[[" not in result.answer.text

    def test_handles_empty_chunks_logs_info(self, mock_retriever_empty, mock_answer_generator, caplog):
        with caplog.at_level(logging.INFO, logger="src.research.workflow"):
            wf = ResearchWorkflow(
                retriever=mock_retriever_empty, answer_generator=mock_answer_generator
            )
            wf.run("anything")

        # Empty-chunks path still goes through start/end log records
        assert "Research started" in caplog.text
        assert "Research complete" in caplog.text


class TestResearchWorkflowLogging:
    """Verify start/end log records."""

    def test_logs_start_and_end(self, mock_retriever, mock_answer_generator, caplog):
        with caplog.at_level(logging.INFO, logger="src.research.workflow"):
            wf = ResearchWorkflow(
                retriever=mock_retriever, answer_generator=mock_answer_generator
            )
            wf.run("test query", top_k=3)

        assert "Research started" in caplog.text
        assert "Research complete" in caplog.text
        assert "test query" in caplog.text
        assert "3" in caplog.text  # top_k appears in log

    def test_logs_error_on_retrieval_failure(self, mock_retriever_raises, mock_answer_generator, caplog):
        with caplog.at_level(logging.ERROR, logger="src.research.workflow"):
            wf = ResearchWorkflow(
                retriever=mock_retriever_raises, answer_generator=mock_answer_generator
            )
            with pytest.raises(WorkflowError):
                wf.run("query")

        assert "retrieval failed" in caplog.text

    def test_logs_error_on_llm_failure(self, mock_retriever, caplog):
        bad_llm = MockClient(response="ignored", raise_on_call=RuntimeError("boom"))
        bad_gen = AnswerGenerator(llm_client=bad_llm)
        with caplog.at_level(logging.ERROR, logger="src.research.workflow"):
            wf = ResearchWorkflow(retriever=mock_retriever, answer_generator=bad_gen)
            with pytest.raises(WorkflowError):
                wf.run("query")

        assert "answer generation failed" in caplog.text


# ---------------------------------------------------------------------------
# TestResearchWorkflowEdgeCases
# ---------------------------------------------------------------------------

class TestResearchWorkflowEdgeCases:
    """Edge cases not covered by the basic / error / empty tests."""

    def test_llm_response_without_citations(self, mock_retriever):
        """LLM returns answer with no [[chunk_id]] markers — workflow still succeeds."""
        # MockClient returns a response that doesn't cite any chunk
        no_cite_llm = MockClient(
            response="Audit evidence is a key concept in PCAOB standards."
        )
        gen = AnswerGenerator(llm_client=no_cite_llm)
        wf = ResearchWorkflow(retriever=mock_retriever, answer_generator=gen)

        result = wf.run("query")
        # Result still valid; citations empty
        assert result.answer.text == "Audit evidence is a key concept in PCAOB standards."
        assert result.answer.citations == []
        # Chunks still attached
        assert len(result.chunks) > 0

    def test_chunks_attached_even_when_no_citations(self, mock_retriever):
        """When LLM doesn't cite any chunk, the chunks list is still populated
        so callers can render the full retrieval context."""
        no_cite_llm = MockClient(response="Generic answer with no citations.")
        gen = AnswerGenerator(llm_client=no_cite_llm)
        wf = ResearchWorkflow(retriever=mock_retriever, answer_generator=gen)
        result = wf.run("query")

        # chunks is the same as what retriever returned
        assert result.chunks is mock_retriever.chunks

    def test_passes_where_dict_to_retriever(self, mock_retriever, mock_answer_generator):
        """`where` dict is passed through correctly (not converted to anything)."""
        wf = ResearchWorkflow(
            retriever=mock_retriever, answer_generator=mock_answer_generator
        )
        wf.run("query", where={"source_type": "A", "ticker": "AAPL"})

        call = mock_retriever.calls[0]
        assert call["where"] == {"source_type": "A", "ticker": "AAPL"}

    def test_passes_use_router_false_to_retriever(self, mock_retriever, mock_answer_generator):
        wf = ResearchWorkflow(
            retriever=mock_retriever, answer_generator=mock_answer_generator
        )
        wf.run("query", use_router=False)
        assert mock_retriever.calls[0]["use_router"] is False

    def test_retriever_with_one_chunk(self, mock_answer_generator):
        """Single-chunk retrieval still works end-to-end."""
        from src.retrieval.models import SearchResult

        class OneChunkRetriever:
            def search(self, *, query, top_k, **kwargs):
                chunk = RetrievedChunk(
                    chunk_id="AS1105.12", source_type="A", document_id="AS1105",
                    document_type="Standard", content="Only chunk.",
                    metadata={}, citation="[AS 1105 § .12]", distance=0.1,
                )
                return SearchResult(query=query, chunks=[chunk], sources_searched=["A"])

        wf = ResearchWorkflow(
            retriever=OneChunkRetriever(), answer_generator=mock_answer_generator
        )
        result = wf.run("query")
        assert len(result.chunks) == 1
