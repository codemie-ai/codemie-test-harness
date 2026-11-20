# Git Workflow

The repository is public. Pull requests target `main`. One approval from a collaborator with write access and green CI are required (`CONTRIBUTING.md`, "Review Rule").

## Branch Naming Convention

- base branch: main

Pattern: `<type>/<slug>`, for example `test/cost-center-rollup` or `docs/harness-agent-guides`. Use the same types as the commit types below. No ticket key in the branch name. No CI job checks branch names.

## Commit Message Format

Use Conventional Commits. The PR title is the checked format (`.github/workflows/pr-title-lint.yml`, job `PR Title`; `CONTRIBUTING.md`, "Pull Requests"):

```
<type>(<optional scope>): <description>
```

Examples: `test(test-harness): cover user deactivation and reactivation` · `fix(test-harness): stop CLI analytics seeding from doubling sessions on rerun` · `ci(workflows): add scheduled codemie-sdk-python version bump`

- Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert` (`CONTRIBUTING.md`).
- Repository convention for commits and PR titles: `<type>(test-harness): <subject>`, for example `test(test-harness): add cost center rollup tests` (`.ai-run/guides/testing/config.json`, `git_conventions`). The scope is a convention; whether the external title lint accepts every scope is not verified.
- Other scopes in history: `workflows`, `deps`, and `budgets`. Some subjects have no scope.
- Individual commit messages are not checked. Use the same format, because `main` shows it.
- No ticket key in a branch name, commit message, PR title or PR body. `CONTRIBUTING.md` forbids internal references in committed content. Record the PR link in the ticket through the Ticket Adapter in `.ai-run/guides/project.md`.
- A closing reference such as `Closes #N` (a GitHub issue of this repository) is allowed.

## Merge Strategy

Not stated in any repository file. This guide does not state one.

## Pull Requests

- An external contributor forks `codemie-ai/codemie-test-harness` and opens the PR from the fork (`CONTRIBUTING.md`, "How to Contribute"). Maintainers may push branches to `origin`.
- Keep a PR on one change. Describe what changed and why.
- Run the checks in `.ai-run/guides/quality-gates.md` and the test suites your change touches, against your own installation, before you open the PR.
- A merge to `main` does not release the package. Releases: `docs/RELEASING.md` and the skill `.claude/skills/codemie-release/`. The tag prefix is `v`, for example `v1.2.3`.
- The internal sync is stopped. Edit the guides in this repository.

## Anti-Patterns

| Bad | Good |
|---|---|
| A ticket key in the PR title | `test(test-harness): cover user deactivation and reactivation` |
| `update stuff` as the PR title | `fix(test-harness): stop analytics seeding from doubling sessions` |
| Ticket key or tracker URL in a tracked file or example | Placeholder form from `.ai-run/guides/project.md` only |
| `dist/` or a rewritten file committed after a local check | Stage only named files |
| `git add -A` | `git add <paths>` |
| Force-push to `main` | Open a PR from a feature branch |

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `PR Title` check fails | Title does not match Conventional Commits | Edit the title. The check runs again on the `edited` event (`.github/workflows/pr-title-lint.yml`, line 5). |
| `Internal references` check fails | Private host, ticket key or personal e-mail in the tree | Replace it with a placeholder such as `https://codemie.example.com` |
| `Security` check fails | Secret detected. Rules are in `.gitleaks.toml` | Remove the value and rotate it if it was real |
| Commit blocked by the hook | ruff error, format difference or missing licence header | Fix it as the hook output says; see `.ai-run/guides/quality-gates.md`, "Pre-commit hook" |
