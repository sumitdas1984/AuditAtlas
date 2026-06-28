import chromadb
from chromadb.config import Settings
from pathlib import Path
from ..chunkers.chunker import Chunk
from ..embedder.embedder import Embedder


class ChromaStore:
    """ChromaDB vector store for embeddings.

    Stores embeddings with metadata for similarity search.
    Located at: data/knowledge_base/chroma/
    """

    def __init__(
        self,
        persist_dir: str = "data/knowledge_base/chroma",
        collection_name: str = "audit_chunks"
    ):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self._client = None
        self._collection = None

    @property
    def client(self):
        """Lazy-initialize ChromaDB client."""
        if self._client is None:
            self._client = chromadb.Client(Settings(
                persist_directory=str(self.persist_dir),
                anonymized_telemetry=False,
            ))
        return self._client

    @property
    def collection(self):
        """Get or create the collection."""
        if self._collection is None:
            self._client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=Settings(anonymized_telemetry=False)
            )
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"source": "audit_atlas"}
            )
        return self._collection

    def add(self, chunks: list[Chunk], embedder: Embedder) -> None:
        """Add chunks with embeddings to the collection.

        Args:
            chunks: List of chunks to add.
            embedder: Embedder instance to generate vectors.
        """
        if not chunks:
            return

        # Generate embeddings for all chunks
        texts = [chunk.content for chunk in chunks]
        embeddings = embedder.embed_batch(texts)

        # Prepare data for ChromaDB
        ids = [chunk.chunk_id for chunk in chunks]
        metadatas = [
            {
                "source_type": chunk.source_type,
                "document_type": chunk.document_type,
                "chunk_id": chunk.chunk_id,
                "ticker": chunk.metadata.get("ticker"),
                "standard_id": chunk.metadata.get("standard_id"),
            }
            for chunk in chunks
        ]
        # Filter out None values from metadata
        metadatas = [
            {k: v for k, v in m.items() if v is not None}
            for m in metadatas
        ]

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=[chunk.content for chunk in chunks],
        )

    def search(
        self,
        query_text: str,
        embedder: Embedder,
        n_results: int = 10,
        where: dict | None = None
    ) -> list[dict]:
        """Search for similar chunks.

        Args:
            query_text: Query text to embed and search.
            embedder: Embedder instance.
            n_results: Number of results to return.
            where: Optional metadata filter.

        Returns:
            List of result dicts with chunk_id, distance, metadata.
        """
        query_embedding = embedder.embed(query_text)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
        )

        return results

    def clear(self) -> None:
        """Delete all items from the collection (for testing)."""
        if self._collection is not None:
            try:
                self._client.delete_collection(self.collection_name)
            except Exception:
                pass
            self._collection = None
