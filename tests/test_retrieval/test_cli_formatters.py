"""Direct unit tests for CLI formatters and helpers (FEATURE-005-TASK-4).

Integration-level CLI tests live in test_integration.py. This file covers
the pure functions (formatters, content preview, KB health check) in isolation
so their behavior is locked down regardless of how the rest of the CLI changes.
"""

import json
from pathlib import Path

import pytest

from src.knowledge_engineering.router import RoutingResult, SourceType
from src.retrieval import RetrievedChunk
from src.retrieval.cli import (
    CONTENT_PREVIEW_CHARS,
    _check_kb_initialized,
    _content_preview,
    _format_json,
    _format_table,
)
from src.retrieval.models import SearchResult


def _make_chunk(
    chunk_id: str = "X.1",
    source_type: str = "A",
    content: str = "short content",
    distance: float = 0.1,
    citation: str = "[X § .1]",
    metadata: dict | None = None,
    document_id: str = "X",
    document_type: str = "Standard",
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        source_type=source_type,
        document_id=document_id,
        document_type=document_type,
        content=content,
        metadata=metadata if metadata is not None else {"paragraph": ".1"},
        citation=citation,
        distance=distance,
    )


# ---------------------------------------------------------------------------
# _content_preview
# ---------------------------------------------------------------------------

class TestContentPreview:
    def test_short_content_returned_unchanged(self):
        assert _content_preview("hello", show_content=True) == "hello"

    def test_exact_limit_returned_unchanged(self):
        text = "x" * CONTENT_PREVIEW_CHARS
        assert _content_preview(text, show_content=True) == text

    def test_long_content_truncated_with_ellipsis(self):
        text = "x" * (CONTENT_PREVIEW_CHARS + 50)
        result = _content_preview(text, show_content=True)
        assert result.endswith("...")
        assert len(result) == CONTENT_PREVIEW_CHARS

    def test_show_content_false_returns_empty(self):
        assert _content_preview("anything", show_content=False) == ""

    def test_show_content_false_ignores_long_content(self):
        """show_content=False short-circuits, no truncation needed."""
        long_text = "x" * 10000
        assert _content_preview(long_text, show_content=False) == ""

    def test_empty_content(self):
        assert _content_preview("", show_content=True) == ""


# ---------------------------------------------------------------------------
# _format_table
# ---------------------------------------------------------------------------

class TestFormatTable:
    def test_empty_chunks_returns_no_results_message(self):
        result = SearchResult(query="q")
        assert _format_table(result) == "No results found."

    def test_single_chunk_produces_header_and_row(self):
        chunk = _make_chunk(chunk_id="AS1105.12", content="audit evidence")
        result = SearchResult(query="q", chunks=[chunk])
        output = _format_table(result)

        assert "chunk_id" in output  # header
        assert "AS1105.12" in output  # chunk id
        assert "audit evidence" in output  # content
        assert "No results found" not in output

    def test_multiple_chunks_appear_in_order(self):
        chunks = [
            _make_chunk(chunk_id="A.1", distance=0.1),
            _make_chunk(chunk_id="B.1", distance=0.2),
        ]
        result = SearchResult(query="q", chunks=chunks)
        output = _format_table(result)

        a_pos = output.index("A.1")
        b_pos = output.index("B.1")
        assert a_pos < b_pos

    def test_sources_searched_in_footer(self):
        result = SearchResult(query="q", chunks=[_make_chunk()], sources_searched=["A", "B", "C"])
        output = _format_table(result)
        assert "Sources searched: ['A', 'B', 'C']" in output

    def test_routing_reasoning_in_footer(self):
        routing = RoutingResult(
            sources=[SourceType.SOURCE_A],
            confidence=0.9,
            reasoning="Topic X -> A",
        )
        result = SearchResult(query="q", chunks=[_make_chunk()], routing=routing)
        output = _format_table(result)
        assert "Routing: Topic X -> A" in output

    def test_show_content_false_omits_content_column_data(self):
        chunk = _make_chunk(content="secret content")
        result = SearchResult(query="q", chunks=[chunk])
        output = _format_table(result, show_content=False)

        # Column header is still present (structural), but content value is empty
        assert "secret content" not in output
        assert "content" in output  # header still there

    def test_distance_formatted_to_4_decimals(self):
        chunk = _make_chunk(distance=0.123456789)
        result = SearchResult(query="q", chunks=[chunk])
        output = _format_table(result)
        assert "0.1235" in output

    def test_long_content_truncated_in_table(self):
        long_content = "x" * 500
        chunk = _make_chunk(content=long_content)
        result = SearchResult(query="q", chunks=[chunk])
        output = _format_table(result)

        # The 500-char content should be truncated in the table view (max 80 chars per column)
        assert "x" * 500 not in output


# ---------------------------------------------------------------------------
# _format_json
# ---------------------------------------------------------------------------

class TestFormatJson:
    def test_empty_chunks_produces_valid_json(self):
        result = SearchResult(query="q")
        output = _format_json(result)

        payload = json.loads(output)
        assert payload["query"] == "q"
        assert payload["chunks"] == []
        assert payload["sources_searched"] == []

    def test_chunk_fields_all_serialized(self):
        chunk = _make_chunk(
            chunk_id="AS1105.12",
            content="audit evidence",
            distance=0.123,
            metadata={"paragraph": ".12", "standard_id": "AS1105"},
        )
        result = SearchResult(query="q", chunks=[chunk])
        output = _format_json(result)

        payload = json.loads(output)
        assert len(payload["chunks"]) == 1
        c = payload["chunks"][0]
        assert c["chunk_id"] == "AS1105.12"
        assert c["source_type"] == "A"
        assert c["content"] == "audit evidence"
        assert c["distance"] == 0.123
        assert c["metadata"]["standard_id"] == "AS1105"
        assert c["citation"] == "[X § .1]"

    def test_routing_serialized_when_present(self):
        routing = RoutingResult(
            sources=[SourceType.SOURCE_A, SourceType.SOURCE_B],
            confidence=0.8,
            reasoning="mixed",
        )
        result = SearchResult(query="q", chunks=[_make_chunk()], routing=routing)
        output = _format_json(result)

        payload = json.loads(output)
        assert payload["routing"]["sources"] == ["A", "B"]
        assert payload["routing"]["confidence"] == 0.8
        assert payload["routing"]["reasoning"] == "mixed"

    def test_routing_absent_when_none(self):
        result = SearchResult(query="q", chunks=[_make_chunk()])
        output = _format_json(result)

        payload = json.loads(output)
        assert "routing" not in payload

    def test_sources_searched_serialized(self):
        result = SearchResult(
            query="q",
            chunks=[_make_chunk()],
            sources_searched=["A", "C"],
        )
        payload = json.loads(_format_json(result))
        assert payload["sources_searched"] == ["A", "C"]


# ---------------------------------------------------------------------------
# _check_kb_initialized
# ---------------------------------------------------------------------------

class TestCheckKbInitialized:
    def test_empty_collection_returns_false_with_message(self, temp_dir, embedder):
        from src.ingestion.storage.chroma_store import ChromaStore
        from src.ingestion.storage.json_store import JsonStore
        from src.ingestion.embedder.embedder import Embedder
        from src.retrieval import Retriever

        chroma = ChromaStore(
            persist_dir=str(Path(temp_dir) / "empty"),
            collection_name="empty_kb_test",
        )
        retriever = Retriever(
            chroma_store=chroma, json_store=JsonStore(), embedder=embedder,
        )

        is_init, msg = _check_kb_initialized(retriever)
        assert is_init is False
        assert "ingestion" in msg.lower()

    def test_populated_collection_returns_true(self, populated_stores):
        from src.ingestion.embedder.embedder import Embedder
        from src.retrieval import Retriever

        chroma, json_store, _ = populated_stores
        retriever = Retriever(
            chroma_store=chroma, json_store=json_store, embedder=Embedder(),
        )
        is_init, msg = _check_kb_initialized(retriever)
        assert is_init is True
        assert msg == ""


# ---------------------------------------------------------------------------
# run_search edge cases
# ---------------------------------------------------------------------------

class TestRunSearchEdgeCases:
    def test_where_json_must_be_object_not_list(self, populated_stores):
        from src.retrieval.cli import run_search
        chroma = populated_stores[0]
        json_store = populated_stores[1]
        collection_name = chroma.collection_name

        code, output = run_search(
            query="x",
            where="[1, 2, 3]",  # valid JSON but not a dict
            chroma_dir=str(chroma.persist_dir),
            jsonl_path=str(json_store.store_path),
            collection_name=collection_name,
        )
        assert code == 4
        assert "JSON object" in output

    def test_where_json_must_be_object_not_string(self, populated_stores):
        from src.retrieval.cli import run_search
        chroma = populated_stores[0]
        json_store = populated_stores[1]
        collection_name = chroma.collection_name

        code, output = run_search(
            query="x",
            where='"a string"',
            chroma_dir=str(chroma.persist_dir),
            jsonl_path=str(json_store.store_path),
            collection_name=collection_name,
        )
        assert code == 4
        assert "JSON object" in output

    def test_unknown_output_format_returns_exit_1(self, populated_stores):
        from src.retrieval.cli import run_search
        chroma = populated_stores[0]
        json_store = populated_stores[1]
        collection_name = chroma.collection_name

        code, output = run_search(
            query="x",
            output_format="yaml",  # not in (table, json)
            chroma_dir=str(chroma.persist_dir),
            jsonl_path=str(json_store.store_path),
            collection_name=collection_name,
        )
        assert code == 1
        assert "unknown" in output.lower() or "format" in output.lower()

    def test_whitespace_only_query_treated_as_empty(self, populated_stores):
        from src.retrieval.cli import run_search
        chroma = populated_stores[0]
        json_store = populated_stores[1]
        collection_name = chroma.collection_name

        code, output = run_search(
            query="   \t  ",  # whitespace only
            chroma_dir=str(chroma.persist_dir),
            jsonl_path=str(json_store.store_path),
            collection_name=collection_name,
        )
        assert code == 2
        assert "empty" in output.lower()
