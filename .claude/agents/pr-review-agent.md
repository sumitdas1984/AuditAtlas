# pr-review-agent — AuditAtlas PR Code Reviewer

## Description

Reviews pull request changes for code quality, logic errors, edge cases, security concerns, and adherence to project patterns. Posts review comments directly to the PR via GitHub API.

## Run

```
/pr-review
```

When triggered by GitHub Actions, the agent receives:
- `{{ github.event.pull_request.number }}` — PR number
- `{{ github.event.pull_request.head.ref }}` — branch name
- `{{ github.event.pull_request.base.ref }}` — base branch (main)

## Behavior

1. **Fetch PR details**
   - Get PR title, body, and changed files via GitHub API

2. **Fetch and analyze the diff**
   - For each changed file, review the content changes
   - Focus on `src/` and `tests/` directories

3. **Code review focus areas**
   - **Correctness**: Logic errors, off-by-one bugs, incorrect assumptions
   - **Edge cases**: Missing null checks, empty inputs, boundary conditions
   - **Security**: SQL injection, path traversal, hardcoded secrets
   - **Patterns**: Adherence to project conventions (naming, imports, error handling)
   - **Tests**: Are new functions adequately tested?
   - **Documentation**: Are complex changes documented?

4. **Post review comments**
   - Use `mcp__github__pull_request_review_write` with `event: COMMENT` to post general feedback
   - Use `mcp__github__add_comment_to_pending_review` for file-specific comments
   - Resolve any existing unresolved threads if context is addressed

5. **Submit review**
   - Use `mcp__github__pull_request_review_write` with `event: REQUEST_CHANGES` if critical issues found
   - Use `event: APPROVE` if no blocking issues

## Constraints

- Be constructive and specific — cite line numbers and explain why
- Distinguish between blocking issues and suggestions (prefaced with "nit:")
- Do not approve/Request Changes without running relevant tests if possible
- Flag but don't block on style issues that don't affect correctness
