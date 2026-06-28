# Knowledge Sources

## Source A — PCAOB Auditing Standards

**Description**: Authoritative audit guidance used as the primary source of truth for audit procedures and requirements.

**Source Location**: https://pcaobus.org/oversight/standards/auditing-standards

**Scope for MVP**:
- 6 PCAOB documents (PDF format)
- Current versions only — no historical versions

**MVP documents**:
- AS 1000 — General Responsibilities of the Auditor
- QC 1000 — Quality Control
- Risk Assessment (release_2010-004)
- Staff Guidance documents
- Rulemaking releases

**Out of Scope**: ASB standards, historical versions, older PCAOB standards not currently effective.

---

## Source B — SEC 10-K Filings

**Description**: Public company annual disclosures used as supporting evidence for risk and control research.

**Source Location**: https://www.sec.gov/search-filings

**Scope for MVP**:
- 5 companies — AAPL, AMZN, JPM, MSFT, TSLA (selected during Phase 2 evaluation)
- Latest filing only — no prior year comparisons
- 10-K annual reports only — no 10-Qs or 8-Ks

**Out of Scope**: 10-Q quarterly filings, 8-K current reports, proxy statements, SEC comment letters.

---

## Source C — Synthetic Company Documents

**Description**: Organization-specific internal documents used for demonstrating internal audit and compliance research workflows.

**Scope for MVP**:
- 5 document types
- 5 documents total (1 per type)
- Synthetically generated for MVP purposes — no real company data

**Document types**:
- Internal Audit Report
- Risk Register
- Control Matrix
- Policies and Procedures
- SOP for Vendor Onboarding

**Out of Scope**: Real company confidential documents, non-synthetic data.

**Data Acquisition**: Generated using Claude Code agent (`synthetic-audit-doc-gen`) with a fictional company "Northwind Retail Solutions Ltd." as the subject. Documents stored in `data/raw/synthetic_company_docs/`.

---

## Data Handling

| Source | Format | Volume (MVP) | Update Frequency |
|---|---|---|---|
| PCAOB Standards | PDF | 6 documents | As issued |
| SEC 10-K Filings | PDF | 5 filings | On filing release |
| Synthetic Docs | Markdown | 5 documents | Static for MVP |
