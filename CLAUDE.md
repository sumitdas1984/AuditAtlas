# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

AuditAtlas is an AI-powered Audit Research Assistant for audit professionals. The system combines retrieval, reasoning, and source attribution to provide evidence-backed answers with traceable citations.

**Current status**: Phase 4 (Data Ingestion) complete. Phase 5 (Retrieval System) in progress — TASK-5-1, TASK-5-2, TASK-5-3 done. TASK-5-4 (CLI, integration tests, docs) next.

## Branch Strategy

- `main` — production-ready code only
- `feat/FEATURE-XXX` — feature branches matching GitHub issue numbers
- Merge via PR after code review

## GitHub Issues

Project uses GitHub issues for tracking: `sumitdas1984/AuditAtlas`

Completed:
- #3 (Knowledge Source Selection) — ✅ Closed
- #4 (Knowledge Engineering) — ✅ Phase 3 complete
- #5 (Data Ingestion) — ✅ Phase 4 complete
- #25 (TASK-5-1 Core Retriever) — ✅ Closed
- #26 (TASK-5-2 Metadata Filtering) — ✅ Closed
- #27 (TASK-5-3 Router Integration) — ✅ Closed

In progress:
- #6 (Retrieval System) — Phase 5 (TASK-5-4 remaining)

Future:
- #7–#9 — Phases 6–8

## Synthetic Document Generation

Use the `/synthetic-audit-doc-gen` slash command to generate audit documents for Source C:

```
/synthetic-audit-doc-gen <Document Type>
```

Document types: Internal Audit Report, Risk Register, Control Matrix, Policies and Procedures, SOP for Vendor Onboarding

## Data Directory Structure

```
data/
  pcaob_standards/   # Source A — PCAOB auditing standards (PDF)
  sec_10k/           # Source B — SEC 10-K filings (PDF)
  synthetic_company_docs/  # Source C — Synthetic audit documents (Markdown)
```

## Key Files

| File | Purpose |
|------|---------|
| `docs/03_project_plan.md` | Phase roadmap and status |
| `docs/04_knowledge_sources.md` | Source definitions, scope, acquisition status |
| `docs/knowledge_engineering/` | Phase 3 outputs — schema, chunking, citation, routing |
| `src/knowledge_engineering/` | Phase 3 code — schemas, models, router, citation |
| `docs/data_ingestion/` | Phase 4 ingestion design documents |
| `src/ingestion/` | Phase 4 ingestion pipeline code |
| `src/retrieval/` | Phase 5 retrieval layer — Retriever, SearchResult, RetrievedChunk |
| `docs/02_product_plan.md` | Target users, core features, success metrics |
| `docs/01_project_overview.md` | Project vision and problem statement |
| `.claude/commands/` | Slash command definitions |
| `.claude/agents/` | Agent prompt templates |

## Slash Commands

- `/synthetic-audit-doc-gen` — Generate synthetic audit documents for Source C
- `/unit-test` — Analyze code changes and add missing unit tests (run after implementing)
- `/doc-sync` — Sync documentation with code changes (run after `/unit-test`)

## Dependencies

| Package | Purpose |
|---------|---------|
| `pydantic` | Data validation |
| `pytest` | Testing |
| `chromadb` | Vector database |
| `sentence-transformers` | Embedding model (all-MiniLM-L6-v2) |
| `python-frontmatter` | Markdown frontmatter parsing |
| `pypdf` | PDF text extraction |

## When Creating New Features

1. Create a branch: `git checkout -b feat/FEATURE-XXX`
2. Work on the feature
3. Open a PR against `main`
4. Link the PR to the corresponding GitHub issue
