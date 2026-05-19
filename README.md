# claude-review

![Python](https://img.shields.io/badge/python-3.12-blue) ![Claude](https://img.shields.io/badge/Claude-API-orange) ![GitHub Actions](https://img.shields.io/badge/GitHub-Actions-black) ![Tests](https://github.com/pintaste/claude-review/actions/workflows/test.yml/badge.svg)

GitHub Action that posts AI code review comments on every PR using Claude.

## Quick Start

Add this workflow to `.github/workflows/claude-review.yml` in your repo:

```yaml
name: Claude PR Review

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    steps:
      - name: Claude PR Review
        uses: pintaste/claude-review@main
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          github_token: ${{ secrets.GITHUB_TOKEN }}
          focus: 'all'
          max_tokens: '2048'
```

Then add `ANTHROPIC_API_KEY` as a repository secret under **Settings → Secrets and variables → Actions**.

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `anthropic_api_key` | Yes | — | Your Anthropic API key |
| `github_token` | Yes | `${{ github.token }}` | GitHub token for posting comments |
| `focus` | No | `all` | Review focus areas (comma-separated) |
| `max_tokens` | No | `2048` | Max tokens for Claude response |

## Example Output

When a PR is opened, claude-review posts a comment like this:

````markdown
## Claude Code Review

**`src/auth.py`** — Lines 42–58

- `SECRET_KEY` is hardcoded. Move it to an environment variable and load via `os.environ`.
- The `except Exception` on line 55 swallows all errors silently. Log the exception or re-raise after cleanup.
- `verify_token()` has no expiry check — expired tokens will be accepted indefinitely.

---

**`src/db.py`** — Lines 10–30

- No connection pooling configured. Under load this will exhaust database connections. Use `create_engine(..., pool_size=5)`.
- Raw string interpolation in the query on line 22 is vulnerable to SQL injection. Use parameterized queries.

> Focus: all · Powered by [claude-review](https://github.com/pintaste/claude-review)
````

## Focus Options

| Value | What Claude reviews |
|-------|---------------------|
| `security` | Auth flaws, injection risks, exposed secrets, insecure defaults |
| `performance` | N+1 queries, unnecessary allocations, blocking I/O, algorithm complexity |
| `style` | Naming, readability, dead code, consistency with idiomatic patterns |
| `all` | Everything above — correctness, security, performance, style, and maintainability |

You can combine multiple areas: `focus: 'security,performance'`

## Self-Dogfooding

This repo uses claude-review on its own PRs.
