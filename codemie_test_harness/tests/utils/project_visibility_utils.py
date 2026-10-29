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

"""Raw project reads and writes for the project-level `cli_analytics_enabled` tests.

The SDK models turn a missing key into None, so key presence is checked on the raw JSON of the
responses (`CliAnalyticsApi`). `RolesWorld` is the set of projects and role clients one test
module shares; every test sets the flag state it needs before it reads.
"""

import json
from functools import cached_property
from typing import NamedTuple, Optional

import pytest
import requests
from hamcrest import (
    all_of,
    assert_that,
    equal_to,
    has_entry,
    has_key,
    instance_of,
    is_not,
    less_than,
    none,
    not_none,
    same_instance,
)

from codemie_test_harness.tests.test_data.project_cli_analytics_test_data import (
    NOT_LISTED,
    PRESENT,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.cli_analytics_api_utils import CliAnalyticsApi

CLI_ANALYTICS_KEY = "cli_analytics_enabled"
LEGACY_APPLICATION_PATH = "/v1/application/{app_name}"
_SHOWN_BODY_CHARS = 300


class View(NamedTuple):
    """One read of a project: HTTP status, the project's JSON (None when not 2xx or not listed)."""

    status: int
    body: Optional[dict]
    text: str


class ProjectFlagUtils(CliAnalyticsApi):
    """Raw project calls with the token of one client; projects it created are remembered."""

    def __init__(self, client):
        super().__init__(client)
        self.created = []

    def get_project(self, name: str) -> requests.Response:
        return self.request("GET", f"/v1/projects/{name}")

    def patch_project(self, name: str, body: dict) -> requests.Response:
        return self.request("PATCH", f"/v1/projects/{name}", json=body)

    def create_project(self, body: dict) -> requests.Response:
        """POST /v1/projects; a created project is remembered for cleanup."""
        response = self.request("POST", "/v1/projects", json=body)
        if response.status_code in (200, 201):
            self.created.append(body["name"])
        return response

    def read(self, name: str) -> dict:
        """Raw JSON of GET /v1/projects/{name}; fails unless the answer is 200."""
        response = self.get_project(name)
        assert_that(
            response.status_code,
            equal_to(200),
            f"GET {name}: {response.status_code} {response.text[:_SHOWN_BODY_CHARS]}",
        )
        return response.json()

    def write_flag(self, name: str, value: bool, description: Optional[str] = None):
        """PATCH the flag (and optionally the description) and fail unless the answer is 200."""
        body = {CLI_ANALYTICS_KEY: value}
        if description is not None:
            body["description"] = description
        response = self.patch_project(name, body)
        assert_that(
            response.status_code,
            equal_to(200),
            f"PATCH {name} {body}: {response.status_code} "
            f"{response.text[:_SHOWN_BODY_CHARS]}",
        )
        return response

    def list_sample(self, names: list) -> list:
        """A bounded sample of the project list: its first page (100 items) plus each of
        `names` found through the list search. It does not page through the stand, whose
        total changes while other workers create and delete projects."""
        response = self.request(
            "GET", "/v1/projects", params={"page": 0, "per_page": 100}
        )
        assert_that(
            response.status_code,
            equal_to(200),
            f"list: {response.status_code} {response.text[:_SHOWN_BODY_CHARS]}",
        )
        items = response.json()["data"]
        for name in names:
            view = self.view("list", name)
            assert_that(view.status, equal_to(200), f"list search {name}: {view.text}")
            assert_that(view.body, not_none(), f"{name} is not in the project list")
            items.append(view.body)
        return items

    def view(self, route: str, name: str) -> View:
        """Read `name` through list | detail | patch_response | legacy (a description-only PATCH)."""
        if route == "list":
            response = self.request(
                "GET", "/v1/projects", params={"search": name, "per_page": 20}
            )
        elif route == "detail":
            response = self.get_project(name)
        elif route == "patch_response":
            response = self.patch_project(
                name, {"description": f"visibility {get_random_name()}"}
            )
        else:
            response = self.request("GET", f"/v1/application/{name}")
        body = response.json() if response.status_code in (200, 201) else None
        if route == "list" and body is not None:
            listed = [item for item in body["data"] if item["name"] == name]
            assert_that(len(listed), less_than(2), f"{name} is listed more than once")
            body = listed[0] if listed else None
        return View(response.status_code, body, response.text[:_SHOWN_BODY_CHARS])

    def visible_values(self, name: str, include_legacy: bool) -> dict:
        """The flag value each route shows for `name` ('<missing>' when the key is absent)."""
        routes = ["detail", "list"] + (["legacy"] if include_legacy else [])
        views = {route: self.view(route, name) for route in routes}
        return {
            route: (view.body or {}).get(CLI_ANALYTICS_KEY, "<missing>")
            for route, view in views.items()
        }

    def legacy_route_mounted(self) -> bool:
        """True when GET /v1/application/{app_name} is mounted. The legacy router needs
        Elasticsearch, so it is absent on some stands. Fails loudly when this cannot be told."""
        response = self.request("GET", "/openapi.json")
        assert_that(
            response.status_code,
            equal_to(200),
            "cannot tell whether the legacy application route is mounted: "
            f"/openapi.json answered {response.status_code}",
        )
        paths = response.json().get("paths")
        assert_that(
            paths, instance_of(dict), "openapi.json has no 'paths' object to inspect"
        )
        return LEGACY_APPLICATION_PATH in paths

    def has_platform_admin_label(self, email: str) -> bool:
        """True when the admin user list shows `email` with the platform_admin label."""
        response = self.request(
            "GET",
            "/v1/admin/users",
            params={
                "search": email,
                "filters": json.dumps({"platform_role": "platform_admin"}),
                "per_page": 10,
            },
        )
        assert_that(
            response.status_code,
            equal_to(200),
            f"admin users: {response.status_code} {response.text[:_SHOWN_BODY_CHARS]}",
        )
        return email in [user["email"] for user in response.json()["data"]]


def assert_view(view: View, expected, shown: bool, what: str) -> None:
    """Check one visibility cell: an int is the exact status, otherwise see test_data."""
    if isinstance(expected, int):
        assert_that(
            view.status, equal_to(expected), f"{what}: status, body={view.text!r}"
        )
        return
    assert_that(view.status, equal_to(200), f"{what}: status, body={view.text!r}")
    if expected == NOT_LISTED:
        assert_that(view.body, none(), f"{what}: the project must not be listed")
    elif expected == PRESENT:
        assert_that(
            view.body,
            has_entry(CLI_ANALYTICS_KEY, same_instance(shown)),
            f"{what}: {CLI_ANALYTICS_KEY} must be shown as {shown}",
        )
    else:
        assert_that(
            view.body,
            all_of(not_none(), is_not(has_key(CLI_ANALYTICS_KEY))),
            f"{what}: {CLI_ANALYTICS_KEY} must be absent from the body",
        )


class RolesWorld:
    """Two projects and one client per role. `target` carries the state under test, `other`
    the opposite; the member belongs to both, the project admin to the target, the other
    project admin to the other project, the auditor and the unrelated user to neither."""

    def __init__(self, clients: dict, target: str, other: str, member_email: str):
        self.clients = clients
        self.target = target
        self.other = other
        self.member_email = member_email
        self.admin = ProjectFlagUtils(clients["global_admin"])

    @cached_property
    def legacy_mounted(self) -> bool:
        return self.admin.legacy_route_mounted()

    def project(self, which: str) -> str:
        return self.target if which == "target" else self.other

    def shown_flag(self, which: str, state: bool) -> bool:
        """The value a viewer must see: the state for the target, the opposite for the other."""
        return state if which == "target" else not state

    def write_states(self, state: bool) -> None:
        self.admin.write_flag(self.target, state)
        self.admin.write_flag(self.other, not state)

    def require_route(self, route: str) -> None:
        """Skip on a positive 'not mounted' signal for the legacy route; never on doubt."""
        if route == "legacy" and not self.legacy_mounted:
            pytest.skip(
                "NOT RUN: /v1/application/{app_name} is not mounted on this backend "
                "(the index router needs Elasticsearch, see openapi.json)"
            )
