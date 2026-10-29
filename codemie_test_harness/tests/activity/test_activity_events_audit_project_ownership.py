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

"""API test for the project.ownership_changed activity event.

Covers:
    TC-009  an ownership transfer is recorded with the usernames of both owners
"""

import pytest
from hamcrest import assert_that, equal_to, has_entries, has_length

from codemie_test_harness.tests.test_data.project_ownership_test_data import (
    OWNERSHIP_CHANGED_EVENT_TYPE,
)


@pytest.mark.activity
@pytest.mark.api
def test_project_ownership_changed_audit_record_stored(
    activity_utils, maintainer_client, project_utils, non_admin_user, ownership_project
):
    """
    event for the project, carrying the previous and the new owner's usernames (not ids).
    """
    _, new_owner_id, new_owner_client = non_admin_user

    project_utils.transfer_ownership(ownership_project.name, new_owner_id)

    response = activity_utils.list_activity_events(
        entity_id=ownership_project.name,
        event_type=[OWNERSHIP_CHANGED_EVENT_TYPE],
        domain=["project_management"],
    )
    assert_that(
        response.data,
        has_length(1),
        "Exactly one project.ownership_changed event is expected for the transfer",
    )
    record = response.data[0]
    assert_that(record.event_type, equal_to(OWNERSHIP_CHANGED_EVENT_TYPE), "event_type")
    assert_that(record.entity_type, equal_to("project"), "entity_type")
    assert_that(
        record.attributes,
        has_entries(
            previous_owner_username=maintainer_client.users.about_me().username,
            new_owner_username=new_owner_client.users.about_me().username,
        ),
        "The event must name both owners by username",
    )
