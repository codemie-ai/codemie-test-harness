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

"""Who may enable or disable a scheduler through PATCH /v1/schedulers/{scheduler_id}.

The PATCH changes the row only for a caller with write access to it: the owner of a
USER row, a project admin of a PROJECT row's project, or a platform admin or
maintainer. Any other caller gets 403 and the row keeps its value. An id that belongs
to a Settings row of another kind (an integration) is not found (404) for every
caller, and that row is left unchanged.

Rows are created enabled, so a PATCH to ``isEnabled: false`` is a visible change.
Grounding: backend src/codemie/service/settings/scheduler_settings_service.py:713
(admin/maintainer bypass), :716 (write check, 403), :728 (non-scheduler row, 404),
:742 (value saved, SchedulerListItem returned); src/codemie/rest_api/routers/
schedulers.py:83 (200, SchedulerListItem); frontend src/store/schedulers.ts:162 sends
``{"isEnabled": <bool>}``, the body ``client.schedulers.update`` sends.
"""

from dataclasses import dataclass

import pytest
from codemie_sdk import CodeMieClient
from codemie_sdk.models.integration import CredentialTypes, IntegrationType
from hamcrest import assert_that, equal_to, is_, not_, has_item, not_none
from requests import HTTPError

from codemie_test_harness.tests.test_data.scheduler_patch_test_data import (
    enabled_scheduler_credential_values,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver
from codemie_test_harness.tests.utils.integration_utils import IntegrationUtils
from codemie_test_harness.tests.utils.scheduler_utils import SchedulerUtils


@dataclass
class OwnedScheduler:
    """A scheduler row and a client that can read it back."""

    id: str
    owner_client: CodeMieClient


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
def member_project(platform_user, project, user_utils):
    """A project platform_user belongs to as a plain member."""
    member = project()
    user_utils.assign_user_to_project(
        platform_user.user_id, member.name, is_project_admin=False
    )
    return member


@pytest.fixture
def other_member_user_scheduler(
    second_platform_user, shared_project, assistant_factory, scoped_integrations
):
    """An enabled USER scheduler of second_platform_user in the shared project."""
    assistant = assistant_factory.create(project_name=shared_project.name)
    scheduler = scoped_integrations.create(
        IntegrationUtils(second_platform_user.client),
        IntegrationType.USER,
        shared_project.name,
        get_random_name(),
        credential_type=CredentialTypes.SCHEDULER,
        credential_values=enabled_scheduler_credential_values(
            assistant.id, "Other member personal scheduler"
        ),
    )
    return OwnedScheduler(scheduler.id, second_platform_user.client)


@pytest.fixture
def shared_project_scheduler(
    client, shared_project, assistant_factory, scoped_integrations
):
    """An enabled PROJECT scheduler of the shared project, created by the admin client."""
    assistant = assistant_factory.create(project_name=shared_project.name)
    scheduler = scoped_integrations.create(
        IntegrationUtils(client),
        IntegrationType.PROJECT,
        shared_project.name,
        get_random_name(),
        credential_type=CredentialTypes.SCHEDULER,
        credential_values=enabled_scheduler_credential_values(
            assistant.id, "Shared project scheduler"
        ),
    )
    return OwnedScheduler(scheduler.id, client)


@pytest.fixture
def own_user_scheduler(
    platform_user, member_project, assistant_factory, scoped_integrations
):
    """An enabled USER scheduler of platform_user in a project they belong to."""
    assistant = assistant_factory.create(project_name=member_project.name)
    scheduler = scoped_integrations.create(
        IntegrationUtils(platform_user.client),
        IntegrationType.USER,
        member_project.name,
        get_random_name(),
        credential_type=CredentialTypes.SCHEDULER,
        credential_values=enabled_scheduler_credential_values(
            assistant.id, "Own personal scheduler"
        ),
    )
    return OwnedScheduler(scheduler.id, platform_user.client)


@pytest.fixture
def project_a_scheduler(
    client, default_project_member, assistant_factory, scoped_integrations
):
    """An enabled PROJECT scheduler of default_project_member.project_a, created by the admin client."""
    assistant = assistant_factory.create(project_name=default_project_member.project_a)
    scheduler = scoped_integrations.create(
        IntegrationUtils(client),
        IntegrationType.PROJECT,
        default_project_member.project_a,
        get_random_name(),
        credential_type=CredentialTypes.SCHEDULER,
        credential_values=enabled_scheduler_credential_values(
            assistant.id, "Project A scheduler"
        ),
    )
    return OwnedScheduler(scheduler.id, client)


@pytest.fixture
def other_project_admin_client(
    second_platform_user, default_project_member, user_utils
):
    """second_platform_user made project admin of project_b only, logged in afresh.

    The fresh login is made after the assignment, so the token carries the new role.
    The user is requested before ``default_project_member`` so it outlives the
    projects' teardown, which unassigns every member.
    """
    user_utils.assign_user_to_project(
        second_platform_user.user_id,
        default_project_member.project_b,
        is_project_admin=True,
    )
    return get_client(
        username=second_platform_user.email, password=second_platform_user.password
    )


@pytest.fixture
def platform_user_client(platform_user):
    """platform_user's client."""
    return platform_user.client


@pytest.fixture
def personal_jira_integration(platform_user, scoped_integrations):
    """A JIRA USER integration of platform_user with placeholder credentials."""
    return scoped_integrations.create(
        IntegrationUtils(platform_user.client),
        IntegrationType.USER,
        platform_user.email,
        get_random_name(),
    )


def _credential_pairs(client: CodeMieClient, integration_id: str) -> list[tuple]:
    integration = IntegrationUtils(client).get_integration_by_id(
        integration_id, IntegrationType.USER
    )
    assert_that(integration, is_(not_none()), "The integration must still exist.")
    return [(value.key, value.value) for value in integration.credential_values]


def _is_enabled(client: CodeMieClient, scheduler_id: str) -> bool:
    scheduler = SchedulerUtils(client).find_scheduler(scheduler_id)
    assert_that(
        scheduler, is_(not_none()), "The scheduler must be in its owner's list."
    )
    return scheduler.is_enabled


@pytest.mark.scheduler
@pytest.mark.api
@pytest.mark.skipif(
    EnvironmentResolver.is_sandbox(),
    reason="Scheduler is disabled on sandbox environments",
)
@pytest.mark.parametrize(
    "scheduler_fixture",
    ["other_member_user_scheduler", "shared_project_scheduler"],
    ids=["another_members_user_scheduler", "project_scheduler_as_plain_member"],
)
def test_patch_scheduler_without_write_access_is_forbidden(
    request, platform_user, scheduler_fixture
):
    # @case scheduler-patch-changes-is-enabled_TC_001
    scheduler = request.getfixturevalue(scheduler_fixture)

    with pytest.raises(HTTPError) as error:
        platform_user.client.schedulers.update(scheduler.id, is_enabled=False)

    assert_that(
        error.value.response.status_code,
        equal_to(403),
        "A caller without write access to the row must get 403.",
    )
    assert_that(
        _is_enabled(scheduler.owner_client, scheduler.id),
        is_(True),
        "A denied PATCH must leave the scheduler enabled.",
    )


@pytest.mark.scheduler
@pytest.mark.api
@pytest.mark.skipif(
    EnvironmentResolver.is_sandbox(),
    reason="Scheduler is disabled on sandbox environments",
)
@pytest.mark.parametrize(
    "caller_fixture",
    ["platform_user_client", "admin_client"],
    ids=["row_owner", "platform_admin"],
)
def test_patch_scheduler_with_integration_id_is_not_found(
    request, platform_user, personal_jira_integration, caller_fixture
):
    # @case scheduler-patch-changes-is-enabled_TC_002
    caller = request.getfixturevalue(caller_fixture)
    before = _credential_pairs(platform_user.client, personal_jira_integration.id)

    with pytest.raises(HTTPError) as error:
        caller.schedulers.update(personal_jira_integration.id, is_enabled=False)

    assert_that(
        error.value.response.status_code,
        equal_to(404),
        "The id of a non-scheduler row must be reported as not found.",
    )
    after = _credential_pairs(platform_user.client, personal_jira_integration.id)
    assert_that(
        after,
        equal_to(before),
        "The integration's credential values must not change.",
    )
    assert_that(
        [key for key, _ in after],
        not_(has_item("is_enabled")),
        "No is_enabled value may be added to the integration.",
    )


@pytest.mark.scheduler
@pytest.mark.api
@pytest.mark.skipif(
    EnvironmentResolver.is_sandbox(),
    reason="Scheduler is disabled on sandbox environments",
)
def test_patch_own_scheduler_saves_is_enabled(platform_user, own_user_scheduler):
    # @case scheduler-patch-changes-is-enabled_TC_003
    # The SDK raises on a non-2xx status, so a returned SchedulerListItem is the 200 response.
    updated = platform_user.client.schedulers.update(
        own_user_scheduler.id, is_enabled=False
    )

    assert_that(updated.id, equal_to(own_user_scheduler.id))
    assert_that(
        updated.is_enabled, is_(False), "The response must carry the new value."
    )
    assert_that(
        _is_enabled(platform_user.client, own_user_scheduler.id),
        is_(False),
        "The new value must be saved and returned by the list.",
    )


@pytest.mark.scheduler
@pytest.mark.api
@pytest.mark.skipif(
    EnvironmentResolver.is_sandbox(),
    reason="Scheduler is disabled on sandbox environments",
)
@pytest.mark.parametrize(
    "caller_fixture",
    ["admin_client", "maintainer_client"],
    ids=["platform_admin", "maintainer"],
)
def test_patch_other_users_scheduler_as_admin_or_maintainer(
    request, own_user_scheduler, caller_fixture
):
    # @case scheduler-patch-changes-is-enabled_TC_004
    caller = request.getfixturevalue(caller_fixture)

    updated = caller.schedulers.update(own_user_scheduler.id, is_enabled=False)

    assert_that(updated.id, equal_to(own_user_scheduler.id))
    assert_that(
        updated.is_enabled,
        is_(False),
        "An admin or maintainer must be able to disable another user's scheduler.",
    )


@pytest.mark.scheduler
@pytest.mark.api
@pytest.mark.skipif(
    EnvironmentResolver.is_sandbox(),
    reason="Scheduler is disabled on sandbox environments",
)
def test_patch_project_scheduler_as_its_project_admin(
    fresh_project_admin_client, project_a_scheduler
):
    # @case scheduler-patch-changes-is-enabled_TC_005
    updated = fresh_project_admin_client.schedulers.update(
        project_a_scheduler.id, is_enabled=False
    )

    assert_that(updated.id, equal_to(project_a_scheduler.id))
    assert_that(
        updated.is_enabled,
        is_(False),
        "The project admin must be able to disable a scheduler of their project.",
    )


@pytest.mark.scheduler
@pytest.mark.api
@pytest.mark.skipif(
    EnvironmentResolver.is_sandbox(),
    reason="Scheduler is disabled on sandbox environments",
)
def test_patch_project_scheduler_as_other_project_admin_is_forbidden(
    other_project_admin_client, project_a_scheduler
):
    # @case scheduler-patch-changes-is-enabled_TC_005
    with pytest.raises(HTTPError) as error:
        other_project_admin_client.schedulers.update(
            project_a_scheduler.id, is_enabled=False
        )

    assert_that(
        error.value.response.status_code,
        equal_to(403),
        "An admin of a different project must get 403.",
    )
    assert_that(
        _is_enabled(project_a_scheduler.owner_client, project_a_scheduler.id),
        is_(True),
        "A denied PATCH must leave the scheduler enabled.",
    )
