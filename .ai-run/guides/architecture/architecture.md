# Architecture Guide

**Project**: codemie-test-harness · **Stack**: Python, pytest 8 + codemie-sdk-python 0.1.709 + pytest-playwright 0.8 (CLI: click 8) · **Scope**: how the `codemie-test-harness` CLI starts pytest, which pytest config it loads, and the package-root plugins; settings live in `.ai-run/guides/development/settings.md`, test authoring in `.ai-run/guides/testing/strategy.md`

## Structure and boundaries

### Rules
- R1. Register a marker or ini setting that `codemie-test-harness run` must honour in `codemie_test_harness/pytest.ini` as well as in `pyproject.toml` (`[tool.pytest.ini_options]`); `run_pytest` starts pytest with the package directory as cwd and the package `tests` path, so a CLI run loads `pytest.ini` and the root `pyproject.toml` settings never apply (an installed wheel ships no `pyproject.toml` at all). Known debt, to fix: `pyproject.toml`, `codemie_test_harness/pytest.ini` (markers `budget`, `skill`, `user` missing from `pytest.ini`). Evidence: `codemie_test_harness/cli/runner.py::run_pytest`
- R2. Keep the modules at the package root (`capability_gate.py`, `results_plugin.py`, `rp_guard.py`, `ingest_sender.py`, `otlp_builder.py`) free of module-level imports from `codemie_test_harness.tests`; importing that package runs `load_env_file` (read: `codemie_test_harness/tests/__init__.py` lines 24-28) and fixes settings constants at import time. Import inside the function that needs it, as `CapabilityGate._unmet` imports `CredentialsManager`. Evidence: `codemie_test_harness/capability_gate.py::CapabilityGate._unmet`
- R3. Stop the run from `pytest_configure` with `pytest.exit(..., returncode=2)` when the installation's `GET /v1/config` or the opt-in secret store cannot be read; README documents exit code 2 for this case, and `capability_gate.pytest_configure` and the root `conftest.py` `pytest_configure` (the `SecretStoreError` branch) both exit that way instead of raising. Evidence: `codemie_test_harness/capability_gate.py::pytest_configure`

### Constraints
| Do not | Do instead | Why | Evidence |
|---|---|---|---|
| Let a reporting plugin raise or change the exit status | Catch `OSError` and print a warning to stderr, as `_JsonResults._write` does, and write from a `wrapper=True` `pytest_sessionfinish` so another hook's exception cannot skip the write | README states the CLI exit code is the pytest exit code | `codemie_test_harness/results_plugin.py::_JsonResults._write` |

### Read first
| When you are | Exemplar | Why this one | Tests |
|---|---|---|---|
| adding a pytest plugin whose state xdist workers need | `codemie_test_harness/capability_gate.py::CapabilityGate.pytest_configure_node` | the controller computes once and hands the result to each worker through `workerinput`; workers never refetch | no covering test |
| adding or changing a CLI suite preset | `codemie_test_harness/cli/constants.py::TEST_SUITES` | marks, workers, reruns and `pytest_args` per suite; `run_cmd` and the interactive menu both read it | no covering test |
