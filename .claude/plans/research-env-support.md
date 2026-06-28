# Plan: Research CLI .env File Support

## Context

The Phase 6 research CLI requires `ANTHROPIC_API_KEY` for real Claude responses. Currently users must export the key in their shell (`export ANTHROPIC_API_KEY=...` or `$env:ANTHROPIC_API_KEY = "..."` in PowerShell).

This is awkward for development — every new shell session needs the export. The standard solution is a project-root `.env` file that the CLI auto-loads, with the actual `.env` in `.gitignore` so secrets never get committed.

This is a small follow-up enhancement, not a numbered feature.

## Approach

### New files

- `.env.example` — template showing the required key format (committed)
- `tests/test_research/test_env_loading.py` — unit tests for .env loading

### Modify

- `pyproject.toml` — add `python-dotenv>=1.0.0` dependency
- `src/research/cli.py` — call `dotenv.load_dotenv()` before constructing the LLM client
- `.gitignore` — add `.env` (so secrets stay local)

### `.env.example`

```bash
# Anthropic API key for the research CLI
# Copy this file to .env and replace with your real key.
# Get one at: https://console.anthropic.com/settings/keys
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### `.gitignore` addition

```
# Environment variables
.env
```

### `src/research/cli.py` — load .env

Add a helper at the top of `cli.py`:

```python
def _load_env_file() -> None:
    """Load .env from the project root if present.

    Uses python-dotenv with `override=False` so that env vars already set in
    the shell take precedence over .env file values (12-factor app convention).
    """
    from dotenv import load_dotenv
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent.parent
    env_path = project_root / ".env"
    load_dotenv(dotenv_path=env_path, override=False)
```

Call `_load_env_file()` from `main()` and `run_research()`. Module-load-time call avoided so:
- Tests can control when loading happens
- Library users (importing `ResearchWorkflow`) don't trigger side effects
- CLI users always get loading

### Dependency

Add to `pyproject.toml`:
```toml
dependencies = [
    ...,
    "python-dotenv>=1.0.0",
]
```

### Tests

`tests/test_research/test_env_loading.py`:

1. **`test_load_dotenv_sets_anthropic_key_when_env_file_present`** — create temp .env with `ANTHROPIC_API_KEY=test-key`, call `_load_env_file()`, verify env var is set
2. **`test_load_dotenv_no_op_when_env_file_missing`** — call in directory without .env, no exception, no env var set
3. **`test_shell_env_var_takes_precedence_over_dotenv`** — both shell and .env set the key; shell wins
4. **`test_load_dotenv_handles_malformed_lines`** — file with comments, blank lines, lines without `=`, invalid values; should not crash
5. **`test_load_dotenv_ignores_quoted_values`** — `KEY="value with spaces"` is parsed correctly
6. **`test_run_research_loads_dotenv_before_checking_api_key`** — integration test: with .env file present but no shell var, `run_research()` succeeds (mock LLM would still need the key to be present in env)
7. **`test_run_research_use_mock_llm_does_not_require_dotenv`** — mock LLM path bypasses key check

### Critical files to be modified

- `pyproject.toml` — add `python-dotenv` dependency
- `src/research/cli.py` — add `_load_env_file()` helper + call from `main()` and `run_research()`
- `.gitignore` — add `.env`
- `.env.example` (new) — template
- `tests/test_research/test_env_loading.py` (new) — unit tests

## Verification

1. `pytest tests/test_research/test_env_loading.py` → all 7 tests pass
2. `pytest tests/` → full suite green, ≥328 tests (321 + 7 new)
3. Manual smoke (no env var set, .env file present):
   ```bash
   echo "ANTHROPIC_API_KEY=test-key" > .env
   python -c "import os; print(os.environ.get('ANTHROPIC_API_KEY'))"
   # Should print: test-key
   ```

## Out of Scope

- Multi-environment `.env.local` / `.env.production` precedence
- Encryption of secrets at rest
- Secret rotation tooling
- Loading `.env` from other directories (e.g., user's home)
- `python-dotenv` for the **retrieval CLI** (Phase 5) — Phase 5 doesn't use any API keys
