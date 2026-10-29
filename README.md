<div align="center">

<img src="assets/codemie-logo.svg" alt="CodeMie" width="96" />

# CodeMie Test Harness

**End-to-end, integration and UI test suites for the CodeMie platform.**

[![PyPI](https://img.shields.io/pypi/v/codemie-test-harness.svg?style=flat-square&label=PyPI)](https://pypi.org/project/codemie-test-harness/)
[![CI](https://img.shields.io/github/actions/workflow/status/codemie-ai/codemie-test-harness/ci.yml?branch=main&style=flat-square&label=CI)](https://github.com/codemie-ai/codemie-test-harness/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg?style=flat-square)](#requirements)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg?style=flat-square)](LICENSE)

</div>

## What is it

A pytest-based test suite and a command-line tool (`codemie-test-harness`) that check the behavior of the [CodeMie](https://www.codemie.ai/) platform from the outside: assistants, workflows, tools, integrations and the web UI.

You run it against a CodeMie installation you can reach: a local stack on your machine or a deployed system. A test that needs an integration you did not configure (Jira, GitLab, ServiceNow, ...) or a platform feature your installation does not have is skipped, and the run summary names the reason.

## Requirements

- Python 3.12 or later
- A running CodeMie installation and a user on it
- Playwright browsers for the UI tests (`playwright install chromium`)

## Install

```bash
pip install codemie-test-harness
codemie-test-harness --help
```

## Settings

Each setting is read from the first source that has it:

1. Environment variable.
2. Config file `~/.codemie/test-harness.json`, written by `codemie-test-harness config set KEY VALUE`.
3. Built-in defaults for a local stack, used only when `CODEMIE_API_DOMAIN` is unset or local: API `http://localhost:8080`, UI `http://localhost:5173`, the default local admin user.

`codemie-test-harness config list` shows all known settings.

| Setting | When | Value |
|---|---|---|
| `CODEMIE_API_DOMAIN` | always | Base URL of the CodeMie API, for example `http://localhost:8080` or `https://codemie.example.com/code-assistant-api` |
| `AUTH_USERNAME`, `AUTH_PASSWORD` | always on a deployed system; on localhost when local login is on | User the tests run as. UI tests log in with it |
| `AUTH_SERVER_URL`, `AUTH_REALM_NAME` | deployed system | Keycloak URL and realm of the installation |
| `AUTH_CLIENT_ID`, `AUTH_CLIENT_SECRET` | deployed system, if needed | Keycloak client. Without a client id, `codemie-sdk` is used. Give the secret for a confidential client |
| `FRONTEND_URL` | UI tests | URL of the CodeMie web UI |
| `VERIFY_SSL` | optional | `true` to check TLS certificates (default `false`) |

On `localhost`, `127.0.0.1`, `0.0.0.0` and `192.168.*` addresses Keycloak is not used: with `AUTH_USERNAME` and `AUTH_PASSWORD` the harness logs in through the backend local login, without them it sends no token. Any other address always logs in through Keycloak.

Integration tests read their own settings (for example `JIRA_URL`, `JIRA_TOKEN`). Leave them unset to skip those tests.

## Run on your machine

Against a local CodeMie stack on the default ports no settings are needed:

```bash
codemie-test-harness run smoke-api
```

On other ports or with another user, set them first, for example `codemie-test-harness config set CODEMIE_API_DOMAIN http://localhost:9090`.

`codemie-test-harness run --list-suites` lists the suites (`sanity-api`, `smoke`, `api`, `ui`, ...). `codemie-test-harness` without arguments opens an interactive menu.

## Run in CI against a deployed system

Install the package, pass the settings as environment variables from the CI secret store, run a suite, keep the result files. Example for GitHub Actions:

```yaml
jobs:
  codemie-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install codemie-test-harness
      - run: playwright install --with-deps chromium   # only for UI suites
      - run: codemie-test-harness run sanity-api
        env:
          CODEMIE_API_DOMAIN: ${{ vars.CODEMIE_API_DOMAIN }}
          FRONTEND_URL: ${{ vars.CODEMIE_FRONTEND_URL }}
          AUTH_SERVER_URL: ${{ vars.CODEMIE_AUTH_SERVER_URL }}
          AUTH_REALM_NAME: ${{ vars.CODEMIE_AUTH_REALM }}
          AUTH_USERNAME: ${{ secrets.CODEMIE_TEST_USER }}
          AUTH_PASSWORD: ${{ secrets.CODEMIE_TEST_PASSWORD }}
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: codemie-test-results
          path: codemie-test-reports/
```

- The exit code is the pytest exit code: a failed test fails the job.
- Each run writes `codemie-test-reports/junit.xml` and `results.json`. `--results-dir PATH` writes them to another folder.
- Before any test the run reads `GET /v1/config` of the installation. If that fails, the run stops with exit code 2.
- A test without its settings or platform feature is skipped. Add `--strict` to fail it instead, when the job must prove that everything is configured.

## Documentation

- [What is CodeMie](https://docs.codemie.ai/user-guide/getting-started/what-is-codemie/): an introduction to the platform.
- [CodeMie documentation](https://docs.codemie.ai/): user guides and platform reference.

## Contributing

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) and the [Code of Conduct](CODE_OF_CONDUCT.md) first.

## Security

Do not report vulnerabilities in public issues. Follow [SECURITY.md](SECURITY.md).

For bugs and feature requests, use [GitHub Issues](https://github.com/codemie-ai/codemie-test-harness/issues).

## Releasing

See [docs/RELEASING.md](docs/RELEASING.md).

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE).
