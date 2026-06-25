# Generate a synthetic audit document

Read `.claude/agents/synthetic-audit-doc-gen.md`. Generate the document using the base prompt, substituting `<Document Type>` with the document type provided by the user.

Save the output to `data/synthetic_company_docs/01-<Document Type>.md` where `<Document Type>` is the user's input with spaces replaced by hyphens (e.g., `Risk Register` → `Risk-Register`).

Output only the path to the saved file.

---

## Run

```
/synthetic-audit-doc-gen <Document Type>
```

**Available document types:**
- Internal Audit Report
- Risk Register
- Control Documentation
- Policies and Procedures
- Audit Issue Tracker

**Example:**
```
/synthetic-audit-doc-gen Risk Register
```
