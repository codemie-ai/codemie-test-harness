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

"""Pytest plugin that writes a compact JSON results file.

Enabled by ``--results-json PATH``. Works on the controller process only
(xdist workers are skipped) and keeps the final report per test, so a test
that fails and then passes on a rerun appears once, as ``passed``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_OUTCOMES = ("passed", "failed", "skipped", "error")


def pytest_addoption(parser):
    parser.addoption(
        "--results-json",
        action="store",
        default=None,
        metavar="PATH",
        help="Write a JSON summary of test outcomes to PATH.",
    )


def pytest_configure(config):
    path = config.getoption("--results-json", default=None)
    if path and not hasattr(config, "workerinput"):
        config.pluginmanager.register(_JsonResults(Path(path)), "json-results-writer")


class _JsonResults:
    def __init__(self, path: Path):
        self.path = path
        self.results: dict[str, dict] = {}

    def _entry(self, nodeid: str) -> dict:
        return self.results.setdefault(
            nodeid,
            {"nodeid": nodeid, "outcome": "error", "duration": 0.0, "reruns": 0},
        )

    def pytest_runtest_logreport(self, report):
        entry = self._entry(report.nodeid)
        # duration is the sum of every phase of every attempt, as in junit.xml
        # (pytest's junit_duration_report=total adds all reports of a test)
        if report.outcome == "rerun":
            entry["reruns"] += 1
            entry["duration"] += float(report.duration)
        elif report.when == "setup":
            # A new attempt starts: forget the outcome of the previous attempt.
            # Stay "error" until the call report arrives, so a test that is
            # interrupted mid-call is never left as passed.
            entry["duration"] += float(report.duration)
            entry["outcome"] = "skipped" if report.skipped else "error"
        elif report.when == "call":
            entry["outcome"] = report.outcome  # xfail is reported as skipped
            entry["duration"] += float(report.duration)
        elif report.when == "teardown":
            entry["duration"] += float(report.duration)
            # A failed call stays "failed" (junit.xml counts it as failure too)
            if report.failed and entry["outcome"] != "failed":
                entry["outcome"] = "error"
        elif report.failed:
            # Unknown phase (e.g. xdist worker crash): never leave it as passed
            entry["outcome"] = "error"

    def pytest_collectreport(self, report):
        if report.failed:
            self._entry(report.nodeid or "collection")["outcome"] = "error"
        elif report.skipped:
            # Module skipped at collection: junit.xml counts it, so do we
            self._entry(report.nodeid or "collection")["outcome"] = "skipped"

    # wrapper: write even when another sessionfinish hook (e.g. the cleanup in
    # tests/conftest.py) raises
    @pytest.hookimpl(wrapper=True)
    def pytest_sessionfinish(self, session, exitstatus):
        try:
            return (yield)
        finally:
            self._write(session, exitstatus)

    def _write(self, session, exitstatus):
        tests = list(self.results.values())
        # collected and exitstatus let a consumer tell a complete run from an
        # interrupted one (-x, Ctrl-C, crashed worker)
        summary = {
            "total": len(tests),
            "collected": session.testscollected,
            "exitstatus": int(exitstatus),
        }
        for outcome in _OUTCOMES:
            summary[outcome] = sum(1 for t in tests if t["outcome"] == outcome)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps({"summary": summary, "tests": tests}, indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            # Never change the pytest exit status because of the results file
            print(f"Warning: could not write {self.path}: {e}", file=sys.stderr)
