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

        # Extract document ID and source type from filename
        filename = file_path.stem
        source_info = self._extract_document_info(filename)
        document_id = source_info["document_id"]
        document_type = source_info["document_type"]
        metadata.update(source_info.get("extra_metadata", {}))

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
            document_type=document_type,
            metadata=metadata,
            content_blocks=content_blocks,
        )

    def _extract_document_info(self, filename: str) -> dict:
        """Extract document ID and metadata from filename.

        Handles both Source A (PCAOB) and Source B (SEC 10-K) filenames.

        Source A examples:
        - 2024-004-as1000.pdf -> {"document_id": "AS1000", "document_type": "Standard", "extra_metadata": {}}
        - pcaob-release-no-2025-004.pdf -> {"document_id": "PCAOB-2025-004", "document_type": "Standard", "extra_metadata": {}}
        - staff-guidance-*.pdf -> {"document_id": "STAFF-GUIDANCE", "document_type": "Standard", "extra_metadata": {}}

        Source B examples:
        - aapl-20250927.pdf -> {"document_id": "AAPL", "document_type": "10-K", "extra_metadata": {"ticker": "AAPL", "fiscal_year": "2025"}}
        - msft.pdf -> {"document_id": "MSFT", "document_type": "10-K", "extra_metadata": {"ticker": "MSFT", "fiscal_year": ""}}
        """
        # Source A checks first (more specific patterns)

        # Source A: Try to extract standard ID like AS1000, QC1000
        match = re.search(r"(as|qc|AS|QC)(\d{4})", filename)
        if match:
            return {
                "document_id": f"{match.group(1).upper()}{match.group(2)}",
                "document_type": "Standard",
                "extra_metadata": {},
            }

        # Try to extract PCAOB release number
        match = re.search(r"release[-_]?(?:no[-_]?)?(\d{4})[-_]?(\d+)", filename, re.IGNORECASE)
        if match:
            return {
                "document_id": f"PCAOB-{match.group(1)}-{match.group(2)}",
                "document_type": "Standard",
                "extra_metadata": {},
            }

        # Staff guidance
        if "staff" in filename.lower() or "guidance" in filename.lower():
            return {
                "document_id": "STAFF-GUIDANCE",
                "document_type": "Standard",
                "extra_metadata": {},
            }

        # Source B: lowercase ticker at start followed by year
        # e.g., aapl-20250927, amzn-20251231, msft (no year), tsla-20251231
        match = re.match(r"^([a-zA-Z]+)-?(\d{4})?.*$", filename)
        if match:
            ticker = match.group(1).upper()
            fiscal_year = match.group(2) if match.group(2) else ""
            # Check if it looks like a known ticker (2-5 letters, and NOT a known PCAOB keyword)
            known_pcaob = {"PCAOB", "AS", "QC", "SEC", "FASB", "IASB"}
            if ticker.isalpha() and len(ticker) >= 2 and len(ticker) <= 5 and ticker not in known_pcaob:
                return {
                    "document_id": ticker,
                    "document_type": "10-K",
                    "extra_metadata": {
                        "ticker": ticker,
                        "fiscal_year": fiscal_year,
                        "company_name": ticker,
                    },
                }

        # Fallback: clean filename
        return {
            "document_id": re.sub(r"[^\w]", "-", filename.upper())[:20],
            "document_type": "Standard",
            "extra_metadata": {},
        }

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
