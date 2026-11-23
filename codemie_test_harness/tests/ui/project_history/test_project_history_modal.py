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

"""UI tests for the activity history modal of the project details page.

Covers:
    The project administrator opens the history: unfiltered, newest first
    Category and date-range filters narrow it; Budget spans budget and enforcement events
    Totals, sort order and category options are the API's
    Paging keeps the applied filter and the total
    Expanded rows show readable detail with formatted amounts
    A history with no matching events shows an explicit empty state
    A failed request shows an error with Retry
    Closing the modal returns to the unchanged details page
    The Actor filter returns only the chosen actor's events

The trail is made through the API (see conftest.py) and every expectation about rows and
totals is read from the SDK for the same project, so the browser is compared with the API
and not with a number written in the test.
"""

import pytest
from hamcrest import assert_that, equal_to, greater_than, has_item, has_items, is_

from codemie_test_harness.tests.test_data.project_activity_test_data import (
    ADMIN_UPDATES,
    ENFORCEMENT_EVENT,
    EVENT_TAXONOMY,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_activity_history_modal import (
    ProjectActivityHistoryModal,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_details_page import (
    ProjectDetailsPage,
)
from codemie_test_harness.tests.ui.test_data.project_history_test_data import (
    AS_PROJECT_ADMIN,
    BUDGET_CATEGORY,
    MAX_BUDGET_INCREASE_TEXT,
    PREVIOUS_MAX_BUDGET_TEXT,
    PROJECT_BUDGET_UPDATED_LABEL,
    RAISED_MAX_BUDGET_TEXT,
    SETTINGS_CATEGORY,
    SMALLEST_PAGE_SIZE,
    SOFT_BUDGET_INCREASE_TEXT,
    api_timestamp,
    far_future_date,
    local_midnight,
)


def open_history(page, project_name):
    """Open the details page of the project and its history modal."""
    details_page = ProjectDetailsPage(page).navigate_to(project_name)
    details_page.should_be_on_project_details_page(project_name)
    return details_page, details_page.open_history()


# @case project-history-modal_TC_001
@AS_PROJECT_ADMIN
@pytest.mark.activity
@pytest.mark.project
@pytest.mark.ui
def test_project_admin_opens_unfiltered_history_newest_first(page, history_trail):
    project = history_trail.project
    details_page = ProjectDetailsPage(page).navigate_to(project.name)
    details_page.should_be_on_project_details_page(project.name)
    details_page.should_have_edit_project_button()
    details_page.should_have_history_button()

    modal = details_page.open_history()

    modal.should_be_open_for(project.name)
    modal.should_show_columns()
    modal.should_show_no_active_filter()
    modal.should_show_total(len(history_trail.events))
    modal.should_list_events(history_trail.events)


# @case project-history-modal_TC_002
@AS_PROJECT_ADMIN
@pytest.mark.activity
@pytest.mark.project
@pytest.mark.ui
def test_category_and_date_range_filters_narrow_the_history(
    page, budget_history_trail, activity_utils
):
    trail, _ = budget_history_trail
    project = trail.project
    yesterday, tomorrow, day_after = (
        local_midnight(-1),
        local_midnight(1),
        local_midnight(2),
    )
    budget_events = activity_utils.list_all_project_events(
        project.instance_id, category=[BUDGET_CATEGORY]
    )
    budget_events_in_range = activity_utils.list_all_project_events(
        project.instance_id,
        category=[BUDGET_CATEGORY],
        from_dt=api_timestamp(yesterday),
        to_dt=api_timestamp(tomorrow),
    )
    events_after_today = activity_utils.list_all_project_events(
        project.instance_id,
        category=[BUDGET_CATEGORY],
        from_dt=api_timestamp(tomorrow),
        to_dt=api_timestamp(day_after),
    )
    assert_that(
        {event.domain for event in budget_events},
        has_items("budget_management", "project_management"),
        "the Budget category spans the budget and the project domain",
    )
    _, modal = open_history(page, project.name)

    modal.select_category(BUDGET_CATEGORY)

    modal.should_show_total(len(budget_events))
    modal.should_list_events(budget_events)
    modal.should_show_event_row(EVENT_TAXONOMY[ENFORCEMENT_EVENT][0])
    modal.should_show_event_row(
        EVENT_TAXONOMY["budget.project_budget_group.created"][0]
    )

    modal.set_to(tomorrow).set_from(yesterday)

    modal.should_show_category_selected(BUDGET_CATEGORY)
    modal.should_show_date_filters(yesterday, tomorrow)
    modal.should_show_active_filters()
    modal.should_show_total(len(budget_events_in_range))
    modal.should_list_events(budget_events_in_range)

    modal.set_to(day_after).set_from(tomorrow)

    modal.should_show_category_selected(BUDGET_CATEGORY)
    modal.should_show_date_filters(tomorrow, day_after)
    modal.should_show_total(len(events_after_today))
    modal.should_show_no_events()


# @case project-history-modal_TC_003
@AS_PROJECT_ADMIN
@pytest.mark.activity
@pytest.mark.project
@pytest.mark.ui
def test_totals_sort_order_and_category_options_come_from_the_api(
    page, history_trail, activity_utils
):
    project = history_trail.project
    metadata = activity_utils.get_project_event_metadata(project.instance_id)
    oldest_settings_events = activity_utils.list_project_events(
        project.instance_id, category=[SETTINGS_CATEGORY], sort_dir="asc"
    )
    _, modal = open_history(page, project.name)

    modal.should_offer_categories(metadata.categories)
    modal.select_category(SETTINGS_CATEGORY)
    modal.sort_oldest_first()

    modal.should_show_total(oldest_settings_events.pagination.total)
    modal.should_list_events(oldest_settings_events.data)


# @case project-history-modal_TC_004
@AS_PROJECT_ADMIN
@pytest.mark.activity
@pytest.mark.project
@pytest.mark.ui
def test_paging_keeps_the_applied_filter_and_the_total(
    page, long_history_trail, activity_utils
):
    project = long_history_trail.project
    settings_events = activity_utils.list_project_events(
        project.instance_id,
        category=[SETTINGS_CATEGORY],
        limit=SMALLEST_PAGE_SIZE,
        offset=0,
    )
    second_page = activity_utils.list_project_events(
        project.instance_id,
        category=[SETTINGS_CATEGORY],
        limit=SMALLEST_PAGE_SIZE,
        offset=SMALLEST_PAGE_SIZE,
    )
    total = settings_events.pagination.total
    assert_that(
        total,
        greater_than(SMALLEST_PAGE_SIZE),
        "the trail needs more matching events than one page of the smallest size",
    )
    assert_that(
        {event.id for event in settings_events.data}.isdisjoint(
            {event.id for event in second_page.data}
        ),
        is_(True),
        "the two pages of the API hold different events",
    )
    _, modal = open_history(page, project.name)

    modal.select_category(SETTINGS_CATEGORY)
    modal.show_per_page(SMALLEST_PAGE_SIZE)

    modal.should_show_category_selected(SETTINGS_CATEGORY)
    modal.should_show_total(total)
    modal.should_list_events(settings_events.data)

    modal.go_to_next_page()

    modal.should_show_category_selected(SETTINGS_CATEGORY)
    modal.should_show_total(total)
    modal.should_list_events(second_page.data)


# @case project-history-modal_TC_005
@AS_PROJECT_ADMIN
@pytest.mark.activity
@pytest.mark.project
@pytest.mark.ui
def test_expanded_row_shows_readable_budget_change_with_formatted_amounts(
    page, raised_budget_trail
):
    project = raised_budget_trail.project
    assert_that(
        [event.event_type for event in raised_budget_trail.events],
        has_item("budget.project_budget.updated"),
        "raising the budget limits is recorded as a project budget update",
    )
    _, modal = open_history(page, project.name)

    modal.should_show_event_row(PROJECT_BUDGET_UPDATED_LABEL)
    modal.expand_row(PROJECT_BUDGET_UPDATED_LABEL)

    modal.should_show_budget_change_detail(
        PROJECT_BUDGET_UPDATED_LABEL,
        project_name=project.name,
        previous_max=PREVIOUS_MAX_BUDGET_TEXT,
        new_max=RAISED_MAX_BUDGET_TEXT,
        max_increase=MAX_BUDGET_INCREASE_TEXT,
        soft_increase=SOFT_BUDGET_INCREASE_TEXT,
    )
    modal.should_show_formatted_timestamps()


# @case project-history-modal_TC_006
@AS_PROJECT_ADMIN
@pytest.mark.activity
@pytest.mark.project
@pytest.mark.ui
def test_event_types_without_specific_rendering_show_a_readable_fallback(
    page, history_trail
):
    _, modal = open_history(page, history_trail.project.name)

    modal.should_show_total(len(history_trail.events))
    modal.should_show_readable_detail_for_every_row()


# @case project-history-modal_TC_011
@AS_PROJECT_ADMIN
@pytest.mark.activity
@pytest.mark.project
@pytest.mark.ui
def test_history_without_matching_events_shows_the_empty_state(
    page, history_trail, activity_utils
):
    project = history_trail.project
    metadata = activity_utils.get_project_event_metadata(project.instance_id)
    assert_that(
        metadata.recording_enabled,
        is_(True),
        "recording is on, so the empty state below comes from the filter and not from a disabled trail",
    )
    _, modal = open_history(page, project.name)
    modal.should_show_total(len(history_trail.events))

    modal.set_from_text(far_future_date())

    modal.should_show_total(0)
    modal.should_show_no_events()


# @case project-history-modal_TC_013
@AS_PROJECT_ADMIN
@pytest.mark.activity
@pytest.mark.project
@pytest.mark.ui
def test_failed_history_request_shows_error_with_retry_and_page_stays_usable(
    page, history_trail
):
    project = history_trail.project
    details_page = ProjectDetailsPage(page).navigate_to(project.name)
    details_page.should_be_on_project_details_page(project.name)
    modal = ProjectActivityHistoryModal(page)
    modal.fail_event_requests()

    details_page.open_history()

    modal.should_show_load_error_with_retry()

    modal.restore_event_requests()
    modal.retry()

    modal.should_show_total(len(history_trail.events))
    modal.should_list_events(history_trail.events)

    modal.close()
    modal.should_be_closed()
    details_page.open_members_tab()
    details_page.should_have_members_tab_selected()


# @case project-history-modal_TC_014
@AS_PROJECT_ADMIN
@pytest.mark.activity
@pytest.mark.project
@pytest.mark.ui
def test_closing_the_modal_returns_to_the_unchanged_details_page(
    page, history_trail, project_utils, activity_utils
):
    project = history_trail.project
    settings_total = activity_utils.list_project_events(
        project.instance_id, category=[SETTINGS_CATEGORY], limit=1
    ).pagination.total
    total_before = activity_utils.list_project_events(
        project.instance_id, limit=1
    ).pagination.total
    detail_before = project_utils.get_project_detail(project.name)
    details_page = ProjectDetailsPage(page).navigate_to(project.name)
    details_page.should_be_on_project_details_page(project.name)
    details_page.open_members_tab()
    modal = details_page.open_history()

    modal.select_category(SETTINGS_CATEGORY)

    modal.should_show_active_filters()
    modal.should_show_total(settings_total)

    modal.close()

    modal.should_be_closed()
    details_page.should_have_members_tab_selected()
    total_after = activity_utils.list_project_events(
        project.instance_id, limit=1
    ).pagination.total
    detail_after = project_utils.get_project_detail(project.name)
    assert_that(
        total_after, equal_to(total_before), "browsing the history records no event"
    )
    assert_that(
        detail_after.description,
        equal_to(detail_before.description),
        "browsing the history changes nothing on the project",
    )


# @case project-history-modal_TC_015
@pytest.mark.activity
@pytest.mark.project
@pytest.mark.ui
def test_actor_filter_returns_only_the_chosen_actors_events(
    page, history_trail, activity_utils
):
    project = history_trail.project
    admin_events = activity_utils.list_all_project_events(
        project.instance_id, actor_id=history_trail.admin_user_id
    )
    assert_that(
        len(admin_events), equal_to(ADMIN_UPDATES), "the administrator made the updates"
    )
    assert_that(
        len(history_trail.events),
        greater_than(len(admin_events)),
        "other actors have events in the trail",
    )
    _, modal = open_history(page, project.name)

    modal.filter_by_actor(admin_events[0].actor_email)

    modal.should_show_total(len(admin_events))
    modal.should_list_events(admin_events)
    modal.should_show_active_filters()
