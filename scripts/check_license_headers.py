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

"""Check (default) or add (--fix) the licence header in tracked .py files.

Run from test-harness/. Scope: tracked `*.py` files under the current
directory (`git ls-files`). The header text is scripts/license_template.txt,
rendered with a "# " prefix and searched in the first 50 lines. Files are read
and written as bytes, so line endings are preserved.

Exit codes: 0 ok, 1 at least one file lacks the header or cannot be read.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

TEMPLATE = Path(__file__).with_name("license_template.txt")
SEARCH_LINES = 50
CODING_RE = re.compile(r"^[ \t\f]*#.*?coding[:=][ \t]*[-\w.]+")
TOP_LEVEL_DEF_RE = re.compile(r"(async\s+def|def|class)\s|@")


def header_lines() -> list[str]:
    lines = TEMPLATE.read_text(encoding="utf-8").splitlines()
    return [f"# {line}".rstrip() for line in lines]


def has_header(text: str) -> bool:
    head = "\n".join(text.replace("\r\n", "\n").split("\n")[:SEARCH_LINES])
    return "\n".join(header_lines()) in head


def add_header(text: str) -> str:
    if has_header(text):
        return text
    # A UTF-8 BOM must stay the first character, or Python rejects the file.
    bom = "﻿" if text.startswith("﻿") else ""
    text = text.removeprefix(bom)
    lines = text.splitlines(keepends=True)
    # Header lines use the first line's ending; other lines keep their own.
    nl = lines[0][len(lines[0].rstrip("\r\n")) :] or "\n" if lines else "\n"
    keep = 0  # shebang and coding cookie stay above the header
    if lines and lines[0].startswith("#!"):
        keep = 1
    if len(lines) > keep and CODING_RE.match(lines[keep]):
        keep += 1
    head = "".join(lines[:keep])
    if head and not head.endswith(("\n", "\r")):
        head += nl
    rest = lines[keep:]
    block = "".join(f"{line}{nl}" for line in header_lines())
    if any(line.strip() for line in rest):
        # Our own blank lines replace the leading ones, so the gap is always the same.
        while not rest[0].strip():
            rest.pop(0)
        block += nl
        # ruff format wants two blank lines between the header and a top-level def/class.
        if TOP_LEVEL_DEF_RE.match(rest[0]):
            block += nl
    return bom + head + block + "".join(rest)


def git_ls_files() -> list[tuple[str, str]]:
    out = subprocess.run(
        ["git", "ls-files", "-v", "--", "*.py"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [(line[0], line[2:]) for line in out.splitlines()]


def discover() -> list[str]:
    # Skip-worktree files (tag "S") are local-only edits: never checked or fixed.
    return sorted(p for tag, p in git_ls_files() if tag != "S")


def count_tracked() -> int:
    """Count tracked .py files from two other git calls (no `-v` parsing).

    It cross-checks discover() against changes in the `-v` tag format.
    """

    def run(*args: str) -> list[str]:
        return subprocess.run(
            ["git", "ls-files", *args, "--", "*.py"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()

    return len(run()) - sum(1 for line in run("-t") if line.startswith("S "))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check", action="store_true", help="report files without header (default)"
    )
    mode.add_argument("--fix", action="store_true", help="insert the header")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="check the file content on stdin (used for staged blobs)",
    )
    parser.add_argument("files", nargs="*")
    args = parser.parse_args(argv)

    if args.stdin:
        return 0 if has_header(sys.stdin.buffer.read().decode("utf-8")) else 1

    candidates = discover()
    if not args.files:
        if not candidates:
            print("no tracked .py files found; refusing to pass on an empty scan")
            return 1
        tracked = count_tracked()
        if len(candidates) != tracked:
            print(
                f"file count mismatch: discovered {len(candidates)}, git lists {tracked}"
            )
            return 1
    if args.files:
        wanted = {str(Path(f).resolve()) for f in args.files}
        candidates = [c for c in candidates if str(Path(c).resolve()) in wanted]

    missing = []
    unreadable = []
    for path in candidates:
        try:
            text = Path(path).read_bytes().decode("utf-8")
        except (OSError, UnicodeDecodeError) as e:
            unreadable.append(f"{path}: {e}")
            continue
        if has_header(text):
            continue
        if args.fix:
            Path(path).write_bytes(add_header(text).encode("utf-8"))
        else:
            missing.append(path)

    for path in missing:
        print(f"missing licence header: {path}")
    for entry in unreadable:
        print(f"cannot read {entry}")
    if not args.quiet:
        print(f"checked {len(candidates)} files")
    return 1 if missing or unreadable else 0


if __name__ == "__main__":
    sys.exit(main())
