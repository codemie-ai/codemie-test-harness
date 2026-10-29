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

"""Rerun failed pytest tests from a console log and group what still fails.

Subcommands (stdlib only, Python 3.9+):

  plan    --log FILE [--shell powershell|bash|cmd] [--cwd DIR]
          [--api-workers N] [--ui-workers N] [--reruns N] [--out-dir DIR]
      Parse the log, find the launch directory, venv and failed node ids,
      split them into api / ui batches and write <out-dir>/plan.json.

  run     --plan PLAN
      Execute every batch sequentially (pytest + junit xml + console log).

  report  --plan PLAN
      Read the junit files, group failures by signature and print markdown
      (also written to <out-dir>/report.md and report.json).

  group   --log FILE [--shell ...]
      Group the failures of the ORIGINAL log without rerunning anything.
"""

import argparse
import datetime as _dt
import fnmatch
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

DEFAULTS = {"api_workers": 8, "ui_workers": 4, "reruns": 2}

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
HEX_ID_RE = re.compile(r"\b(?=[0-9a-fA-F]*\d)[0-9a-fA-F]{8,}\b")
RANDOM_SUFFIX_RE = re.compile(r"(?<=[A-Za-z])[-_](?=[0-9a-fA-F]*\d)[0-9a-fA-F]{6,}\b")
ADDR_RE = re.compile(r"\b0x[0-9a-fA-F]+\b")
NUM_RE = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?:e-?\d+)?(?![\w.])")
WORKER_RE = re.compile(r"\bgw\d+\b")

UI_SEGMENTS = {
    "ui",
    "e2e-ui",
    "e2e_ui",
    "web",
    "frontend",
    "playwright",
    "browser",
    "selenium",
    "pageobject",
}
UI_CONTENT_RE = re.compile(
    r"(from playwright|import playwright|selenium|pytest\.mark\.ui\b)"
)
# Options of the original command that the rerun controls itself (value-taking ones map to True).
DROP_OPTS = {
    "-n": True,
    "--numprocesses": True,
    "-m": True,
    "-k": True,
    "--reruns": True,
    "--reruns-delay": True,
    "--dist": True,
    "--maxprocesses": True,
    "--junitxml": True,
    "--junit-xml": True,
    "-x": False,
    "--exitfirst": False,
    "--lf": False,
    "--last-failed": False,
    "--ff": False,
    "--failed-first": False,
    "-v": False,
    "-vv": False,
    "-q": False,
    "--headed": False,
    "--ui-headed": False,
    "--collect-only": False,
    "--co": False,
}


# --------------------------------------------------------------------------- log parsing

PS_PROMPT = re.compile(
    r"^(?:\((?P<venv>[^)]+)\)\s*)?PS (?P<cwd>(?:[A-Za-z]:[\\/]|\\\\|/)[^>]*)>\s*(?P<cmd>.*)$"
)
CMD_PROMPT = re.compile(
    r"^(?:\((?P<venv>[^)]+)\)\s*)?(?P<cwd>[A-Za-z]:\\[^>]*)>\s*(?P<cmd>.*)$"
)
SH_PROMPT = re.compile(
    r"^(?:\((?P<venv>[^)]+)\)\s*)?(?:[\w.-]+@[\w.-]+(?::|\s+))?(?P<cwd>(?:~|/)[^$%#>]*?)?\s*[$%#❯]\s+(?P<cmd>.*)$"
)
MINGW_LINE = re.compile(r"\bMINGW(?:32|64)\s+(?P<cwd>/\S.*)$")
RUNNER_RE = re.compile(
    r"(?:^|\s)(?:poetry run |uv run |pipenv run |python3? -m |py -m )?pytest(?:\.exe)?(?:\s|$)"
)
SUMMARY_RE = re.compile(r"^(FAILED|ERROR) ((?:[^\s\[]+)(?:\[.*?\])?)(?: - (.*))?\s*$")
PROGRESS_RE = re.compile(
    r"(?:\[gw\d+\]\s+\[\s*\d+%\]\s+)?(PASSED|FAILED|ERROR|RERUN|SKIPPED|XFAIL|XPASS) ((?:[^\s\[]+::[^\s\[]+)(?:\[.*?\])?)"
)
PROGRESS_V_RE = re.compile(
    r"^((?:[^\s\[]+::[^\s\[]+)(?:\[.*?\])?) (PASSED|FAILED|ERROR|RERUN|SKIPPED|XFAIL|XPASS)\b"
)


def read_text(path):
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "utf-16", "cp1251", "latin-1"):
        try:
            text = raw.decode(enc)
            if enc == "utf-16" and "\x00" in text[:200]:
                continue
            return ANSI_RE.sub("", text).replace("\r\n", "\n").replace("\r", "\n")
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def detect_prompt(lines):
    """Return the shell prompt that launched pytest: cwd, shell, venv name, command."""
    for i, line in enumerate(lines[:400]):
        s = line.strip()
        if not RUNNER_RE.search(s):
            continue
        for shell, rx in (
            ("powershell", PS_PROMPT),
            ("cmd", CMD_PROMPT),
            ("bash", SH_PROMPT),
        ):
            m = rx.match(s)
            if not m or not RUNNER_RE.search(m.group("cmd")):
                continue
            cwd = (m.group("cwd") or "").strip()
            if shell == "bash" and not cwd and i > 0:
                prev = MINGW_LINE.search(lines[i - 1].strip())
                if prev:
                    cwd = prev.group("cwd").strip()
            return {
                "shell": shell,
                "cwd": cwd or None,
                "venv": m.group("venv"),
                "command": m.group("cmd").strip(),
            }
    return {"shell": None, "cwd": None, "venv": None, "command": None}


def mingw_to_windows(path):
    m = re.match(r"^/([a-zA-Z])(/.*)?$", path or "")
    if m and platform.system() == "Windows":
        return f"{m.group(1).upper()}:{(m.group(2) or '/').replace('/', chr(92))}"
    return path


def parse_log(text):
    lines = text.split("\n")
    info = detect_prompt(lines)
    if info["cwd"]:
        info["cwd"] = mingw_to_windows(info["cwd"])
    for line in lines[:400]:
        if line.startswith("rootdir: "):
            info["rootdir"] = line[len("rootdir: ") :].split(",")[0].strip()
        elif line.startswith("platform "):
            info["platform"] = line.split()[1]
            if " -- " in line:
                exe = line.rsplit(" -- ", 1)[1].strip()
                if re.search(r"python[\d.]*(\.exe)?$", exe, re.I):
                    info["python"] = exe
        elif line.startswith("plugins: "):
            info["plugins"] = [
                p.strip().rsplit("-", 1)[0] for p in line[len("plugins: ") :].split(",")
            ]

    final = {}  # nodeid -> {"status", "reason"}
    for line in lines:
        s = line.strip()
        m = SUMMARY_RE.match(s)
        if m:
            final[m.group(2)] = {
                "status": m.group(1).lower(),
                "reason": (m.group(3) or "").strip(),
                "source": "summary",
            }
    progress = {}
    reruns = {}
    for line in lines:
        s = line.strip()
        for m in PROGRESS_RE.finditer(s):
            status, node = m.group(1), m.group(2)
            if status == "RERUN":
                reruns[node] = reruns.get(node, 0) + 1
            else:
                progress[node] = status.lower()
        m = PROGRESS_V_RE.match(s)
        if m:
            node, status = m.group(1), m.group(2)
            if status == "RERUN":
                reruns[node] = reruns.get(node, 0) + 1
            else:
                progress[node] = status.lower()
    for node, status in progress.items():
        if status in ("failed", "error") and node not in final:
            final[node] = {"status": status, "reason": "", "source": "progress"}
    # A test that errored in teardown after passing shows both; keep one entry per node id.
    info["failed"] = [dict(nodeid=k, **v) for k, v in final.items()]
    info["passed_in_log"] = sorted(
        k for k, v in progress.items() if v == "passed" and k not in final
    )
    info["reruns_in_log"] = reruns
    totals = [
        ln
        for ln in lines
        if re.match(r"^=+ .*\b(passed|failed|error)\b.* in [\d.]+s", ln.strip())
    ]
    info["totals_line"] = totals[-1].strip("= ").strip() if totals else None
    info["crash_reasons"] = {
        m.group(2): m.group(0)
        for m in re.finditer(r"worker '(gw\d+)' crashed while running '([^']+)'", text)
    }
    info["sections"] = split_failure_sections(lines)
    return info


def split_failure_sections(lines):
    """Map test function name -> traceback text from the FAILURES / ERRORS blocks."""
    sections, current, buf = {}, None, []
    header = re.compile(r"^_{3,} (?:ERROR at (?:setup|teardown) of )?(.+?) _{3,}$")
    in_block = False
    for line in lines:
        s = line.rstrip()
        if re.match(r"^=+ (FAILURES|ERRORS) =+$", s):
            in_block = True
            continue
        if in_block and re.match(r"^=+ .* =+$", s):
            if current:
                sections[current] = "\n".join(buf)
            current, buf, in_block = None, [], "summary" not in s and in_block
            continue
        if not in_block:
            continue
        m = header.match(s)
        if m:
            if current:
                sections[current] = "\n".join(buf)
            current, buf = m.group(1).strip(), []
        elif current:
            buf.append(s)
    if current:
        sections[current] = "\n".join(buf)
    return sections


def split_command(cmd, shell):
    try:
        return shlex.split(cmd, posix=(shell != "cmd" and shell != "powershell"))
    except ValueError:
        return cmd.split()


def carried_options(cmd, shell):
    """Options of the original pytest command worth keeping (custom env/config flags)."""
    if not cmd:
        return []
    tokens = [t.strip("'\"") for t in split_command(cmd, shell)]
    while tokens and not re.match(r"^pytest(\.exe)?$", tokens[0]):
        tokens.pop(0)
    tokens = tokens[1:]
    keep, i = [], 0
    while i < len(tokens):
        tok = tokens[i]
        name = tok.split("=", 1)[0]
        takes_value = DROP_OPTS.get(name)
        compact = re.match(r"^-(n|m|k)(.+)$", tok)  # -n4, -mapi
        if compact or (takes_value is not None and "=" in tok):
            i += 1
            continue
        if takes_value is not None:
            i += 2 if takes_value else 1
            continue
        if tok.startswith("-"):
            keep.append(tok)
            nxt = tokens[i + 1] if i + 1 < len(tokens) else None
            if (
                "=" not in tok
                and nxt
                and not nxt.startswith("-")
                and not looks_like_path(nxt)
            ):
                keep.append(nxt)
                i += 1
        i += 1
    return keep


def looks_like_path(tok):
    return "::" in tok or tok.endswith(".py") or "/" in tok or "\\" in tok


# --------------------------------------------------------------------------- qa-factory config


def find_qa_config(start):
    p = Path(start).resolve()
    for d in [p, *p.parents]:
        cfg = d / "qa-factory" / "config.json"
        if cfg.is_file():
            return cfg
    return None


def profile_settings(config, capability):
    """workers / reruns / extra flags from the qa-factory profile for 'api' or 'web'."""
    for prof in config.get("profiles", []):
        if capability not in prof.get("required_capabilities", []):
            continue
        cmds = prof.get("named_commands", [])
        cmd = next(
            (c for c in cmds if c.get("kind") == "suite"), cmds[0] if cmds else None
        )
        if not cmd:
            continue
        argv = list(cmd.get("argv", []))
        if "pytest" in argv:
            argv = argv[argv.index("pytest") + 1 :]
        out = {
            "source": f"qa-factory profile '{prof.get('profile_id')}' ({cmd.get('kind')})",
            "flags": [],
        }
        i = 0
        while i < len(argv):
            tok = argv[i]
            if (
                tok in ("-n", "--numprocesses")
                and i + 1 < len(argv)
                and argv[i + 1].isdigit()
            ):
                out["workers"] = int(argv[i + 1])
                i += 2
                continue
            if tok == "--reruns" and i + 1 < len(argv) and argv[i + 1].isdigit():
                out["reruns"] = int(argv[i + 1])
                i += 2
                continue
            name = tok.split("=", 1)[0]
            if name in DROP_OPTS or tok.startswith("--tb"):
                i += 2 if DROP_OPTS.get(name) and "=" not in tok else 1
                continue
            out["flags"].append(tok)
            i += 1
        return out
    return None


def ui_levels(config):
    """Glob patterns that mark a test file as UI (run.levels entries whose name mentions ui/web)."""
    levels = (config.get("run") or {}).get("levels") or {}
    ui, api = [], []
    for name, globs in levels.items():
        (ui if re.search(r"ui|web|browser", name, re.I) else api).extend(globs)
    return ui, api


def detect_headless_flag(cwd):
    """A project-level --*headless* option declared in any conftest.py, if there is one."""
    rx = re.compile(r"addoption\(\s*[\"'](--[\w-]*headless[\w-]*)[\"']")
    root = Path(cwd)
    for conf in (
        list(root.glob("conftest.py"))
        + list(root.glob("*/conftest.py"))
        + list(root.glob("*/*/conftest.py"))
        + list(root.glob("*/*/*/conftest.py"))
    ):
        try:
            m = rx.search(conf.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
        if m:
            return m.group(1)
    return None


# --------------------------------------------------------------------------- planning


def node_file(nodeid):
    return nodeid.split("::", 1)[0]


def node_func(nodeid):
    return re.sub(r"\[.*\]$", "", nodeid.split("::")[-1])


def classify_kind(nodeid, cwd, ui_globs, api_globs):
    path = node_file(nodeid).replace("\\", "/")
    for g in ui_globs:
        if fnmatch.fnmatch(path, g) or fnmatch.fnmatch(
            path, g.rstrip("*").rstrip("/") + "/*"
        ):
            return "ui"
    for g in api_globs:
        if fnmatch.fnmatch(path, g) or fnmatch.fnmatch(
            path, g.rstrip("*").rstrip("/") + "/*"
        ):
            return "api"
    if any(seg.lower() in UI_SEGMENTS for seg in path.split("/")[:-1]):
        return "ui"
    try:
        if UI_CONTENT_RE.search(
            (Path(cwd) / path).read_text(encoding="utf-8", errors="ignore")
        ):
            return "ui"
    except OSError:
        pass
    return "api"


def node_exists(nodeid, cwd):
    f = Path(cwd) / node_file(nodeid)
    if not f.is_file():
        return False, f"file not found: {node_file(nodeid)}"
    if "::" not in nodeid:
        return True, ""
    func = node_func(nodeid)
    src = f.read_text(encoding="utf-8", errors="ignore")
    if re.search(rf"\bdef {re.escape(func)}\s*\(", src):
        return True, ""
    return False, f"'{func}' not found in {node_file(nodeid)} (renamed or removed?)"


def find_venv_bin(info, cwd):
    exe = info.get("python")
    if exe and Path(exe).is_file():
        return str(Path(exe).parent)
    for name in (info.get("venv"), ".venv", "venv", "env"):
        if not name:
            continue
        for sub in ("Scripts", "bin"):
            cand = Path(cwd) / name / sub
            if (cand / "pytest").exists() or (cand / "pytest.exe").exists():
                return str(cand)
    return None


def default_shell():
    return "powershell" if platform.system() == "Windows" else "bash"


SAFE_ARG = re.compile(r"^[\w./:\\=+,-]+$")


def quote(arg, shell):
    if SAFE_ARG.match(arg) and not (
        shell == "powershell"
        and arg.startswith(("@", "-", "$"))
        and not arg.startswith("-")
    ):
        return arg
    if shell == "powershell":
        return "'" + arg.replace("'", "''") + "'"
    if shell == "cmd":
        return '"' + arg.replace('"', '""') + '"'
    return shlex.quote(arg)


def build_command(nodeids, workers, reruns, flags, shell):
    args = ["pytest"]
    n = min(workers, len(nodeids))
    if n > 1:
        args += ["-n", str(n)]
    if reruns:
        args += ["--reruns", str(reruns)]
    args += flags
    args += nodeids
    return " ".join(quote(a, shell) for a in args)


def resolve_cwd(a, info, log, warnings):
    cwd = a.cwd or info.get("cwd") or info.get("rootdir")
    if not cwd:
        sys.exit(
            "Could not find the launch directory in the log (no shell prompt, no 'rootdir:' line). Pass --cwd."
        )
    if not Path(cwd).is_dir():
        # The log may come from another machine; if it was saved inside the project, use that.
        first = node_file(info["failed"][0]["nodeid"]) if info["failed"] else None
        candidates = [log.parent, *log.parent.parents][:4]
        found = next((d for d in candidates if first and (d / first).is_file()), None)
        if found and not a.cwd:
            warnings.append(
                f"Launch directory from the log ({cwd}) does not exist here; using {found}, which contains the failed tests."
            )
            cwd = str(found)
            info["python"] = None
        else:
            warnings.append(
                f"Launch directory from the log does not exist on this machine: {cwd}. Pass --cwd."
            )
    return cwd


def cmd_plan(a):
    log = Path(a.log).resolve()
    info = parse_log(read_text(log))
    shell = a.shell or default_shell()
    warnings = []
    cwd = resolve_cwd(a, info, log, warnings)
    rootdir = info.get("rootdir")
    rel_prefix = ""
    if rootdir and Path(rootdir).is_dir() and Path(cwd).is_dir():
        try:
            rel = Path(cwd).resolve().relative_to(Path(rootdir).resolve())
            rel_prefix = "" if str(rel) == "." else rel.as_posix().rstrip("/") + "/"
        except ValueError:
            pass

    cfg_path = find_qa_config(cwd) if Path(cwd).is_dir() else None
    config = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path else {}
    ui_globs, api_globs = ui_levels(config)
    settings = {}
    for kind, cap in (("api", "api"), ("ui", "web")):
        prof = profile_settings(config, cap) if config else None
        s = {
            "workers": DEFAULTS[f"{kind}_workers"],
            "reruns": DEFAULTS["reruns"],
            "flags": [],
            "source": "skill defaults",
        }
        if prof:
            s.update({k: v for k, v in prof.items() if v is not None})
        cli_workers = getattr(a, f"{kind}_workers")
        if cli_workers is not None:
            s["workers"], s["source"] = cli_workers, s["source"] + " + user override"
        if a.reruns is not None:
            s["reruns"] = a.reruns
        settings[kind] = s
    if not any("headless" in f for f in settings["ui"]["flags"]):
        flag = detect_headless_flag(cwd) if Path(cwd).is_dir() else None
        if flag:
            settings["ui"]["flags"].append(flag)
        elif "playwright" in (info.get("plugins") or []):
            warnings.append(
                "pytest-playwright runs headless by default; no extra headless flag added."
            )
        else:
            warnings.append(
                "No headless option found for UI tests; check the project's conftest/pytest config."
            )

    carried = carried_options(info.get("command"), info.get("shell") or shell)
    plugins = info.get("plugins") or []
    if plugins and "rerunfailures" not in plugins:
        warnings.append(
            "pytest-rerunfailures is not in the log's plugin list; --reruns may be rejected."
        )
    if plugins and "xdist" not in plugins:
        warnings.append(
            "pytest-xdist is not in the log's plugin list; -n may be rejected."
        )

    batches = {"api": [], "ui": []}
    missing = []
    for f in info["failed"]:
        node = f["nodeid"]
        local = (
            node[len(rel_prefix) :]
            if rel_prefix and node.startswith(rel_prefix)
            else node
        )
        if Path(cwd).is_dir():
            ok, why = node_exists(local, cwd)
            if not ok:
                missing.append({"nodeid": node, "reason": why})
                continue
        batches[classify_kind(local, cwd, ui_globs, api_globs)].append(local)

    out_dir = (
        Path(a.out_dir)
        if a.out_dir
        else Path(tempfile.gettempdir())
        / "rerun-failed-tests"
        / _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    plan = {
        "log": str(log),
        "cwd": str(cwd),
        "rootdir": rootdir,
        "shell": shell,
        "log_shell": info.get("shell"),
        "venv_bin": find_venv_bin(info, cwd),
        "original_command": info.get("command"),
        "original_totals": info.get("totals_line"),
        "qa_factory_config": str(cfg_path) if cfg_path else None,
        "carried_flags": carried,
        "settings": settings,
        "not_found": missing,
        "warnings": warnings,
        "out_dir": str(out_dir),
        "batches": [],
        "original_failures": {
            f["nodeid"]: (f["reason"] or info["crash_reasons"].get(f["nodeid"], ""))
            for f in info["failed"]
        },
    }
    for kind in ("api", "ui"):
        ids = batches[kind]
        if not ids:
            continue
        s = settings[kind]
        flags = carried + [f for f in s["flags"] if f not in carried]
        plan["batches"].append(
            {
                "kind": kind,
                "nodeids": ids,
                "workers": min(s["workers"], len(ids)),
                "reruns": s["reruns"],
                "flags": flags,
                "junit": str(out_dir / f"{kind}.xml"),
                "console": str(out_dir / f"{kind}.log"),
                "command": build_command(ids, s["workers"], s["reruns"], flags, shell),
            }
        )
    (out_dir / "plan.json").write_text(
        json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(
        json.dumps(
            {k: plan[k] for k in plan if k != "original_failures"}
            | {"plan": str(out_dir / "plan.json")},
            indent=2,
            ensure_ascii=False,
        )
    )


# --------------------------------------------------------------------------- running


def cmd_run(a):
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))
    env = os.environ.copy()
    if plan.get("venv_bin"):
        env["PATH"] = plan["venv_bin"] + os.pathsep + env.get("PATH", "")
        env["VIRTUAL_ENV"] = str(Path(plan["venv_bin"]).parent)
    pytest_exe = shutil.which("pytest", path=env["PATH"])
    if not pytest_exe:
        sys.exit(
            "pytest not found on PATH (and no venv detected). Activate the project's environment first."
        )
    codes = {}
    for b in plan["batches"]:
        args = [pytest_exe]
        if b["workers"] > 1:
            args += ["-n", str(b["workers"])]
        if b["reruns"]:
            args += ["--reruns", str(b["reruns"])]
        args += b["flags"] + ["-v", "-rfE", f"--junitxml={b['junit']}"]
        ids = b["nodeids"]
        if (
            sum(len(x) + 1 for x in ids) > 7000
        ):  # Windows command-line limit: pass node ids through an args file
            argfile = Path(plan["out_dir"]) / f"{b['kind']}.args"
            argfile.write_text("\n".join(ids), encoding="utf-8")
            args.append("@" + str(argfile))
        else:
            args += ids
        print(f"[{b['kind']}] {len(ids)} test(s): {b['command']}", flush=True)
        with open(b["console"], "w", encoding="utf-8", errors="replace") as out:
            proc = subprocess.run(
                args, cwd=plan["cwd"], env=env, stdout=out, stderr=subprocess.STDOUT
            )
        codes[b["kind"]] = proc.returncode
        print(
            f"[{b['kind']}] exit code {proc.returncode}; console: {b['console']}",
            flush=True,
        )
    print(json.dumps({"exit_codes": codes}))


# --------------------------------------------------------------------------- grouping


def normalize(text):
    t = UUID_RE.sub("{id}", text)
    t = ADDR_RE.sub("{addr}", t)
    t = RANDOM_SUFFIX_RE.sub("-{id}", t)
    t = HEX_ID_RE.sub("{id}", t)
    t = WORKER_RE.sub("gw{N}", t)
    t = NUM_RE.sub("{N}", t)
    return re.sub(r"\s+", " ", t).strip()


ID_SEGMENT = re.compile(
    r"^(\d+|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}|(?=[0-9a-fA-F]*\d)[0-9a-fA-F]{8,}|[A-Za-z0-9_-]{20,})$"
)


def normalize_path(path):
    segs = []
    for seg in path.split("/"):
        if ID_SEGMENT.match(seg) and not re.match(r"^v\d+$", seg):
            segs.append("{id}")
        else:
            segs.append(RANDOM_SUFFIX_RE.sub("-{id}", seg))
    return "/".join(segs)


def split_url(url):
    m = re.match(r"^(?:https?://)?([^/\s?]*)(/[^?\s#]*)?", url.strip().rstrip(").,'\""))
    host, path = (m.group(1), m.group(2) or "/") if m else ("", url)
    return host, normalize_path(path)


METHOD_RES = [
    re.compile(r"Error during (GET|POST|PUT|PATCH|DELETE|HEAD) request to"),
    re.compile(r"<PreparedRequest \[(GET|POST|PUT|PATCH|DELETE|HEAD)\]>"),
    re.compile(r"\bmethod\s*=\s*['\"](GET|POST|PUT|PATCH|DELETE|HEAD)['\"]"),
    re.compile(
        r"\b(GET|POST|PUT|PATCH|DELETE|HEAD) (?:https?://\S+|/\S+).{0,40}\b\d{3}\b"
    ),
]


def find_method(text, path_fragment):
    for rx in METHOD_RES:
        for m in rx.finditer(text or ""):
            window = text[m.start() : m.start() + 400]
            if (
                not path_fragment
                or path_fragment.split("{id}")[0][-20:] in window
                or rx is METHOD_RES[1]
            ):
                return m.group(1)
    return None


def usable_message(message):
    """The failure message, or '' when it is a width-truncated summary reason like 'demo_app...'."""
    msg = (message or "").strip()
    return "" if msg.endswith("...") and len(msg) < 120 else msg


def error_lines(text):
    """Only the 'E   ...' lines of a traceback: the raised error, not the quoted source code."""
    return "\n".join(
        ln[1:].strip() for ln in (text or "").split("\n") if ln.startswith("E ")
    )


def first_exception_line(message, text):
    """The junit/summary message, else the first 'E   Something: message' line of the traceback."""
    msg = usable_message(message)
    e_lines = error_lines(text).split("\n")
    return msg or e_lines[0]


def signature(message, text):
    """Return (group_key, title, detail) for one failure.

    Patterns are matched against the error itself (message + 'E' lines). The full traceback also
    quotes source code such as `raise HTTPError(f"... for url: {HOST}{path}")`, which would
    otherwise be picked up as the failing URL.
    """
    raw = (message or "").strip()
    elines = error_lines(text)
    msg = (usable_message(raw) + "\n" + elines).strip()
    body = elines or (text or "")
    blob = raw + "\n" + (text or "")

    m = re.search(r"worker '(gw\d+)' crashed", blob) or re.search(
        r"node down: Not properly terminated", blob
    )
    if m:
        return (
            ("worker-crash",),
            "xdist worker crashed (process died, no Python traceback)",
            "Usually the process was killed: memory, a native crash or a hard timeout. The tests themselves may be fine.",
        )

    m = re.search(r"Failed: Timeout[^\n]*", msg) or re.search(
        r"^E\s+Failed: Timeout[^\n]*", body, re.M
    )
    if m:
        return (
            ("pytest-timeout",),
            "pytest-timeout: test exceeded its time limit",
            normalize(m.group(0)),
        )

    http = (
        re.search(r"\b(\d{3}) (?:Client|Server) Error: ([^\n]*?) for url: (\S+)", msg)
        or re.search(
            r"(?:Client|Server) error '(\d{3}) ([^']*)' for url '([^']+)'", msg
        )
        or re.search(
            r"\b(\d{3}) (?:Client|Server) Error: ([^\n]*?) for url: (\S+)", body
        )
    )
    if http:
        code, reason, url = http.group(1), http.group(2).strip(), http.group(3)
        host, path = split_url(url)
        method = find_method(blob, path)
        verb = f"{method} " if method else ""
        return (
            ("http", code, path),
            f"HTTP {code} {reason} — {verb}{path}",
            f"host: {host}" if host else "",
        )

    status = re.search(r"status(?:_code| code)?[\"']?\s*[=:]\s*(\d{3})\b", msg, re.I)
    if status and re.search(r"(https?://\S+|/v\d+/\S*)", msg):
        url = re.search(r"(https?://\S+|/v\d+/\S*)", msg).group(1)
        host, path = split_url(url)
        return ("http", status.group(1), path), f"HTTP {status.group(1)} — {path}", ""

    if re.search(
        r"NameResolutionError|getaddrinfo failed|Failed to resolve|Name or service not known|nodename nor servname",
        msg,
    ):
        host = re.search(r"Failed to resolve '([^']+)'|host='([^']+)'", msg)
        h = (host.group(1) or host.group(2)) if host else "?"
        return (
            ("dns", h),
            f"DNS resolution failed for {h} (stand unreachable / VPN)",
            "Host-level failure: every endpoint on this host is affected, so the endpoint is not part of the group.",
        )

    if re.search(
        r"Connection refused|ConnectionRefusedError|actively refused|ECONNREFUSED", msg
    ):
        host = re.search(r"host='([^']+)'", msg)
        h = host.group(1) if host else "?"
        return ("conn-refused", h), f"Connection refused by {h}", ""

    if re.search(
        r"(ReadTimeout|ConnectTimeout|Read timed out|ConnectTimeoutError)", msg
    ):
        url = re.search(r"url: (\S+)", msg)
        host, path = split_url(url.group(1)) if url else ("", "?")
        return (
            ("net-timeout", path),
            f"Network timeout — {path}",
            f"host: {host}" if host else "",
        )

    if re.search(
        r"ConnectionError|RemoteDisconnected|Connection aborted|ConnectionResetError",
        msg,
    ):
        url = re.search(r"url: (\S+)", msg)
        host, path = split_url(url.group(1)) if url else ("", "")
        return (
            ("conn-error", path),
            f"Connection error — {path or host or 'unknown endpoint'}",
            normalize(msg)[:200],
        )

    pw = re.search(
        r"(?:playwright\S*\.)?TimeoutError: (Locator|Page|Frame|ElementHandle)\.(\w+): Timeout \d+ms exceeded",
        msg,
    )
    if pw:
        loc = re.search(
            r"waiting for ((?:locator|get_by_\w+)\(.+?\)(?:\.\w+\(.*?\))*)\s*$",
            msg,
            re.M,
        )
        target = normalize(loc.group(1)) if loc else "?"
        return (
            ("pw-timeout", pw.group(1), pw.group(2), target),
            f"Playwright timeout: {pw.group(1)}.{pw.group(2)} on {target}",
            "",
        )
    pwa = re.search(r"(Locator|Page) expected to ([^\n]+)", msg)
    if pwa:
        loc = re.search(r"waiting for ((?:locator|get_by_\w+)\(.+?\))", msg)
        target = normalize(loc.group(1)) if loc else "?"
        return (
            ("pw-expect", pwa.group(2).strip(), target),
            f"Playwright expect failed: {pwa.group(1)} expected to {pwa.group(2).strip()} — {target}",
            "",
        )

    line = first_exception_line(msg, body)
    exc = re.match(
        r"^([\w.]+(?:Error|Exception|Failed|Exit|Interrupt|Warning)|Failed|AssertionError)\b:?\s*(.*)$",
        line,
        re.S,
    )
    if exc:
        etype, rest = exc.group(1), exc.group(2).strip()
    else:
        etype, rest = (
            ("AssertionError", line) if line.startswith("assert ") else ("Error", line)
        )
    # Skip bare "AssertionError:" echoes (message + E-lines repeat the type when the reason is empty).
    lines = [
        ln.strip()
        for ln in rest.split("\n")
        if ln.strip() and not re.fullmatch(r"[\w.]*(?:Error|Exception):?", ln.strip())
    ]
    first = lines[0] if lines else ""
    if not first or first.startswith(
        "Expected:"
    ):  # hamcrest-style message with empty reason: use the Expected line
        exp = re.search(r"Expected:\s*(.+)", msg) or re.search(
            r"Expected:\s*(.+)", body
        )
        first = exp.group(1).strip() if exp else ""
    if not first and not elines and not usable_message(raw):
        return (
            ("no-details",),
            "No error details in the log (no traceback, summary reason truncated)",
            "Rerun these to get the actual error.",
        )
    norm = normalize(first)[:240]
    short = etype.split(".")[-1]
    return ("exc", short, norm), f"{short}: {norm or '(no message)'}", ""


def testcase_key(nodeid):
    parts = nodeid.split("::")
    module = re.sub(r"\.py$", "", parts[0].replace("\\", "/")).replace("/", ".")
    return ".".join([module] + parts[1:-1]), parts[-1]


def read_junit(path):
    results = {}
    if not Path(path).is_file():
        return None
    root = ET.parse(path).getroot()
    for tc in root.iter("testcase"):
        key = (tc.get("classname", ""), tc.get("name", ""))
        fail = tc.find("failure")
        err = tc.find("error")
        skip = tc.find("skipped")
        node = fail if fail is not None else err
        if node is not None:
            results[key] = {
                "status": "failed" if fail is not None else "error",
                "message": node.get("message", ""),
                "text": node.text or "",
            }
        elif skip is not None:
            results[key] = {
                "status": "skipped",
                "message": skip.get("message", ""),
                "text": "",
            }
        else:
            prev = results.get(key)
            if not prev or prev["status"] == "passed":
                results[key] = {"status": "passed", "message": "", "text": ""}
    return results


def count_reruns(console_path):
    counts = {}
    try:
        text = read_text(console_path)
    except OSError:
        return counts
    for m in re.finditer(r"RERUN ((?:[^\s\[]+::[^\s\[]+)(?:\[.*?\])?)", text):
        counts[m.group(1)] = counts.get(m.group(1), 0) + 1
    return counts


def junit_lookup(results, nodeid):
    cls, name = testcase_key(nodeid)
    if (cls, name) in results:
        return results[(cls, name)]
    for (c, n), r in results.items():  # rootdir-relative vs cwd-relative prefixes
        if n == name and (c.endswith("." + cls) or cls.endswith("." + c) or c == cls):
            return r
    return None


def group_failures(failures, shell, settings, carried):
    groups = {}
    for f in failures:
        key, title, detail = signature(f.get("message"), f.get("text"))
        g = groups.setdefault(
            key, {"title": title, "detail": detail, "tests": [], "samples": []}
        )
        g["tests"].append(f)
        sample = first_exception_line(f.get("message"), f.get("text"))
        if sample and len(g["samples"]) < 1:
            g["samples"].append(sample.split("\n")[0][:400])
    ordered = sorted(groups.values(), key=lambda g: (-len(g["tests"]), g["title"]))
    for g in ordered:
        g["commands"] = []
        for kind in ("api", "ui"):
            ids = [t["nodeid"] for t in g["tests"] if t.get("kind", "api") == kind]
            if ids:
                s = settings[kind]
                flags = carried + [x for x in s["flags"] if x not in carried]
                g["commands"].append(
                    {
                        "kind": kind,
                        "command": build_command(
                            ids, s["workers"], s["reruns"], flags, shell
                        ),
                    }
                )
    return ordered


FENCE = {"powershell": "powershell", "bash": "bash", "cmd": "bat"}


def render(report):
    shell = report["shell"]
    fence = FENCE.get(shell, "")
    out = ["# Rerun of failed tests", ""]
    out.append(f"- **Log:** `{report['log']}`")
    out.append(f"- **Run from:** `{report['cwd']}` ({shell})")
    if report.get("original_command"):
        out.append(f"- **Original command:** `{report['original_command']}`")
    if report.get("original_totals"):
        out.append(f"- **Original result:** {report['original_totals']}")
    s = report["settings"]
    out.append(
        f"- **Settings:** api `-n {s['api']['workers']}`, ui `-n {s['ui']['workers']}`, `--reruns {s['api']['reruns']}`"
        + (f", ui flags `{' '.join(s['ui']['flags'])}`" if s["ui"]["flags"] else "")
        + f" — from {s['api']['source']}"
    )
    t = report["totals"]
    out.append(
        f"- **Rerun result:** {t['rerun']} rerun → ✅ {t['passed']} passed, ❌ {t['failed']} failed"
        + (f", ⏭ {t['skipped']} skipped" if t["skipped"] else "")
        + (f", ⚠ {t['not_run']} not run" if t["not_run"] else "")
    )
    out.append("")
    for w in report.get("warnings", []):
        out.append(f"> ⚠ {w}")
    if report.get("warnings"):
        out.append("")

    out.append(f"## ✅ Passed on rerun ({len(report['passed'])})")
    out.append("")
    for p in report["passed"] or []:
        flaky = (
            f" — flaky, passed after {p['reruns']} rerun(s)" if p.get("reruns") else ""
        )
        out.append(f"- `{p['nodeid']}`{flaky}")
    if not report["passed"]:
        out.append("_none_")
    out.append("")

    out.append(
        f"## ❌ Still failing ({report['totals']['failed']}) — {len(report['groups'])} group(s)"
    )
    out.append("")
    for i, g in enumerate(report["groups"], 1):
        out.append(f"### Group {i}: {g['title']} ({len(g['tests'])} test(s))")
        out.append("")
        if g.get("detail"):
            out.append(f"_{g['detail']}_")
            out.append("")
        if g["samples"]:
            out.append(f"Sample error: `{g['samples'][0].replace('`', chr(39))}`")
            out.append("")
        for tst in g["tests"]:
            tag = " (ui)" if tst.get("kind") == "ui" else ""
            out.append(f"- `{tst['nodeid']}`{tag}")
        out.append("")
        for c in g["commands"]:
            if len(g["commands"]) > 1:
                out.append(f"{c['kind'].upper()} tests:")
            out.append(f"```{fence}\n{c['command']}\n```")
        out.append("")
    if not report["groups"]:
        out.append("_none — everything passed_ 🎉")
        out.append("")

    if report.get("all_failed_commands"):
        out.append("## Rerun everything that still fails")
        out.append("")
        for c in report["all_failed_commands"]:
            out.append(f"```{fence}\n{c['command']}\n```")
        out.append("")
    if report.get("not_run"):
        out.append(f"## ⚠ Not rerun ({len(report['not_run'])})")
        out.append("")
        for n in report["not_run"]:
            out.append(f"- `{n['nodeid']}` — {n['reason']}")
        out.append("")
    return "\n".join(out)


def all_failed_commands(failed, settings, carried, shell):
    cmds = []
    for kind in ("api", "ui"):
        ids = [f["nodeid"] for f in failed if f.get("kind") == kind]
        if ids:
            s = settings[kind]
            flags = carried + [x for x in s["flags"] if x not in carried]
            cmds.append(
                {
                    "kind": kind,
                    "command": build_command(
                        ids, s["workers"], s["reruns"], flags, shell
                    ),
                }
            )
    return cmds


def cmd_report(a):
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))
    shell = a.shell or plan["shell"]
    passed, failed, skipped, not_run = [], [], [], list(plan.get("not_found", []))
    for b in plan["batches"]:
        results = read_junit(b["junit"])
        reruns = count_reruns(b["console"])
        if results is None:
            for n in b["nodeids"]:
                not_run.append(
                    {
                        "nodeid": n,
                        "reason": f"no junit report — the {b['kind']} batch did not finish; see {b['console']}",
                    }
                )
            continue
        for n in b["nodeids"]:
            r = junit_lookup(results, n)
            entry = {"nodeid": n, "kind": b["kind"], "reruns": reruns.get(n, 0)}
            if r is None:
                not_run.append(
                    {
                        "nodeid": n,
                        "reason": f"not in junit report (not collected or deselected); see {b['console']}",
                    }
                )
            elif r["status"] == "passed":
                passed.append(entry)
            elif r["status"] == "skipped":
                skipped.append(entry | {"message": r["message"]})
            else:
                failed.append(
                    entry
                    | {
                        "message": r["message"],
                        "text": r["text"],
                        "status": r["status"],
                    }
                )
    carried = plan.get("carried_flags", [])
    groups = group_failures(failed, shell, plan["settings"], carried)
    report = {
        "log": plan["log"],
        "cwd": plan["cwd"],
        "shell": shell,
        "original_command": plan.get("original_command"),
        "original_totals": plan.get("original_totals"),
        "settings": plan["settings"],
        "warnings": plan.get("warnings", []),
        "totals": {
            "rerun": sum(len(b["nodeids"]) for b in plan["batches"]),
            "passed": len(passed),
            "failed": len(failed),
            "skipped": len(skipped),
            "not_run": len(not_run),
        },
        "passed": passed,
        "skipped": skipped,
        "not_run": not_run,
        "groups": [
            {k: v for k, v in g.items()}
            | {
                "tests": [
                    {"nodeid": t["nodeid"], "kind": t["kind"], "status": t["status"]}
                    for t in g["tests"]
                ]
            }
            for g in groups
        ],
        "all_failed_commands": all_failed_commands(
            failed, plan["settings"], carried, shell
        )
        if len(groups) > 1
        else [],
    }
    md = render(report)
    out_dir = Path(plan["out_dir"])
    (out_dir / "report.md").write_text(md, encoding="utf-8")
    (out_dir / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(md)
    print(f"\n<!-- report: {out_dir / 'report.md'} -->")


def cmd_group(a):
    """Group the failures of the original log (no rerun) using its FAILURES sections."""
    log = Path(a.log).resolve()
    info = parse_log(read_text(log))
    shell = a.shell or default_shell()
    warnings = []
    cwd = resolve_cwd(a, info, log, warnings)
    cfg = find_qa_config(cwd) if Path(cwd).is_dir() else None
    config = json.loads(cfg.read_text(encoding="utf-8")) if cfg else {}
    ui_globs, api_globs = ui_levels(config)
    settings = {}
    for kind, cap in (("api", "api"), ("ui", "web")):
        s = {
            "workers": DEFAULTS[f"{kind}_workers"],
            "reruns": DEFAULTS["reruns"],
            "flags": [],
            "source": "skill defaults",
        }
        prof = profile_settings(config, cap) if config else None
        if prof:
            s.update(prof)
        settings[kind] = s
    failures, missing = [], []
    for f in info["failed"]:
        if Path(cwd).is_dir():
            ok, why = node_exists(f["nodeid"], cwd)
            if not ok:  # a stale node id in a command makes pytest abort the whole run
                missing.append({"nodeid": f["nodeid"], "reason": why})
                continue
        func = f["nodeid"].split("::")[-1]
        text = info["sections"].get(func) or info["sections"].get(
            func.split("[")[0], ""
        )
        if f["nodeid"] in info["crash_reasons"]:
            text = info["crash_reasons"][f["nodeid"]] + "\n" + text
        failures.append(
            {
                "nodeid": f["nodeid"],
                "kind": classify_kind(f["nodeid"], cwd, ui_globs, api_globs),
                "message": f["reason"],
                "text": text,
                "status": f["status"],
            }
        )
    carried = carried_options(info.get("command"), info.get("shell") or shell)
    groups = group_failures(failures, shell, settings, carried)
    print(
        json.dumps(
            {
                "cwd": cwd,
                "shell": shell,
                "original_command": info.get("command"),
                "original_totals": info.get("totals_line"),
                "settings": settings,
                "carried_flags": carried,
                "warnings": warnings,
                "groups": [
                    {
                        "title": g["title"],
                        "detail": g["detail"],
                        "sample": (g["samples"] or [""])[0],
                        "count": len(g["tests"]),
                        "tests": [t["nodeid"] for t in g["tests"]],
                        "commands": g["commands"],
                    }
                    for g in groups
                ],
                "all_failed_commands": all_failed_commands(
                    failures, settings, carried, shell
                )
                if len(groups) > 1
                else [],
                "not_found": missing,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    pl = sub.add_parser("plan")
    pl.add_argument("--log", required=True)
    pl.add_argument("--shell", choices=["powershell", "bash", "cmd"])
    pl.add_argument("--cwd")
    pl.add_argument("--api-workers", type=int)
    pl.add_argument("--ui-workers", type=int)
    pl.add_argument("--reruns", type=int)
    pl.add_argument("--out-dir")
    r = sub.add_parser("run")
    r.add_argument("--plan", required=True)
    rp = sub.add_parser("report")
    rp.add_argument("--plan", required=True)
    rp.add_argument("--shell", choices=["powershell", "bash", "cmd"])
    g = sub.add_parser("group")
    g.add_argument("--log", required=True)
    g.add_argument("--shell", choices=["powershell", "bash", "cmd"])
    g.add_argument("--cwd")
    a = p.parse_args()
    {"plan": cmd_plan, "run": cmd_run, "report": cmd_report, "group": cmd_group}[a.cmd](
        a
    )


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
