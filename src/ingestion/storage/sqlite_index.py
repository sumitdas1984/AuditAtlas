import sqlite3
from pathlib import Path
from ..chunkers.chunker import Chunk


class SqliteIndex:
    """SQLite metadata index for fast filtering.

    Provides lightweight index on chunk metadata without loading full JSON.
    Located at: data/knowledge_base/index.db
    """

    def __init__(self, db_path: str = "data/knowledge_base/index.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    source_type TEXT NOT NULL,
                    document_type TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    effective_date TEXT,
                    classification TEXT,
                    ticker TEXT,
                    standard_id TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_source_type ON chunks(source_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_document_id ON chunks(document_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ticker ON chunks(ticker)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_standard_id ON chunks(standard_id)")

    def insert(self, chunk: Chunk) -> None:
        """Insert a single chunk's metadata."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO chunks
                (chunk_id, source_type, document_type, document_id, effective_date, classification, ticker, standard_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                chunk.chunk_id,
                chunk.source_type,
                chunk.document_type,
                chunk.document_id,
                chunk.metadata.get("effective_date"),
                chunk.metadata.get("classification"),
                chunk.metadata.get("ticker"),
                chunk.metadata.get("standard_id"),
            ))

    def insert_batch(self, chunks: list[Chunk]) -> None:
        """Insert multiple chunks' metadata."""
        with sqlite3.connect(self.db_path) as conn:
            for chunk in chunks:
                conn.execute("""
                    INSERT OR REPLACE INTO chunks
                    (chunk_id, source_type, document_type, document_id, effective_date, classification, ticker, standard_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    chunk.chunk_id,
                    chunk.source_type,
                    chunk.document_type,
                    chunk.document_id,
                    chunk.metadata.get("effective_date"),
                    chunk.metadata.get("classification"),
                    chunk.metadata.get("ticker"),
                    chunk.metadata.get("standard_id"),
                ))

    def query_by_source(self, source_type: str) -> list[str]:
        """Get all chunk_ids for a given source type."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT chunk_id FROM chunks WHERE source_type = ?",
                (source_type,)
            )
            return [row[0] for row in cursor.fetchall()]

    def query_by_document(self, document_id: str) -> list[str]:
        """Get all chunk_ids for a given document."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT chunk_id FROM chunks WHERE document_id = ?",
                (document_id,)
            )
            return [row[0] for row in cursor.fetchall()]
