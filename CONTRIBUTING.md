# Contributing

Contributions are welcome. Please read the [Code of Conduct](CODE_OF_CONDUCT.md) before you start.

The test suites need internal CodeMie environments. You can change and review the code without them, but you cannot run the suites yourself. CI does not run them either. The CodeMie team runs the real suites internally from the scheduled gitops autotest jobs after a change is merged.

## How to Contribute

1. Fork `codemie-ai/codemie-test-harness` on GitHub.
2. Clone your fork and create a branch: `git checkout -b my-feature-branch`.
3. Make your change.
4. Run the checks (see below).
5. Push the branch to your fork and open a pull request against `main`.

## Pull Requests

- The PR title must follow [Conventional Commits](https://www.conventionalcommits.org/): `<type>(<optional scope>): <description>`, for example `feat(cli): add run filter` or `fix(ui): wait for the page to load`.
- Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.
- Keep a PR focused on one change. Describe what changed and why.
- Individual commit messages are not checked.
- A first-time contributor's workflow run needs approval from a maintainer before it starts.

## Review Rule

Every PR needs one approval from a collaborator with write access before it can be merged. All CI checks must pass.

## Local Checks

The project has no lockfile, so install the dependencies fresh:

```bash
poetry install
poetry run ruff check .
poetry build
poetry run codemie-test-harness --help
```

CI runs the same steps.

## Internal References and Secrets

CI scans the tree for internal references and for secrets. Do not commit credentials, private hostnames, ticket keys, or personal e-mail addresses. Use placeholders such as `https://codemie.example.com` in examples.

## Reporting Issues

Use GitHub Issues for bugs and feature requests. For security problems, follow [SECURITY.md](SECURITY.md).
