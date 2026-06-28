# doc-sync-agent — Documentation Synchronization Agent

## Description

Analyzes recent code/data changes and updates project documentation to keep it in sync. Runs after `/unit-test` when new source files or dependencies are added.

## Run

```
/doc-sync
```

## Behavior

### 1. Check dependency sync

Compare `pyproject.toml` dependencies with `CLAUDE.md` dependency section. If new packages are in `pyproject.toml` but not in `CLAUDE.md`, add them.

### 2. Check source inventory sync

Compare actual files in `data/raw/*/` with docs in:
- `docs/04_knowledge_sources.md` — lists document counts per source
- `docs/knowledge_engineering/05_schema_design.md` — lists file paths

If new files exist in `data/raw/` but aren't documented, update the docs.

### 3. Check directory structure sync

If new `src/` directories or major files exist, update `CLAUDE.md` key files table.

### 4. Report changes

- List what was updated
- List what couldn't be auto-updated (needs manual review)

## Constraints

- Only update `CLAUDE.md`, `docs/04_knowledge_sources.md`, `docs/knowledge_engineering/05_schema_design.md`
- Do not change design decisions or add new documentation
- If a change requires judgment, skip and report it
- Always show diff before writing
