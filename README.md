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

> **Internal environment required.** The test suites run against internal CodeMie environments and the infrastructure around them (platform instances, integration credentials, test data). You cannot run them against a customer installation, and customer installations are not supported. This repository is published for transparency and for contributions to the harness code. It is not a general-purpose test kit.

## Requirements

- Python 3.12 or later
- `codemie-sdk-python` `>=0.1.620 <0.2` (installed as a dependency)
- Playwright browsers for the UI tests (`playwright install`)
- Access to an internal CodeMie environment to run the suites

## Install

```bash
pip install codemie-test-harness
codemie-test-harness --help
```

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
