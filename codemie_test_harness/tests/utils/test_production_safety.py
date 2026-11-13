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

import pytest
import requests

from codemie_test_harness.tests.utils import production_safety


class FakeItem:
    def __init__(self, *markers: str):
        self._markers = set(markers)

    def get_closest_marker(self, name: str):
        return object() if name in self._markers else None

    def iter_markers(self, name: str | None = None):
        markers = self._markers if name is None else {name} & self._markers
        return [object() for _ in markers]


def _settings(monkeypatch, values: dict[str, str] | None = None) -> None:
    monkeypatch.setattr(
        production_safety.CredentialsManager,
        "get_parameter",
        staticmethod(lambda name, default="": (values or {}).get(name, default)),
    )
    monkeypatch.setattr(production_safety, "_read_only_run", False)


def test_unrelated_run_does_not_install_transport_guard(monkeypatch):
    _settings(monkeypatch)

    items = [FakeItem("ui")]

    assert production_safety.transport_guard_required(items) is False
    assert production_safety.configure_run(items) is False


def test_read_only_env_requires_transport_guard_without_cli_analytics(monkeypatch):
    _settings(monkeypatch, {production_safety.READ_ONLY_RUN: "true"})

    items = [FakeItem("ui")]

    assert production_safety.transport_guard_required(items) is True
    assert production_safety.configure_run(items) is True


def test_empty_selection_is_not_vacuously_read_only(monkeypatch):
    _settings(monkeypatch)

    assert production_safety.transport_guard_required([]) is False
    assert production_safety.configure_run([]) is False


def test_skipped_only_selection_is_not_vacuously_read_only(monkeypatch):
    _settings(monkeypatch)

    items = [FakeItem("cli_analytics", "prod_regression", "skip")]

    assert production_safety.transport_guard_required(items) is True
    assert production_safety.configure_run(items) is False


def test_all_runnable_read_only_cli_analytics_tests_require_guard(monkeypatch):
    _settings(monkeypatch)

    items = [FakeItem("cli_analytics", "prod_regression")]

    assert production_safety.transport_guard_required(items) is True
    assert production_safety.configure_run(items) is True


def test_read_only_run_rejects_state_changing_http_request(monkeypatch):
    _settings(
        monkeypatch,
        {
            production_safety.READ_ONLY_RUN: "true",
            "CODEMIE_API_DOMAIN": "https://codemie.test/code-assistant-api",
            "FRONTEND_URL": "https://codemie.test",
        },
    )
    monkeypatch.setattr(production_safety, "_transport_guard_installed", False)
    monkeypatch.setattr(
        production_safety.requests.Session, "send", production_safety._original_send
    )
    production_safety.configure_run([FakeItem("ui")])
    production_safety.install_transport_guard()
    request = requests.Request(
        "POST", "https://codemie.test/code-assistant-api/v1/projects"
    ).prepare()

    with pytest.raises(production_safety.ReadOnlyViolation):
        requests.Session().send(request)
