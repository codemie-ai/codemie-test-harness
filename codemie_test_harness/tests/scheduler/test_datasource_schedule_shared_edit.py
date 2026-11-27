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

"""Datasource schedule edited by another member of the datasource's project.

A shared datasource has one PROJECT schedule row. When a second project member
changes its cron, the row is updated in place: no second row appears for the
datasource, the row keeps its id (and with it the creator as owner, since the
in-place update leaves the owner unchanged), and both members read the new cron.
"""

import pytest
from codemie_sdk.models.integration import CredentialTypes, IntegrationType
from hamcrest import assert_that, equal_to, has_length

from codemie_test_harness.tests.test_data.datasource_schedule_test_data import (
    datasource_schedule_edit,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.datasource_utils import DataSourceUtils
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver
from codemie_test_harness.tests.utils.integration_utils import IntegrationUtils
from codemie_test_harness.tests.utils.scheduler_utils import SchedulerUtils


@pytest.fixture
def shared_project(platform_user, second_platform_user, project, user_utils):
    """A project both plain members belong to, without project admin rights.

    The users are requested before ``project`` so they outlive its teardown, which
    unassigns every member before deleting the project.
    """
    shared = project()
    for member in (platform_user, second_platform_user):
        user_utils.assign_user_to_project(
            member.user_id, shared.name, is_project_admin=False
        )
    return shared


@pytest.fixture
def schedule_edit():
    return datasource_schedule_edit()


@pytest.fixture
def project_jira_integration(
    client, shared_project, scoped_integrations, jira_seed_issue
):
    """Project-level Jira integration of the shared project, created by the admin client.

    Plain members cannot create PROJECT settings; both members can use the integration.
    """
    return scoped_integrations.create(
        IntegrationUtils(client),
        IntegrationType.PROJECT,
        shared_project.name,
        get_random_name(),
        credential_type=CredentialTypes.JIRA,
        credential_values=CredentialsManager.jira_credentials(),
    )


@pytest.fixture
def shared_jira_datasource(
    platform_user, shared_project, project_jira_integration, schedule_edit
):
    """Jira datasource of platform_user shared with the project, with a schedule.

    Sharing makes the schedule a PROJECT row, which the second member can list.
    """
    datasource_utils = DataSourceUtils(platform_user.client)
    datasource = datasource_utils.create_jira_datasource(
        project_name=shared_project.name,
        setting_id=project_jira_integration.id,
        project_space_visible=True,
        cron_expression=schedule_edit.initial_cron,
        timezone=schedule_edit.timezone,
    )
    yield datasource
    datasource_utils.safe_delete_datasource(datasource)


@pytest.mark.scheduler
@pytest.mark.jira
@pytest.mark.requires_capability("retrieval")
@pytest.mark.api
@pytest.mark.skipif(
    EnvironmentResolver.is_sandbox(),
    reason="Scheduler is disabled on sandbox environments",
)
def test_edit_datasource_schedule_by_second_member_keeps_one_schedule(
    platform_user,
    second_platform_user,
    project_jira_integration,
    shared_jira_datasource,
    schedule_edit,
):
    # @case datasource-reindex-schedule-ownership-switches_TC_001
    creator_schedulers = SchedulerUtils(platform_user.client)
    editor_schedulers = SchedulerUtils(second_platform_user.client)

    created_rows = creator_schedulers.list_schedulers_for_resource(
        shared_jira_datasource.id
    )
    assert_that(
        created_rows,
        has_length(1),
        "A new scheduled datasource must have exactly one schedule row.",
    )
    schedule_id = created_rows[0].id
    assert_that(
        created_rows[0].schedule.cron,
        equal_to(schedule_edit.initial_cron),
        "The schedule row must hold the cron the datasource was created with.",
    )

    # Edit only the cron, as the other member, without a reindex.
    DataSourceUtils(second_platform_user.client).update_jira_datasource(
        shared_jira_datasource.id,
        setting_id=project_jira_integration.id,
        cron_expression=schedule_edit.edited_cron,
        timezone=schedule_edit.timezone,
    )

    creator_rows = creator_schedulers.list_schedulers_for_resource(
        shared_jira_datasource.id
    )
    assert_that(
        creator_rows,
        has_length(1),
        "The creator must still see one schedule row after another member's edit.",
    )
    assert_that(
        creator_rows[0].id,
        equal_to(schedule_id),
        "The edit must update the creator's schedule row in place, keeping its id.",
    )
    assert_that(
        creator_rows[0].schedule.cron,
        equal_to(schedule_edit.edited_cron),
        "The creator's schedule row must hold the edited cron.",
    )

    editor_rows = editor_schedulers.list_schedulers_for_resource(
        shared_jira_datasource.id
    )
    assert_that(
        editor_rows,
        has_length(1),
        "The editing member must see one schedule row, not a second one of their own.",
    )
    assert_that(
        editor_rows[0].id,
        equal_to(schedule_id),
        "The editing member must see the creator's schedule row, keeping its id.",
    )
    assert_that(
        editor_rows[0].schedule.cron,
        equal_to(schedule_edit.edited_cron),
        "The editing member must see the edited cron on the schedule row.",
    )

    stored = platform_user.client.datasources.get(shared_jira_datasource.id)
    assert_that(
        stored.cron_expression,
        equal_to(schedule_edit.edited_cron),
        "The datasource must report the edited cron.",
    )
