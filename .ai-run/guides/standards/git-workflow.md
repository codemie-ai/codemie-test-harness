# Git Workflow

**Project**: codemie-test-harness · **Stack**: Python, pytest 8 + codemie-sdk-python 0.1.709 + pytest-playwright 0.8 (CLI: click 8) · **Scope**: branch names, commit subjects, merge policy and their recovery steps; exact gate commands live in `.ai-run/guides/quality-gates.md`, the MR adapter in `.ai-run/guides/project.md`

## Branch Naming Convention

- base branch: main
- pattern: `<type>/<slug>`

### Rules
- R1. Name a branch `<type>/<slug>` by convention (observed on the remotes: `feat/...`, `test/...`, `docs/...`); nothing enforces a branch name.
- R2. Do not push to `automated/codemie-sdk-version`; the `Automated codemie-sdk version` workflow resets it with `git checkout -B` and force-pushes it daily, then opens or edits the `chore(deps): automated update of codemie-sdk-python (<version>)` pull request.

## Commit Message Format

```
<type>(<optional scope>): <description>
```

### Rules
- R1. Title a pull request `<type>(<optional scope>): <description>` with a type from `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert` (CONTRIBUTING.md). The `PR Checks` workflow runs the reusable `reusable-commit-lint.yml` of `codemie-ai/ci-workflows` on the title of every pull request to `main` (opened, synchronize, reopened, edited); the checks it applies live in that remote file.
- R2. Individual commit messages are not checked (CONTRIBUTING.md). By convention each change lands on `main` as one commit carrying the pull request title and number, `<type>(<scope>): <subject> (#<n>)`; scopes in recent history are `test-harness`, `budgets`, `workflows`, `deps`.

## Merge Strategy

### Rules
- R1. Merge into `main` by squash (each pull request lands on `main` as one commit carrying its title and number). Evidence: recorded user decision
- R2. Push the branch to your fork and open the pull request against `main` of `codemie-ai/codemie-test-harness`. CONTRIBUTING.md states that a first-time contributor's workflow run waits for maintainer approval and that merging needs one approval from a collaborator with write access and passing CI checks; the branch-protection settings themselves are outside the repository.

## Anti-Patterns

| Do not | Do instead | Why |
|---|---|---|
| Cut a branch from another feature branch | `git switch -c <type>/<slug> main` | rebases and PR diffs stay against the integration branch |
| Push to `main` directly | push the branch to your fork and open a pull request against `main` | merging needs one approval from a collaborator with write access and passing CI checks (CONTRIBUTING.md) |
| Force-push a shared branch with `--force` | `git push --force-with-lease` after a rebase, and only on your own branch | a teammate's commits survive |

## Troubleshooting

| Issue | Fix |
|---|---|
| Branch was cut from the wrong base | `git rebase --onto main <old-base> <branch>`, then `git push --force-with-lease` |
| `PR Checks` rejects the pull request title | edit the title to `<type>(<optional scope>): <description>`; the check runs again on `edited` |
| Rebase conflicts on `main` | resolve file by file, `git add`, `git rebase --continue`; `git rebase --abort` to restart; never resolve by taking one side wholesale |
