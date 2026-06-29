"""End-to-end integration tests for the research CLI (FEATURE-006-TASK-3)."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.ingestion.chunkers.chunker import Chunk
from src.ingestion.embedder.embedder import Embedder
from src.ingestion.storage.chroma_store import ChromaStore
from src.ingestion.storage.json_store import JsonStore
from src.research import ResearchResult, ResearchWorkflow
from src.research.answer_generator import AnswerGenerator
from src.research.llm_client import MockClient
from src.research.workflow import ResearchWorkflow
from src.retrieval import RetrievedChunk


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def populated_kb(temp_dir, embedder):
    """Build a small KB in a temp directory (all 3 sources, 1 chunk each)."""
    collection_name = "research_integration_test"
    chroma = ChromaStore(
        persist_dir=str(Path(temp_dir) / "chroma"),
        collection_name=collection_name,
    )
    json_store = JsonStore(store_path=str(Path(temp_dir) / "chunks.jsonl"))

    chunks = [
        Chunk(
            chunk_id="AS1105.12",
            source_type="A",
            document_id="AS1105",
            document_type="Standard",
            chunk_index=12,
            content="The auditor must obtain sufficient appropriate audit evidence to support the audit opinion.",
            metadata={"paragraph": ".12", "standard_id": "AS1105"},
            citation={"format": "[AS 1105 § .12]", "type": "pcaob"},
        ),
        Chunk(
            chunk_id="AAPL.2025.Item1A.1",
            source_type="B",
            document_id="AAPL",
            document_type="10-K",
            chunk_index=1,
            content="Risk factors include supply chain disruption, regulatory scrutiny, and cybersecurity threats.",
            metadata={"ticker": "AAPL", "fiscal_year": "2025", "item": "Item 1A"},
            citation={"format": "[AAPL 10-K, Item 1A (2025)]", "type": "sec"},
        ),
        Chunk(
            chunk_id="IA-2026-004.3.1",
            source_type="C",
            document_id="IA-2026-004",
            document_type="InternalAuditReport",
            chunk_index=1,
            content="Finding 2025-H-001: E-Commerce Payment Reconciliation Gap. Severity: High.",
            metadata={"heading": "Finding 2025-H-001", "classification": "InternalConfidential"},
            citation={"format": "[InternalAuditReport:2025-H-001]", "type": "synthetic"},
        ),
    ]
    chroma.add(chunks, embedder)
    json_store.write_batch(chunks)
    return chroma, json_store, chunks, collection_name


# ---------------------------------------------------------------------------
# End-to-end integration tests
# ---------------------------------------------------------------------------

class TestResearchWorkflowE2E:
    """Full pipeline: build KB → workflow.run → assert result."""

    def test_e2e_compliance_query(self, populated_kb):
        """Compliance query should pull from multiple sources via the router."""
        chroma, json_store, _, _ = populated_kb
        from src.knowledge_engineering.router import Router
        from src.retrieval import Retriever
        retriever = Retriever(
            chroma_store=chroma, json_store=json_store,
            embedder=Embedder(), router=Router(),
        )
        workflow = ResearchWorkflow(
            retriever=retriever,
            answer_generator=AnswerGenerator(
                llm_client=MockClient(response="Per [[AS1105.12]] and [[AAPL.2025.Item1A.1]], compliance requires both.")
            ),
        )
        result = workflow.run("compliance requirements", top_k=5)

        assert result.query == "compliance requirements"
        assert result.answer.text  # non-empty
        assert len(result.answer.citations) == 2
        assert result.latency_ms > 0
        # Router should have run
        assert result.routing is not None

    def test_e2e_with_ticker_filter(self, populated_kb):
        """Ticker filter narrows to Source B."""
        chroma, json_store, _, _ = populated_kb
        from src.knowledge_engineering.router import Router
        from src.retrieval import Retriever
        retriever = Retriever(
            chroma_store=chroma, json_store=json_store,
            embedder=Embedder(), router=Router(),
        )
        workflow = ResearchWorkflow(
            retriever=retriever,
            answer_generator=AnswerGenerator(
                llm_client=MockClient(response="See [[AAPL.2025.Item1A.1]].")
            ),
        )
        result = workflow.run("risk factors", ticker="AAPL")

        for chunk in result.chunks:
            assert chunk.source_type == "B"
            assert chunk.metadata.get("ticker") == "AAPL"

    def test_e2e_empty_kb_returns_graceful_answer(self, temp_dir, embedder):
        """KB with zero chunks → graceful 'I don't have enough information'."""
        chroma = ChromaStore(
            persist_dir=str(Path(temp_dir) / "empty_chroma"),
            collection_name="empty_kb",
        )
        json_store = JsonStore(store_path=str(Path(temp_dir) / "empty.jsonl"))
        from src.retrieval import Retriever
        retriever = Retriever(
            chroma_store=chroma, json_store=json_store,
            embedder=embedder,
        )
        workflow = ResearchWorkflow(
            retriever=retriever,
            answer_generator=AnswerGenerator(llm_client=MockClient()),
        )
        result = workflow.run("anything")

        assert "don't have enough information" in result.answer.text.lower()
        assert result.answer.citations == []


# ---------------------------------------------------------------------------
# CLI handler unit tests (no subprocess)
# ---------------------------------------------------------------------------

class TestResearchRunResearch:
    """Test the run_research handler directly."""

    def test_run_research_returns_exit_0_for_success(self, populated_kb):
        from src.research.cli import run_research
        chroma, json_store, _, collection_name = populated_kb
        code, output = run_research(
            query="audit evidence",
            use_mock_llm=True,
            chroma_dir=str(chroma.persist_dir),
            collection_name=collection_name,
            jsonl_path=str(json_store.store_path),
        )
        assert code == 0
        # Mock LLM default response is shown
        assert "Mock LLM response" in output
        assert "Sources searched:" in output  # footer is always present

    def test_run_research_empty_query_exits_2(self, populated_kb):
        from src.research.cli import run_research
        chroma, json_store, _, collection_name = populated_kb
        code, output = run_research(
            query="",
            use_mock_llm=True,
            chroma_dir=str(chroma.persist_dir),
            collection_name=collection_name,
            jsonl_path=str(json_store.store_path),
        )
        assert code == 2
        assert "empty" in output.lower()

    def test_run_research_invalid_where_exits_4(self, populated_kb):
        from src.research.cli import run_research
        chroma, json_store, _, collection_name = populated_kb
        code, output = run_research(
            query="x",
            where="not json",
            use_mock_llm=True,
            chroma_dir=str(chroma.persist_dir),
            collection_name=collection_name,
            jsonl_path=str(json_store.store_path),
        )
        assert code == 4
        assert "JSON" in output or "json" in output

    def test_run_research_uninitialized_kb_exits_3(self, temp_dir):
        from src.research.cli import run_research
        empty_chroma = str(Path(temp_dir) / "empty_chroma")
        empty_jsonl = str(Path(temp_dir) / "empty.jsonl")
        code, output = run_research(
            query="x",
            use_mock_llm=True,
            chroma_dir=empty_chroma,
            collection_name="nonexistent",
            jsonl_path=empty_jsonl,
        )
        assert code == 3
        assert "ingestion" in output.lower() or "empty" in output.lower()

    def test_run_research_json_format_returns_valid_json(self, populated_kb):
        from src.research.cli import run_research
        chroma, json_store, _, collection_name = populated_kb
        code, output = run_research(
            query="audit",
            output_format="json",
            use_mock_llm=True,
            chroma_dir=str(chroma.persist_dir),
            collection_name=collection_name,
            jsonl_path=str(json_store.store_path),
        )
        assert code == 0
        payload = json.loads(output)
        assert "query" in payload
        assert "answer" in payload
        assert "chunks" in payload
        assert "latency_ms" in payload

    def test_run_research_use_mock_llm_skips_api_key(self, populated_kb, monkeypatch):
        """--use-mock-llm works even when ANTHROPIC_API_KEY is unset."""
        from src.research.cli import run_research
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        chroma, json_store, _, collection_name = populated_kb
        code, output = run_research(
            query="x",
            use_mock_llm=True,
            chroma_dir=str(chroma.persist_dir),
            collection_name=collection_name,
            jsonl_path=str(json_store.store_path),
        )
        # No API key error since mock LLM is used
        assert code == 0

    def test_run_research_without_mock_llm_requires_api_key(self, populated_kb, monkeypatch):
        """Without --use-mock-llm and no API key, returns exit 5 with clear error."""
        from src.research.cli import run_research
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        chroma, json_store, _, collection_name = populated_kb
        code, output = run_research(
            query="x",
            use_mock_llm=False,
            chroma_dir=str(chroma.persist_dir),
            collection_name=collection_name,
            jsonl_path=str(json_store.store_path),
        )
        assert code == 5
        assert "ANTHROPIC_API_KEY" in output


# ---------------------------------------------------------------------------
# CLI subprocess tests (true end-to-end via `python -m src.research`)
# ---------------------------------------------------------------------------

@pytest.fixture
def kb_paths(populated_kb):
    return {
        "chroma_dir": str(populated_kb[0].persist_dir),
        "jsonl_path": str(populated_kb[1].store_path),
        "collection_name": populated_kb[3],
    }


def _run_cli(args: list[str], kb_paths: dict, cwd: str = ".") -> subprocess.CompletedProcess:
    cmd = [
        sys.executable, "-m", "src.research",
        *args,
        "--chroma-dir", kb_paths["chroma_dir"],
        "--collection-name", kb_paths["collection_name"],
        "--jsonl-path", kb_paths["jsonl_path"],
    ]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)


@pytest.mark.slow
class TestResearchCliSubprocess:
    """End-to-end via subprocess to verify __main__.py works.

    Each test spawns a fresh `python -m src.research` subprocess, paying the
    cost of importing chromadb + sentence-transformers (~5-15s per test).
    Marked `slow` so CI can skip via `pytest -m "not slow"`; locally these
    still run to verify the wiring layer.
    """

    def test_cli_workflow_basic_invocation(self, kb_paths):
        result = _run_cli(
            ["workflow", "audit evidence", "--top-k", "3", "--use-mock-llm"],
            kb_paths,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        # Text format shows mock response and footer
        assert "Mock LLM response" in result.stdout
        assert "Sources searched:" in result.stdout

    def test_cli_workflow_json_output_is_valid(self, kb_paths):
        result = _run_cli(
            ["workflow", "audit", "--format", "json", "--use-mock-llm"],
            kb_paths,
        )
        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert "answer" in payload
        assert "chunks" in payload
        assert "latency_ms" in payload

    def test_cli_workflow_with_ticker_filter(self, kb_paths):
        result = _run_cli(
            ["workflow", "risk", "--ticker", "AAPL", "--use-mock-llm"],
            kb_paths,
        )
        assert result.returncode == 0
        # With ticker filter, sources_searched is just ['B']
        assert "Sources searched: ['B']" in result.stdout
        # Chunks include AAPL content (verify via JSON output for clarity)
        result_json = _run_cli(
            ["workflow", "risk", "--ticker", "AAPL", "--use-mock-llm", "--format", "json"],
            kb_paths,
        )
        payload = json.loads(result_json.stdout)
        assert any("AAPL" in c["chunk_id"] for c in payload["chunks"])

    def test_cli_workflow_use_mock_llm_no_api_key(self, kb_paths, monkeypatch):
        """--use-mock-llm works without ANTHROPIC_API_KEY env var."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = _run_cli(
            ["workflow", "test", "--use-mock-llm"],
            kb_paths,
        )
        assert result.returncode == 0

    def test_cli_workflow_without_mock_llm_fails_without_api_key(self, kb_paths, monkeypatch):
        """No --use-mock-llm + no API key → exit 5."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = _run_cli(
            ["workflow", "test"],  # no --use-mock-llm
            kb_paths,
        )
        assert result.returncode == 5
        assert "ANTHROPIC_API_KEY" in result.stdout

    def test_cli_workflow_empty_query_exits_2(self, kb_paths):
        # argparse catches missing required arg → exit 2
        result = subprocess.run(
            [
                sys.executable, "-m", "src.research", "workflow",
                "--chroma-dir", kb_paths["chroma_dir"],
                "--collection-name", kb_paths["collection_name"],
                "--jsonl-path", kb_paths["jsonl_path"],
            ],
            capture_output=True, text=True,
        )
        assert result.returncode == 2  # argparse error

    def test_cli_workflow_invalid_where_exits_4(self, kb_paths):
        result = _run_cli(
            ["workflow", "test", "--where", "not json", "--use-mock-llm"],
            kb_paths,
        )
        assert result.returncode == 4
        assert "JSON" in result.stdout or "json" in result.stdout

    def test_cli_workflow_help_prints(self, kb_paths):
        result = _run_cli(["workflow", "--help"], kb_paths)
        assert result.returncode == 0
        assert "query" in result.stdout
        assert "--top-k" in result.stdout
        assert "--use-mock-llm" in result.stdout


# ---------------------------------------------------------------------------
# TestFormatText (direct unit tests for _format_text)
# ---------------------------------------------------------------------------

class TestFormatText:
    """Direct tests for the _format_text formatter (no subprocess)."""

    def test_empty_citations_omits_sources_section(self):
        from src.research.cli import _format_text
        from src.research.models import CitedAnswer
        result = ResearchResult(
            query="q",
            answer=CitedAnswer(text="no citations here", model="m"),
        )
        output = _format_text(result)
        assert "no citations here" in output
        assert "Sources:" not in output  # no citations → no Sources: section

    def test_includes_numbered_citations(self):
        from src.research.cli import _format_text
        from src.research.models import CitedAnswer, Citation
        chunk = RetrievedChunk(
            chunk_id="AS1105.12", source_type="A", document_id="AS1105",
            document_type="Standard", content="text", metadata={},
            citation="[AS 1105 § .12]", distance=0.1,
        )
        result = ResearchResult(
            query="q",
            answer=CitedAnswer(
                text="answer",
                citations=[Citation(marker="[[AS1105.12]]", chunk_id="AS1105.12", chunk=chunk)],
                model="m",
            ),
        )
        output = _format_text(result)
        assert "[1] [AS 1105 § .12]" in output

    def test_includes_footer_with_sources_and_latency(self):
        from src.research.cli import _format_text
        from src.research.models import CitedAnswer
        result = ResearchResult(
            query="q",
            answer=CitedAnswer(text="a", model="m"),
            sources_searched=["A", "B"],
            latency_ms=123.0,
        )
        output = _format_text(result)
        assert "Sources searched: ['A', 'B']" in output
        assert "Latency: 123ms" in output

    def test_omits_footer_when_fields_empty(self):
        from src.research.cli import _format_text
        from src.research.models import CitedAnswer
        result = ResearchResult(
            query="q",
            answer=CitedAnswer(text="a", model="m"),
        )
        output = _format_text(result)
        assert "Sources searched:" not in output
        assert "Latency:" not in output
        assert "Routing:" not in output

    def test_newlines_in_answer_text_are_collapsed(self):
        """Whitespace in answer text is sanitized so layout doesn't break."""
        from src.research.cli import _format_text
        from src.research.models import CitedAnswer
        result = ResearchResult(
            query="q",
            answer=CitedAnswer(text="line one\n\nline two", model="m"),
        )
        output = _format_text(result)
        # The line containing "line one" should not have raw \n
        for line in output.split("\n"):
            if "line one" in line:
                assert "\n" not in line
        # The text should be flattened
        assert "line one line two" in output

    def test_unicode_in_answer_text_preserved(self):
        """ensure_ascii=False → em dashes and smart quotes appear literally."""
        from src.research.cli import _format_text
        from src.research.models import CitedAnswer
        result = ResearchResult(
            query="q",
            answer=CitedAnswer(text="Northwind — IFRS-15", model="m"),
        )
        output = _format_text(result)
        assert "— IFRS-15" in output  # em dash literal
        assert "\\u2014" not in output  # no escape sequence


# ---------------------------------------------------------------------------
# TestFormatJson (direct unit tests for _format_json)
# ---------------------------------------------------------------------------

class TestFormatJson:
    """Direct tests for the _format_json formatter."""

    def test_empty_chunks_produces_valid_json(self):
        from src.research.cli import _format_json
        from src.research.models import CitedAnswer
        result = ResearchResult(
            query="q",
            answer=CitedAnswer(text="a", model="m"),
        )
        payload = json.loads(_format_json(result))
        assert payload["query"] == "q"
        assert payload["chunks"] == []
        assert payload["answer"]["citations"] == []

    def test_round_trip_with_all_fields(self):
        from src.research.cli import _format_json
        from src.research.models import CitedAnswer, Citation
        from src.knowledge_engineering.router import RoutingResult, SourceType
        chunk = RetrievedChunk(
            chunk_id="X.1", source_type="A", document_id="X",
            document_type="Standard", content="text", metadata={},
            citation="[X]", distance=0.1,
        )
        result = ResearchResult(
            query="q",
            answer=CitedAnswer(
                text="a",
                citations=[Citation(marker="[[X.1]]", chunk_id="X.1", chunk=chunk)],
                model="m",
            ),
            chunks=[chunk],
            routing=RoutingResult(
                sources=[SourceType.SOURCE_A, SourceType.SOURCE_B],
                confidence=0.9,
                reasoning="test",
            ),
            sources_searched=["A", "B"],
            latency_ms=42.0,
        )
        payload = json.loads(_format_json(result))
        assert payload["query"] == "q"
        assert payload["answer"]["text"] == "a"
        assert payload["answer"]["citations"][0]["chunk_id"] == "X.1"
        assert len(payload["chunks"]) == 1
        assert payload["routing"]["sources"] == ["A", "B"]
        assert payload["routing"]["confidence"] == 0.9
        assert payload["sources_searched"] == ["A", "B"]
        assert payload["latency_ms"] == 42.0

    def test_routing_absent_when_none(self):
        from src.research.cli import _format_json
        from src.research.models import CitedAnswer
        result = ResearchResult(
            query="q",
            answer=CitedAnswer(text="a", model="m"),
        )
        payload = json.loads(_format_json(result))
        assert "routing" not in payload

    def test_unicode_preserved_in_json(self):
        from src.research.cli import _format_json
        from src.research.models import CitedAnswer
        result = ResearchResult(
            query="q",
            answer=CitedAnswer(text="Northwind — IFRS-15", model="m"),
        )
        output = _format_json(result)
        assert "— IFRS-15" in output
        assert "\\u2014" not in output


# ---------------------------------------------------------------------------
# TestMainEntry (direct unit tests for main() argparse)
# ---------------------------------------------------------------------------

class TestMainEntry:
    """Direct tests for the main() argparse entry point."""

    def test_main_no_command_prints_help(self, capsys):
        from src.research.cli import main
        exit_code = main([])
        captured = capsys.readouterr()
        # No command → prints help, returns 0
        assert exit_code == 0
        assert "workflow" in captured.out  # help mentions the subcommand

    def test_main_workflow_delegates_to_run_research(self, populated_kb, monkeypatch, capsys):
        """workflow subcommand triggers run_research with parsed args."""
        from src.research.cli import main
        chroma, json_store, _, collection_name = populated_kb

        # Capture run_research calls
        captured_args = {}
        original_run_research = main.__globals__["run_research"]

        def fake_run_research(**kwargs):
            captured_args.update(kwargs)
            return 0, "fake output"

        monkeypatch.setattr("src.research.cli.run_research", fake_run_research)

        exit_code = main([
            "workflow", "test query",
            "--top-k", "3",
            "--ticker", "AAPL",
            "--use-mock-llm",
            "--format", "json",
            "--chroma-dir", str(chroma.persist_dir),
            "--collection-name", collection_name,
            "--jsonl-path", str(json_store.store_path),
        ])
        assert exit_code == 0
        # Check the kwargs that were passed
        assert captured_args["query"] == "test query"
        assert captured_args["top_k"] == 3
        assert captured_args["ticker"] == "AAPL"
        assert captured_args["use_mock_llm"] is True
        assert captured_args["output_format"] == "json"
        assert captured_args["chroma_dir"] == str(chroma.persist_dir)
        assert captured_args["collection_name"] == collection_name
        assert captured_args["jsonl_path"] == str(json_store.store_path)


# ---------------------------------------------------------------------------
# TestRunResearchAdditional (additional edge cases)
# ---------------------------------------------------------------------------

class TestRunResearchAdditional:
    """Edge cases for run_research not covered by the basic suite."""

    def test_workflow_error_returns_exit_5(self, populated_kb):
        """If the workflow raises WorkflowError, run_research returns exit 5."""
        from src.research.cli import run_research
        from src.research import WorkflowError
        from unittest.mock import patch

        chroma, json_store, _, collection_name = populated_kb

        # Patch the workflow's run() to raise WorkflowError
        with patch.object(ResearchWorkflow, "run") as mock_run:
            mock_run.side_effect = WorkflowError("test workflow failure")
            code, output = run_research(
                query="x",
                use_mock_llm=True,
                chroma_dir=str(chroma.persist_dir),
                collection_name=collection_name,
                jsonl_path=str(json_store.store_path),
            )
        assert code == 5
        assert "test workflow failure" in output

    def test_default_top_k_is_5(self, populated_kb):
        """When top_k not specified, default 5 is used."""
        from src.research.cli import run_research
        from src.research.models import CitedAnswer
        from unittest.mock import patch

        chroma, json_store, _, collection_name = populated_kb

        with patch.object(ResearchWorkflow, "run") as mock_run:
            mock_run.return_value = ResearchResult(
                query="x",
                answer=CitedAnswer(text="a", model="m"),
            )
            run_research(
                query="x",
                use_mock_llm=True,
                chroma_dir=str(chroma.persist_dir),
                collection_name=collection_name,
                jsonl_path=str(json_store.store_path),
            )
        # run_research called with top_k=5
        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs.get("top_k") == 5

    def test_ticker_and_standard_id_both_passed(self, populated_kb):
        """Both ticker and standard_id flow through to workflow.run."""
        from src.research.cli import run_research
        from src.research.models import CitedAnswer
        from unittest.mock import patch

        chroma, json_store, _, collection_name = populated_kb

        with patch.object(ResearchWorkflow, "run") as mock_run:
            mock_run.return_value = ResearchResult(
                query="x",
                answer=CitedAnswer(text="a", model="m"),
            )
            run_research(
                query="x",
                use_mock_llm=True,
                ticker="AAPL",
                standard_id="AS1105",
                chroma_dir=str(chroma.persist_dir),
                collection_name=collection_name,
                jsonl_path=str(json_store.store_path),
            )
        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs.get("ticker") == "AAPL"
        assert call_kwargs.get("standard_id") == "AS1105"
