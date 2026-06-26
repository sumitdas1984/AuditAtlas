# Multi-Source Query Routing — Knowledge Engineering

**Phase**: 3 — Knowledge Engineering
**Issue**: FEATURE-003-TASK-4 (#14)
**Status**: Complete

---

## Overview

Query routing determines which sources are searched for a given user question and how results are combined. Every query is classified along three axes — topic, intent, and scope — to route to the right sources.

---

## Query Classification Taxonomy

### Axis 1 — Topic

| Topic | Description | Primary Sources |
|-------|-------------|-----------------|
| `audit_standards` | PCAOB rules, guidance, releases | A |
| `risk_factors` | SEC 10-K risk factor sections | B |
| `financials` | SEC 10-K financial statements, MD&A | B |
| `internal_controls` | Control frameworks and evaluations | A, C |
| `audit_findings` | Internal audit observations | C |
| `risk_register` | Risk entries and ratings | C |
| `policy_procedure` | Policies, procedures, SOPs | C |
| `compliance` | Regulatory compliance requirements | A, B, C |

### Axis 2 — Intent

| Intent | Description |
|--------|-------------|
| `definition` | "What is X?" — return conceptual explanation |
| `requirement` | "What does the standard require?" — return mandate |
| `finding` | "Show me findings about Y" — return specific observations |
| `example` | "Give an example of X" — return illustrative case |
| `comparison` | "How does X differ from Y?" — return comparative analysis |

### Axis 3 — Scope

| Scope | Description |
|-------|-------------|
| `specific` | Query names a specific company or standard (e.g., "AAPL risk factors", "AS 1105") |
| `general` | Query asks about a topic without specifying a source (e.g., "what are risk factors for tech companies?") |

---

## Topic-Based Routing

| Query Pattern | Primary Source | Secondary Source |
|--------------|----------------|------------------|
| "What does PCAOB say about X?" | A | — |
| "What are the risk factors for X?" | B | C (if internal risk) |
| "How does company X handle Y?" | B + C | A (if standards reference) |
| "What controls exist for X?" | C (Control Matrix) | A (if standards reference) |
| "Show me audit findings for X" | C (Internal Audit Report) | — |
| "What is the policy on X?" | C (Policy/SOP) | — |
| "Compare X and Y" | A + B + C | — |
| Unclassified | All sources | Ranked by relevance |

---

## Intent-Based Routing

| Intent | Behavior |
|--------|----------|
| `definition` | Route to conceptual sources — A (standards) and C (policies) |
| `requirement` | Route to Source A only — authoritative standards only |
| `finding` | Route to Source C — Internal Audit Report |
| `example` | Route to Source C first, then Source B (10-K examples) |
| `comparison` | Aggregate from all relevant sources |

---

## Scope-Based Routing

| Scope | Behavior |
|-------|----------|
| `specific` | Route to the named source only (e.g., "AS 1105" → Source A only) |
| `general` | Route to all sources, rank by topic keyword overlap |

---

## Compound Query Handling

Queries spanning multiple topics route to multiple sources and results are aggregated by source.

**Example:**
- "What are AAPL's risk factors and how do they compare to AMZN's?"
- Routes to: Source B (AAPL 10-K + AMZN 10-K)
- Aggregated by risk category (operational, financial, regulatory)

---

## Default Fallback

If classification fails or query is ambiguous:
1. Route to all three sources
2. Rank results by topical keyword overlap
3. Return top chunks from each source with citations

---

## Routing Summary

| Source | Reachable From |
|--------|----------------|
| A — PCAOB Standards | `audit_standards`, `internal_controls`, `compliance` topics; `requirement` intent |
| B — SEC 10-K | `risk_factors`, `financials` topics; `comparison` intent; `specific` scope (named ticker) |
| C — Synthetic Docs | `audit_findings`, `risk_register`, `policy_procedure`, `internal_controls` topics; `finding`, `example` intent |

---

## Out of Scope for MVP

- **Learning-based routing** — adjusting routes based on user feedback
- **Context carryover** — maintaining conversation context across queries
- **Dynamic source weighting** — re-ranking sources based on result quality