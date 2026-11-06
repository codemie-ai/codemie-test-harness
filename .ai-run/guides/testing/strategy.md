# Testing strategy

**Project**: codemie-test-harness · **Stack**: Python, pytest 8 + codemie-sdk-python 0.1.709 + pytest-playwright 0.8 (CLI: click 8) · **Scope**: writing API and UI tests (fixtures, cleanup, markers, page objects, parallel runs), followed by the QA-owned sections the qa-* skills read; settings and gating live in `.ai-run/guides/development/settings.md`, shared seeds in `.ai-run/guides/testing/environments.md`

## Writing API and UI tests

### Rules
- R1. Create each platform entity a test needs through a `yield` fixture (or `request.addfinalizer`) whose teardown deletes it, and name it with `get_random_name()`; the session backstop `pytest_sessionfinish` deletes only the assistants and the integrations, datasources, workflows and projects whose name holds this session's `autotest_entity_prefix`, and does nothing when `CLEANUP_DATA` is not `true`. Evidence: `codemie_test_harness/tests/conftest.py::pytest_sessionfinish`
- R2. Use `assistant_factory.create(...)` when a test creates more than one assistant; the `assistant` fixture keeps only the last assistant its callable created and its teardown deletes only that one. Evidence: `codemie_test_harness/tests/conftest.py::assistant`
- R3. Assert on the value `poll_until` returns; it returns the last fetched value whether or not the predicate held, so the wait itself never fails a test. Evidence: `codemie_test_harness/tests/utils/base_utils.py::poll_until`
- R4. Call the CodeMie API through `client.<service>` or a `*_utils` wrapper; if the SDK lacks the call, add it to `codemie-sdk-python` in its own repository rather than a raw `RequestHandler` or `requests` call in a test. Allowed exceptions: `codemie_test_harness/tests/conversations/test_conversation_feedback.py`, `codemie_test_harness/tests/assistant/tools/ado/test_assistant_for_ado_work_item_tools.py`. Known debt, to fix: `codemie_test_harness/tests/assistant/tools/openapi/test_assistant_with_open_api_tools.py`, `codemie_test_harness/tests/workflow/direct_tools_calling/test_workflow_with_open_api_tools.py`, `codemie_test_harness/tests/workflow/assistant_tools/open_api/test_workflow_with_assistant_with_open_api_tools.py`, `codemie_test_harness/tests/workflow/virtual_assistant_tools/open_api/test_workflow_with_open_api_tools.py`, `codemie_test_harness/tests/workflow/test_workflow_version_history.py`, `codemie_test_harness/tests/workspace_scripts/test_direct_workspace_script_run.py`. Evidence: `codemie_test_harness/tests/utils/assistant_utils.py::AssistantUtils.create_assistant`
- R5. Mark a test that mutates state other tests share with `@pytest.mark.not_for_parallel_run` and verify it without `-n`; `pytest_collection_modifyitems` deselects it whenever xdist is active, and every `TEST_SUITES` preset except `codemie_claude` and `codemie_gemini` sets workers above 0, so `codemie-test-harness run <suite>` never executes it. Evidence: `codemie_test_harness/tests/conftest.py::pytest_collection_modifyitems`
- R6. Pin tests that share one singleton to a worker with `@pytest.mark.xdist_group(name=...)` and run them with `--dist=loadgroup`; without that flag xdist ignores the group, and `build_pytest_cmd` never adds it, so a CLI suite run must receive it as an extra argument. Known debt, to fix: `codemie_test_harness/cli/constants.py`. Evidence: `codemie_test_harness/cli/runner.py::build_pytest_cmd`
- R7. Give every test exactly one of `@pytest.mark.api` or `@pytest.mark.ui`; the `api`, `ui`, `smoke-*`, `sanity-*`, `opensource`, `enterprise` and `budget` presets select on one of them, so a test without either runs only in the bare `smoke` or `sanity` preset, if it carries that marker. Allowed exceptions: `codemie_test_harness/tests/llm/proxy/cli/` (selected by `codemie_claude` / `codemie_gemini`). Known debt, to fix: `codemie_test_harness/tests/projects/test_project_budget_chargeback_sync_status.py`. Evidence: `codemie_test_harness/cli/constants.py::TEST_SUITES`
- R8. Judge a suspected flaky test by its `reruns` count in `results.json`, not by its outcome; `_JsonResults` keeps the final attempt, so a test that failed and then passed under `--reruns` is recorded as `passed`. Evidence: `codemie_test_harness/results_plugin.py::_JsonResults.pytest_runtest_logreport`
- R9. Derive a page-level class (`tests/ui/pageobject/**/*_page.py`) from `BasePage`, expose elements as `@property` locators and put `@step` on public actions; `BasePage` carries the navigation helpers and the `pop_up` and `menu` components. Reusable widgets live in `tests/ui/pageobject/components/` and do not derive from it. Known debt, to fix: `codemie_test_harness/tests/ui/pageobject/assistants/assistant_view_page.py`, `codemie_test_harness/tests/ui/pageobject/administration/unified_project_budget_modal_page.py`. Evidence: `codemie_test_harness/tests/ui/pageobject/base_page.py::BasePage`
- R10. Keep locators and `expect()` out of UI test bodies; call page-object `should_*` methods that wrap `expect()`, which retries until its timeout. Known debt, to fix: `codemie_test_harness/tests/ui/administration/test_project_budget_chargeback.py`, `codemie_test_harness/tests/ui/assistants/test_tools_tokens_size_limit.py`, `codemie_test_harness/tests/ui/chats/test_chat_input_field.py`, `codemie_test_harness/tests/ui/datasource/test_create_datasource.py`, `codemie_test_harness/tests/ui/datasource/test_jira_custom_fields.py`, `codemie_test_harness/tests/ui/datasource/test_view_datasource.py`, `codemie_test_harness/tests/ui/integrations/test_gitlab_webhook_filter.py`, `codemie_test_harness/tests/ui/integrations/test_webhook_form_structure.py`, `codemie_test_harness/tests/ui/integrations/test_webhook_resource_isolation.py`, `codemie_test_harness/tests/ui/workflows/test_edit_workflow.py`, `codemie_test_harness/tests/ui/workflows/test_workflow_executions_page.py`, `codemie_test_harness/tests/ui/workflows/test_workflow_version_history.py`. Evidence: `codemie_test_harness/tests/ui/pageobject/help_page.py::HelpPage.should_be_on_help_page`
- R11. Do not log the configured user in from a UI test; the autouse `login` fixture logs in before every test, and the autouse `screenshot_on_failure` attaches a full-page screenshot when the call phase fails. A test that needs another user's session logs that user in with `LoginPage(page).login_suppressing_popups(...)`, as `test_regular_member_does_not_see_member_override_controls` does. Evidence: `codemie_test_harness/tests/ui/conftest.py::login`
- R12. Pass `--ui-headless` when you run UI tests with plain `pytest`; `codemie_test_harness/pytest.ini` keeps the headed default commented out (lines 3-4), and only the CLI presets `smoke`, `smoke-ui`, `sanity-ui` and `ui` add the flag through `pytest_args`. Evidence: `codemie_test_harness/cli/constants.py::TEST_SUITES`

### Constraints
| Do not | Do instead | Why | Evidence |
|---|---|---|---|
| `assert result == value` in an API test | `assert_that(result, equal_to(value), "reason")` from PyHamcrest | the matcher prints the mismatch | `codemie_test_harness/tests/assistant/test_assistant_slug_lookup.py::test_slug_lookup_with_project_is_deterministic` |
| Clean up at the end of the test body | delete in the fixture's teardown, registered before the create call when the create can fail after committing | the body stops at the first failed assertion | `codemie_test_harness/tests/assistant/test_assistant_slug_lookup.py::duplicate_slug_assistants` |
| Do not copy `page.wait_for_timeout()` from `codemie_test_harness/tests/ui/integrations/test_webhook_form_structure.py` (also in test_assistant_marketplace_sorting.py, test_alias_generation.py, test_scheduler_timezone.py, test_webhook_resource_isolation.py, test_workflow_details.py) | an `expect()` wait inside a page-object method | a fixed sleep is slow and still races the UI | `codemie_test_harness/tests/ui/pageobject/help_page.py::HelpPage.should_be_on_help_page` |

### Read first
| When you are | Exemplar | Why this one | Tests |
|---|---|---|---|
| adding a fixture that creates several entities | `codemie_test_harness/tests/conftest.py::assistant_factory` | tracks every created assistant and deletes each in teardown, logging a failed delete instead of raising | `codemie_test_harness/tests/assistant/test_assistant_partial_update.py::test_partial_update_preserves_omitted_optional_fields` |
| adding an API test that needs its own projects | `codemie_test_harness/tests/assistant/test_assistant_slug_lookup.py::duplicate_slug_assistants` | random names, teardown registered first, cascade delete by project name | exemplar is a test |
| adding a page object | `codemie_test_harness/tests/ui/pageobject/help_page.py::HelpPage` | `BasePage` subclass with `@property` locators, `@step` navigation and `should_*` checks | `codemie_test_harness/tests/ui/help/test_help_page.py::test_help_page_elements_persistence` |
| adding a UI test | `codemie_test_harness/tests/ui/help/test_help_page.py::test_help_page_elements_persistence` | marker stack and a body of page-object calls only | exemplar is a test |

## Layers

### API / integration
- **Framework:** pytest over the `codemie-python` SDK client, PyHamcrest assertions
- **Location:** `codemie_test_harness/tests/<area>/` (every area except `ui/`)
- **Naming:** `test_*.py`; functions named for the behaviour, `test_<action>_<subject>_<condition>` (e.g. `test_create_assistant_with_gitlab_tool`)
- **Structure:** bare `def test_...()` functions (no `Test*` classes for new code), linear bodies, `pytest.mark.parametrize` with readable `ids=` instead of `if`/loops
- **Setup style:** shared fixtures in `tests/conftest.py` — `client`, `regular_client`, one `*_utils` fixture per area (`assistant_utils`, `workflow_utils`, `integration_utils`, `project_utils`, …) backed by helper classes in `tests/utils/`, and factory fixtures such as `assistant()` that clean up after themselves. Use them; do not rebuild their calls inline. Any new resource gets a `yield` fixture whose teardown deletes it (`try: client.<resource>.delete(...)` / `except Exception: pass`) — never cleanup in the test body. External systems the tests rely on (issue trackers, wikis, VCS, cloud, monitoring) come from the persistent seed fixtures (`jira_seed_issue`, `confluence_seed_page`, …); read them, never mutate or delete them.
- **Test data:** `@dataclass` + factory function using `get_random_name()`, in `tests/test_data/<feature>_test_data.py` — not inline in the test
- **Selectors:** n/a (no browser)
- **Abstractions:** the `*_utils` helper classes; no other layer
- **Run one test:** `poetry run pytest -v <test-file>`
- **Run suite:** `poetry run pytest -n 10 --dist=loadgroup -m api --reruns 2`
- **Run suite (silent):** `poetry run pytest -q -n 10 --dist=loadgroup -m api --reruns 2 --tb=short`

`--dist=loadgroup` is required for `@pytest.mark.xdist_group(...)` to take effect — tests
without that marker still load-balance across workers as before; only a named group is pinned
to one worker. Used for suites with singleton shared-state tests (e.g. `marketplaceThresholds`
in `test_marketplace_thresholds_api.py`) that must serialize among themselves without forcing
a dedicated non-parallel pass.

### E2E UI
- **Framework:** pytest-playwright
- **Location:** `codemie_test_harness/tests/ui/<area>/`
- **Naming:** `test_*.py`, same function naming as the API layer
- **Structure:** bare `def test_...()` functions that call page-object methods only — no locators and no `expect()` in the test body
- **Setup style:** `tests/ui/conftest.py` logs in automatically (`login`, autouse), takes a screenshot on failure (`screenshot_on_failure`, autouse), installs Playwright browsers once per session. Tests never log in themselves. CRUD flows split creation and cleanup across layers: create via UI → clean up via API; create via API → mutate or delete via UI → clean up via API.
- **Test data:** `tests/ui/test_data/<area>_test_data.py`
- **Selectors:** `get_by_role()` first, then `get_by_label()` / `get_by_text()` / `get_by_placeholder()`, then a scoped `.locator()` with `.filter()`. No `nth-child`, deeply nested CSS, or generated class names.
- **Abstractions:** page-object model — `tests/ui/pageobject/<area>/<subject>_page.py`, every class derives from `BasePage` (navigation helpers, `self.pop_up`, `self.menu`, common verifications). Elements are `@property` locators with a docstring. Public methods carry `@step` (from `reportportal_client`). Assertions live in page-object `should_*` methods using `expect()`, which retries; never a bare `assert` on a locator. Reusable widgets: `tests/ui/pageobject/components/`.
- **Run one test:** `poetry run pytest -v <test-file> --ui-headless`
- **Run suite:** `poetry run pytest -n 4 -m ui --reruns 2 --ui-headless`

`--ui-headless` is required explicitly — the pytest.ini line that would make it the default is commented out.

## Suite inventory

| Suite | Location | Covers |
|---|---|---|
| `api` | `codemie_test_harness/tests/` (all areas except `ui/`) | API / integration tests against a deployed stand |
| `ui` | `codemie_test_harness/tests/ui/` | Playwright UI tests |
| `sanity` | marker, across areas | assistants / workflows / datasources without integrations; the only suite that needs no AWS credentials |
| `smoke` | marker, across areas | quick checks for local development |
| `enterprise` | marker, across areas | enterprise-only features |
| `prod_regression` | marker, `ui` only | UI tests safe to run on PROD with a regular user or admin (not a maintainer); run with `-m "ui and prod_regression"`. Never on `budget`, `cli_analytics`, `auditor` or `aice` tests |
| feature markers (`budget`, `skill`, `user`, `project`, `cli_analytics`, …) | marker, across areas | one product area each; combine with `api` or `ui` |

## Markers

- Every test carries exactly one of `@pytest.mark.api` or `@pytest.mark.ui` — never both. A test with neither is selected by no suite.
- Stated stack order for new tests: scope (`smoke`, `sanity`) → feature → `api`/`ui` last, directly above `def`. Older tests vary (`timeout` or `parametrize` sometimes sit last); don't reorder existing tests just for this.
- **No ticket references in new tests.** Do not add `@pytest.mark.testcase(...)`, and do not put a ticket key anywhere in test code, names, comments, docstrings or test data. The factory's `# @case <case ID>` traceability comment stays: its ID is ticket-free (`<slug>_TC_001`). Some existing tests still carry the old marker or ticket-keyed `@case` IDs; leave them, and do not copy the form.
- `@pytest.mark.not_for_parallel_run` on any test that mutates state other tests share.

## Execution traps

- **`-n` silently drops `not_for_parallel_run` tests.** `pytest_collection_modifyitems` in `tests/conftest.py` deselects them whenever xdist is active, so both `Run suite` commands above skip them. Run them sequentially (no `-n`) for full coverage — and when a generated test carries this marker, verify it with `Run one test`, never with a suite command.
- **`--reruns 2` hides flakiness.** A test that passes on rerun shows green; judge a suspected flaky test by its rerun count, and debug with one run without reruns first.
- **Unknown markers are silent.** Both pytest configs ignore `PytestUnknownMarkWarning`, and markers such as `not_for_parallel_run` are registered in neither, so a mistyped marker selects nothing without warning.
- **Two pytest configs.** `pyproject.toml` and `codemie_test_harness/pytest.ini` both hold pytest settings and register different marker sets (`budget`, `skill` and `user` are registered only in `pyproject.toml`; the live-log settings are only in `pytest.ini`). Which one pytest reads depends on where it is invoked and with which paths, so check the header line `configfile:` when a marker or log setting seems to be ignored.
- **`codemie_test_harness/.env` is git-ignored.** Copy `.env.template` to `.env` locally; the template is the only tracked file.

## Code rules

- **SDK first.** Every CodeMie API call in a test or fixture goes through `client.<service>` or a `*_utils` wrapper. The tests import the published `codemie-sdk-python`, pinned in `pyproject.toml`; the SDK is developed in its own public repository, recorded as the `sdk` entry in `config.json` (`code_repos`, change policy `extend`). If the SDK lacks the call, add it there — new code only, following that repository's contributing guide and its checks — never in a copy inside this monorepo. `from requests import HTTPError` is the normal way to assert an error the SDK raises — that import is fine. Known raw-HTTP exceptions: `conversations/test_conversation_feedback.py` (SDK gap for `/v1/feedback`) and `assistant/tools/ado/test_assistant_for_ado_work_item_tools.py` (verifies state in Azure DevOps itself, not CodeMie).
- **Credentials** come from `CredentialsManager.get_parameter("KEY")`, never `os.getenv()`. Some older datasource and UI workflow tests still read values with `os.getenv()`; don't copy that. `EnvironmentResolver` (`tests/utils/env_resolver.py`) derives the current environment from `CODEMIE_API_DOMAIN`.
- **No mocking library** in tests — they run against a deployed stand.
- **Every `.py` file carries the Apache-2.0 licence header** from `scripts/license_template.txt`; a new file needs it (`make license-fix` inserts it).
- **No internal values in tracked files.** Hosts, e-mail domains, ticket keys and customer names stay out of the tree; `make scan-internal` checks it (needs `HARNESS_SCAN_PATTERNS` and/or `HARNESS_SCAN_CUSTOMER_NAMES` set on the machine; exit 2 means none is set).

## Anti-patterns

| Bad | Better | Why |
|---|---|---|
| `assert result == value` (API) | `assert_that(result, equal_to(value), "message")` | descriptive failure output |
| `assert locator.count() == 3` (UI) | `expect(locator).to_have_count(3)` inside a `should_*` method | `expect()` retries until timeout; a bare `assert` fails immediately |
| `expect(...)` or a locator in the test body | page-object `should_*` method / `@property` locator | POM rule: tests never touch selectors |
| cleanup at the end of the test body | `yield` fixture teardown | the body's cleanup is skipped when the test fails midway |
| `requests.post(url)` against CodeMie | add the SDK method, call `client.<service>` | SDK-first rule |
| `os.getenv("KEY")` | `CredentialsManager.get_parameter("KEY")` | single credential source |
| `try/except` or `pytest.fail()` in a test | let the assertion raise | hides product defects, weaker diagnostics |
| `if`/loops in a test | `parametrize` or split the test | tests stay linear and deterministic |
| inline test data | `tests/test_data/` or `tests/ui/test_data/` module | reusable and reviewable |
| hardcoded ids, hosts or names of a third-party system | a seed helper in `tests/utils/*_seed.py` read through a session fixture | the test runs against any instance of that system |
| `page.wait_for_timeout()` / fixed `sleep` | an explicit wait in a page-object method, or polling | fixed sleeps are slow and flaky |

A few legacy tests still contain some of these (`wait_for_timeout`, `pytest.fail`, `expect()` in the test body, `Test*` classes). Don't copy them; fix them only when the ticket touches that test.

## Project conventions

- Lint and format through `ruff` (`Makefile`): `poetry run ruff check --fix`, `poetry run ruff check`, `poetry run ruff format`. Check-only forms: `poetry run ruff check`, `poetry run ruff format --check`.
- Other `Makefile` targets: `make license-check` / `make license-fix` (licence headers), `make license-scan` (dependency licences), `make scan-internal` (internal values). The scan scripts are invoked as `python3`; where only `python` exists, run them with that.
- UI tests need Playwright browsers (`playwright install`).
- To run the tests against an unreleased SDK change, install the SDK clone on top of the Poetry environment (`consume.local` of the `sdk` entry in `config.json`); `make install` returns to the pinned release. The tests then follow whatever branch that clone has checked out.
