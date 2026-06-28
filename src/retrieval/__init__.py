"""AuditAtlas retrieval layer.

Combines the embedder, ChromaDB vector store, JSON chunk store, and citation
formatter into a single search API. Phase 5 work.
"""

from .models import RetrievedChunk, SearchResult
from .retriever import Retriever

__all__ = ["Retriever", "RetrievedChunk", "SearchResult"]