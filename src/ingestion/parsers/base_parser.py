from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ParsedDocument:
    """Represents a parsed document with metadata and content."""
    file_path: str
    document_id: str
    document_type: str
    metadata: dict
    content_blocks: list[dict]  # [{"heading": str, "content": str}]


class BaseParser(ABC):
    """Abstract base class for document parsers."""

    @abstractmethod
    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse a document and return structured content."""
        pass
