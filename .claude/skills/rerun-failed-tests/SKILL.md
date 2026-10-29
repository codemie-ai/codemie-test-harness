---
name: rerun-failed-tests
description: >-
  Rerun the failed tests from a pytest console log, then report which now pass and which still
  fail. Remaining failures are grouped by root cause (the same HTTP status on the same endpoint
  counts as one group even when entity ids differ; also assertion text, DNS or connection errors,
  timeouts, xdist worker crashes), and every group gets a ready-to-paste one-line `pytest` command
  for the user's OS and shell. It reads the launch directory, venv and original flags from the
  log, and takes worker counts, reruns and the UI headless flag from qa-factory/config.json when
  the project has one. Use this skill whenever the user pastes or attaches a pytest log or
  failures list, or says "rerun failed tests", "перезапусти упавшие тесты", "реран фейлов",
  "прогони заново что упало", "which of these still fail", "group these failures", "дай команды
  для перезапуска". Also use it for a pytest output file such as failed.md or failed.log, or for
  checking whether failures are flaky or a real regression.
metadata:
  author: codemie-team
  version: "0.1.0"
---

# Rerun Failed Tests

The user gives you a pytest console log from a run that had failures. You rerun exactly those
tests from the directory the user launched them in, then report:

- **Passed on rerun**, with flaky ones marked. A test is flaky only when the report shows it
  needed `--reruns` retries before it passed. A test that passed on the first attempt is not
  flaky by that evidence. If it passed because the rerun changed something (it added
  `--ui-headless`, or used fewer workers than the original run), say that is the likely cause
  rather than calling it flaky.
- **Still failing**, grouped by failure signature. Each group gets a one-line command that starts
  with `pytest`.

A bundled script does the parsing, running and grouping. Use it: grouping 20 tracebacks by hand
in a 4000-line log is slow, and different runs of it drift. Your job is to feed the script the
right inputs, check its plan, run it and relay the result clearly.

Script: `scripts/rerun_failed.py`. It uses only the standard library and runs on any Python 3.9+,
not just the project's venv. Below, `<skill>` means this skill's directory.

## 1. Get the log into a file

- If the user gave a path, use it.
- If they pasted the log, save it verbatim to a temp file such as `$env:TEMP\failed-<ts>.log` or
  `/tmp/failed-<ts>.log`, and parse that. Keep the first lines: the shell prompt with the launch
  directory and the original command lives there.

## 2. Work out OS, shell and overrides

- The OS is the machine you are running on (see your environment info). The tests are rerun
  here, so commands must work here.
- Pick the shell for the printed commands:
  - Windows: `powershell` is the primary shell. Use `cmd` only if the user's log prompt was cmd
    (`C:\path>` with no `PS`) or the user asks for it.
  - Linux or macOS: `bash`.
- Settings precedence: an explicit value in the user's message beats the qa-factory profile,
  which beats the skill defaults (api 8 workers, ui 4 workers, 2 reruns). "Run with 2 workers" →
  `--api-workers 2 --ui-workers 2`. "No reruns" → `--reruns 0`.

## 3. Build the plan

```
python <skill>/scripts/rerun_failed.py plan --log <log> --shell <shell> [--api-workers N] [--ui-workers N] [--reruns N] [--cwd DIR]
```

The script:

- Reads the launch dir from the prompt line: `(.venv) PS C:\proj>`, `C:\proj>`, `user@host:~/proj$`,
  or the Git Bash `MINGW64 /c/proj` line. If there is no prompt, it uses `rootdir:`.
- Reads the venv from the `platform ... -- <python.exe>` line.
- Reads the failed node ids from `short test summary info`, falling back to progress lines.
- Keeps custom flags of the original command (e.g. `--env=staging`). It drops selection and
  parallelism flags such as `-m`, `-k`, `-n`, `-x` and `--lf`, because the rerun selects by node
  id and sets those itself.
- Loads `qa-factory/config.json` from the launch dir or a parent. The profile with
  `required_capabilities: ["api"]` gives the API `-n`/`--reruns`, and the `["web"]` profile gives
  UI `-n`/`--reruns` plus flags such as `--ui-headless`. `run.levels` globs whose name contains
  ui/web mark a file as UI.
- Without qa-factory, it classifies a file as UI by path segment (`ui`, `e2e-ui`, `web`,
  `playwright`, …) or by file content. It finds a headless option by scanning `conftest.py` for an
  `addoption("--…headless…")`. Plain pytest-playwright is already headless, so no flag is needed
  there.
- Checks that each test still exists. A renamed test would make pytest exit with "not found" and
  abort the whole batch, so missing tests are set aside as "not rerun".

Read the JSON it prints before running anything:

- `cwd` doesn't exist, or a `warnings` entry says the dir was substituted: confirm with the user or
  pass `--cwd`. Rerunning from the wrong directory gives meaningless results.
- `venv_bin` is null: find the environment yourself. Look for `.venv`/`venv` in `cwd`, run
  `poetry env info -p`, or check whether `pytest` is on PATH. Then activate it for the run or
  prepend its `Scripts`/`bin` dir to PATH.
- Warnings about missing `xdist`/`rerunfailures` plugins: tell the user. The printed commands use
  `-n`/`--reruns`, so they need those plugins.
- Settings come out the same as the user asked (qa-factory vs defaults vs override).

## 4. Run

```
python <skill>/scripts/rerun_failed.py run --plan <out_dir>/plan.json
```

- It runs the API batch first, then the UI batch, from `cwd` with the venv on PATH.
- It writes `api.xml`/`ui.xml` (junit) and `api.log`/`ui.log` into the plan's `out_dir`, a temp
  dir, so nothing lands in the user's repo.
- The tests hit real environments, and a batch can take as long as the original run. The sample
  log took over 2 hours for 75 tests. Run it in the background and tell the user it's running and
  roughly how many tests are in each batch. Don't sit in a blocking call that will time out.
- Exit code 1 just means some tests failed. That is expected. Exit codes 2–5 (usage error,
  interrupted, no tests collected) mean the batch itself broke: look at the tail of its console
  log and fix the cause before reporting.

## 5. Report

```
python <skill>/scripts/rerun_failed.py report --plan <out_dir>/plan.json
```

It prints markdown and saves `report.md`/`report.json` next to the plan. Present it to the user in
their language, keeping the structure:

1. **Source** – log, launch dir, original command, which settings were used and where they came
   from.
2. **Summary** – rerun N → passed / still failing / not rerun.
3. **✅ Passed on rerun** – mark flaky ones.
4. **❌ Still failing, by group** – for each group give the title, one sample error line, the test
   list, and the command in a fenced block for the chosen shell. Keep each command on one line.
   The user copies it as is.
5. **Rerun everything that still fails** – the combined command. The script prints it when there
   is more than one group.
6. **Not rerun** – with the reason (renamed/removed test, batch crashed).

Then add a short read of the result. Stick to what the evidence supports:

- Every failure in one DNS or connection-refused group points to the environment or VPN, not the
  code. Say so and suggest checking access before digging into tests.
- 5xx/504 groups on one endpoint usually point to backend or gateway load. They are worth a
  separate rerun later with fewer workers.
- Assertion groups that fail the same way twice in a row are likely real regressions or test
  bugs.
- Flaky tests passed only after retries. List them so they can be looked at even though they're
  green.

Don't edit the tests or the project: this skill diagnoses and reruns, nothing more.

## How grouping works (so you can explain or sanity-check it)

The signature is taken from the final exception: the failure message plus the traceback's `E `
lines. Incidental log lines don't count, and neither do quoted source lines. A test that logs a
504 but then fails on an assertion is grouped by the assertion.

| Failure | Grouped by |
|---|---|
| HTTP error (`504 Server Error: … for url: …`, httpx style too) | status + path with the query string dropped and ids (uuid, numbers, long hex, `name-<hex>` suffixes) replaced by `{id}`. The method is shown when the log reveals it. |
| DNS / NameResolution | host only. Every endpoint on that host fails the same way. |
| Connection refused / reset, network timeouts | host or normalized endpoint |
| xdist worker crash | one group. The process died, so there is no traceback. |
| pytest-timeout | one group |
| Playwright `TimeoutError` / `expect` | action + normalized locator |
| AssertionError and others | exception type + first message line, with numbers → `{N}` and ids → `{id}`. If the message is empty, the hamcrest `Expected:` line is used instead. |

If the user wants to see the grouping of the **original** log without rerunning (e.g. "just group
these failures"), run:

```
python <skill>/scripts/rerun_failed.py group --log <log> --shell <shell>
```

It prints groups with commands and runs no tests. The grouping is taken from the traceback's
`E ` lines and the summary reason. Tests that show up only in the short summary, with a reason
cut off at the terminal width (`- demo_app...`), land in a "No error details in the log" group.
Say that those need a rerun to know the cause, rather than guessing. Tests that no longer exist
in the project are listed under `not_found` and left out of every command. Report them, because a
stale node id would make the user's pasted command abort.

## Command format

- It always starts with `pytest` and is one line.
- It omits `-n` for a single test. For several tests, `-n` is capped at the test count, since
  spawning 10 workers for 2 tests only adds startup time.
- It adds `--reruns R`, then the carried-over flags, then the node ids.
- Node ids are quoted only when they need it. Parametrized ids like `test_x[premium]` get single
  quotes in PowerShell and bash, and double quotes in cmd.
- UI and API tests in one group get separate commands, because they use different worker counts
  and flags.
