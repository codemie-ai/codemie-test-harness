# Quality Gates

Run order is fastest-to-slowest.

## Full runs

| Command | Covers | Source |
|---|---|---|
| `CI on pull_request (ci.yml)` | build job: poetry install, poetry build, poetry run codemie-test-harness --help; lint job: poetry run ruff check .; internal-refs and secrets-detection reusable jobs | .github/workflows/ci.yml |
| `PR Checks on pull_request to main (pr-title-lint.yml)` | commit-lint of the PR title | .github/workflows/pr-title-lint.yml |
| `CodeQL on pull_request to main (codeql.yml)` | CodeQL for actions and python, CI-only | .github/workflows/codeql.yml |
| `make ruff` | ruff check --fix, ruff check, ruff format (rewrites files) | Makefile:54-57 |
| `Release verify job (publish.yml)` | tag checks, ruff check, check_version.py against PyPI, poetry build | .github/workflows/publish.yml |

---

### lint

**Run**: `poetry run ruff check .`
**Pass**: exit code 0
**Fail**: non-zero exit code; ruff prints each violation
**Auto-fix**: make ruff-fix

### format

**Run**: `poetry run ruff format --check .`
**Pass**: exit code 0
**Fail**: non-zero exit code
**Auto-fix**: make ruff-format

### license-check

**Run**: `make license-check`
**Pass**: exit code 0 and 'checked <n> files'
**Fail**: exit code 1: 'missing licence header: <path>', 'cannot read <path>', an empty scan, or a file-count mismatch
**Auto-fix**: make license-fix

### secret-scan

**Run**: `make scan-internal`
**Pass**: exit code 0
**Fail**: exit code 1 with '<path>:<line>: [<rule>]' lines; exit code 2 when no HARNESS_SCAN_PATTERNS / HARNESS_SCAN_CUSTOMER_NAMES are configured

### build

**Run**: `poetry build`
**Side effects**: writes dist/
**Pass**: exit code 0
**Fail**: non-zero exit code

### test

**Run**: `poetry run codemie-test-harness run sanity-api`
**Side effects**: creates and deletes entities on the target installation; may create the default project; rewrites codemie-test-reports/junit.xml and results.json
**Pass**: exit code 0
**Fail**: non-zero exit code (1 test failures, 2 start-up config/secret-store failure, 3 local-login failure, other pytest codes)
**Skip if**: no reachable CodeMie installation configured (run on request only); tests with an unmet requires_setting/requires_capability are skipped; not_for_parallel_run tests are deselected
