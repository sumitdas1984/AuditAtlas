# Plan: FEATURE-003-TASK-4 — Multi-Source Query Routing

## Context

TASK-4 defines how a user query routes to relevant sources and how results are aggregated. TASK-3 citation strategy tells us what citations look like; this task determines which sources get queried for a given question.

Building on TASK-1 schemas and TASK-2 chunk IDs:
- Source A (PCAOB): topic axis covers audit standards, internal controls, quality control
- Source B (SEC 10-K): topic axis covers risk factors, MD&A, financial statements, controls
- Source C (Synthetic): topic axis covers findings, controls, risks, policies, procedures

## Approach

### Query Classification Taxonomy

Each query is classified along three axes:

**Axis 1 — Topic**
- `audit_standards` — PCAOB rules, guidance, releases
- `risk_factors` — SEC 10-K risk factor sections
- `financials` — SEC 10-K financial statements, MD&A
- `internal_controls` — Source A (standards) + Source C (control matrix)
- `audit_findings` — Source C (internal audit report)
- `risk_register` — Source C (risk register)
- `policy_procedure` — Source C (policies, SOPs)
- `compliance` — Cross-source (standards + risk factors + policies)

**Axis 2 — Intent**
- `definition` — "What is X?" → return conceptual explanation
- `requirement` — "What does the standard require?" → return mandate
- `finding` — "Show me findings about Y" → return specific observations
- `example` — "Give an example of X" → return illustrative case
- `comparison` — "How does X differ from Y?" → return comparative analysis

**Axis 3 — Scope**
- `specific` — Query references a specific company or standard (e.g., "AAPL risk factors", "AS 1105")
- `general` — Query asks about a topic without specifying a source (e.g., "what are risk factors for tech companies?")

### Routing Rules

| Topic Query | Primary Source | Secondary Source |
|-------------|----------------|------------------|
| "What does PCAOB say about X?" | A | — |
| "What are the risk factors for X?" | B | C (if internal risk) |
| "How does company X handle Y?" | B + C | A (if standards-based) |
| "What controls exist for X?" | C (Control Matrix) | A (if standards reference) |
| "Show me audit findings for X" | C (Internal Audit Report) | — |
| "What is the policy on X?" | C (Policy/SOP) | — |
| "Compare X and Y" | A + B + C (comparison) | — |
| Unclassified | All sources, ranked by relevance | — |

### Intent Routing

| Intent | Behavior |
|--------|----------|
| `definition` | Route to conceptual sources (A for standards, C for policies) |
| `requirement` | Route to Source A only (authoritative standards) |
| `finding` | Route to Source C (Internal Audit Report) |
| `example` | Route to Source C first, then B |
| `comparison` | Aggregate from all relevant sources |

### Scope Routing

| Scope | Behavior |
|-------|----------|
| `specific` | Route to the named source only |
| `general` | Route to all sources, rank by topic relevance |

### Compound Query Handling

Queries that span multiple topics route to multiple sources and results are aggregated. Example:
- "What are AAPL's risk factors and how do they compare to AMZN's?" → Source B (AAPL 10-K + AMZN 10-K), aggregated by risk category

### Default Fallback

If classification fails or query is ambiguous: route to all sources, rank by topical keyword overlap.

## Output

Create `docs/knowledge_engineering/08_query_routing.md` with:
1. Query classification taxonomy (topic, intent, scope axes)
2. Routing rules table (topic → source mapping)
3. Intent-based routing
4. Scope-based routing
5. Compound query handling
6. Default fallback behavior

## Verification

- Every source type is reachable from some query pattern
- Compound queries aggregate from multiple sources
- Routing rules are consistent with citation formats from TASK-3
- Ambiguous queries have a defined fallback