# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

AuditAtlas is an AI-powered Audit Research Assistant for audit professionals. The system combines retrieval, reasoning, and source attribution to provide evidence-backed answers with traceable citations.

**Current status**: Early-stage — documentation and data acquisition complete (Phases 1–2), actively working on Phase 3 (Knowledge Engineering).

## Branch Strategy

- `main` — production-ready code only
- `feat/FEATURE-XXX` — feature branches matching GitHub issue numbers
- Merge via PR after code review

## GitHub Issues

Project uses GitHub issues for tracking: `sumitdas1984/AuditAtlas`

Active issues:
- #3 (Knowledge Source Selection) — ✅ Closed
- #4 (Knowledge Engineering) — Phase 3, in progress
- #5–#9 — Future phases

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
| `docs/02_product_plan.md` | Target users, core features, success metrics |
| `docs/01_project_overview.md` | Project vision and problem statement |
| `.claude/commands/synthetic-audit-doc-gen.md` | Slash command definition |
| `.claude/agents/synthetic-audit-doc-gen.md` | Agent prompt template |

## Slash Commands

- `/synthetic-audit-doc-gen` — Generate synthetic audit documents for Source C

## When Creating New Features

1. Create a branch: `git checkout -b feat/FEATURE-XXX`
2. Work on the feature
3. Open a PR against `main`
4. Link the PR to the corresponding GitHub issue
