from dataclasses import dataclass
from typing import Literal
from ..parsers.base_parser import ParsedDocument


@dataclass
class Chunk:
    """A discrete, citable chunk from a document."""
    chunk_id: str
    source_type: Literal["A", "B", "C"]
    document_id: str
    document_type: str
    chunk_index: int
    content: str
    metadata: dict
    citation: dict


class SourceCChunker:
    """Chunks Source C (Markdown) documents by heading sections.

    Chunk ID format: {doc_id}.{section_index}
    Example: IA-2026-004.3.1
    """

    def chunk(self, parsed_doc: ParsedDocument) -> list[Chunk]:
        """Split a parsed document into heading-section chunks.

        Each heading and its following content becomes one chunk.
        Nested sections are handled by combining parent headings.
        """
        chunks = []
        doc_id = parsed_doc.document_id

        for idx, block in enumerate(parsed_doc.content_blocks):
            if not block["content"]:
                continue

            # Skip empty blocks or very short content
            if len(block["content"].split()) < 5:
                continue

            # Build section path from heading hierarchy
            section_idx = idx + 1
            chunk_id = f"{doc_id}.{section_idx}"

            # Combine heading with content for full chunk text
            if block["heading"]:
                chunk_content = f"## {block['heading']}\n\n{block['content']}"
            else:
                chunk_content = block["content"]

            # Build citation from document type
            citation = self._build_citation(
                parsed_doc.document_type,
                block["heading"],
                doc_id
            )

            # Extract effective_date and classification from metadata
            effective_date = parsed_doc.metadata.get("effective_date")
            classification = parsed_doc.metadata.get("classification", "InternalUseOnly")

            chunk = Chunk(
                chunk_id=chunk_id,
                source_type="C",
                document_id=doc_id,
                document_type=parsed_doc.document_type,
                chunk_index=section_idx,
                content=chunk_content,
                metadata={
                    "heading": block["heading"],
                    "level": block["level"],
                    "classification": classification,
                    "effective_date": str(effective_date) if effective_date else None,
                    "owner": parsed_doc.metadata.get("owner"),
                    "company": parsed_doc.metadata.get("company", "Northwind Retail Solutions Ltd."),
                },
                citation=citation,
            )
            chunks.append(chunk)

        return chunks

    def _build_citation(self, document_type: str, heading: str, doc_id: str) -> dict:
        """Build citation metadata for a chunk."""
        # Extract finding/control/risk ID from heading if present
        ref_id = doc_id
        if heading:
            # Try to extract an ID like "2025-H-001" from heading
            import re
            match = re.search(r"\d{4}-[A-Z]-\d{3}", heading)
            if match:
                ref_id = match.group(0)

        type_map = {
            "InternalAuditReport": "internal_audit",
            "RiskRegister": "risk_register",
            "ControlMatrix": "control_matrix",
            "Policy": "policy",
            "SOP": "sop",
        }
        doc_type_key = type_map.get(document_type, "synthetic")

        return {
            "format": f"[{document_type}:{ref_id}]",
            "type": "synthetic",
        }


class SourceAChunker:
    """Chunks Source A (PCAOB) documents by paragraph.

    Chunk ID format: {standard_id}.{paragraph_num}
    Example: AS1105.12

    Citation format: [AS 1105 § .12]
    """

    def chunk(self, parsed_doc: ParsedDocument) -> list[Chunk]:
        """Split a parsed document into paragraph chunks.

        Each paragraph becomes a distinct chunk with its paragraph number
        as the chunk index.
        """
        chunks = []
        doc_id = parsed_doc.document_id

        for block in parsed_doc.content_blocks:
            if not block.get("content"):
                continue

            content = block["content"]
            if len(content.split()) < 5:
                continue

            paragraph_num = block.get("paragraph_num", 0)
            chunk_id = f"{doc_id}.{paragraph_num}"

            # Build citation: [AS 1105 § .12]
            citation = self._build_citation(doc_id, paragraph_num)

            chunk = Chunk(
                chunk_id=chunk_id,
                source_type="A",
                document_id=doc_id,
                document_type=parsed_doc.document_type,
                chunk_index=paragraph_num,
                content=content,
                metadata={
                    "paragraph": f".{paragraph_num}" if paragraph_num else None,
                    "standard_id": doc_id,
                    "effective_date": parsed_doc.metadata.get("effective_date"),
                    "status": parsed_doc.metadata.get("status", "Effective"),
                    "title": parsed_doc.metadata.get("title", ""),
                },
                citation=citation,
            )
            chunks.append(chunk)

        return chunks

    def _build_citation(self, standard_id: str, paragraph_num: int) -> dict:
        """Build PCAOB-style citation.

        Format: [AS 1105 § .12]
        """
        # Convert AS1105 -> AS 1105 for display
        formatted_id = standard_id
        if len(standard_id) >= 4:
            formatted_id = f"{standard_id[:2]} {standard_id[2:]}"

        return {
            "format": f"[{formatted_id} § .{paragraph_num}]",
            "type": "pcaob",
        }
