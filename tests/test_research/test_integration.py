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
from src.research import ResearchWorkflow
from src.research.answer_generator import AnswerGenerator
from src.research.llm_client import MockClient
from src.research.workflow import ResearchWorkflow


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


class TestResearchCliSubprocess:
    """End-to-end via subprocess to verify __main__.py works."""

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
