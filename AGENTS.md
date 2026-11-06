# AGENTS.md

Primary AI entrypoint for `codemie-test-harness`. Load the relevant `.ai-run/guides/` file before changing code.

## Guide Imports

<!-- ai-run-init:guide-imports start -->
| Category | Guide Path | Purpose |
|---|---|---|
| Project | .ai-run/guides/project.md | Project identity, tracker and source control |
| Quality | .ai-run/guides/quality-gates.md | Quality gates and how to run them |
| Architecture | .ai-run/guides/architecture/architecture.md | How the CLI starts pytest, which config it loads, and the package-root plugins |
| Development | .ai-run/guides/development/settings.md | Reading settings and credentials and gating tests on them |
| Standards | .ai-run/guides/standards/git-workflow.md | Branch, commit and pull-request conventions |
| Testing | .ai-run/guides/testing/environments.md | Shared seeds, the default project and test data on the shared stand |
| Testing | .ai-run/guides/testing/risk-model.md | Impact-to-priority scheme used by the QA flows |
| Testing | .ai-run/guides/testing/strategy.md | Writing API and UI tests: fixtures, cleanup, markers, page objects, parallel runs |
<!-- ai-run-init:guide-imports end -->

## Task Classifier

<!-- ai-run-init:task-classifier start -->
| Category | User Intent | Example Requests | P0 Guide | P1 Guide |
|---|---|---|---|---|
| Architecture | change the CLI, a suite preset, a pytest plugin or the result files | "add a suite preset", "add a pytest option", "change what results.json records" | .ai-run/guides/architecture/architecture.md | - |
| Development | add or read a setting, or make a test skip when its integration is not configured | "add an integration's settings", "read a token in a fixture", "mark a test as needing a capability" | .ai-run/guides/development/settings.md | - |
| Standards | branch, commit or open a pull request | "name a branch", "title a pull request" | .ai-run/guides/standards/git-workflow.md | - |
| Testing | write, fix or review an API or UI test | "add an API test", "add a page object", "make a test safe for parallel runs" | .ai-run/guides/testing/strategy.md | .ai-run/guides/testing/environments.md |
<!-- ai-run-init:task-classifier end -->

## Critical Rules

<!-- ai-run-init:critical-rules start -->
| Rule | Trigger | Action |
|---|---|---|
| Check Guides First | ANY task | Match request to category and load the P0 guide before searching broadly |
| Testing | "write tests" / "run tests" | ONLY then |
| Git Operations | "commit" / "push" / "PR" / "MR" | Only then; load `.ai-run/guides/standards/git-workflow.md` |
| Shell | ANY shell command | Use bash/Linux-compatible syntax |
| Create every platform entity in a fixture with teardown and a get_random_name() name; the session backstop deletes only names carrying the session prefix | writing a test or fixture that creates platform entities | load `.ai-run/guides/testing/strategy.md` |
| Run a test that needs integration settings or a platform capability only after declaring the need with its marker; a gated suite run then skips it instead of failing | writing or changing a test that uses an external integration or a /v1/config feature | load `.ai-run/guides/development/settings.md` |
| Treat the shared stand's seeds and default project as read-only | using external-system seed data or the default project | load `.ai-run/guides/testing/environments.md` |
<!-- ai-run-init:critical-rules end -->

## Commands

<!-- ai-run-init:commands start -->
| Need | Source Guide | Source Evidence | Notes |
|---|---|---|---|
| lint | .ai-run/guides/quality-gates.md | .github/workflows/ci.yml lint job; CONTRIBUTING.md Local Checks | Load guide before running |
| format | .ai-run/guides/quality-gates.md | scripts/pre-commit-hook.sh:46-49 | Load guide before running |
| license-check | .ai-run/guides/quality-gates.md | Makefile:42-44; scripts/check_license_headers.py | Load guide before running |
| secret-scan | .ai-run/guides/quality-gates.md | Makefile:36-40; scripts/scan_internal_values.py | Load guide before running |
| build | .ai-run/guides/quality-gates.md | .github/workflows/ci.yml build job; Makefile build | Load guide before running |
| test | .ai-run/guides/quality-gates.md | README.md 'Run on your machine'; codemie_test_harness/cli/commands/run_cmd.py | Load guide before running |
| Git / review workflow | .ai-run/guides/standards/git-workflow.md | git history and project context | Load guide before git operations |
<!-- ai-run-init:commands end -->
