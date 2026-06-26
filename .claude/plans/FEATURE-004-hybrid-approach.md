# Plan: Hybrid Approach — Metadata + Vector Embeddings

## Overview

The hybrid approach combines structured metadata storage with vector embeddings for semantic search. Both are created during ingestion, and both are used during retrieval.

---

## Ingestion Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           INGESTION PIPELINE                                │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────────┐
  │   Document   │────▶│    Parser    │────▶│   Structured Output      │
  │   (Source)   │     │              │     │   - document_id           │
  │              │     │              │     │   - document_type         │
  │  .md / .pdf  │     │  Extracts:   │     │   - metadata fields      │
  │              │     │  - content   │     │   - raw text             │
  └──────────────┘     │  - metadata  │     └────────────┬─────────────┘
                       │  - headings  │                  │
                       └──────────────┘                  │
                                                       ▼
  ┌───────────────────────────────────────────────────────────────────────┐
  │                          CHUNKER                                      │
  │                                                                       │
  │   Input: Structured document                                           │
  │   Output: List of chunks                                              │
  │                                                                       │
  │   Each chunk gets:                                                    │
  │   - chunk_id (per Phase 3 chunking strategy)                         │
  │   - content (text content)                                             │
  │   - metadata (source-specific fields)                                   │
  │   - section reference                                                  │
  └────────────────────────────────┬──────────────────────────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                              ▼
  ┌─────────────────────────┐        ┌─────────────────────────┐
  │   JSON / SQLite Store   │        │   Vector Embedding      │
  │                         │        │                         │
  │ Stores:                 │        │ Creates:                 │
  │ - chunk_id              │        │ - embedding vector       │
  │ - document_id           │        │   for chunk content      │
  │ - content              │        │                         │
  │ - metadata             │        │ Uses:                    │
  │ - source_type          │        │ - chunk content text     │
  │                         │        │ - embedding model        │
  │ Purpose:                │        │   (OpenAI/sentence-      │
  │ - Exact lookups         │        │   transformers)        │
  │ - Citation reference    │        │                         │
  │ - Metadata filtering    │        │ Purpose:                │
  │                         │        │ - Semantic search        │
  └─────────────────────────┘        │ - Similarity matching    │
                                     └────────────┬────────────┘
                                                  │
                                                  ▼
                               ┌─────────────────────────┐
                               │   ChromaDB / Vector DB  │
                               │                         │
                               │ Stores:                 │
                               │ - chunk_id (reference)  │
                               │ - embedding vector      │
                               │ - metadata (for         │
                               │   filtering)           │
                               └─────────────────────────┘
```

---

## Retrieval Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          RETRIEVAL PIPELINE                                 │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────────┐
  │    User      │────▶│    Router    │────▶│   Source Routing         │
  │   Query      │     │  (Phase 3)   │     │   A / B / C / Multiple   │
  │              │     │              │     └────────────┬─────────────┘
  │ "What are    │     │ Classifies:   │                  │
  │  risk factors│     │ - topic       │                  │
  │  for Apple?" │     │ - intent      │                  │
  └──────────────┘     │ - scope       │                  │
                       └──────────────┘                  │
                                                        ▼
                    ┌─────────────────────────────────────────────────────┐
                    │              VECTOR SEARCH (ChromaDB)               │
                    │                                                      │
                    │  1. Generate embedding for query                     │
                    │     query_text → embedding_vector                    │
                    │                                                      │
                    │  2. Search vector DB with:                           │
                    │     - query embedding                                │
                    │     - metadata filter (source_type = routed source)   │
                    │                                                      │
                    │  3. Returns top-K chunks with similarity scores      │
                    │     - chunk_id                                       │
                    │     - similarity_score (0-1)                          │
                    │     - content                                        │
                    └────────────────────────┬──────────────────────────────┘
                                             │
                    ┌────────────────────────┴────────────────────────┐
                    ▼                                                 ▼
  ┌─────────────────────────┐        ┌─────────────────────────────┐
  │   JSON Store Lookup     │        │   RESULT RANKING / FUSION   │
  │                         │        │                             │
  │ Get full chunk by:      │        │ Combine:                    │
  │ - chunk_id              │        │ - vector similarity scores  │
  │                         │        │ - keyword match scores      │
  │ Returns:                │        │ - metadata relevance        │
  │ - content               │        │                             │
  │ - metadata              │        │ Rank and return top chunks │
  │ - citation info         │        │                             │
  └─────────────────────────┘        └──────────────┬──────────────┘
                                                    │
                                                    ▼
                    ┌─────────────────────────────────────────────────────┐
                    │                 RESPONSE GENERATOR                  │
                    │                                                      │
                    │  Input: Top ranked chunks                           │
                    │  Output: Natural language answer + citations        │
                    │                                                      │
                    │  Citations from chunk metadata:                      │
                    │  - Source A: [AS 1105 § .12]                        │
                    │  - Source B: [AAPL 10-K, Item 1A (2025)]            │
                    │  - Source C: [InternalAuditReport:2025-H-001]       │
                    └─────────────────────────────────────────────────────┘
```

---

## Metadata Creation & Usage

### During Ingestion

| Metadata Field | Created By | Stored In | Used For |
|---------------|------------|-----------|----------|
| `chunk_id` | Chunker | JSON + Vector DB | Citation anchor |
| `document_id` | Parser | JSON | Document grouping |
| `document_type` | Parser | JSON + Vector DB | Source filtering |
| `standard_id` / `ticker` | Parser | JSON + Vector DB | Source-specific queries |
| `effective_date` / `fiscal_year` | Parser | JSON + Vector DB | Temporal filtering |
| `classification` | Parser | JSON | Access control |
| `section` | Chunker | JSON | Section navigation |
| `content` (text) | Chunker | JSON | Exact match search |
| `content` (embedding) | Embedding model | Vector DB | Semantic search |

### During Retrieval

| Metadata Usage | Purpose |
|---------------|---------|
| `source_type` filter | Route to correct source (A/B/C) |
| `document_type` filter | Narrow by doc type |
| `ticker` / `standard_id` | Specific company/standard queries |
| `effective_date` | Temporal queries ("latest") |
| `chunk_id` | Exact citation generation |

---

## Vector Embedding Creation & Usage

### Creation (Ingestion)

```
Chunk Content Text
        │
        ▼
┌───────────────────┐
│  Embedding Model  │
│                   │
│  Options:          │
│  - OpenAI (ada,   │
│    gpt-3.5)       │
│  - sentence-       │
│    transformers   │
│    (local)         │
│  - Cohere         │
└─────────┬─────────┘
          │
          ▼
   [0.123, -0.456, 0.789, ...]
   (1536-dimensional vector for OpenAI ada)
   (384-dim for sentence-transformers)
          │
          ▼
┌───────────────────┐
│     ChromaDB      │
│                   │
│ Stores:           │
│ - embeddings       │
│ - chunk_id (ref)  │
│ - metadata        │
└───────────────────┘
```

### Usage (Retrieval)

```
User Query
    │
    ▼
┌───────────────────┐
│  Same Embedding   │
│  Model            │
└─────────┬─────────┘
          │
          ▼
   [0.234, -0.123, 0.567, ...]
          │
          ▼
┌───────────────────┐
│     ChromaDB      │
│                   │
│ .similarity_search│
│ - query_vector    │
│ - n_results=10    │
│ - where filter    │
│   (source_type)   │
└─────────┬─────────┘
          │
          ▼
  Top-K chunks with
  similarity scores
```

---

## Key Design Decisions

1. **Chunk ID is the join key** — Vector DB stores `chunk_id` as metadata, not the full chunk. Join with JSON store to get full content.

2. **Metadata filtering at query time** — Router determines source type (A/B/C), Vector DB filters by `source_type` before semantic search.

3. **Embedding model choice**:
   - **OpenAI ada-002**: Best quality, requires API key + cost
   - **Sentence-transformers (all-MiniLM-L6-v2)**: Good enough, runs locally, free

4. **Storage split**:
   - **JSON**: Source of truth for metadata and content
   - **ChromaDB**: Search index only (can rebuild from JSON)

---

## Simplest Hybrid MVP Setup

```
ChromaDB (local, no API key)
├── collection: "audit_chunks"
│   ├── embeddings: [vectors]
│   ├── documents: [chunk_id only]
│   └── metadatas: [{source_type, document_type, chunk_id}]
│
JSON Store (source of truth)
└── chunks.json: [{chunk_id, content, metadata, citation_info}]
```

This is the recommended MVP approach. No API keys needed, runs offline, and can be upgraded to OpenAI later.