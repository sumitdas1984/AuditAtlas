# synthetic-audit-doc-gen — Synthetic Document Generator

## Description
Generates realistic synthetic enterprise audit documents for AuditAtlas MVP demos.

## Base Prompt

Generate a realistic synthetic enterprise document for use in an AI-powered Audit Research Assistant (AuditAtlas).

Requirements:

* The document must be completely fictional.
* Do not use or resemble any real company, person, or confidential information.
* Create a fictional company named "Northwind Retail Solutions Ltd."
* The company operates as a mid-sized retail and e-commerce business.
* The document should resemble what an auditor would encounter in a real organization.
* Use professional business language.
* Include appropriate headings, numbered sections, tables where appropriate, and realistic details.
* The document should be approximately 4–6 pages in length (around 1500–2500 words).
* Include sufficient detail so that it can be used for Retrieval-Augmented Generation (RAG), semantic search, metadata extraction, and citation generation.
* Include information that could answer audit-related questions about controls, risks, responsibilities, approvals, compliance, and business processes.
* Do not mention that the document is synthetic.

Generate the following document:

`<Document Type>`

Output only the document in Markdown format.


