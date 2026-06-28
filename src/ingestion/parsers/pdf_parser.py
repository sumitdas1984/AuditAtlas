import re
from pathlib import Path
from pypdf import PdfReader
from .base_parser import BaseParser, ParsedDocument


class PDFParser(BaseParser):
    """Parser for Source A (PCAOB) and Source B (SEC 10-K) PDFs.

    Extracts text and metadata from PDF documents.
    """

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse a PDF document.

        Extracts text content and PDF metadata. Content is split into
        paragraphs for paragraph-level chunking.
        """
        reader = PdfReader(str(file_path))

        # Extract PDF metadata
        metadata = {}
        if reader.metadata:
            metadata = {
                "title": reader.metadata.get("/Title", ""),
                "author": reader.metadata.get("/Author", ""),
                "subject": reader.metadata.get("/Subject", ""),
                "creator": reader.metadata.get("/Creator", ""),
            }

        # Extract document ID from filename
        filename = file_path.stem
        document_id = self._extract_document_id(filename)

        # Extract text from all pages
        full_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n\n"

        # Split into paragraphs
        content_blocks = self._split_into_paragraphs(full_text)

        return ParsedDocument(
            file_path=str(file_path),
            document_id=document_id,
            document_type="Standard",
            metadata=metadata,
            content_blocks=content_blocks,
        )

    def _extract_document_id(self, filename: str) -> str:
        """Extract document ID from filename.

        Examples:
        - 2024-004-as1000.pdf -> AS1000
        - pcaob-release-no-2025-004.pdf -> PCAOB-2025-004
        - staff-guidance-*.pdf -> STAFF-GUIDANCE
        """
        # Try to extract standard ID like AS1000, QC1000
        match = re.search(r"(as|qc|AS|QC)(\d{4})", filename)
        if match:
            return f"{match.group(1).upper()}{match.group(2)}"

        # Try to extract release number
        match = re.search(r"release[-_]?(?:no[-_]?)?(\d{4})[-_]?(\d+)", filename, re.IGNORECASE)
        if match:
            return f"PCAOB-{match.group(1)}-{match.group(2)}"

        # Staff guidance
        if "staff" in filename.lower() or "guidance" in filename.lower():
            return "STAFF-GUIDANCE"

        # Fallback: clean filename
        return re.sub(r"[^\w]", "-", filename.upper())[:20]

    def _split_into_paragraphs(self, text: str) -> list[dict]:
        """Split text into paragraphs.

        Returns list of {"heading": "", "content": str, "level": 0, "paragraph_num": int}
        """
        # Split on double newlines or single newlines followed by uppercase (likely new paragraph)
        paragraphs = []
        raw_paragraphs = re.split(r"\n\s*\n", text)

        for idx, para in enumerate(raw_paragraphs):
            # Clean up whitespace
            para = re.sub(r"\s+", " ", para).strip()
            if para and len(para.split()) >= 3:
                paragraphs.append({
                    "heading": "",
                    "content": para,
                    "level": 0,
                    "paragraph_num": idx + 1,
                })

        return paragraphs
