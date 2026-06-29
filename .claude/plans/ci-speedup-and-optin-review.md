# Plan: CI Speedup + Opt-in AI Code Review

## Context

Two pain points with the current `.github/workflows/`:

1. **CI runs the full 333-test suite on every PR push** — wall time ~3-9 min depending on hardware. This slows the feedback loop and wastes GitHub Actions minutes.
2. **Code-review pipeline runs on every PR event** (`opened`, `synchronize`, `reopened`) and calls Claude API on every push — significant token cost with limited marginal value (humans review too).

Goal: cut CI time and AI-review cost **without losing safety** (tests must still gate merges) or causing confusion (opt-in trigger must be discoverable).

## Approach

### 1. CI: speed up test execution (`ci.yml`)

Three changes that compound:

**a) Cache the sentence-transformers model**

The `all-MiniLM-L6-v2` model (~80MB) downloads on every CI run. Cache `~/.cache/huggingface` keyed on `pyproject.toml` hash so the model is reused across runs.

```yaml
- name: Cache sentence-transformers model
  uses: actions/cache@v4
  with:
    path: ~/.cache/huggingface
    key: ${{ runner.os }}-st-model-${{ hashFiles('pyproject.toml') }}
```

**b) Run tests in parallel with `pytest-xdist`**

`pytest -n auto` uses all available cores. On GitHub-hosted `ubuntu-latest` (2 cores), this gives ~1.7-1.9× speedup. On larger runners it's even better.

Add `pytest-xdist` to install step, add `-n auto` to test command.

**c) Skip subprocess-based tests in CI (not local)**

Subprocess tests in `tests/test_research/test_integration.py::TestResearchCliSubprocess` re-test behavior already verified in-process by `TestResearchRunResearch`. They cost 5-15s each in CI. **Note**: these aren't yet marked. Two options:

- (i) Add `@pytest.mark.slow` to each subprocess test, then `-m "not slow"` in CI
- (ii) Leave subprocess tests in CI for now (they're the only ones touching `python -m src.research`)

→ **Pick (i)** — marker is reusable for future slowness tagging; the cleanup is small (8-10 tests to mark). Use the existing `pytest -m` selector in CI: `pytest -m "not slow"`.

**Updated CI shape:**

```yaml
- run: pip install -e . pytest pytest-cov pytest-xdist

- name: Cache sentence-transformers model
  uses: actions/cache@v4
  with:
    path: ~/.cache/huggingface
    key: ${{ runner.os }}-st-model-${{ hashFiles('pyproject.toml') }}

- name: Run tests
  run: python -m pytest tests/ -n auto -m "not slow" -v --cov=src --cov-report=term-missing
```

**Register the marker** in `pyproject.toml` so `-m "not slow"` doesn't warn:

```toml
[tool.pytest.ini_options]
pythonpath = ["."]
markers = [
    "slow: tests that spawn subprocesses or have multi-second runtime (CI skips these)",
]
```

**Expected impact**: 333→318 tests × parallel × cache hit × subprocess-skip = **~1-2 min per CI run** (down from 3-9 min). Slow tests still run locally; CI just doesn't gate on them.

### 2. Code-review: opt-in via PR label (`code-review.yml`)

Change trigger so the review job only runs when the PR has the `ai-review` label.

```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened, labeled, unlabeled]

jobs:
  review:
    if: contains(github.event.pull_request.labels.*.name, 'ai-review')
    runs-on: ubuntu-latest
    ...
```

The `if:` short-circuits the job — no checkout, no API call, zero token cost — when the label isn't present. The `labeled`/`unlabeled` types ensure adding/removing the label triggers a re-evaluation.

**Workflow for the user**: when you want an AI review on a PR, add the `ai-review` label. Add/remove the label any time to re-trigger or stop.

**Auto-create the label** via a one-time repo setting (manual step outside this PR — I'll include instructions in the PR body).

## Files modified

| File | Change |
|---|---|
| `.github/workflows/ci.yml` | Add cache step, install pytest-xdist, add `-n auto -m "not slow"` to pytest invocation |
| `pyproject.toml` | Add `pytest-xdist` to test deps; register `slow` marker |
| `tests/test_research/test_integration.py` | Mark subprocess tests with `@pytest.mark.slow` |
| `.github/workflows/code-review.yml` | Add `if:` gate requiring `ai-review` label; expand `types:` to include `labeled`/`unlabeled` |

**No source code changes.**

## Verification

1. **Local**: `pytest tests/ -m "not slow"` should pass and run faster than full suite. Confirm subprocess tests in `tests/test_research/test_integration.py::TestResearchCliSubprocess` get skipped.
2. **Local**: `pytest tests/` (no marker) still runs everything including slow tests.
3. **CI**: push branch → CI workflow runs → check Actions tab for cache hit and parallel test output.
4. **Code review**: open a test PR WITHOUT the `ai-review` label → no review comment posted. Add the label → review fires within seconds.

## Risk

- **CI skip-slow**: small — slow tests still run locally; they're integration-level so CI gating on them wasn't strictly necessary.
- **Code-review label**: zero — workflow is a no-op when label absent. If you forget to add the label and wanted a review, just add it.
- **xdist**: very low — sentence-transformers + chromadb are thread-safe at the level we use them; if any test breaks we'll see it in local runs first.

## Out of scope

- Splitting CI into fast/slow workflows (single workflow with marker is enough)
- Replacing `claude-opus-4-7` in `run_review.py` with a cheaper model
- Required status checks for label application