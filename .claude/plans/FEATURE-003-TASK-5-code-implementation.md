# Plan: FEATURE-003-TASK-5 — Schema and Router Code Implementation

## Context

TASK-5 implements the schemas, routing, and citation logic as code. This is the bridge between the design documents (TASK-1 through TASK-4) and Phase 4 (Data Ingestion).

Building on:
- TASK-1 schemas: 8 fields (Source A), 7 fields (Source B), 9 fields (Source C)
- TASK-2 chunk IDs: `{standard_id}.{paragraph}`, `{ticker}.{year}.{item}`, `{doc_id}.{section}`
- TASK-3 citation formats: `[AS {id} § {paragraph}]`, `[{ticker} 10-K, {item} ({year})]`, `[{doc_type}:{ref_id}]`
- TASK-4 routing rules: topic/intent/scope axes, routing table

## Approach

### Directory Structure

```
src/knowledge_engineering/
├── schemas/
│   ├── source_a_schema.yaml   # PCAOB Standards metadata
│   ├── source_b_schema.yaml   # SEC 10-K metadata
│   └── source_c_schema.yaml   # Synthetic Docs metadata
├── models/
│   ├── source_a.py            # Pydantic models for Source A
│   ├── source_b.py            # Pydantic models for Source B
│   └── source_c.py            # Pydantic models for Source C
├── router.py                  # Query classification and routing
├── citation.py                # Citation formatting utilities
└── __init__.py
```

### Schema Files (YAML)

Each schema YAML mirrors the field definitions from TASK-1:
- `source_a_schema.yaml`: standard_id, title, document_type, issue_date, effective_date, status, source_url, file_path
- `source_b_schema.yaml`: company_name, ticker, filing_date, fiscal_year, sections_present, source_url, file_path
- `source_c_schema.yaml`: document_id, document_type, version, effective_date, review_date, classification, owner, company, file_path

### Pydantic Models

Typed Python classes for runtime validation:
- `SourceA_Document`: fields matching source_a_schema.yaml
- `SourceB_Document`: fields matching source_b_schema.yaml
- `SourceC_Document`: fields matching source_c_schema.yaml

### Router Module (`router.py`)

```
class QueryClassifier:
    def classify(query: str) -> ClassificationResult:
        # Returns: topic, intent, scope, primary_sources, secondary_sources

    def route(query: str) -> RoutingResult:
        # Returns: list of sources to query, ranked

class RoutingResult:
    sources: list[Source]
    confidence: float
    reasoning: str
```

- `classify()`: parses query text, extracts topic/intent/scope
- `route()`: applies routing rules from TASK-4, returns ordered source list
- Keyword extraction for topic detection (e.g., "PCAOB", "risk factors", "audit findings")
- Intent detection via pattern matching (question words: "what is" → definition, "show me" → finding)

### Citation Module (`citation.py`)

```
def format_citation(chunk_id: str, source_type: str) -> str:
    # Converts chunk_id to human-readable citation

def parse_citation(citation: str) -> dict:
    # Parses citation string back to (source_type, chunk_id)

def format_compound(citations: list[str]) -> str:
    # Joins multiple citations with semicolons
```

| Source | Chunk ID Format | Citation Output |
|--------|----------------|-----------------|
| A | `AS1105.12` | `[AS 1105 § .12]` |
| B | `AAPL.2025.Item1A` | `[AAPL 10-K, Item 1A (2025)]` |
| C | `IA-2026-004.3.1` | `[InternalAuditReport:2025-H-001]` |

## Output

Create `src/knowledge_engineering/` directory with:
- `schemas/` — YAML schema definitions (3 files)
- `models/` — Pydantic models (3 files)
- `router.py` — Query classification and routing logic
- `citation.py` — Citation formatting utilities
- `__init__.py` — Package exports

## Verification

- Citation formatter produces exact output specified in TASK-3
- Router classifies queries into all three axes (topic, intent, scope)
- Router routes each query to at least one source
- Pydantic models validate all fields from TASK-1 schemas
- Unit tests for citation formatting and routing logic

## Dependencies

- Phase 4 (Data Ingestion) — will import these schemas and utilities
- No external API calls — pure local logic

## Out of Scope for MVP

- Integration with vector store or retrieval engine
- Configuration file for routing weights
- User feedback loop for routing improvement