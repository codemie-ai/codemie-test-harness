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
"""UI test for the Actor column of the project history after the actor is deleted.

Covers:
    An event keeps the identity recorded on it once its actor account is deleted
"""

import pytest
from hamcrest import assert_that, contains_string, equal_to

from codemie_test_harness.tests.ui.pageobject.administration.project_details_page import (
    ProjectDetailsPage,
)
from codemie_test_harness.tests.ui.test_data.project_history_test_data import (
    event_actor_text,
)


# @case project-history-modal_TC_010
@pytest.mark.activity
@pytest.mark.project
@pytest.mark.ui
def test_actor_column_shows_the_recorded_identity_after_the_actor_is_deleted(
    page, deleted_actor_trail, platform_user, delete_account, activity_utils
):
    project = deleted_actor_trail.project
    recorded_identity = event_actor_text(deleted_actor_trail.events_by_actor[0])
    assert_that(
        recorded_identity,
        contains_string(platform_user.email),
        "before the deletion the event names its actor by e-mail",
    )

    delete_account(platform_user)

    details_page = ProjectDetailsPage(page).navigate_to(project.name)
    details_page.should_be_on_project_details_page(project.name)
    modal = details_page.open_history()
    modal.should_be_open_for(project.name)
    modal.should_show_actor_text(
        recorded_identity, len(deleted_actor_trail.events_by_actor)
    )
    events_after_deletion = activity_utils.list_all_project_events(
        project.instance_id, actor_id=deleted_actor_trail.actor_id
    )
    assert_that(
        [event_actor_text(event) for event in events_after_deletion],
        equal_to([recorded_identity] * len(deleted_actor_trail.events_by_actor)),
        "the API serves the identity recorded on the events after the deletion",
    )
