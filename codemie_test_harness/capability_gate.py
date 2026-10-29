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

"""Pytest plugin that skips tests whose needs the installation lacks.

Tests declare needs with ``requires_capability("<name>")`` (a component of
``GET /v1/config``) and ``requires_setting("<KEY>", ...)`` (a harness setting).
Existing markers count as declarations too: ``datasource`` needs ``retrieval``,
and an integration marker such as ``servicenow`` needs that integration's
settings, so the tests of a configured integration run and the others skip.
In a *gated* run (every run that is not narrowed and has no ``--no-gate``) an unmet need
skips the test with ``missing capability 'name'`` / ``missing setting 'KEY'``.
Explicit runs (``-k``, a node id, a narrower path, ``--no-gate`` set by ``run --marks``) never skip.
With ``--strict-requirements`` or ``HARNESS_STRICT=1`` the skip becomes a failure.
"""

from __future__ import annotations

import os
import re
import threading
from collections import defaultdict
from pathlib import Path
from typing import Callable

import pytest

# capability name -> /v1/config component ids; any enabled id means available.
# A name that is not a key here is looked up as a component id itself.
CAPABILITIES: dict[str, tuple[str, ...]] = {
    "retrieval": (
        "features:knowledgeBases",
        "features:datasources",
        "features:codeIndexing",
    ),
}

# marker -> capability it needs.
MARKER_CAPABILITIES: dict[str, str] = {"datasource": "retrieval"}

# integration marker -> setting keys that mean "configured"; a test with the
# marker needs them, and `requires_setting("jira")` expands to them.
# Not listed: sonar and email (one test reads two providers' keys), elastic,
# sql, influx (keys depend on the environment).
INTEGRATION_SETTINGS: dict[str, tuple[str, ...]] = {
    "aws": ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"),
    "azure": ("AZURE_CLIENT_ID", "AZURE_TENANT_ID", "AZURE_SUBSCRIPTION_ID"),
    "gcp": ("GCP_SA_KEY_BASE64",),
    "jira": ("JIRA_URL", "JIRA_TOKEN"),
    "jira_cloud": ("JIRA_CLOUD_URL", "JIRA_CLOUD_TOKEN"),
    "confluence": ("CONFLUENCE_URL", "CONFLUENCE_TOKEN"),
    "confluence_cloud": ("CONFLUENCE_CLOUD_URL", "CONFLUENCE_CLOUD_TOKEN"),
    "gitlab": ("GITLAB_URL", "GITLAB_TOKEN"),
    "github": ("GITHUB_TOKEN",),
    "ado": ("AZURE_DEVOPS_URL", "AZURE_DEVOPS_TOKEN"),
    "servicenow": ("SERVICENOW_URL", "SERVICENOW_TOKEN"),
    "xwiki": ("XWIKI_URL",),
    "keycloak": ("KEYCLOAK_URL", "KEYCLOAK_CLIENT_SECRET"),
    "report_portal": ("REPORT_PORTAL_URL", "REPORT_PORTAL_API_KEY"),
    "kubernetes": ("KUBERNETES_URL", "KUBERNETES_TOKEN"),
    "telegram": ("TELEGRAM_TOKEN",),
}

# Seconds to wait for the start-up read of /v1/config before the run stops.
FETCH_TIMEOUT = 30

# Set by tests/conftest.py (or a test): returns {component id: enabled}.
FETCHER: Callable[[], dict[str, bool]] | None = None

_REASON = re.compile(r"missing (?:setting|capability) '[^']+'")
_SETTING_ERROR = re.compile(r"[Ss]etting '([^']+)'")


def pytest_addoption(parser):
    parser.addoption(
        "--no-gate",
        action="store_true",
        default=False,
        help="Do not skip tests whose declared setting or capability is missing.",
    )
    parser.addoption(
        "--strict-requirements",
        action="store_true",
        default=False,
        help="Fail instead of skip when a declared need is missing "
        "(or set HARNESS_STRICT=1).",
    )


def _roots(config) -> list[Path]:
    paths = config.getini("testpaths")
    if paths:
        return [(config.rootpath / p).resolve() for p in paths]
    return [(Path(__file__).parent / "tests").resolve()]


def is_gated_run(config) -> bool:
    """True unless --no-gate is given or the selection is narrowed."""
    if config.getoption("no_gate", default=False):
        return False
    if config.getoption("keyword", default=""):
        return False
    roots = _roots(config)
    for arg in config.args:
        if "::" in arg:
            return False
        path = Path(arg).resolve()
        # narrower: a file, or a directory strictly inside a test root
        if path.is_file() or any(r in path.parents for r in roots):
            return False
    return True


def _fetch_with_timeout() -> dict[str, bool]:
    # A daemon thread: the SDK login has no timeout, and a hung server must not hang the run.
    box: dict = {}

    def work():
        try:
            box["value"] = FETCHER()
        except Exception as e:
            box["error"] = e

    thread = threading.Thread(target=work, daemon=True)
    thread.start()
    thread.join(FETCH_TIMEOUT)
    if thread.is_alive():
        raise TimeoutError(f"no answer within {FETCH_TIMEOUT}s")
    if "error" in box:
        raise box["error"]
    return box["value"]


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "requires_capability(name): needs a /v1/config capability"
    )
    config.addinivalue_line(
        "markers", "requires_setting(KEY, ...): needs harness settings"
    )
    worker = getattr(config, "workerinput", None)
    if worker is not None:
        data = worker["capability_gate"]
        capabilities, gated = data["capabilities"], data["gated"]
    else:
        gated = is_gated_run(config)
        capabilities = {}
        if FETCHER is not None and not config.option.collectonly:
            try:
                capabilities = _fetch_with_timeout()
            except Exception as e:
                pytest.exit(f"Cannot read GET /v1/config: {e}", returncode=2)
    strict = config.getoption("strict_requirements", default=False) or (
        os.getenv("HARNESS_STRICT") == "1"
    )
    config.pluginmanager.register(
        CapabilityGate(capabilities, gated, strict), "capability-gate"
    )


class CapabilityGate:
    def __init__(
        self, capabilities: dict[str, bool], gated: bool, strict: bool = False
    ):
        self.capabilities = capabilities
        self.gated = gated
        self.strict = strict

    def pytest_configure_node(self, node):
        node.workerinput["capability_gate"] = {
            "capabilities": self.capabilities,
            "gated": self.gated,
        }

    def _unmet(self, item) -> str | None:
        markers = list(item.iter_markers())
        capabilities = [
            arg for m in markers if m.name == "requires_capability" for arg in m.args
        ] + [
            MARKER_CAPABILITIES[m.name]
            for m in markers
            if m.name in MARKER_CAPABILITIES
        ]
        for name in capabilities:
            ids = CAPABILITIES.get(name, (name,))
            if not any(self.capabilities.get(i) for i in ids):
                return f"missing capability '{name}'"
        from codemie_test_harness.tests.utils.credentials_manager import (
            CredentialsManager,
        )

        names = {m.name for m in markers}
        settings = [
            arg for m in markers if m.name == "requires_setting" for arg in m.args
        ] + [
            n
            for n in names
            if n in INTEGRATION_SETTINGS
            # A Cloud test carries the plain marker too, but its fixtures do not
            # use the Server settings: the Cloud marker alone decides.
            and f"{n}_cloud" not in names
        ]
        for arg in settings:
            for key in INTEGRATION_SETTINGS.get(arg, (arg,)):
                if not CredentialsManager.get_parameter(key, ""):
                    return f"missing setting '{key}'"
        return None

    @pytest.hookimpl(tryfirst=True)
    def pytest_runtest_setup(self, item):
        if not self.gated:
            return
        reason = self._unmet(item)
        if reason is None:
            return
        if self.strict:
            pytest.fail(reason, pytrace=False)
        pytest.skip(reason)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        outcome = yield
        if not self.gated or self.strict or call.excinfo is None:
            return
        if call.excinfo.type.__name__ != "MissingRequiredSettingError":
            return
        match = _SETTING_ERROR.search(str(call.excinfo.value))
        if not match:
            return
        report = outcome.get_result()
        report.outcome = "skipped"
        path, line = item.location[0], item.location[1] or 0
        report.longrepr = (path, line, f"Skipped: missing setting '{match.group(1)}'")

    def pytest_terminal_summary(self, terminalreporter):
        groups: dict[str, list[str]] = defaultdict(list)
        for report in terminalreporter.stats.get("skipped", []):
            longrepr = report.longrepr
            text = longrepr[2] if isinstance(longrepr, tuple) else str(longrepr)
            match = _REASON.search(text)
            if match:
                groups[match.group(0)].append(report.nodeid)
        if not groups:
            return
        terminalreporter.section("skipped by missing requirements")
        for reason, ids in sorted(groups.items()):
            terminalreporter.line(f"{reason}: {len(ids)} test(s): {', '.join(ids)}")
