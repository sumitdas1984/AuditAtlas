"""CLI handlers for the research (Phase 6) layer.

The argparse layer (in __main__.py) is a thin shell over these handlers, which
are independently testable. The handlers:
- Validate input
- Construct a Retriever + AnswerGenerator + ResearchWorkflow
- Run the workflow
- Format the result as text or JSON
- Return a (exit_code, output_string) tuple

Exit codes:
    0  success (including "no results found")
    1  internal error
    2  empty query
    3  uninitialized knowledge base
    4  invalid --where JSON
    5  runtime error (incl. LLM failure, retrieval failure — WorkflowError)
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

from ..knowledge_engineering.citation import SourceType, format_citation
from ..retrieval.cli import _check_kb_initialized, _sanitize_for_table
from ..retrieval import Retriever
from .answer_generator import AnswerGenerator
from .llm_client import AnthropicClient, MockClient
from .models import ResearchResult
from .workflow import ResearchWorkflow, WorkflowError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# .env loading
# ---------------------------------------------------------------------------

def _load_env_file(env_path: Path | None = None) -> None:
    """Load a .env file from disk into os.environ, if present.

    Uses `python-dotenv` with `override=False` so env vars already set in
    the shell take precedence over .env file values (12-factor convention).

    Args:
        env_path: Path to .env. Defaults to the project-root .env. Pass an
            explicit path (e.g., a temp file) in tests.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        # python-dotenv missing — skip silently; env vars must be set externally
        return

    if env_path is None:
        # src/research/cli.py → project root = parents[2]
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"

    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def _format_text(result: ResearchResult) -> str:
    """Format a ResearchResult as human-readable text with numbered citations."""
    lines: list[str] = []

    # Answer text (sanitized so newlines don't break the layout)
    lines.append(_sanitize_for_table(result.answer.text))
    lines.append("")

    # Numbered citations
    if result.answer.citations:
        lines.append("Sources:")
        for i, citation in enumerate(result.answer.citations, 1):
            try:
                source_type = SourceType(citation.chunk.source_type)
                formal = format_citation(citation.chunk_id, source_type)
            except ValueError:
                formal = f"[{citation.chunk_id}]"
            lines.append(f"  [{i}] {formal}")
        lines.append("")

    # Footer
    if result.sources_searched:
        lines.append(f"Sources searched: {result.sources_searched}")
    if result.routing is not None:
        lines.append(f"Routing: {result.routing.reasoning}")
    if result.latency_ms:
        lines.append(f"Latency: {result.latency_ms:.0f}ms")

    return "\n".join(lines).rstrip()


def _format_json(result: ResearchResult) -> str:
    """Format a ResearchResult as JSON."""
    payload: dict[str, Any] = {
        "query": result.query,
        "answer": {
            "text": result.answer.text,
            "model": result.answer.model,
            "citations": [
                {
                    "marker": c.marker,
                    "chunk_id": c.chunk_id,
                    "citation": c.chunk.citation,
                }
                for c in result.answer.citations
            ],
        },
        "chunks": [
            {
                "chunk_id": c.chunk_id,
                "source_type": c.source_type,
                "document_id": c.document_id,
                "content": c.content,
                "metadata": c.metadata,
                "citation": c.citation,
            }
            for c in result.chunks
        ],
        "sources_searched": result.sources_searched,
        "latency_ms": result.latency_ms,
    }
    if result.routing is not None:
        payload["routing"] = {
            "sources": [s.value for s in result.routing.sources],
            "confidence": result.routing.confidence,
            "reasoning": result.routing.reasoning,
        }
    return json.dumps(payload, indent=2, default=str, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Research command
# ---------------------------------------------------------------------------

def run_research(
    query: str,
    top_k: int = 5,
    ticker: str | None = None,
    standard_id: str | None = None,
    where: str | None = None,
    use_router: bool = True,
    output_format: str = "text",
    use_mock_llm: bool = False,
    chroma_dir: str | None = None,
    collection_name: str | None = None,
    jsonl_path: str | None = None,
) -> tuple[int, str]:
    """Run a research workflow and return (exit_code, output_string).

    Args:
        query: Natural-language research question.
        top_k: Number of chunks to retrieve.
        ticker: Optional Source B ticker filter.
        standard_id: Optional Source A standard ID filter.
        where: Optional raw ChromaDB where clause as JSON string.
        use_router: If True, use Router for multi-source search.
        output_format: "text" or "json".
        use_mock_llm: If True, use MockClient (no API key needed).
        chroma_dir: Optional override for ChromaDB persist directory.
        collection_name: Optional override for ChromaDB collection name.
        jsonl_path: Optional override for JSONL store path.

    Returns:
        (exit_code, output) tuple.
    """
    # Load .env file (if present) so ANTHROPIC_API_KEY is in os.environ
    _load_env_file()

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

    if output_format not in ("text", "json"):
        return 1, f"Error: unknown output format '{output_format}' (use 'text' or 'json')"

    # Build retriever
    from ..ingestion.embedder.embedder import Embedder
    from ..ingestion.storage.chroma_store import ChromaStore
    from ..ingestion.storage.json_store import JsonStore
    from ..knowledge_engineering.router import Router

    try:
        if chroma_dir or collection_name:
            chroma_kwargs: dict[str, Any] = {}
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

    # Build LLM client and answer generator
    try:
        if use_mock_llm:
            # Default mock response so the CLI is useful for demos without
            # an API key. Tests that need specific answers should call
            # run_research directly with their own MockClient.
            llm_client: Any = MockClient(
                response="(Mock LLM response — set ANTHROPIC_API_KEY and omit --use-mock-llm for real generation.)"
            )
        else:
            llm_client = AnthropicClient()
    except ValueError as exc:
        # Missing API key — clear error message
        return 5, f"Error: {exc}"
    except ImportError as exc:
        return 5, f"Error: {exc}"

    answer_generator = AnswerGenerator(llm_client=llm_client)

    # Build workflow
    workflow = ResearchWorkflow(
        retriever=retriever, answer_generator=answer_generator
    )

    # Run
    try:
        result = workflow.run(
            query=query,
            top_k=top_k,
            ticker=ticker,
            standard_id=standard_id,
            where=where_dict,
            use_router=use_router,
        )
    except WorkflowError as exc:
        logger.exception("Research workflow failed")
        return 5, f"Error: {exc}"
    except Exception as exc:
        logger.exception("Unexpected error in research workflow")
        return 5, f"Error: unexpected error: {exc}"

    # Format output
    if output_format == "json":
        return 0, _format_json(result)
    return 0, _format_text(result)


# ---------------------------------------------------------------------------
# Argparse entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """Entry point for `python -m src.research`."""
    # Load .env so ANTHROPIC_API_KEY is in os.environ before run_research is called
    _load_env_file()

    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m src.research",
        description="AuditAtlas Research — answer questions using the knowledge base",
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # workflow subcommand
    wf_p = subparsers.add_parser(
        "workflow", help="Run a research workflow (retrieve + answer)"
    )
    wf_p.add_argument("query", help="Natural-language research question")
    wf_p.add_argument("--top-k", type=int, default=5, help="Number of chunks to retrieve (default: 5)")
    wf_p.add_argument("--ticker", help="Source B ticker filter (e.g., AAPL)")
    wf_p.add_argument("--standard-id", dest="standard_id", help="Source A standard ID filter (e.g., AS1105)")
    wf_p.add_argument(
        "--where", help=(
            "Raw ChromaDB where clause as JSON object "
            "(e.g., '{\"source_type\": \"A\"}'). Merged with --ticker/--standard-id "
            "via ChromaDB $and. Conflicting values will be rejected by ChromaDB."
        ),
    )
    wf_p.add_argument(
        "--use-router", dest="use_router", action=argparse.BooleanOptionalAction,
        default=True, help="Use router for multi-source search (default: True)",
    )
    wf_p.add_argument(
        "--format", dest="output_format", choices=["text", "json"], default="text",
        help="Output format (default: text)",
    )
    wf_p.add_argument(
        "--use-mock-llm", dest="use_mock_llm", action="store_true",
        help="Use a mock LLM (no API key needed; for testing)",
    )
    wf_p.add_argument(
        "--chroma-dir", dest="chroma_dir", default=None,
        help="Override ChromaDB persist directory",
    )
    wf_p.add_argument(
        "--collection-name", dest="collection_name", default=None,
        help="Override ChromaDB collection name (default: audit_chunks)",
    )
    wf_p.add_argument(
        "--jsonl-path", dest="jsonl_path", default=None,
        help="Override JSONL store path",
    )

    args = parser.parse_args(argv)

    if args.command == "workflow":
        code, output = run_research(
            query=args.query,
            top_k=args.top_k,
            ticker=args.ticker,
            standard_id=args.standard_id,
            where=args.where,
            use_router=args.use_router,
            output_format=args.output_format,
            use_mock_llm=args.use_mock_llm,
            chroma_dir=args.chroma_dir,
            collection_name=args.collection_name,
            jsonl_path=args.jsonl_path,
        )
        print(output)
        return code

    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
