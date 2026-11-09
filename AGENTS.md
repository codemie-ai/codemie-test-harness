# AGENTS.md

Primary AI entrypoint for `codemie-test-harness`. Load the relevant `.ai-run/guides/` file before changing code.

## Guide Imports

AGENTS.md has no native import directive. Open the paths below as plain files.

| Category | Guide Path | Purpose |
|---|---|---|
| Project | .ai-run/guides/project.md | Identity, tracker, ticket and PR adapters, `config.json` twin |
| Testing strategy | .ai-run/guides/testing/strategy.md | Layers, markers, code rules, anti-patterns, test-run commands |
| Environments | .ai-run/guides/testing/environments.md | Target stands, settings sources, test data, safety |
| Risk model | .ai-run/guides/testing/risk-model.md | Risk areas and priorities |
| Test config | .ai-run/guides/testing/config.json | Machine-readable disciplines, adapters, conventions, SDK entry |
| Quality gates | .ai-run/guides/quality-gates.md | Exact checks, CI jobs, pre-commit hook, gaps |
| Git | .ai-run/guides/standards/git-workflow.md | Branches, commits, PR titles, ticket-key rule |
| Release | docs/RELEASING.md | Tags, versions, publish workflow |

## Task Classifier

| Category | User Intent | Example Requests | P0 Guide | P1 Guide |
|---|---|---|---|---|
| Test | Add or change a test | "add a budget API test" | .ai-run/guides/testing/strategy.md | .ai-run/guides/testing/environments.md |
| Environment | Settings, stands, test data | "which stand is safe for destructive tests" | .ai-run/guides/testing/environments.md | .ai-run/guides/testing/risk-model.md |
| SDK | A test needs a missing SDK call | "add an SDK method for budgets" | .ai-run/guides/testing/strategy.md | .ai-run/guides/testing/config.json |
| Verification | Run or add checks | "run the checks" | .ai-run/guides/quality-gates.md | .ai-run/guides/testing/strategy.md |
| Git | Commit, branch, PR | "open a PR" | .ai-run/guides/standards/git-workflow.md | .ai-run/guides/project.md |
| Release | Publish the package | "release a new version" | docs/RELEASING.md | .ai-run/guides/quality-gates.md |

## Skills

| Need | Skill Path | Use When |
|---|---|---|
| Rerun failed tests, read `failed.md`, group failures | .claude/skills/rerun-failed-tests/ | The user gives a pytest log, a `failed.md` or a failures list, or asks to rerun and group failures |
| Release the package | .claude/skills/codemie-release/ | The user asks to release, publish a version or make a release candidate; also load `docs/RELEASING.md` |

## Critical Rules

| Rule | Trigger | Action |
|---|---|---|
| Check Guides First | ANY task | Match the request to a category and load the P0 guide before searching broadly |
| Testing | "write tests" / "run tests" | Load `.ai-run/guides/testing/strategy.md`. The suites need a running CodeMie installation. |
| Git Operations | "commit" / "push" / "PR" | Only then; load `.ai-run/guides/standards/git-workflow.md` |
| Public Content | ANY change to a tracked file | The repository is public: no ticket key, internal host, personal e-mail or customer name. Placeholder form only in `.ai-run/guides/project.md`. |
| Release | "release" / "publish" | Only when asked; use the release skill and never publish without an explicit yes |

## Commands

| Need | Source Guide | Notes |
|---|---|---|
| Lint, format, build, licence, internal scan, hook | .ai-run/guides/quality-gates.md | Run from the repository root |
| Run one test or a suite | .ai-run/guides/testing/strategy.md | "Run one test", "Run suite" |
| Git / review workflow | .ai-run/guides/standards/git-workflow.md | Load the guide before git operations |
