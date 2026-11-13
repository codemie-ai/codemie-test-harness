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

from codemie_test_harness.tests.ui.analytics.test_cli_analytics_api_consistency import (
    _cost,
    _currency,
)
from codemie_test_harness.tests.ui.pageobject.analytics.cli_analytics_page import (
    CLIAnalyticsPage,
)


class FakeRequest:
    def __init__(self, method: str):
        self.method = method


class FakeResponse:
    def __init__(self, url: str, method: str = "GET"):
        self.url = url
        self.request = FakeRequest(method)


def _page() -> CLIAnalyticsPage:
    return object.__new__(CLIAnalyticsPage)


def _api_domain(monkeypatch, value: str = "https://codemie.test/code-assistant-api"):
    monkeypatch.setattr(
        "codemie_test_harness.tests.ui.pageobject.analytics.cli_analytics_page."
        "CredentialsManager.get_parameter",
        staticmethod(lambda name, default="": value),
    )


def test_cost_matches_frontend_negative_and_negative_zero_formatting():
    assert _cost(-0.0) == "$0.00"
    assert _cost(-0.00001) == "$-0.0000"
    assert _cost(-0.001) == "$-0.0010"
    assert _cost(-0.5) == "$-0.50"
    assert _cost(-99.995) == "$-100.00"
    assert _cost(-101) == "$-101"


def test_cost_uses_absolute_magnitude_for_precision_thresholds():
    assert _cost(-0.009) == "$-0.0090"
    assert _cost(-0.01) == "$-0.01"
    assert _cost(-99.99) == "$-99.99"
    assert _cost(-100) == "$-100"
    assert _cost(0.009) == "$0.0090"
    assert _cost(0.01) == "$0.01"
    assert _cost(99.99) == "$99.99"
    assert _cost(100) == "$100"


def test_currency_matches_frontend_negative_and_negative_zero_formatting():
    assert _currency(-0.0) == "$-0.00"
    assert _currency(-0.001) == "$-0.00"
    assert _currency(-0.005) == "$-0.01"
    assert _currency(-0.5) == "$-0.50"
    assert _currency(-101) == "$-101.00"
    assert _currency(0.005) == "$0.01"


def test_framework_sessions_request_matches_without_default_page(monkeypatch):
    _api_domain(monkeypatch)
    response = FakeResponse(
        "https://codemie.test/code-assistant-api/v1/analytics/cli-analytics/"
        "sessions?framework=claude_code"
    )

    assert _page()._is_api_response(response, "sessions", {"framework": "claude_code"})


def test_framework_sessions_request_rejects_unrelated_endpoint(monkeypatch):
    _api_domain(monkeypatch)
    response = FakeResponse(
        "https://codemie.test/code-assistant-api/v1/analytics/cli-analytics/"
        "users?framework=claude_code"
    )

    assert not _page()._is_api_response(
        response, "sessions", {"framework": "claude_code"}
    )


def test_framework_sessions_request_accepts_optional_single_path_prefix(monkeypatch):
    _api_domain(monkeypatch, "https://codemie.test/gateway/code-assistant-api")
    response = FakeResponse(
        "https://codemie.test/gateway/code-assistant-api/v1/analytics/cli-analytics/"
        "sessions?framework=claude_code"
    )

    assert _page()._is_api_response(response, "sessions", {"framework": "claude_code"})


def test_framework_sessions_request_rejects_unrelated_prefix(monkeypatch):
    _api_domain(monkeypatch, "https://codemie.test/code-assistant-api")
    response = FakeResponse(
        "https://codemie.test/other/code-assistant-api/v1/analytics/cli-analytics/"
        "sessions?framework=claude_code"
    )

    assert not _page()._is_api_response(
        response, "sessions", {"framework": "claude_code"}
    )


def test_framework_sessions_request_rejects_path_with_endpoint_suffix_only(monkeypatch):
    _api_domain(monkeypatch, "")
    response = FakeResponse(
        "https://codemie.test/unrelated/v1/analytics/cli-analytics/"
        "sessions?framework=claude_code"
    )

    assert not _page()._is_api_response(
        response, "sessions", {"framework": "claude_code"}
    )


def test_framework_sessions_request_rejects_wrong_method(monkeypatch):
    _api_domain(monkeypatch)
    response = FakeResponse(
        "https://codemie.test/code-assistant-api/v1/analytics/cli-analytics/"
        "sessions?framework=claude_code",
        method="POST",
    )

    assert not _page()._is_api_response(
        response, "sessions", {"framework": "claude_code"}
    )


def test_framework_sessions_request_rejects_wrong_framework(monkeypatch):
    _api_domain(monkeypatch)
    response = FakeResponse(
        "https://codemie.test/code-assistant-api/v1/analytics/cli-analytics/"
        "sessions?framework=codex"
    )

    assert not _page()._is_api_response(
        response, "sessions", {"framework": "claude_code"}
    )
