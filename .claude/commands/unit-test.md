# Run unit tests

Read `.claude/agents/unit-test-agent.md`. Analyze the current branch changes vs `main`, identify missing tests, generate them, and run the test suite.

## Behavior

1. Run `git diff main...HEAD --name-only` to get changed files
2. Identify functions/methods lacking tests
3. Write missing unit tests to `tests/` directory
4. Run `pytest tests/ -v` to verify all tests pass
5. Report: files analyzed, tests added, test results

---

## Run

```
/unit-test
```
