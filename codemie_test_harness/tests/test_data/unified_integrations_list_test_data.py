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

"""Test data for the unified Integrations list API tests (GET /v1/settings with a scope)."""

from dataclasses import dataclass
from typing import Any

from codemie_sdk.models.integration import CredentialValues

PLACEHOLDER_URL = "https://example.invalid"
PLACEHOLDER_TOKEN = "autotest-placeholder-token"

# Labels of the rows the filter scenarios create, in creation order.
ROW_JIRA = "jira"
ROW_GIT = "git"
ROW_GLOBAL = "global"
ROW_PROJECT = "proj"

# `{token}`, `{project}` and `{creator}` in a filter value are replaced by the test with the
# run's alias token, the administered project and the project admin's display name.
TOKEN = "{token}"
PROJECT = "{project}"
CREATOR = "{creator}"

# The scope names the API accepts, and one it must reject.
SCOPE_ALL = "all"
SCOPE_USER = "user"
SCOPE_PROJECT = "project"
UNKNOWN_SCOPE = "team"

# Backend project-budget LiteLLM alias prefix: rows with it are hidden from non-admins.
BUDGET_ALIAS_PREFIX = "codemie:project:"

INVALID_FILTERS_MESSAGE = "Invalid filters"
INVALID_FILTERS_HELP = "URL-encoded JSON object"


def jira_placeholder_credentials() -> list[CredentialValues]:
    """Jira values that are saved but never used to connect anywhere."""
    return [
        CredentialValues(key="url", value=PLACEHOLDER_URL),
        CredentialValues(key="token", value=PLACEHOLDER_TOKEN),
        CredentialValues(key="username", value=""),
    ]


def git_placeholder_credentials() -> list[CredentialValues]:
    """Git values that are saved but never used to connect anywhere."""
    return [
        CredentialValues(key="url", value=PLACEHOLDER_URL),
        CredentialValues(key="name", value=""),
        CredentialValues(key="token", value=PLACEHOLDER_TOKEN),
    ]


def alias_for(token: str, label: str) -> str:
    """Alias that carries the run's token, so a search by the token finds exactly the run's rows."""
    return f"{token}-{label}"


@dataclass(frozen=True)
class FilterScenario:
    """One filter request against a scope and the rows it must return."""

    scope: str
    filters: dict[str, Any]
    expected: frozenset[str]


def resolve_filters(filters: dict[str, Any], **values: str) -> dict[str, Any]:
    """The filters with every `{name}` in a string value replaced; other values are kept."""
    return {
        key: value.format(**values) if isinstance(value, str) else value
        for key, value in filters.items()
    }


FILTER_SCENARIOS = {
    "search": FilterScenario(
        SCOPE_USER, {"search": f"{TOKEN}-{ROW_GIT}"}, frozenset({ROW_GIT})
    ),
    "type": FilterScenario(
        SCOPE_USER,
        {"search": TOKEN, "type": "Jira"},
        frozenset({ROW_JIRA, ROW_GLOBAL}),
    ),
    "global": FilterScenario(
        SCOPE_USER, {"search": TOKEN, "is_global": True}, frozenset({ROW_GLOBAL})
    ),
    "not_global": FilterScenario(
        SCOPE_USER,
        {"search": TOKEN, "is_global": False},
        frozenset({ROW_JIRA, ROW_GIT}),
    ),
    "project": FilterScenario(
        SCOPE_ALL, {"search": TOKEN, "project": PROJECT}, frozenset({ROW_PROJECT})
    ),
    "created_by": FilterScenario(
        SCOPE_PROJECT,
        {"search": TOKEN, "created_by": CREATOR},
        frozenset({ROW_PROJECT}),
    ),
    "created_by_other": FilterScenario(
        SCOPE_PROJECT,
        {"search": TOKEN, "created_by": f"{TOKEN}-nobody"},
        frozenset(),
    ),
    "scope_key_ignored": FilterScenario(
        SCOPE_USER,
        {"search": TOKEN, "scope": SCOPE_PROJECT},
        frozenset({ROW_JIRA, ROW_GIT, ROW_GLOBAL}),
    ),
}

MALFORMED_FILTERS = {
    "malformed_json": "{not json",
    "json_array": "[1, 2]",
    "nested_too_deeply": "[" * 1000 + "]" * 1000,
}
OUT_OF_RANGE_PER_PAGE = {"zero": 0, "above_maximum": 101}
