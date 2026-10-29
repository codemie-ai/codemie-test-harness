#!/usr/bin/env bash
# Installed by `make install-hooks` (test-harness/Makefile) as the repo-wide
# git pre-commit hook. Only lints staged files under test-harness/ — other
# codemie-sdk subprojects are untouched.
set -euo pipefail

repo_root=$(git rev-parse --show-toplevel)

staged=()
while IFS= read -r -d '' f; do
    staged+=("${f#test-harness/}")
done < <(git -C "$repo_root" diff --cached --name-only -z --diff-filter=ACMR -- 'test-harness/*.py')

cd "$repo_root/test-harness"

# Internal-value scan runs on every commit, whether or not .py files are staged.
# Without scan config it prints a notice and is skipped (the commit goes on).
if [ -n "${HARNESS_SCAN_PATTERNS:-}" ] || [ -n "${HARNESS_SCAN_CUSTOMER_NAMES:-}" ]; then
    echo "Scanning test-harness for internal values..."
    if ! python3 scripts/scan_internal_values.py; then
        echo "Internal-value scan failed. Remove the values above (see 'make scan-internal')." >&2
        exit 1
    fi
else
    echo "Notice: HARNESS_SCAN_PATTERNS / HARNESS_SCAN_CUSTOMER_NAMES not set; skipping internal-value scan." >&2
fi

if [ ${#staged[@]} -eq 0 ]; then
    exit 0
fi

# Lint the staged blobs (not the working tree), so unstaged edits cannot mask
# or cause failures. --stdin-filename keeps per-file config and messages intact.
echo "Running ruff on staged test-harness files..."

# Resolve ruff once: `poetry run` costs ~0.5-1s per start.
ruff=$(poetry run which ruff)

failed=0
for f in "${staged[@]}"; do
    # Pipe the staged bytes straight into ruff (no command substitution, which
    # strips trailing newlines and would hide what CI sees).
    if ! git -C "$repo_root" show ":test-harness/$f" | "$ruff" check --stdin-filename "$f" -; then
        failed=1
    fi
    if ! git -C "$repo_root" show ":test-harness/$f" | "$ruff" format --check --stdin-filename "$f" - >/dev/null; then
        echo "ruff format check failed for $f. Run 'make ruff-format' and re-stage." >&2
        failed=1
    fi
done

if [ "$failed" -ne 0 ]; then
    echo "ruff failed. Fix the issues above (or run 'make ruff-fix') before committing." >&2
    exit 1
fi

echo "Checking licence headers on staged test-harness files..."
# Check the staged blobs, like ruff above, so an unstaged edit cannot mask a missing header.
failed=0
for f in "${staged[@]}"; do
    if ! git -C "$repo_root" show ":test-harness/$f" | python3 scripts/check_license_headers.py --stdin; then
        echo "missing licence header: $f" >&2
        failed=1
    fi
done
if [ "$failed" -ne 0 ]; then
    echo "Licence header check failed. Run 'make license-fix' and re-stage." >&2
    exit 1
fi
