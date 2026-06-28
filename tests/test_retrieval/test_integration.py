"""End-to-end integration tests for the retrieval layer (FEATURE-005-TASK-4).

These tests cover the full pipeline (embed → store → search → hydrate) and
the CLI entry point. Unit tests for the Retriever live in test_retriever.py
and test_router_integration.py.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.ingestion.chunkers.chunker import Chunk
from src.ingestion.embedder.embedder import Embedder
from src.ingestion.storage.chroma_store import ChromaStore
from src.ingestion.storage.json_store import JsonStore
from src.knowledge_engineering.router import Router
from src.retrieval import Retriever


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def populated_kb(temp_dir, embedder):
    """Build a complete knowledge base in a temp directory (all 3 sources).

    Returns (chroma, json_store, chunks) tuple. Uses unique collection_name
    so tests don't collide on the shared ChromaDB on-disk format.
    """
    collection_name = "integration_test"
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
            chunk_id="AS2110.5",
            source_type="A",
            document_id="AS2110",
            document_type="Standard",
            chunk_index=5,
            content="Identifying and assessing risks of material misstatement is fundamental to the audit.",
            metadata={"paragraph": ".5", "standard_id": "AS2110"},
            citation={"format": "[AS 2110 § .5]", "type": "pcaob"},
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

class TestIntegrationSearch:
    """Full pipeline: embed → store → search → assert."""

    def test_integration_search_returns_hydrated_chunks(self, populated_kb):
        chroma, json_store, _, _ = populated_kb
        retriever = Retriever(
            chroma_store=chroma, json_store=json_store,
            embedder=Embedder(), router=Router(),
        )
        result = retriever.search("audit evidence", top_k=5)

        assert len(result.chunks) > 0
        for chunk in result.chunks:
            assert chunk.content  # hydrated from JSON store
            assert chunk.citation
            assert chunk.chunk_id
            assert chunk.source_type in ("A", "B", "C")

    def test_integration_routing_to_all_sources(self, populated_kb):
        """Compliance query should pull from A+B+C via the router."""
        chroma, json_store, _, _ = populated_kb
        retriever = Retriever(
            chroma_store=chroma, json_store=json_store,
            embedder=Embedder(), router=Router(),
        )
        result = retriever.search("compliance requirements", top_k=10)

        sources = {c.source_type for c in result.chunks}
        # At minimum 2 of 3 sources should appear
        assert len(sources) >= 2
        assert result.routing is not None
        assert len(result.sources_searched) >= 2

    def test_integration_ticker_filter_narrows_to_source_b(self, populated_kb):
        chroma, json_store, _, _ = populated_kb
        retriever = Retriever(
            chroma_store=chroma, json_store=json_store,
            embedder=Embedder(), router=Router(),
        )
        result = retriever.search("risk factors", ticker="AAPL", top_k=10)

        assert len(result.chunks) > 0
        for chunk in result.chunks:
            assert chunk.source_type == "B"
            assert chunk.metadata.get("ticker") == "AAPL"

    def test_integration_standard_id_filter_narrows_to_source_a(self, populated_kb):
        chroma, json_store, _, _ = populated_kb
        retriever = Retriever(
            chroma_store=chroma, json_store=json_store,
            embedder=Embedder(), router=Router(),
        )
        result = retriever.search("audit evidence", standard_id="AS1105", top_k=10)

        assert len(result.chunks) > 0
        for chunk in result.chunks:
            assert chunk.source_type == "A"
            assert chunk.metadata.get("standard_id") == "AS1105"

    def test_integration_empty_kb_returns_empty_search_result(self, temp_dir, embedder):
        """A knowledge base with zero chunks returns an empty SearchResult, no error."""
        chroma = ChromaStore(
            persist_dir=str(Path(temp_dir) / "empty_chroma"),
            collection_name="empty_kb",
        )
        json_store = JsonStore(store_path=str(Path(temp_dir) / "empty.jsonl"))
        retriever = Retriever(
            chroma_store=chroma, json_store=json_store,
            embedder=embedder, router=Router(),
        )
        result = retriever.search("anything")

        assert result.chunks == []
        assert result.query == "anything"

    def test_integration_multi_source_aggregates_by_distance(self, populated_kb):
        """Multi-source search results are sorted globally by distance."""
        chroma, json_store, _, _ = populated_kb
        retriever = Retriever(
            chroma_store=chroma, json_store=json_store,
            embedder=Embedder(), router=Router(),
        )
        result = retriever.search("audit risk", top_k=10)

        distances = [c.distance for c in result.chunks]
        assert distances == sorted(distances)


# ---------------------------------------------------------------------------
# CLI handler unit tests
# ---------------------------------------------------------------------------

class TestCliRunSearch:
    """Test the run_search handler directly (no subprocess)."""

    def test_run_search_returns_exit_code_0_for_success(self, populated_kb):
        from src.retrieval.cli import run_search
        chroma_dir = populated_kb[0].persist_dir
        jsonl_path = populated_kb[1].store_path
        collection_name = populated_kb[3]
        code, output = run_search(
            query="audit evidence",
            chroma_dir=str(chroma_dir),
            jsonl_path=str(jsonl_path),
            collection_name=collection_name,
        )
        assert code == 0
        assert "No results found" not in output  # we expect results

    def test_run_search_empty_query_exits_2(self, populated_kb):
        from src.retrieval.cli import run_search
        chroma_dir = populated_kb[0].persist_dir
        jsonl_path = populated_kb[1].store_path
        collection_name = populated_kb[3]
        code, output = run_search(
            query="",
            chroma_dir=str(chroma_dir),
            jsonl_path=str(jsonl_path),
            collection_name=collection_name,
        )
        assert code == 2
        assert "empty" in output.lower()

    def test_run_search_invalid_where_exits_4(self, populated_kb):
        from src.retrieval.cli import run_search
        chroma_dir = populated_kb[0].persist_dir
        jsonl_path = populated_kb[1].store_path
        collection_name = populated_kb[3]
        code, output = run_search(
            query="test",
            where="not valid json",
            chroma_dir=str(chroma_dir),
            jsonl_path=str(jsonl_path),
            collection_name=collection_name,
        )
        assert code == 4
        assert "JSON" in output or "json" in output

    def test_run_search_uninitialized_kb_exits_3(self, temp_dir):
        from src.retrieval.cli import run_search
        empty_chroma_dir = str(Path(temp_dir) / "empty_chroma")
        empty_jsonl = str(Path(temp_dir) / "empty.jsonl")
        code, output = run_search(
            query="anything",
            chroma_dir=empty_chroma_dir,
            jsonl_path=empty_jsonl,
            collection_name="nonexistent_kb",
        )
        assert code == 3
        assert "ingestion" in output.lower() or "empty" in output.lower()

    def test_run_search_json_format_returns_valid_json(self, populated_kb):
        from src.retrieval.cli import run_search
        chroma_dir = populated_kb[0].persist_dir
        jsonl_path = populated_kb[1].store_path
        collection_name = populated_kb[3]
        code, output = run_search(
            query="audit",
            output_format="json",
            chroma_dir=str(chroma_dir),
            jsonl_path=str(jsonl_path),
            collection_name=collection_name,
        )
        assert code == 0
        payload = json.loads(output)
        assert "query" in payload
        assert "chunks" in payload
        assert "sources_searched" in payload


# ---------------------------------------------------------------------------
# CLI subprocess tests (true end-to-end via `python -m src.retrieval`)
# ---------------------------------------------------------------------------

@pytest.fixture
def kb_paths(populated_kb):
    """Helper: returns dict of chroma_dir, jsonl_path, and collection_name."""
    return {
        "chroma_dir": str(populated_kb[0].persist_dir),
        "jsonl_path": str(populated_kb[1].store_path),
        "collection_name": populated_kb[3],
    }


def _run_cli(args: list[str], kb_paths: dict, cwd: str = ".") -> subprocess.CompletedProcess:
    """Run python -m src.retrieval with given args."""
    cmd = [
        sys.executable, "-m", "src.retrieval",
        *args,
        "--chroma-dir", kb_paths["chroma_dir"],
        "--jsonl-path", kb_paths["jsonl_path"],
        "--collection-name", kb_paths["collection_name"],
    ]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)


class TestCliSubprocess:
    """End-to-end via subprocess to verify __main__.py works."""

    def test_cli_search_basic_invocation(self, kb_paths):
        result = _run_cli(["search", "audit evidence", "--top-k", "3"], kb_paths)
        assert result.returncode == 0, f"stderr: {result.stderr}"
        # Should print a table with header
        assert "chunk_id" in result.stdout
        assert "No results found" not in result.stdout

    def test_cli_search_json_output_is_valid(self, kb_paths):
        result = _run_cli(
            ["search", "audit", "--format", "json", "--top-k", "2"],
            kb_paths,
        )
        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert "chunks" in payload
        assert len(payload["chunks"]) <= 2

    def test_cli_search_with_ticker_filter(self, kb_paths):
        result = _run_cli(
            ["search", "risk", "--ticker", "AAPL", "--top-k", "5"],
            kb_paths,
        )
        assert result.returncode == 0
        # All returned chunks should be Source B (AAPL)
        assert "AAPL" in result.stdout or "10-K" in result.stdout

    def test_cli_search_empty_query_exits_with_error(self, kb_paths):
        # Note: argparse catches this before our handler (since query is required)
        result = subprocess.run(
            [
                sys.executable, "-m", "src.retrieval", "search",
                "--chroma-dir", kb_paths["chroma_dir"],
                "--jsonl-path", kb_paths["jsonl_path"],
                "--collection-name", kb_paths["collection_name"],
            ],
            capture_output=True, text=True,
        )
        assert result.returncode == 2  # argparse error

    def test_cli_search_invalid_where_exits_with_error(self, kb_paths):
        result = _run_cli(
            ["search", "test", "--where", "not json"],
            kb_paths,
        )
        assert result.returncode == 4
        assert "JSON" in result.stdout or "json" in result.stdout

    def test_cli_search_help_prints(self, kb_paths):
        result = _run_cli(["search", "--help"], kb_paths)
        assert result.returncode == 0
        assert "query" in result.stdout
        assert "--top-k" in result.stdout
