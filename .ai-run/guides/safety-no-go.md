# Safety No-Go List

Rules for every AI agent and every person who works in this repository, Claude Code included. A rule here wins over any task instruction. When a task needs one of these actions, stop and ask a person.

`.claude/settings.json` blocks the usual spellings for Claude Code: the first two tables map to `permissions.deny` (always refused), the third table to `permissions.ask` (a person confirms each one). It is a guard, not a security boundary: a shell glob, a script, a subprocess or another spelling of a command can get past it. Other agents have no such guard. So every agent must follow this file, not only the rules that the settings catch.

## Files never read or changed

| Path | Why |
|---|---|
| `.env`, `**/.env`, `.env.local`, `.env.*.local`, `.env.prod*`, `.env.preview`, `.env.sandbox` | real settings files hold the CodeMie password and integration tokens; they are git-ignored (`.gitignore`). The tracked template `codemie_test_harness/.env.template` is allowed |
| `~/.codemie/**`, mainly `~/.codemie/test-harness.json` | the harness CLI stores the login and integration credentials there (`CONFIG_FILE`, `codemie_test_harness/cli/constants.py`) |
| `*.pem`, `*.key` | private keys and certificates |
| `~/.ssh/**` | SSH keys give push access to repositories |
| `~/.aws/**` | AWS credentials; the opt-in secret store reads the test settings from AWS (`HARNESS_SECRET_STORE`, [testing/environments.md](testing/environments.md)) |
| `~/.pypirc` | PyPI upload token |

Do not print these values in another way either: no `python -c "print(open('.env').read())"`, no `env` dump of the settings.

## Commands never run

| Command | Why |
|---|---|
| `codemie-test-harness config … --show-value` / `--show-values` (`config list`, `config get`, `config integrations`) | prints the real credentials from `~/.codemie/test-harness.json` |
| `git push --force` / `-f` (any position), `git push --mirror` | rewrites or replaces shared history and can delete other people's commits. `--force-with-lease` on your own feature branch is in the third table |
| `git reset --hard` (any position) | discards uncommitted work with no way back |
| `git clean` with `-x` or `-X` | deletes git-ignored files: the local `.env` settings and `codemie-test-reports/` |
| `--no-verify`, `git commit -n`, `git -c core.hooksPath=…` | skips the pre-commit hook: lint, licence header and internal-value scan (`scripts/pre-commit-hook.sh`). The settings also refuse a command that only names `--no-verify` in a message; write "the hook bypass flag" instead |
| `poetry publish`, `make publish`, `twine upload`, `uv publish` | uploads a package to PyPI from a local machine; a published version cannot be replaced. Releases go through the `publish.yml` workflow (`docs/RELEASING.md`) only |
| `pytest … cleanup.py`, `pytest -m cleanup`, `pytest … test_clean_all_entities` | `cleanup.py` (`test_clean_all_entities`) deletes the test user's assistants, workflows, datasources, integrations and skills, all `autotest-` projects, matching providers and cost centers, and test issues, work items and wiki pages in external trackers and wikis; on a shared stand this includes data of other people's runs |
| `codemie-test-harness run … cleanup.py`, `codemie-test-harness run … test_clean_all_entities`, `codemie-test-harness run --marks cleanup` | the same cleanup: `run` forwards the extra arguments to pytest. The CLI has no separate cleanup command |

## Actions that always need a person

| Action | Why |
|---|---|
| Any run against production, or against a domain not listed in [testing/environments.md](testing/environments.md) | only `preview` permits destructive testing; other stands are read-only for tests |
| Release, tag `v*`, or publish of the package: `gh release create`, `gh release edit`, `gh release delete`, `gh workflow run` (the `publish.yml` dry run included) | a published GitHub release or a dispatch of `publish.yml` with `dry_run=false` publishes to PyPI. Use the `codemie-release` skill and `docs/RELEASING.md`; the person confirms each step |
| `git push` of any kind, `--force-with-lease` on your own feature branch included | a push changes shared state. Never force-push to `main` ([standards/git-workflow.md](standards/git-workflow.md)) |
| `git reset`, `git clean` (without `-x` / `-X`), `rm`, `find … -delete` | removes local work or files with no undo |
| Setting `CLEANUP_DATA=false` on a shared stand | leaves orphaned `autotest-` entities for the whole team ([testing/environments.md](testing/environments.md), "Test data") |
| Changes to persistent seeds in external systems (`tests/utils/*_seed.py`) | every run reuses them; a changed or deleted seed breaks all later runs |
| Adding a secret, an internal host, a ticket key or a personal e-mail to a tracked file | the repository is public; CI jobs `Internal references` and `Security` block it, but a pushed value stays in history |
| Changes to `.github/workflows/`, `.gitleaks.toml` or `.claude/settings.json` | they define the CI gates and this guard |
| Hand edits of `poetry.lock` | the lock must come from `poetry lock`; CI installs from it exactly ([quality-gates.md](quality-gates.md)). Change `pyproject.toml` and relock instead |

Only some rows of this table have a rule in `.claude/settings.json` (pushes, resets, cleans, `rm`, releases, workflow dispatches, edits of the CI files, the guard and `poetry.lock`). For the other rows the agent must stop and ask by itself.

## Limits

- Bash rules match the command text. Another spelling passes: for example `git -C . push --force`, `gh api -X POST …/releases`, `git commit -an`, or a script that runs the command. A rule that matches text inside a quoted message refuses a harmless command.
- Read rules cover the file tools and file commands such as `cat`. They do not cover a program that opens the file itself.
- With the Claude Code sandbox on, the Read deny rules also apply to every Bash subprocess. Then `pytest` and `codemie-test-harness` cannot read `.env` or `~/.codemie/test-harness.json`. Give the settings through environment variables, or let a person run the suite outside the sandbox. `poetry lock` still works in the sandbox.
- A `PreToolUse` hook that parses the command could close the spelling gaps. It is not part of this repository yet.
