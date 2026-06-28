import re
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


class SourceBChunker:
    """Chunks Source B (SEC 10-K) documents by Item sections.

    Chunk ID format: {ticker}.{year}.{item}.{paragraph}
    Example: AAPL.2025.Item1A.3

    Citation format: [AAPL 10-K, Item 1A (2025)]
    """

    # Common 10-K Item sections
    ITEM_PATTERNS = [
        "Item 1A", "Item 1B", "Item 2", "Item 3", "Item 4",
        "Item 5", "Item 6", "Item 7", "Item 7A", "Item 8",
        "Item 9A", "Item 9B", "Item 10", "Item 11", "Item 12",
        "Item 13", "Item 14", "Item 15"
    ]

    def chunk(self, parsed_doc: ParsedDocument) -> list[Chunk]:
        """Split a parsed document into Item-section chunks.

        Each Item section becomes a chunk. Paragraphs within each Item
        are combined into the chunk content.

        PDFs vary in how Item headers are laid out: some have each Item
        header as the first line of its own paragraph block, others
        embed Item headers mid-block (e.g., AMZN's TOC and section
        pages concatenate Items on a single line). To handle both, we
        split each block at Item boundaries within its content.

        When the same Item appears multiple times (e.g., once in TOC,
        once as the real section), we keep the longest content per
        chunk_id so the real section wins over the short TOC entry.
        """
        chunks = []
        ticker = parsed_doc.document_id
        fiscal_year = parsed_doc.metadata.get("fiscal_year", "")

        # Normalize blocks by splitting at Item boundaries within content.
        normalized_segments: list[tuple[str | None, str]] = []
        for block in parsed_doc.content_blocks:
            content = block.get("content", "")
            if len(content.split()) < 3:
                continue
            normalized_segments.extend(self._split_at_item_boundaries(content))

        # Group segments by Item section, accumulating content.
        current_item = None
        current_item_content: list[str] = []

        for item, content in normalized_segments:
            if item:
                # Flush previous item
                if current_item and current_item_content:
                    chunks.append(self._create_chunk(
                        ticker=ticker,
                        fiscal_year=fiscal_year,
                        item=current_item,
                        content="\n\n".join(current_item_content),
                        paragraph_num=1,
                        metadata=parsed_doc.metadata,
                    ))
                current_item = item
                current_item_content = [content]
            else:
                if current_item:
                    current_item_content.append(content)

        # Flush last item
        if current_item and current_item_content:
            chunks.append(self._create_chunk(
                ticker=ticker,
                fiscal_year=fiscal_year,
                item=current_item,
                content="\n\n".join(current_item_content),
                paragraph_num=1,
                metadata=parsed_doc.metadata,
            ))

        # Filter out cross-reference mentions like "Item 7 of Part II,
        # Management's Discussion..." which aren't real sections.
        chunks = [c for c in chunks if not self._is_cross_reference(c.content)]

        # Deduplicate by chunk_id, keeping the longest content. The same
        # Item can appear in TOC and as the real section; the latter is
        # always longer and is what we want to retain.
        return self._dedupe_by_longest(chunks)

    def _split_at_item_boundaries(self, content: str) -> list[tuple[str | None, str]]:
        """Split a content block at Item section boundaries.

        The parser collapses all whitespace to single spaces, so Item
        headers like "Item 1A. Risk Factors" appear embedded in larger
        strings like "...Corning Incorporated Item 1A. Risk Factors
        Please carefully consider...". We detect Item headers anywhere
        in the content and split into (item_or_None, content) segments.

        Returns a list of (item, content) tuples. Preamble text before
        the first Item is emitted with item=None so callers can decide
        whether to keep it.
        """
        # Find all Item header positions. The header pattern is "Item N"
        # or "Item NX" where N is digits and X is an optional letter.
        # We require a word boundary so "Items" doesn't match.
        matches = list(re.finditer(r"\b(Item\s+\d+[A-Z]?)\b", content))

        if not matches:
            return [(None, content)]

        segments: list[tuple[str | None, str]] = []

        # Preamble: text before the first Item header
        first_start = matches[0].start()
        preamble = content[:first_start].rstrip()
        if preamble:
            segments.append((None, preamble))

        # Each Item segment: from this match to next match (or end).
        for i, m in enumerate(matches):
            item_id = m.group(1)
            next_start = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            segment = content[m.start():next_start].strip()
            if segment:
                segments.append((item_id, segment))

        return segments

    def _dedupe_by_longest(self, chunks: list[Chunk]) -> list[Chunk]:
        """Keep the longest chunk per chunk_id."""
        best: dict[str, Chunk] = {}
        for chunk in chunks:
            existing = best.get(chunk.chunk_id)
            if existing is None or len(chunk.content) > len(existing.content):
                best[chunk.chunk_id] = chunk
        # Preserve first-seen order
        seen = set()
        result = []
        for chunk in chunks:
            if chunk.chunk_id in seen:
                continue
            seen.add(chunk.chunk_id)
            result.append(best[chunk.chunk_id])
        return result

    def _is_cross_reference(self, content: str) -> bool:
        """Detect cross-reference mentions of Items that aren't real sections.

        Real sections start with "Item N. Title..." (period separator).
        Cross-references say "Item N of Part Y, Title..." (no period
        after the number, "of Part" linking phrase).
        """
        return bool(re.search(r"\bItem\s+\d+[A-Z]?\s+of\s+Part\b", content))

    def _create_chunk(
        self,
        ticker: str,
        fiscal_year: str,
        item: str,
        content: str,
        paragraph_num: int,
        metadata: dict,
    ) -> Chunk:
        """Create a Source B chunk."""
        # Format item for chunk ID: Item 1A -> Item1A
        item_id = item.replace(" ", "")
        chunk_id = f"{ticker}.{fiscal_year}.{item_id}.{paragraph_num}"

        citation = self._build_citation(ticker, item, fiscal_year)

        chunk = Chunk(
            chunk_id=chunk_id,
            source_type="B",
            document_id=ticker,
            document_type="10-K",
            chunk_index=paragraph_num,
            content=content,
            metadata={
                "ticker": ticker,
                "fiscal_year": fiscal_year,
                "item": item,
                "company_name": metadata.get("company_name", ticker),
            },
            citation=citation,
        )
        return chunk

    def _build_citation(self, ticker: str, item: str, fiscal_year: str) -> dict:
        """Build SEC 10-K citation.

        Format: [AAPL 10-K, Item 1A (2025)]
        """
        return {
            "format": f"[{ticker} 10-K, {item} ({fiscal_year})]",
            "type": "sec",
        }
