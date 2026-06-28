import json
from pathlib import Path
from ..chunkers.chunker import Chunk


class JsonStore:
    """JSONL store for complete chunk data.

    Each chunk is stored as a JSON object on its own line.
    Located at: data/knowledge_base/chunks.jsonl
    """

    def __init__(self, store_path: str = "data/knowledge_base/chunks.jsonl"):
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, chunk: Chunk) -> None:
        """Append a single chunk to the JSONL store."""
        record = {
            "chunk_id": chunk.chunk_id,
            "source_type": chunk.source_type,
            "document_id": chunk.document_id,
            "document_type": chunk.document_type,
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "metadata": chunk.metadata,
            "citation": chunk.citation,
        }
        with open(self.store_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def write_batch(self, chunks: list[Chunk]) -> None:
        """Append multiple chunks to the JSONL store."""
        with open(self.store_path, "a", encoding="utf-8") as f:
            for chunk in chunks:
                record = {
                    "chunk_id": chunk.chunk_id,
                    "source_type": chunk.source_type,
                    "document_id": chunk.document_id,
                    "document_type": chunk.document_type,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "metadata": chunk.metadata,
                    "citation": chunk.citation,
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def read(self, chunk_id: str) -> dict | None:
        """Read a single chunk by chunk_id."""
        with open(self.store_path, "r", encoding="utf-8") as f:
            for line in f:
                record = json.loads(line)
                if record["chunk_id"] == chunk_id:
                    return record
        return None

    def read_all(self) -> list[dict]:
        """Read all chunks from the store."""
        chunks = []
        if not self.store_path.exists():
            return chunks
        with open(self.store_path, "r", encoding="utf-8") as f:
            for line in f:
                chunks.append(json.loads(line))
        return chunks

    def clear(self) -> None:
        """Clear all chunks from the store (for testing)."""
        if self.store_path.exists():
            self.store_path.unlink()
