"""Shared fixtures for research tests."""

import pytest

from src.ingestion.chunkers.chunker import Chunk
from src.ingestion.embedder.embedder import Embedder
from src.ingestion.storage.chroma_store import ChromaStore
from src.ingestion.storage.json_store import JsonStore
from src.knowledge_engineering.router import Router
from src.retrieval import Retriever, RetrievedChunk
from src.research import AnswerGenerator, MockClient


@pytest.fixture
def temp_dir():
    import tempfile
    import shutil
    from pathlib import Path
    d = tempfile.mkdtemp()
    yield d
    try:
        shutil.rmtree(d)
    except Exception:
        pass


@pytest.fixture
def embedder():
    return Embedder()


def _make_chunk(
    chunk_id: str,
    content: str = "Sample content",
    source_type: str = "A",
    document_id: str = "DOC",
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        source_type=source_type,
        document_id=document_id,
        document_type="Standard",
        content=content,
        metadata={"paragraph": ".1"},
        citation=f"[{chunk_id}]",
        distance=0.1,
    )


@pytest.fixture
def sample_chunks() -> list[RetrievedChunk]:
    """Three chunks covering all sources — used as fixture data."""
    return [
        _make_chunk("AS1105.12", content="Audit evidence requirements.", source_type="A"),
        _make_chunk("AAPL.2025.Item1A.1", content="Apple risk factors.", source_type="B"),
        _make_chunk("IA-2026-004.3.1", content="Internal audit finding.", source_type="C"),
    ]


@pytest.fixture
def mock_llm():
    """Default MockClient returning a canned answer that cites a chunk."""
    return MockClient(response="Per [[AS1105.12]], evidence is required.")


@pytest.fixture
def mock_answer_generator(mock_llm):
    """AnswerGenerator wired to a MockClient (no API key needed)."""
    return AnswerGenerator(llm_client=mock_llm)


@pytest.fixture
def mock_retriever(sample_chunks):
    """A Retriever with a stubbed search() that returns a prebuilt SearchResult.

    Bypasses real ChromaDB; tests that need a real KB should build their own.
    """
    from src.retrieval.models import SearchResult

    class _StubRetriever:
        def __init__(self, chunks, routing=None, sources_searched=None):
            self.chunks = chunks
            self.routing = routing
            self.sources_searched = sources_searched or []
            self.calls = []  # record call args for assertion

        def search(self, *, query, top_k, **kwargs):
            self.calls.append({
                "query": query,
                "top_k": top_k,
                **kwargs,
            })
            return SearchResult(
                query=query,
                chunks=self.chunks,
                routing=self.routing,
                sources_searched=self.sources_searched,
            )

    return _StubRetriever(sample_chunks)


@pytest.fixture
def mock_retriever_empty():
    """A Retriever stub that returns an empty SearchResult."""
    from src.retrieval.models import SearchResult

    class _StubRetriever:
        def search(self, *, query, top_k, **kwargs):
            return SearchResult(query=query, chunks=[])

    return _StubRetriever()


@pytest.fixture
def mock_retriever_raises():
    """A Retriever stub whose search() raises."""
    class _StubRetriever:
        def search(self, *, query, top_k, **kwargs):
            raise RuntimeError("retriever boom")

    return _StubRetriever()
