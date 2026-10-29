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

"""API tests for the ServiceNow project lookup (GET /v1/integrations/servicenow/projects)."""

import pytest
from hamcrest import assert_that, empty, equal_to
from requests import HTTPError


@pytest.mark.project
@pytest.mark.api
def test_list_projects_returns_distinct_shared_projects_for_several_emails(
    servicenow_account, lookup_world
):
    # @case servicenow-project-budget-integration-api_TC_001
    emails = [
        lookup_world.user_a.email,
        lookup_world.user_b.email,
        lookup_world.unregistered_email,
    ]

    projects = servicenow_account.integration.list_projects(emails)

    assert_that(
        [project.project_name for project in projects],
        equal_to(list(lookup_world.display_names_by_project)),
        "Each shared project of either user must appear once, ordered by name; the project "
        "both users share must not be repeated and personal projects must be left out",
    )
    assert_that(
        {project.project_name: project.display_name for project in projects},
        equal_to(lookup_world.display_names_by_project),
        "Each item must carry the project's display name, null when it has none",
    )


@pytest.mark.project
@pytest.mark.api
def test_list_projects_skips_email_without_registered_user(
    servicenow_account, lookup_world
):
    # @case servicenow-project-budget-integration-api_TC_001
    projects = servicenow_account.integration.list_projects(
        [lookup_world.unregistered_email]
    )

    assert_that(
        projects,
        empty(),
        "An email with no CodeMie user contributes no project, so nothing matches",
    )


@pytest.mark.project
@pytest.mark.api
@pytest.mark.parametrize(
    "emails",
    [[], ["not-an-email"]],
    ids=["no_emails", "malformed_email"],
)
def test_list_projects_rejects_missing_or_invalid_emails(servicenow_account, emails):
    # @case servicenow-project-budget-integration-api_TC_002
    with pytest.raises(HTTPError) as exc_info:
        servicenow_account.integration.list_projects(emails)

    assert_that(
        exc_info.value.response.status_code,
        equal_to(422),
        "A lookup without a valid email must be refused as invalid input",
    )
