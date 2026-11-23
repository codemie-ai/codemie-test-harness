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
"""UI tests for who is offered the project history and where.

Covers:
    A maintainer and a project administrator see the same history of a project
    The details page of a personal project offers no history entry point
"""

import pytest
from hamcrest import assert_that, not_none

from codemie_test_harness.tests.ui.pageobject.administration.project_details_page import (
    ProjectDetailsPage,
)
from codemie_test_harness.tests.utils.marketplace_management_utils import (
    personal_project_of,
)


# @case project-history-modal_TC_008
@pytest.mark.activity
@pytest.mark.project
@pytest.mark.parametrize(
    "acting_credentials",
    ["maintainer", "project_admin"],
    indirect=True,
    ids=["maintainer", "project_admin"],
)
@pytest.mark.ui
def test_maintainer_and_project_admin_see_the_same_history(
    page, trail_outside_maintainer_membership, activity_utils
):
    project = trail_outside_maintainer_membership.project
    events = activity_utils.list_all_project_events(project.instance_id)
    details_page = ProjectDetailsPage(page).navigate_to(project.name)
    details_page.should_be_on_project_details_page(project.name)

    details_page.should_have_history_button()
    modal = details_page.open_history()

    modal.should_be_open_for(project.name)
    modal.should_show_columns()
    modal.should_show_all_filter_controls()
    modal.should_show_total(len(events))
    modal.should_list_events(events)
    modal.should_show_readable_detail_for_every_row()


# @case project-history-modal_TC_009
@pytest.mark.activity
@pytest.mark.project
@pytest.mark.ui
def test_personal_project_details_page_offers_no_history_entry_point(page, client):
    personal_project = personal_project_of(client.users.about_me())
    assert_that(personal_project, not_none(), "the maintainer has a personal project")

    details_page = ProjectDetailsPage(page).navigate_to(personal_project)

    details_page.should_be_on_project_details_page(personal_project)
    details_page.should_not_have_history_button()
