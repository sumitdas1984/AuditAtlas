"""CLI handlers for the retrieval layer.

The argparse layer (in __main__.py) is a thin shell over these handlers, which
are independently testable. The handlers:
- Validate input
- Construct a Retriever
- Run the search
- Format the result as a table or JSON
- Return a (exit_code, output_string) tuple

Exit codes:
    0  success (including "no results found")
    1  internal error
    2  empty query
    3  uninitialized knowledge base
    4  invalid --where JSON
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

from ..knowledge_engineering.router import Router
from .retriever import Retriever

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

CONTENT_PREVIEW_CHARS = 200


def _content_preview(content: str, show_content: bool) -> str:
    """Return a content snippet (or empty string if hidden)."""
    if not show_content:
        return ""
    if len(content) <= CONTENT_PREVIEW_CHARS:
        return content
    return content[:CONTENT_PREVIEW_CHARS - 3] + "..."


def _format_table(result, show_content: bool = True) -> str:
    """Format a SearchResult as a human-readable table."""
    if not result.chunks:
        return "No results found."

    rows = []
    for chunk in result.chunks:
        rows.append({
            "chunk_id": chunk.chunk_id,
            "source_type": chunk.source_type,
            "distance": f"{chunk.distance:.4f}",
            "citation": chunk.citation,
            "content": _content_preview(chunk.content, show_content),
        })

    # Compute column widths
    headers = ["chunk_id", "source_type", "distance", "citation", "content"]
    widths = {h: len(h) for h in headers}
    for row in rows:
        for h in headers:
            widths[h] = max(widths[h], len(str(row[h])))

    # Truncate content to keep table readable
    content_width = min(widths["content"], 80)
    widths["content"] = content_width

    def _truncate(s: str, w: int) -> str:
        s = str(s)
        return s if len(s) <= w else s[: w - 3] + "..."

    # Header
    lines = []
    header = " | ".join(_truncate(h, widths[h]).ljust(widths[h]) for h in headers)
    lines.append(header)
    lines.append("-+-".join("-" * widths[h] for h in headers))
    # Rows
    for row in rows:
        line = " | ".join(
            _truncate(row[h], widths[h]).ljust(widths[h]) for h in headers
        )
        lines.append(line)

    # Footer with routing info
    footer_parts = []
    if result.sources_searched:
        footer_parts.append(f"Sources searched: {result.sources_searched}")
    if result.routing is not None:
        footer_parts.append(f"Routing: {result.routing.reasoning}")
    if footer_parts:
        lines.append("")
        lines.extend(footer_parts)

    return "\n".join(lines)


def _format_json(result) -> str:
    """Format a SearchResult as JSON (chunks + routing + sources_searched)."""
    payload: dict[str, Any] = {
        "query": result.query,
        "chunks": [
            {
                "chunk_id": c.chunk_id,
                "source_type": c.source_type,
                "document_id": c.document_id,
                "document_type": c.document_type,
                "content": c.content,
                "metadata": c.metadata,
                "citation": c.citation,
                "distance": c.distance,
            }
            for c in result.chunks
        ],
        "sources_searched": result.sources_searched,
    }
    if result.routing is not None:
        payload["routing"] = {
            "sources": [s.value for s in result.routing.sources],
            "confidence": result.routing.confidence,
            "reasoning": result.routing.reasoning,
        }
    return json.dumps(payload, indent=2, default=str)


# ---------------------------------------------------------------------------
# Knowledge-base health check
# ---------------------------------------------------------------------------

def _check_kb_initialized(retriever: Retriever) -> tuple[bool, str]:
    """Verify the knowledge base has at least one chunk.

    Returns (is_initialized, message). If the KB is empty (no chunks in
    ChromaDB), returns (False, helpful message about running ingestion).
    """
    try:
        # ChromaDB raises or returns empty list when collection has no entries
        count = retriever.chroma_store.collection.count()
        if count == 0:
            return False, (
                "Knowledge base is empty. Run "
                "'python -m src.ingestion run --all' to populate it first."
            )
        return True, ""
    except Exception as exc:  # pragma: no cover (defensive)
        return False, f"Knowledge base not initialized: {exc}"


# ---------------------------------------------------------------------------
# Search command
# ---------------------------------------------------------------------------

def run_search(
    query: str,
    top_k: int = 5,
    ticker: str | None = None,
    standard_id: str | None = None,
    where: str | None = None,
    use_router: bool = True,
    output_format: str = "table",
    show_content: bool = True,
    chroma_dir: str | None = None,
    jsonl_path: str | None = None,
    collection_name: str | None = None,
) -> tuple[int, str]:
    """Run a search and return (exit_code, output_string).

    Args:
        query: Natural-language search query.
        top_k: Number of chunks to return.
        ticker: Optional Source B ticker filter.
        standard_id: Optional Source A standard ID filter.
        where: Optional raw ChromaDB where clause as JSON string.
        use_router: If True, use Router for multi-source aggregation.
        output_format: "table" or "json".
        show_content: Whether to include content snippet in table output.
        chroma_dir: Optional override for ChromaDB persist directory.
        jsonl_path: Optional override for JSONL store path.
        collection_name: Optional override for ChromaDB collection name
            (default: "audit_chunks"). Tests use this to avoid colliding
            with the production collection.

    Returns:
        (exit_code, output) tuple. exit_code is 0 on success (including
        "no results"), 2 for empty query, 3 for uninit KB, 4 for bad JSON.
    """
    # Input validation
    if not query or not query.strip():
        return 2, "Error: query cannot be empty"

    where_dict: dict | None = None
    if where:
        try:
            where_dict = json.loads(where)
            if not isinstance(where_dict, dict):
                return 4, "Error: --where must be a JSON object (e.g., '{\"source_type\": \"A\"}')"
        except json.JSONDecodeError as exc:
            return 4, f"Error: --where must be valid JSON: {exc}"

    if output_format not in ("table", "json"):
        return 1, f"Error: unknown output format '{output_format}' (use 'table' or 'json')"

    # Build retriever
    from ..ingestion.embedder.embedder import Embedder
    from ..ingestion.storage.chroma_store import ChromaStore
    from ..ingestion.storage.json_store import JsonStore

    try:
        if chroma_dir or collection_name:
            chroma_kwargs = {}
            if chroma_dir:
                chroma_kwargs["persist_dir"] = chroma_dir
            if collection_name:
                chroma_kwargs["collection_name"] = collection_name
            chroma = ChromaStore(**chroma_kwargs)
        else:
            chroma = ChromaStore()
        json_store = JsonStore(store_path=jsonl_path) if jsonl_path else JsonStore()
        embedder = Embedder()
        router = Router() if use_router else None
        retriever = Retriever(
            chroma_store=chroma,
            json_store=json_store,
            embedder=embedder,
            router=router,
        )
    except Exception as exc:
        logger.exception("Failed to initialize retriever")
        return 5, f"Error: failed to initialize retriever: {exc}"

    # KB health check
    is_init, msg = _check_kb_initialized(retriever)
    if not is_init:
        return 3, f"Error: {msg}"

    # Run search
    try:
        result = retriever.search(
            query=query,
            top_k=top_k,
            where=where_dict,
            ticker=ticker,
            standard_id=standard_id,
            use_router=use_router,
        )
    except Exception as exc:
        logger.exception("Search failed")
        return 5, f"Error: search failed: {exc}"

    # Format output
    if output_format == "json":
        return 0, _format_json(result)
    return 0, _format_table(result, show_content=show_content)


def main(argv: list[str] | None = None) -> int:
    """Entry point for `python -m src.retrieval`."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m src.retrieval",
        description="AuditAtlas Retrieval — search the knowledge base",
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # search subcommand
    search_p = subparsers.add_parser("search", help="Search the knowledge base")
    search_p.add_argument("query", help="Natural-language search query")
    search_p.add_argument("--top-k", type=int, default=5, help="Number of chunks to return (default: 5)")
    search_p.add_argument("--ticker", help="Source B ticker filter (e.g., AAPL)")
    search_p.add_argument("--standard-id", dest="standard_id", help="Source A standard ID filter (e.g., AS1105)")
    search_p.add_argument("--where", help="Raw ChromaDB where clause as JSON (e.g., '{\"source_type\": \"A\"}')")
    search_p.add_argument(
        "--use-router", dest="use_router", action=argparse.BooleanOptionalAction,
        default=True, help="Use router for multi-source search (default: True)",
    )
    search_p.add_argument(
        "--format", dest="output_format", choices=["table", "json"], default="table",
        help="Output format (default: table)",
    )
    search_p.add_argument(
        "--show-content", dest="show_content", action=argparse.BooleanOptionalAction,
        default=True, help="Include content snippet in table output (default: True)",
    )
    search_p.add_argument(
        "--chroma-dir", dest="chroma_dir", default=None,
        help="Override ChromaDB persist directory",
    )
    search_p.add_argument(
        "--collection-name", dest="collection_name", default=None,
        help="Override ChromaDB collection name (default: audit_chunks)",
    )
    search_p.add_argument(
        "--jsonl-path", dest="jsonl_path", default=None,
        help="Override JSONL store path",
    )

    args = parser.parse_args(argv)

    if args.command == "search":
        code, output = run_search(
            query=args.query,
            top_k=args.top_k,
            ticker=args.ticker,
            standard_id=args.standard_id,
            where=args.where,
            use_router=args.use_router,
            output_format=args.output_format,
            show_content=args.show_content,
            chroma_dir=args.chroma_dir,
            jsonl_path=args.jsonl_path,
            collection_name=args.collection_name,
        )
        print(output)
        return code

    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
