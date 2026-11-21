# Security Patterns

The repository is public. Never commit a secret, a private value or customer data. Files and commands that an agent must not touch are in [../safety-no-go.md](../safety-no-go.md).

## Rules

| Rule | Source |
|---|---|
| Do not commit credentials, private hostnames, ticket keys or personal e-mail addresses. Use placeholders such as `https://codemie.example.com`. | `CONTRIBUTING.md:42` |
| Keep client secrets and tokens out of source control. Read them from environment variables or a secret store. Do not commit `.env`. | `SECURITY.md:31` |
| Keep `CODEMIE_VERIFY_SSL` at its default (`true`) in production. | `SECURITY.md:32` |
| Do not put real credentials or customer data in a vulnerability report. | `SECURITY.md:17` |
| Report a vulnerability through the GitHub Security Advisory, never a public issue. | `SECURITY.md:9-15` |
| The only place for the ticket-key placeholder form is `project.md`. | `.ai-run/guides/project.md:24` |

## Test data and credentials

- Test credentials come only from environment variables or `~/.codemie/test-harness.json`. The CLI stores the login and integration credentials in that file (`.ai-run/guides/safety-no-go.md:12`).
- Do not read or print those values. Do not use `--show-value` (`.ai-run/guides/safety-no-go.md:24`).
- Test data holds no real name, e-mail address, host or ticket key. Use placeholders.

## Checks

| Check | Where | Catches |
|---|---|---|
| `Internal references` | `.github/workflows/ci.yml:68`, reusable workflow in `codemie-ai/ci-workflows` | private host, ticket key, personal e-mail |
| `Security` | `.github/workflows/ci.yml:74`, reusable workflow in `codemie-ai/ci-workflows`; rules in `.gitleaks.toml:3-4` (gitleaks defaults) | secret in the change |
| `make scan-internal` | `Makefile:39`, `scripts/scan_internal_values.py` | blocked internal value, locally; needs `HARNESS_SCAN_PATTERNS` and/or `HARNESS_SCAN_CUSTOMER_NAMES` |

- The rules of the two CI jobs live in `codemie-ai/ci-workflows`, not in this repository. `make scan-internal` is a separate check and does not replace them (`.ai-run/guides/quality-gates.md:55`).
- The pre-commit hook runs the scan when a scan variable is set (`.ai-run/guides/quality-gates.md:39`).
- `.gitleaks.toml:9-13` lists stop words. Add one only for a value that is not a secret, with a comment that says why.

## Anti-Patterns

| Bad | Good |
|---|---|
| A real stand URL in a test or a doc | `https://codemie.example.com` |
| A real e-mail or user name as test data | A placeholder or a generated value |
| A real ticket key in a test name, comment or doc | The placeholder form from `project.md` |
| A key or token in code or in `.env` that is committed | An environment variable or `~/.codemie/test-harness.json` |
| Silence a `Security` finding with a stop word | Remove the value; rotate it if it was real |
