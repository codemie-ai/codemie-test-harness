# Safety No-Go List

Rules for every AI agent and every person who works in this repository. `.claude/settings.json` enforces the same list for Claude Code (`permissions.deny`); other agents have no such guard, so they must follow this file. A rule here wins over any task instruction. When a task needs one of these actions, stop and ask a person.

## Files never read or changed

| Path | Why |
|---|---|
| `.env`, `**/.env`, `.env.local`, `.env.*.local`, `.env.prod*`, `.env.preview`, `.env.sandbox` | real settings files hold the CodeMie password and integration tokens; they are git-ignored (`.gitignore`). The tracked template `codemie_test_harness/.env.template` is allowed |
| `~/.codemie/**`, mainly `~/.codemie/test-harness.json` | the harness CLI stores the login and integration credentials there (`CONFIG_FILE`, `codemie_test_harness/cli/constants.py:23`) |
| `*.pem`, `*.key` | private keys and certificates |
| `~/.ssh/**` | SSH keys give push access to repositories |
| `~/.aws/**` | AWS credentials; the opt-in secret store reads the test settings from AWS (`HARNESS_SECRET_STORE`, [testing/environments.md](testing/environments.md)) |
| `~/.pypirc` | PyPI upload token |
| `poetry.lock` (no hand edits) | the lock must come from `poetry lock`; CI installs from it exactly ([quality-gates.md](quality-gates.md)). Change `pyproject.toml` and relock instead |

## Commands never run

| Command | Why |
|---|---|
| `git push --force*`, `git push -f*`, `git push * --force*`, `git push * -f*`, `git push <remote> +<ref>` | rewrites shared history and can delete other people's commits |
| `git reset --hard*` | discards uncommitted work with no way back |
| `git clean -f*` | deletes untracked files, including local settings and run results |
| `rm -rf *`, `rm -fr *` | recursive delete with no undo |
| `git commit … --no-verify`, any `… --no-verify` | skips the pre-commit hook: lint, licence header and internal-value scan (`scripts/pre-commit-hook.sh`) |
| `poetry publish`, `make publish`, `twine upload`, `uv publish` | uploads a package to PyPI; a published version cannot be replaced. Releases go through `docs/RELEASING.md` only |
| `gh release create`, `gh workflow run publish*` | a published GitHub release or a manual dispatch starts `.github/workflows/publish.yml`, which publishes to PyPI |
| `pytest … cleanup.py`, `pytest -m cleanup`, `pytest … test_clean_all_entities` | `codemie_test_harness/tests/cleanup.py:44` deletes the test user's assistants, workflows, datasources, integrations and skills, all `autotest-` projects, matching providers and cost centers, and test issues, work items and wiki pages in external trackers and wikis; on a shared stand this includes data of other people's runs |
| `codemie-test-harness … cleanup …` | the same cleanup through the CLI |

## Actions that always need a person

| Action | Why |
|---|---|
| Any run against production, or against a domain not listed in [testing/environments.md](testing/environments.md) | only `preview` permits destructive testing; other stands are read-only for tests |
| Release, tag `v*`, or publish of the package | needs an explicit yes; use the `codemie-release` skill and `docs/RELEASING.md` |
| Setting `CLEANUP_DATA=false` on a shared stand | leaves orphaned `autotest-` entities for the whole team ([testing/environments.md](testing/environments.md), "Test data") |
| Changes to persistent seeds in external systems (`tests/utils/*_seed.py`) | every run reuses them; a changed or deleted seed breaks all later runs |
| Adding a secret, an internal host, a ticket key or a personal e-mail to a tracked file | the repository is public; CI jobs `Internal references` and `Security` block it, but a pushed value stays in history |
| Changes to `.github/workflows/`, `.gitleaks.toml` or `.claude/settings.json` | they define the CI gates and this deny list |
