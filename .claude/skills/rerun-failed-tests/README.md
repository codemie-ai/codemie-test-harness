# Rerun Failed Tests

Takes a pytest console log, reruns the tests that failed from the directory they were launched in, and reports which ones now pass and which still fail. Remaining failures are grouped by root cause, and each group gets a one-line `pytest` command for your OS and shell. For example, a 504 on `/v1/projects/{id}` is one group no matter which project id was hit.

## Use It For

- Checking which failures from a long run are flaky and which are real.
- Grouping a pile of failures into a few actionable buckets:
  - an HTTP status on a specific endpoint
  - assertion message
  - DNS or connection problems
  - timeouts
  - xdist worker crashes
  - Playwright locator timeouts
- Getting copy-paste rerun commands per group. PowerShell is the default on Windows, bash on Linux and macOS, and cmd when your log came from cmd.
- Projects onboarded with QA Factory: worker counts, rerun count and the UI headless flag come from `qa-factory/config.json`. Other pytest projects get the defaults: API 8 workers, UI 4 workers, 2 reruns, UI headless.

## How To Ask

Examples:

- "Rerun the failed tests from `C:\proj\failed.md`."
- "Перезапусти упавшие тесты из этого лога и сгруппируй что осталось." (Rerun the failed tests from this log and group what's left.)
- "Here's my pytest output — which of these still fail?" (paste the log)
- "Rerun these failures with 2 workers and no reruns."
- "Just group the failures in this log, don't run anything."

## What It Needs

- Python 3.9+ to run the bundled helper script (standard library only).
- The project checked out on the machine where the agent runs, with its test environment (venv or poetry env) installed. The skill finds the venv and launch directory from the log, and asks you if they don't exist locally.
- `pytest-xdist` and `pytest-rerunfailures` in that environment, for `-n` and `--reruns`.
- Access to whatever environment the tests hit: stand URL, VPN, credentials in `.env`. The skill reruns real tests and does not mock anything.
- The log should include the start of the run: the shell prompt line and the `rootdir:` / `platform` header. It should also include the `short test summary info` section. A plain copy of the terminal output is enough.

Rerun output (junit XML, console logs, `report.md`) goes to a temp directory, not into your repository. The skill never edits tests.
