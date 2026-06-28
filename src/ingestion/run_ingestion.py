import argparse
import sys
from pathlib import Path

from .parsers.markdown_parser import MarkdownParser
from .parsers.pdf_parser import PDFParser
from .chunkers.chunker import SourceCChunker, SourceAChunker, SourceBChunker
from .embedder.embedder import Embedder
from .storage.json_store import JsonStore
from .storage.sqlite_index import SqliteIndex
from .storage.chroma_store import ChromaStore


def run_source_a(args) -> None:
    """Ingest Source A (PCAOB PDF) documents."""
    source_dir = Path("data/raw/pcaob_standards")
    if not source_dir.exists():
        print(f"Source directory not found: {source_dir}")
        sys.exit(1)

    # Find all PDF files
    pdf_files = list(source_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {source_dir}")
        sys.exit(1)

    # Initialize components
    parser = PDFParser()
    chunker = SourceAChunker()
    embedder = Embedder()
    json_store = JsonStore()
    sqlite_index = SqliteIndex()
    chroma_store = ChromaStore()

    total_chunks = 0

    for pdf_file in pdf_files:
        print(f"Processing: {pdf_file.name}")

        # Parse
        parsed = parser.parse(pdf_file)
        print(f"  Parsed: {parsed.document_id} ({parsed.document_type})")

        # Chunk
        chunks = chunker.chunk(parsed)
        print(f"  Chunks: {len(chunks)}")

        # Store
        json_store.write_batch(chunks)
        sqlite_index.insert_batch(chunks)
        chroma_store.add(chunks, embedder)

        total_chunks += len(chunks)

    print(f"\nSource A ingestion complete: {total_chunks} chunks from {len(pdf_files)} documents")


def run_source_b(args) -> None:
    """Ingest Source B (SEC 10-K PDF) documents."""
    source_dir = Path("data/raw/sec_10k")
    if not source_dir.exists():
        print(f"Source directory not found: {source_dir}")
        sys.exit(1)

    # Find all PDF files
    pdf_files = list(source_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {source_dir}")
        sys.exit(1)

    # Initialize components
    parser = PDFParser()
    chunker = SourceBChunker()
    embedder = Embedder()
    json_store = JsonStore()
    sqlite_index = SqliteIndex()
    chroma_store = ChromaStore()

    total_chunks = 0

    for pdf_file in pdf_files:
        print(f"Processing: {pdf_file.name}")

        # Parse
        parsed = parser.parse(pdf_file)
        print(f"  Parsed: {parsed.document_id} ({parsed.document_type})")

        # Chunk
        chunks = chunker.chunk(parsed)
        print(f"  Chunks: {len(chunks)}")

        # Store
        json_store.write_batch(chunks)
        sqlite_index.insert_batch(chunks)
        chroma_store.add(chunks, embedder)

        total_chunks += len(chunks)

    print(f"\nSource B ingestion complete: {total_chunks} chunks from {len(pdf_files)} documents")


def run_source_c(args) -> None:
    """Ingest Source C (Markdown) documents."""
    source_dir = Path("data/raw/synthetic_company_docs")
    if not source_dir.exists():
        print(f"Source directory not found: {source_dir}")
        sys.exit(1)

    # Find all markdown files
    md_files = list(source_dir.glob("*.md"))
    if not md_files:
        print(f"No Markdown files found in {source_dir}")
        sys.exit(1)

    # Initialize components
    parser = MarkdownParser()
    chunker = SourceCChunker()
    embedder = Embedder()
    json_store = JsonStore()
    sqlite_index = SqliteIndex()
    chroma_store = ChromaStore()

    total_chunks = 0

    for md_file in md_files:
        print(f"Processing: {md_file.name}")

        # Parse
        parsed = parser.parse(md_file)
        print(f"  Parsed: {parsed.document_id} ({parsed.document_type})")

        # Chunk
        chunks = chunker.chunk(parsed)
        print(f"  Chunks: {len(chunks)}")

        # Store
        json_store.write_batch(chunks)
        sqlite_index.insert_batch(chunks)
        chroma_store.add(chunks, embedder)

        total_chunks += len(chunks)

    print(f"\nSource C ingestion complete: {total_chunks} chunks from {len(md_files)} documents")


def run_single_file(args) -> None:
    """Ingest a single document file."""
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"File not found: {file_path}")
        sys.exit(1)

    # Determine parser based on extension
    if file_path.suffix == ".md":
        parser = MarkdownParser()
    else:
        print(f"Unsupported file type: {file_path.suffix}")
        sys.exit(1)

    # Initialize components
    chunker = SourceCChunker()
    embedder = Embedder()
    json_store = JsonStore()
    sqlite_index = SqliteIndex()
    chroma_store = ChromaStore()

    print(f"Processing: {file_path}")

    # Parse
    parsed = parser.parse(file_path)
    print(f"  Parsed: {parsed.document_id} ({parsed.document_type})")

    # Chunk
    chunks = chunker.chunk(parsed)
    print(f"  Chunks: {len(chunks)}")

    # Store
    json_store.write_batch(chunks)
    sqlite_index.insert_batch(chunks)
    chroma_store.add(chunks, embedder)

    print(f"\nIngestion complete: {len(chunks)} chunks")


def main():
    parser = argparse.ArgumentParser(description="AuditAtlas Data Ingestion")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # run subcommand
    run_parser = subparsers.add_parser("run", help="Run ingestion")
    run_parser.add_argument("--source", choices=["A", "B", "C"], help="Source to ingest")
    run_parser.add_argument("--file", help="Single file to ingest")
    run_parser.add_argument("--all", action="store_true", help="Ingest all sources")

    args = parser.parse_args()

    if args.command == "run":
        if args.source == "A":
            run_source_a(args)
        elif args.source == "B":
            run_source_b(args)
        elif args.source == "C" or args.file or args.all:
            if args.file:
                run_single_file(args)
            else:
                run_source_c(args)
        else:
            parser.print_help()
            sys.exit(1)
    else:
        # Support direct invocation: python -m src.ingestion run --source C
        if len(sys.argv) > 1 and sys.argv[1] == "run":
            sys.argv.pop(1)
            args = parser.parse_args(["run", "--source", "C"])
            if args.file:
                run_single_file(args)
            else:
                run_source_c(args)
        else:
            parser.print_help()
            sys.exit(1)


if __name__ == "__main__":
    main()
