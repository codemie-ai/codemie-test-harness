# Test environments

**Project**: codemie-test-harness · **Stack**: Python, pytest 8 + codemie-sdk-python 0.1.709 + pytest-playwright 0.8 (CLI: click 8) · **Scope**: shared seeds and the default project on the shared stand, followed by the QA-owned environments, test-data and safety sections the qa-* skills read; test authoring lives in `.ai-run/guides/testing/strategy.md`

## Shared test data

### Rules
- R1. Read a third-party seed (`jira_seed_issue`, `confluence_seed_page`, the other `*_seed` session fixtures) and never edit or delete it; `resolve_shared` creates it once per run under a file lock the xdist workers share, and the seed then persists on the external system for every later run. Evidence: `codemie_test_harness/tests/utils/jira_seed.py::resolve_shared`
- R2. Use `PROJECT` from `codemie_test_harness.tests` (env `PROJECT_NAME`, default `codemie`) as the shared default project and never create it in a test; the session autouse `ensure_test_project` creates it when absent. Evidence: `codemie_test_harness/tests/conftest.py::ensure_test_project`

### Read first
| When you are | Exemplar | Why this one | Tests |
|---|---|---|---|
| adding a seed for a new external system | `codemie_test_harness/tests/utils/jira_seed.py::resolve_shared` | one produce call per run, cached as JSON under a lock, `TimeoutError` naming the stuck seed | no covering test |

## Environments

| Label | URL | Auth mechanism | Credential env var | Destructive testing |
|---|---|---|---|---|
| preview (default) | from `$CODEMIE_API_DOMAIN` (UI: `$FRONTEND_URL`) | Keycloak password grant | `AUTH_SERVER_URL`, `AUTH_REALM_NAME`, `AUTH_CLIENT_ID`, `AUTH_USERNAME`, `AUTH_PASSWORD` | yes |
| production | from `$CODEMIE_API_DOMAIN` (UI: `$FRONTEND_URL`) | Keycloak password grant (same vars as preview) | `AUTH_SERVER_URL`, `AUTH_REALM_NAME`, `AUTH_CLIENT_ID`, `AUTH_USERNAME`, `AUTH_PASSWORD` | no |

The target is selected by the value of `CODEMIE_API_DOMAIN`; `EnvironmentResolver` (`tests/utils/env_resolver.py`) derives the environment from it. The resolver also recognises other domains (a local stand, `oss_preview`, and Azure, GCP and AWS sandboxes). They are deliberately not listed here, so a flow must treat them as unsafe until they are added.

Settings come from the environment, the config file or `.env`. The AWS Parameter Store is opt-in: it is read only when `HARNESS_SECRET_STORE=aws-parameter-store` (with `AWS_PS_REGION` and `AWS_PS_PATH_PREFIX`). Without it the harness makes no AWS call.

## Test data

- **Strategy:** factories + seeded-shared + committed fixtures.
  - *Per-run factories:* each test fixture creates its own resources through the SDK client, named with `get_random_name()` (`tests/utils/base_utils.py`) so parallel workers don't collide, and cleans them up in the fixture's `yield` teardown.
  - *Shared seeds:* persistent resources in external systems (issue trackers, wikis, VCS, cloud, monitoring, Keycloak users, Report Portal), one idempotent `ensure_seed_*` helper per system in `tests/utils/*_seed.py`. A seed is created once per target system and reused by every later run; session-scoped fixtures in `tests/conftest.py` resolve it under a file lock shared by the xdist workers (`resolve_shared`). Tests read a seed; they never mutate or delete it.
  - *Committed fixtures:* static input files under `tests/test_data/`.
  - *Shared default project:* the project named by `PROJECT` (default `codemie`), ensured by the `ensure_test_project` fixture if absent.
- **Reset mechanism:** none. No automated flow may attempt to reset the shared environment, the shared default project or any seed. Session-level cleanup is gated by `CLEANUP_DATA` (default `true`) and may be switched off on the shared stand, so orphaned autotest entities there are a known, accepted condition, not something a flow should try to fix by writing a reset.
- **Notes:** preview is a shared, long-lived stand (not reset between runs). Tests must own and clean up their own records and must not depend on the absence of other tests' data; the only data they may rely on already existing is a seed.

## Safety

- Environments not marked as permitting destructive testing (production, and any domain not listed above) must be treated as unsafe — read-only use.
- `preview` permits destructive testing.
- Credentials are referenced by variable name only. No secret value appears in this file or any artifact this factory produces.
