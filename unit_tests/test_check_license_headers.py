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

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_license_headers as clh  # noqa: E402


def git(*args):
    subprocess.run(["git", *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    git("init", "-q", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    return tmp_path


def track(repo, name, data: bytes):
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    git("add", name)
    return path


def test_missing_header_reported(repo, capsys):
    track(repo, "a.py", b"x = 1\n")
    assert clh.main(["--check"]) == 1
    assert "a.py" in capsys.readouterr().out


def test_present_header_passes(repo):
    track(repo, "a.py", clh.add_header("x = 1\n").encode())
    assert clh.main(["--check"]) == 0


def test_shebang_stays_first():
    out = clh.add_header("#!/usr/bin/env python3\nx = 1\n").splitlines()
    assert out[0] == "#!/usr/bin/env python3"
    assert out[1].startswith("# Copyright")


@pytest.mark.parametrize("first", ["def f():", "async def f():", "class C:", "@dec"])
def test_two_blank_lines_before_top_level_definition(first):
    # ruff format wants two blank lines between the header comment and a def/class.
    out = clh.add_header(f"{first}\n    pass\n").splitlines()
    assert out[len(clh.header_lines()) :][:3] == ["", "", first]


def test_one_blank_line_before_other_code():
    out = clh.add_header("x = 1\n").splitlines()
    assert out[len(clh.header_lines()) :] == ["", "x = 1"]


def test_leading_blank_lines_replaced():
    out = clh.add_header("\n\n\ndef f():\n    pass\n").splitlines()
    assert out[len(clh.header_lines()) :][:3] == ["", "", "def f():"]


def test_shebang_and_cookie_precede_header():
    out = clh.add_header(
        "#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\nx = 1\n"
    ).splitlines()
    assert out[1] == "# -*- coding: utf-8 -*-"
    assert out[2].startswith("# Copyright")
    assert clh.has_header("\n".join(out))


def test_bom_stays_first_and_file_compiles():
    out = clh.add_header("﻿#!/usr/bin/env python3\nx = 1\n")
    assert out.startswith("﻿#!/usr/bin/env python3\n# Copyright")
    compile(out.encode("utf-8"), "a.py", "exec")


def test_explicit_file_check_reports_only_that_file(repo, capsys):
    track(repo, "a.py", b"x = 1\n")
    track(repo, "b.py", b"y = 1\n")
    assert clh.main(["--check", "a.py"]) == 1
    out = capsys.readouterr().out
    assert "a.py" in out
    assert "b.py" not in out


def test_explicit_file_fix_leaves_other_files(repo):
    a = track(repo, "a.py", b"x = 1\n")
    b = track(repo, "b.py", b"y = 1\n")
    assert clh.main(["--fix", "a.py"]) == 0
    assert clh.has_header(a.read_text())
    assert b.read_bytes() == b"y = 1\n"


def test_empty_file_gets_header(repo):
    track(repo, "pkg/__init__.py", b"")
    assert clh.main(["--check"]) == 1
    assert clh.main(["--fix"]) == 0
    assert clh.main(["--check"]) == 0


def test_crlf_fix_then_check(repo):
    path = track(repo, "a.py", b"x = 1\r\ny = 2\r\n")
    assert clh.main(["--fix"]) == 0
    data = path.read_bytes()
    assert b"\n" not in data.replace(b"\r\n", b"")
    assert clh.main(["--check"]) == 0


def test_fix_idempotent(repo):
    path = track(repo, "a.py", b"x = 1\n")
    clh.main(["--fix"])
    first = path.read_bytes()
    clh.main(["--fix"])
    assert path.read_bytes() == first


def test_path_outside_cwd_ignored(repo, tmp_path_factory):
    sub = repo / "th"
    track(repo, "th/a.py", b"x = 1\n")
    outside = track(repo, "other.py", b"y = 1\n")
    import os

    os.chdir(sub)
    assert clh.main(["--fix", str(outside)]) == 0
    assert outside.read_bytes() == b"y = 1\n"


def test_zero_files_fails(repo, capsys):
    assert clh.main(["--check"]) == 1
    assert "no tracked" in capsys.readouterr().out


def test_count_mismatch_fails(repo, monkeypatch, capsys):
    track(repo, "a.py", clh.add_header("x = 1\n").encode())
    track(repo, "b.py", clh.add_header("y = 1\n").encode())
    monkeypatch.setattr(clh, "discover", lambda: ["a.py"])
    assert clh.main(["--check"]) == 1
    assert "mismatch" in capsys.readouterr().out


def test_skip_worktree_file_ignored(repo):
    track(repo, "a.py", clh.add_header("x = 1\n").encode())
    skipped = track(repo, "z.py", b"z = 1\n")
    git("update-index", "--skip-worktree", "z.py")
    assert clh.main(["--check"]) == 0
    assert clh.main(["--fix"]) == 0
    assert skipped.read_bytes() == b"z = 1\n"


def test_checked_count_printed_unless_quiet(repo, capsys):
    track(repo, "a.py", clh.add_header("x = 1\n").encode())
    clh.main(["--check"])
    assert "checked 1 files" in capsys.readouterr().out
    clh.main(["--check", "--quiet"])
    assert "checked" not in capsys.readouterr().out


def test_mixed_line_endings_preserved():
    out = clh.add_header("x = 1\ny = 2\r\nz = 3\n")
    assert out.endswith("x = 1\ny = 2\r\nz = 3\n")
    assert clh.has_header(out)


def test_shebang_followed_by_blank_lines_only():
    out = clh.add_header("#!/usr/bin/env python3\n\n\n")
    assert out.startswith("#!/usr/bin/env python3\n# Copyright")
    assert out.endswith("\n\n\n")
    assert clh.has_header(out)


def test_non_utf8_file_reported_and_run_continues(repo, capsys):
    track(repo, "a.py", b"\xff\xfe = 1\n")
    track(repo, "b.py", b"y = 1\n")
    assert clh.main(["--fix"]) == 1
    out = capsys.readouterr().out
    assert "cannot read a.py" in out
    assert clh.has_header((repo / "b.py").read_text())


def test_stdin_checks_content(monkeypatch):
    import io

    class Stdin:
        def __init__(self, data):
            self.buffer = io.BytesIO(data)

    monkeypatch.setattr(sys, "stdin", Stdin(b"x = 1\n"))
    assert clh.main(["--stdin"]) == 1
    monkeypatch.setattr(sys, "stdin", Stdin(clh.add_header("x = 1\n").encode()))
    assert clh.main(["--stdin"]) == 0


def test_count_tracked_excludes_skip_worktree(repo):
    track(repo, "a.py", b"x = 1\n")
    track(repo, "b.py", b"y = 1\n")
    git("update-index", "--skip-worktree", "b.py")
    assert clh.count_tracked() == 1
