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

"""Repository registration API: PUT/GET/DELETE /v1/projects/{name}/repositories.

The SDK has no call for it, so the tests use the raw-HTTP CliAnalyticsApi with a global admin
(admin or maintainer rights are what the API requires).
"""

import pytest
from hamcrest import assert_that, contains_string, equal_to

from codemie_test_harness.tests.test_data.cli_classification_test_data import (
    REGISTRATION_ERROR_ROWS,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name, poll_until
from codemie_test_harness.tests.utils.cli_analytics_api_utils import CliAnalyticsApi
from codemie_test_harness.tests.utils.cli_classification_utils import new_remote

REPOSITORIES = "/v1/projects/{project}/repositories"


@pytest.fixture
def registration_world(provisioner, gate_admin_client):
    """An admin API, one shared project and the personal project of a fresh user."""
    admin_api = CliAnalyticsApi(gate_admin_client)
    owner = provisioner.sender()
    shared = provisioner.project()
    status = poll_until(
        lambda: admin_api.request("GET", f"/v1/projects/{owner.email}").status_code,
        lambda code: code == 200,
        timeout=30,
        interval=2,
    )
    assert_that(
        status,
        equal_to(200),
        f"setup: the personal project of {owner.email} does not exist (HTTP {status})",
    )
    return {"api": admin_api, "shared": shared, "personal": owner.email}


# @case classify-cli-sessions-by-subscription_TC_024
@pytest.mark.cli_analytics
@pytest.mark.parametrize("row", REGISTRATION_ERROR_ROWS)
@pytest.mark.api
def test_registration_api_refuses_personal_projects_bad_remotes_and_missing_registrations(
    registration_world, row
):
    """Registering on a personal project and registering an unparseable remote are 400 with the
    API's message; unregistering a registration that does not exist is 404."""
    project = registration_world[row.target]

    response = registration_world["api"].request(
        row.method, REPOSITORIES.format(project=project), json={"remote": row.remote}
    )

    assert_that(
        response.status_code,
        equal_to(row.status),
        f"{response.status_code}: {response.text[:200]}",
    )
    assert_that(
        response.text,
        contains_string(row.message),
        "the error must say why the call was refused",
    )


# @case classify-cli-sessions-by-subscription_TC_024
@pytest.mark.cli_analytics
@pytest.mark.api
def test_listing_registrations_of_an_unknown_project_is_404(registration_world):
    """The registrations of a project that does not exist are 404 (the API reveals nothing else)."""
    response = registration_world["api"].request(
        "GET", REPOSITORIES.format(project=get_random_name())
    )

    assert_that(
        response.status_code,
        equal_to(404),
        f"{response.status_code}: {response.text[:200]}",
    )


# @case classify-cli-sessions-by-subscription_TC_024
@pytest.mark.cli_analytics
@pytest.mark.api
def test_registered_repository_is_listed_and_can_be_unregistered_once(
    provisioner, registration_world
):
    """A valid remote registered to a shared project is returned under its normalized key, listed
    for the project and removed by DELETE; a second DELETE finds nothing and is 404."""
    api, project = registration_world["api"], registration_world["shared"]
    remote = new_remote()
    key = remote.removeprefix("https://").removesuffix(".git")

    registered = provisioner.register(project, remote)
    listed = api.request("GET", REPOSITORIES.format(project=project))
    removed = api.request(
        "DELETE", REPOSITORIES.format(project=project), json={"remote": remote}
    )
    removed_again = api.request(
        "DELETE", REPOSITORIES.format(project=project), json={"remote": remote}
    )

    assert_that(
        registered,
        equal_to({"key": key, "project_name": project}),
        "the registration must name the normalized remote and the project",
    )
    assert_that(listed.json(), equal_to([registered]), "the project must list it")
    assert_that(
        (removed.status_code, removed_again.status_code),
        equal_to((200, 404)),
        "the first DELETE must remove the registration and the second find nothing",
    )
