# QA Health

**Last assessed**: 2026-11-09
**Coverage**: qualitative: medium — broad API and UI suites across product areas; no code-coverage data (black-box harness)

How to write and run tests: [qa-strategy.md](qa-strategy.md). Counts below come from `git grep` on `main` on the assessment date; re-count before you quote them.

## Coverage Summary

There is no coverage report. The harness tests a deployed CodeMie installation from the outside, so line or branch coverage of the product cannot be measured from this repository, and the harness code itself has no unit tests. The table records what exists per suite instead.

| Module / area | Coverage | Notes |
|---|---|---|
| API suites, `codemie_test_harness/tests/<area>/` | unknown (no report) | 280 `test_*.py` files outside `ui/`; 1338 `@pytest.mark.api` lines. Areas: assistant, workflow, integrations, llm, conversations, projects, user, roles, budgets, analytics, auditor, scheduler, search, skill, webhook, export, providers, e2e and more |
| UI suites, `codemie_test_harness/tests/ui/<area>/` | unknown (no report) | 137 `test_*.py` files; 478 `@pytest.mark.ui` lines; page objects in `tests/ui/pageobject/` |
| `sanity-api`, `sanity-ui` (CLI suites) | unknown (no report) | the only suites that need no integration settings (`marks: "api and sanity"`, `codemie_test_harness/cli/constants.py:220`); contributors run these before a PR |
| Harness code: CLI, `capability_gate.py`, `results_plugin.py`, `scripts/` | none | no unit tests; CI checks only `ruff check .`, `poetry build` and `codemie-test-harness --help` ([quality-gates.md](../quality-gates.md)) |
| Accessibility, performance, security, contract | none | `practiced: false` in [config.json](config.json) |

## Risky Untested Areas

| Path | Coverage | Risk reason |
|---|---|---|
| `codemie_test_harness/capability_gate.py` | 0% (no tests) | decides which tests skip in a gated run; a wrong mapping silently skips a whole area and the run still looks green |
| `codemie_test_harness/cli/` | 0% (no tests) | suite definitions (`TEST_SUITES`, `cli/constants.py:192`) choose markers, workers and reruns for every CLI run; only `--help` is smoke-tested in CI |
| `codemie_test_harness/tests/utils/cleanup_utils.py` | 0% (no tests) | deletes platform entities and external-system data for the session cleanup and for `tests/cleanup.py`; a filter bug deletes data the run does not own |
| every suite in CI | not run | CI has no CodeMie installation; suites run only on contributors' machines and in the team's scheduled jobs (`CONTRIBUTING.md`, intro) |

The team has not named critical flows yet ([risk-model.md](risk-model.md), "Critical flows"), so no product area is ranked here.

## Known Test Debt

### Skipped and expected-to-fail tests

Decorator counts: 13 `@pytest.mark.skip`, 11 `@pytest.mark.xfail`, 49 `@pytest.mark.skipif`, 10 module-level `pytestmark = pytest.mark.skipif`, plus `marks=` on parametrize cases.

| Kind | Example | Reason in the code |
|---|---|---|
| Skip, known product bug | `codemie_test_harness/tests/e2e/test_e2e.py:267`, `:320`, `:378` | integration context leaks between GitLab and GitHub tools |
| Skip, flaky | `codemie_test_harness/tests/assistant/tools/filemanagement/test_assistant_with_file_management_tools.py:129`; `codemie_test_harness/tests/workflow/assistant_tools/file_management/test_workflow_with_assistant_with_file_management_tools.py:165`, `:222`; `codemie_test_harness/tests/workflow/virtual_assistant_tools/file_management/test_workflow_with_file_management_tools.py:165`, `:231` | file management tools are unstable |
| Skip, test to fix | `codemie_test_harness/tests/assistant/tools/project_management/test_assistant_pm_tools.py:225`; `codemie_test_harness/tests/assistant/test_assistants.py:318` | "Test should be fixed"; "Not implemented yet" |
| Skip, no environment | `codemie_test_harness/tests/assistant/datasource/test_xwiki_datasource.py:54`; `codemie_test_harness/tests/test_data/research_tools_test_data.py:35` | no XWiki environment; Tavily case off until fixed |
| Skipif, known defect | `codemie_test_harness/tests/assistant/tools/openapi/test_assistant_with_open_api_tools.py:44`; `codemie_test_harness/tests/integrations/test_integration_update.py:322` | "issue with encoding long strings" (16 marks in total) |
| Skipif, environment | most of the 49 | local, sandbox or preview-only features (scheduler, webhook, InfluxDB, LiteLLM, AICE) |
| Xfail, non-strict | `codemie_test_harness/tests/assistant/datasource/test_azure_devops_wiki_datasource.py:357`; `codemie_test_harness/tests/assistant/datasource/test_azure_devops_work_items_datasource.py:224`; `codemie_test_harness/tests/test_data/integrations_test_data.py:586`; SMTP cases in `codemie_test_harness/tests/test_data/integrations_test_data.py:340`, `:433` | datasource reindex fails; empty assistant response; outgoing SMTP blocked on the test network |
| Xfail, strict (product defect) | `codemie_test_harness/tests/ui/workflows/test_expanded_yaml_configuration.py:140`, `:181`, `:214`; `codemie_test_harness/tests/ui/budgets/test_project_member_use_project_allocation.py:39` | expanded YAML editor keeps only the last typed character; member allocation "Undo" row hides. `strict=True` turns the fix into an XPASS failure, so the mark gets removed |

A non-strict `xfail` passes silently when the product is fixed; prefer `strict=True` for a confirmed product defect.

### Legacy patterns

Do not copy these; fix them only when a change touches the test ([qa-strategy.md](qa-strategy.md), "Anti-patterns").

| Pattern | Count | Where |
|---|---|---|
| `wait_for_timeout` | 97 | `codemie_test_harness/tests/ui/` |
| `time.sleep(` | 40 | `codemie_test_harness/tests/` |
| `os.getenv(` outside `tests/utils/` | 30 | `codemie_test_harness/tests/` |
| `class Test…` | 13 | `codemie_test_harness/tests/` |
| `pytest.fail(` | 10 | `codemie_test_harness/tests/` |

### Execution and flakiness signals

- **Reruns hide flakiness.** Every CLI suite except `codemie_claude` and `codemie_gemini` runs with `reruns: 2` (`TEST_SUITES`, `codemie_test_harness/cli/constants.py:192`), so a test that passes on retry shows green. `--results-json` (`codemie_test_harness/results_plugin.py`, written by the CLI runner at `codemie_test_harness/cli/runner.py:100`) keeps only the final outcome per test.
- **Rerun tooling.** The `rerun-failed-tests` skill (`.claude/skills/rerun-failed-tests/`) reruns the failures from a pytest log and marks a test flaky only when it needed `--reruns` to pass. `pytest-repeat` (`--count N`) is installed for repeat runs of one test.
- **Parallel runs drop tests.** 113 `not_for_parallel_run` marks; `pytest_collection_modifyitems` (`codemie_test_harness/tests/conftest.py:308`) deselects them under `-n`, so a suite run with workers never executes them.
- **Gated runs skip tests.** 72 `requires_capability` / `requires_setting` uses; in a gated run an unmet need is a skip, not a failure, unless `--strict-requirements` or `HARNESS_STRICT=1` is set (`codemie_test_harness/capability_gate.py`, module docstring).
- **Shared stand.** Orphaned `autotest-` entities are an accepted condition when `CLEANUP_DATA` is off ([environments.md](environments.md), "Test data").

## Recent Test Activity

From `git log --diff-filter=AM` on test files, newest first:

1. `codemie_test_harness/tests/assistant/test_assistant_sharing.py` (2026-11-09)
2. `codemie_test_harness/tests/ui/assistants/test_share_assistant_owner_view.py` (2026-11-09)
3. `codemie_test_harness/tests/ui/assistants/test_shared_assistant_recipient_access.py` (2026-11-09)
4. `codemie_test_harness/tests/export/test_export_api.py` (2026-11-09)
5. `codemie_test_harness/tests/ui/administration/test_user_management_default_project.py` (2026-11-09)
