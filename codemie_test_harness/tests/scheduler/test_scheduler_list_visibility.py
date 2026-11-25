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

"""Scheduler list visibility between project members.

A plain project member listing schedulers without an ownerType filter must see the
project's shared rows and their own personal rows, never the personal rows of another
member of the same project.
"""

import pytest
from hamcrest import assert_that, has_item, not_

from codemie_sdk.models.integration import CredentialTypes, IntegrationType

from codemie_test_harness.tests.test_data.scheduler_list_test_data import (
    scheduler_credential_values,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver
from codemie_test_harness.tests.utils.integration_utils import IntegrationUtils

# Largest page the list accepts; the project holds two personal rows, so one page is enough.
LIST_PAGE_SIZE = 100


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
def project_assistant(assistant_factory, shared_project):
    """Assistant in the shared project; a scheduler's assistant must belong to its project."""
    return assistant_factory.create(project_name=shared_project.name)


@pytest.mark.scheduler
@pytest.mark.api
@pytest.mark.skipif(
    EnvironmentResolver.is_sandbox(),
    reason="Scheduler is disabled on sandbox environments",
)
def test_scheduler_list_hides_other_members_personal_schedulers(
    platform_user,
    second_platform_user,
    shared_project,
    project_assistant,
    scoped_integrations,
):
    # @case scheduler-list-hides-other-members_TC_001
    own_scheduler = scoped_integrations.create(
        IntegrationUtils(platform_user.client),
        IntegrationType.USER,
        shared_project.name,
        get_random_name(),
        credential_type=CredentialTypes.SCHEDULER,
        credential_values=scheduler_credential_values(
            project_assistant.id, "Own personal scheduler"
        ),
    )
    other_scheduler = scoped_integrations.create(
        IntegrationUtils(second_platform_user.client),
        IntegrationType.USER,
        shared_project.name,
        get_random_name(),
        credential_type=CredentialTypes.SCHEDULER,
        credential_values=scheduler_credential_values(
            project_assistant.id, "Other member personal scheduler"
        ),
    )

    listed = platform_user.client.schedulers.list(per_page=LIST_PAGE_SIZE)
    listed_ids = [item.id for item in listed.items]

    assert_that(
        listed_ids,
        has_item(own_scheduler.id),
        "The caller's own personal scheduler must stay in the default list.",
    )
    assert_that(
        listed_ids,
        not_(has_item(other_scheduler.id)),
        "Another member's personal scheduler must not appear in the default list.",
    )
