import frontmatter
from pathlib import Path
import re
from .base_parser import BaseParser, ParsedDocument


class MarkdownParser(BaseParser):
    """Parser for Source C Markdown documents with YAML frontmatter."""

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse a Markdown document with frontmatter.

        Extracts YAML frontmatter metadata and splits content into
        heading sections for chunking.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            post = frontmatter.loads(f.read())

        metadata = dict(post.metadata)

        # Extract document_id from filename pattern: 01-Internal-Audit-Report.md
        filename = file_path.stem  # e.g., "01-Internal-Audit-Report"
        doc_id = self._extract_doc_id(metadata.get("document_id"), filename)

        # Extract document_type from metadata or filename
        document_type = metadata.get(
            "document_type",
            self._infer_document_type(filename)
        )

        # Split content by headings
        content_blocks = self._split_by_headings(post.content)

        return ParsedDocument(
            file_path=str(file_path),
            document_id=doc_id,
            document_type=document_type,
            metadata=metadata,
            content_blocks=content_blocks,
        )

    def _extract_doc_id(self, metadata_doc_id: str | None, filename: str) -> str:
        """Extract document ID from metadata or filename."""
        if metadata_doc_id:
            return metadata_doc_id
        # Pattern: 01-Internal-Audit-Report -> IA-2026-001 style
        # For existing files, use the filename without prefix number
        match = re.match(r"\d+-(.+)", filename)
        if match:
            base = match.group(1).replace("-", "")
            return f"IA-2026-{base[:3].upper()}"
        return filename

    def _infer_document_type(self, filename: str) -> str:
        """Infer document type from filename."""
        filename_lower = filename.lower()
        if "internal-audit" in filename_lower or "audit-report" in filename_lower:
            return "InternalAuditReport"
        elif "risk-register" in filename_lower or "risk-register" in filename_lower:
            return "RiskRegister"
        elif "control-matrix" in filename_lower:
            return "ControlMatrix"
        elif "policy" in filename_lower:
            return "Policy"
        elif "sop" in filename_lower or "vendor" in filename_lower:
            return "SOP"
        return "Unknown"

    def _split_by_headings(self, content: str) -> list[dict]:
        """Split Markdown content into sections by heading level.

        Returns list of {"heading": str, "content": str, "level": int}
        """
        lines = content.split("\n")
        blocks = []
        current_heading = ""
        current_level = 0
        current_content_lines = []

        for line in lines:
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if heading_match:
                # Save previous block
                if current_heading or current_content_lines:
                    blocks.append({
                        "heading": current_heading.strip(),
                        "level": current_level,
                        "content": "\n".join(current_content_lines).strip(),
                    })

                # Start new block
                current_level = len(heading_match.group(1))
                current_heading = heading_match.group(2)
                current_content_lines = []
            else:
                current_content_lines.append(line)

        # Don't forget the last block
        if current_heading or current_content_lines:
            blocks.append({
                "heading": current_heading.strip(),
                "level": current_level,
                "content": "\n".join(current_content_lines).strip(),
            })

        return blocks
