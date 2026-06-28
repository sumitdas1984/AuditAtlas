# unit-test-agent — AuditAtlas Unit Test Generator

## Description

Analyzes code changes on the current branch, identifies functions/methods lacking unit tests, generates missing tests, and verifies the test suite passes.

## Run

```
/unit-test
```

## Behavior

1. **Analyze current branch vs main**
   - Run `git diff main...HEAD --name-only` to get changed Python files
   - Run `git diff main...HEAD` to get the actual diff content

2. **Identify test coverage gaps**
   - For each changed `.py` file in `src/`, check if a corresponding test file exists in `tests/`
   - Use static analysis to identify functions/methods without `test_` prefixes
   - Prioritize: ingestion pipeline, retrieval, router, citation formatter, embedder

3. **Generate missing unit tests**
   - Use pytest fixtures where appropriate
   - Mock external dependencies (ChromaDB, sentence-transformers, file I/O)
   - Cover happy path + at least one edge case per function
   - Follow existing test patterns in the codebase

4. **Run test suite**
   - Execute `python -m pytest tests/ -v` to verify all tests pass
   - If tests fail, diagnose and fix or report issues

5. **Report**
   - List files analyzed
   - List tests added/enhanced
   - List any coverage gaps that remain
   - Report pytest result (pass/fail)

## Constraints

- Only write to `tests/` directory
- Do not modify source code
- If a test file already exists, add new tests to it (don't overwrite)
- Use pytest as the test framework
- Follow existing test naming conventions: `test_<module>_<function>.py`
