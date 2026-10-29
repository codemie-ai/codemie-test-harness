.PHONY: install test unit-test build publish install-hooks scan-internal license-check license-fix license-scan

# `make install` resolves codemie-sdk-python from poetry.lock, exactly like CI.
# Optional override on top of the locked environment (never written to
# pyproject.toml or poetry.lock):
#   SDK_VERSION=0.1.648 exact version, to reproduce a bug
SDK_VERSION ?=

install:
	poetry install
	@if [ -n "$(SDK_VERSION)" ]; then \
		echo "Pinning codemie-sdk-python==$(SDK_VERSION)..."; \
		poetry run pip install "codemie-sdk-python==$(SDK_VERSION)"; \
	fi

unit-test:
	poetry run pytest -p no:cacheprovider -p pytester unit_tests

# Installs scripts/pre-commit-hook.sh as the repo-wide git pre-commit hook.
# It only lints staged test-harness/*.py files, so it is safe to run even
# though .git/hooks is shared with the other codemie-sdk subprojects.
# Refuses to overwrite a different existing hook; FORCE=1 backs it up to
# pre-commit.bak first.
install-hooks:
	@hook_path=$$(git rev-parse --git-path hooks)/pre-commit; \
	if [ -e "$$hook_path" ] && ! cmp -s scripts/pre-commit-hook.sh "$$hook_path"; then \
		if [ "$(FORCE)" = "1" ]; then \
			cp "$$hook_path" "$$hook_path.bak"; \
			echo "Backed up existing hook to $$hook_path.bak"; \
		else \
			echo "A different pre-commit hook exists at $$hook_path. Re-run with FORCE=1 to back it up and replace it." >&2; \
			exit 1; \
		fi; \
	fi; \
	cp scripts/pre-commit-hook.sh "$$hook_path"; \
	chmod +x "$$hook_path"; \
	echo "Installed pre-commit hook at $$hook_path"

# Fails (exit 1) on any blocked internal value, and (exit 2) when no scan
# config is set. Set HARNESS_SCAN_PATTERNS and/or HARNESS_SCAN_CUSTOMER_NAMES
# (value or path to a file, one entry per line); see the script docstring.
scan-internal:
	python3 scripts/scan_internal_values.py

# Licence header check/fix for tracked .py files (see README, "Licensing").
license-check:
	python3 scripts/check_license_headers.py --check

license-fix:
	python3 scripts/check_license_headers.py --fix

# Fails (non-zero, offenders listed) on any dependency licence outside
# [tool.pip-licenses] allow-only in pyproject.toml.
license-scan:
	poetry run pip-licenses

ruff:
	poetry run ruff check --fix
	poetry run ruff check
	poetry run ruff format

ruff-format:
	poetry run ruff format

ruff-fix:
	poetry run ruff check --fix

build:
	poetry build

publish:
	poetry publish
