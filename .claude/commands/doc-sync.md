# Sync documentation

Read `.claude/agents/doc-sync-agent.md`. Analyze recent changes to dependencies, source files, and directories. Update `CLAUDE.md`, `docs/04_knowledge_sources.md`, and `docs/knowledge_engineering/05_schema_design.md` if they are out of sync.

Show diff before making any changes.

---

## Run

```
/doc-sync
```

**Run after:** `/unit-test` — when new code, dependencies, or source files are added
