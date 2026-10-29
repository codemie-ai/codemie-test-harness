#!/usr/bin/env python3
# Copyright 2026 EPAM Systems, Inc. (“EPAM”)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Scan the publishable harness tree for blocked internal values.

The script has NO built-in patterns. The blocked values are supplied at run
time and are kept outside the repository.

Settings (environment variables):

  HARNESS_SCAN_PATTERNS
      Regular expressions (Python `re` syntax), for example internal host
      names, e-mail domains, instance ids and ticket-key patterns.
  HARNESS_SCAN_CUSTOMER_NAMES
      Customer names. Each name is matched as a case-insensitive literal
      (not as a regex).

Format of both settings: if the value is a path to an existing file, the file
is read; otherwise the value is used as is. In both cases the content is a
NEWLINE-separated list, one entry per line. Blank lines and lines that start
with "#" are ignored.

Scope: tracked files under the root (`git ls-files`) when the root is in a git
repository, otherwise every file under the root. The directories in
EXCLUDED_DIRS and the files in EXCLUDED_FILES are always skipped. Binary files
are skipped.

Exit codes: 0 clean, 1 at least one match (prints `file:line: [rule]`; the
matched text is not printed), 2 no pattern is configured (never passes silently).
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

PATTERNS_ENV = "HARNESS_SCAN_PATTERNS"
CUSTOMER_NAMES_ENV = "HARNESS_SCAN_CUSTOMER_NAMES"

EXCLUDED_DIRS = (
    "docs/superpowers",
    "qa-factory",
    ".claude",
    ".codegraph",
    "test_screenshots",
)
EXCLUDED_FILES = ("AGENTS.md", "CLAUDE.md")
SKIPPED_WALK_DIRS = {".git", ".venv", "node_modules", "__pycache__"}


def read_entries(value: str | None) -> list[str]:
    """Return the entries of a setting value (file path or newline list)."""
    if not value or not value.strip():
        return []
    text = value
    candidate = value.strip()
    if "\n" not in candidate and os.path.isfile(candidate):
        text = Path(candidate).read_text(encoding="utf-8")
    entries = []
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            entries.append(line)
    return entries


def build_rules(environ=os.environ) -> list[tuple[str, re.Pattern]]:
    rules = []
    for i, pattern in enumerate(read_entries(environ.get(PATTERNS_ENV)), 1):
        rules.append((f"pattern#{i}", re.compile(pattern, re.IGNORECASE)))
    for i, name in enumerate(read_entries(environ.get(CUSTOMER_NAMES_ENV)), 1):
        rules.append((f"customer#{i}", re.compile(re.escape(name), re.IGNORECASE)))
    return rules


def is_excluded(rel: str) -> bool:
    rel = rel.replace(os.sep, "/")
    if rel in EXCLUDED_FILES:
        return True
    return any(rel == d or rel.startswith(d + "/") for d in EXCLUDED_DIRS)


def list_files(root: Path) -> list[str]:
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", "--", "."],
            capture_output=True,
            check=True,
        ).stdout
        return [p for p in out.decode("utf-8", "surrogateescape").split("\0") if p]
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIPPED_WALK_DIRS]
        for name in filenames:
            files.append(os.path.relpath(os.path.join(dirpath, name), root))
    return sorted(files)


def scan(root: Path, rules) -> list[tuple[str, int, str]]:
    hits = []
    for rel in list_files(root):
        if is_excluded(rel):
            continue
        path = root / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for rule, regex in rules:
                if regex.search(line):
                    hits.append((rel.replace(os.sep, "/"), lineno, rule))
    return hits


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parent.parent),
        help="tree to scan (default: the test-harness directory)",
    )
    args = parser.parse_args(argv)

    rules = build_rules()
    if not rules:
        print(
            f"ERROR: no scan patterns configured. Set {PATTERNS_ENV} and/or "
            f"{CUSTOMER_NAMES_ENV} (value or path to a file, one entry per line).",
            file=sys.stderr,
        )
        return 2

    hits = scan(Path(args.root), rules)
    for rel, lineno, rule in hits:
        print(f"{rel}:{lineno}: [{rule}]")
    if hits:
        print(f"{len(hits)} blocked value(s) found.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
