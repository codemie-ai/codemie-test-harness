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

"""Production safety for the CLI Analytics regression suite.

Three rules, all failing closed:

- State-changing CLI Analytics tests (projects, users, ingested telemetry that cannot be
  deleted) run only on a stand known not to be Production or Preview. An unrecognised
  host counts as Production unless CLI_ANALYTICS_ALLOW_STATE_CHANGES=true says otherwise.
- Tests that seed synthetic telemetry into the totals they assert additionally require
  CLI_ANALYTICS_DISPOSABLE_ENVIRONMENT=true: a host name is not proof of isolation.
- A read-only test (marked both cli_analytics and prod_regression) runs behind a transport guard
  that rejects every state-changing HTTP call to the CodeMie API or frontend, except sign-in.
  When every selected test is read-only, or HARNESS_READ_ONLY=true, the whole run is read-only:
  the guard covers session fixtures too and the session hooks create and delete nothing.
"""

from contextlib import contextmanager
from typing import Optional
from urllib.parse import urlsplit

import requests

from codemie_test_harness.tests.enums.environment import Environment
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
# Signing in is a POST that changes nothing the suite asserts on.
SIGN_IN_PATH_SUFFIXES = ("/v1/local-auth/login", "/protocol/openid-connect/token")

READ_ONLY_RUN = "HARNESS_READ_ONLY"
ALLOW_STATE_CHANGES = "CLI_ANALYTICS_ALLOW_STATE_CHANGES"
DISPOSABLE_ENVIRONMENT = "CLI_ANALYTICS_DISPOSABLE_ENVIRONMENT"

_read_only_run = False
_guarded_tests = 0
_original_send = requests.Session.send
_transport_guard_installed = False


class ReadOnlyViolation(RuntimeError):
    """A read-only test tried to change state on the CodeMie stand."""


def _setting_enabled(name: str) -> bool:
    return (
        str(CredentialsManager.get_parameter(name, "false")).strip().lower() == "true"
    )


def is_read_only_item(item) -> bool:
    return bool(
        item.get_closest_marker("cli_analytics")
        and item.get_closest_marker("prod_regression")
    )


def state_change_refusal() -> Optional[str]:
    """Why state-changing CLI Analytics tests may not run on this stand; None when they may."""
    if _read_only_run or _setting_enabled(READ_ONLY_RUN):
        return "the run is read-only"
    try:
        environment = EnvironmentResolver.get_environment()
    except ValueError as error:
        return str(error)
    if environment.is_production:
        return "the stand is Production"
    if environment.is_preview:
        return "the stand is Preview"
    if environment is Environment.UNKNOWN and not _setting_enabled(ALLOW_STATE_CHANGES):
        return (
            "the stand is not recognised as a test stand; set "
            f"{ALLOW_STATE_CHANGES}=true if it is not Production or Preview"
        )
    return None


def disposable_environment_declared() -> bool:
    """True when the stand is declared isolated: its analytics totals may change."""
    return _setting_enabled(DISPOSABLE_ENVIRONMENT)


def configure_run(items) -> bool:
    """Make the run read-only when asked, or when every runnable item is read-only."""
    global _read_only_run
    selected = list(items)
    runnable = [item for item in selected if not any(item.iter_markers(name="skip"))]
    _read_only_run = _setting_enabled(READ_ONLY_RUN) or (
        bool(runnable) and all(is_read_only_item(item) for item in runnable)
    )
    return _read_only_run


def is_read_only_run() -> bool:
    return _read_only_run


def transport_guard_required(items) -> bool:
    """True when the requests transport guard must be installed for this selection."""
    return _setting_enabled(READ_ONLY_RUN) or any(
        item.get_closest_marker("cli_analytics") for item in items
    )


def _guarded_origins() -> set[str]:
    origins = set()
    for name in ("CODEMIE_API_DOMAIN", "FRONTEND_URL"):
        value = CredentialsManager.get_parameter(name, "")
        if value:
            parts = urlsplit(value)
            origins.add(f"{parts.scheme}://{parts.netloc}".lower())
    return origins


def is_forbidden(method: str, url: str) -> bool:
    """True for a state-changing call to the CodeMie stand other than signing in."""
    if method.upper() in SAFE_METHODS:
        return False
    parts = urlsplit(url)
    if f"{parts.scheme}://{parts.netloc}".lower() not in _guarded_origins():
        return False
    return not parts.path.rstrip("/").endswith(SIGN_IN_PATH_SUFFIXES)


def _guarded_send(session, request, **kwargs):
    if (_read_only_run or _guarded_tests) and is_forbidden(request.method, request.url):
        raise ReadOnlyViolation(
            f"read-only run refused {request.method} {urlsplit(request.url).path}"
        )
    return _original_send(session, request, **kwargs)


def install_transport_guard() -> None:
    """Install the requests guard once, only for runs that collect CLI Analytics tests."""
    global _transport_guard_installed
    if not _transport_guard_installed:
        requests.Session.send = _guarded_send
        _transport_guard_installed = True


@contextmanager
def read_only_test(item):
    """Guard a read-only test in a run that is not read-only; a no-op for any other test.

    Wraps setup and call, so the session fixtures a read-only test is the first to request are
    guarded too. Teardown of a mixed run is not wrapped: it also finalises fixtures of the
    state-changing tests that ran before.
    """
    global _guarded_tests
    if not is_read_only_item(item):
        yield
        return
    _guarded_tests += 1
    try:
        yield
    finally:
        _guarded_tests -= 1


def is_guarded(item) -> bool:
    return _read_only_run or is_read_only_item(item)


def guard_browser(page) -> list[str]:
    """Abort the page's state-changing calls to the stand; returns what was blocked."""
    blocked: list[str] = []

    def _route(route):
        request = route.request
        if is_forbidden(request.method, request.url):
            blocked.append(f"{request.method} {urlsplit(request.url).path}")
            route.abort("blockedbyclient")
        else:
            route.fallback()

    page.route("**/*", _route)
    return blocked
