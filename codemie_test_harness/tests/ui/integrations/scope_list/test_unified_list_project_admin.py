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

"""UI tests for the unified Integrations list as a project admin: one table, Scope filter,
Type filter and filters that survive navigation. Rows are seeded through the API."""

import pytest

from codemie_sdk.models.integration import IntegrationType
from codemie_test_harness.tests.ui.pageobject.integrations.integration_form_page import (
    IntegrationFormPage,
)
from codemie_test_harness.tests.ui.pageobject.integrations.integrations_list_page import (
    IntegrationsListPage,
)
from codemie_test_harness.tests.ui.test_data.unified_integrations_ui_test_data import (
    DIAL,
    DIAL_REMOVED_NOTE,
    GOOGLE_OAUTH,
    PROJECT_ROWS_FOR_PAGINATION,
    SCOPE_BADGE_PROJECT_ONLY,
    SCOPE_BADGE_USER_ONLY,
    SCOPE_PROJECT,
    SCOPE_USER,
    SINGLE_ENTRY_TYPES,
    TYPE_HINT_NOT_AVAILABLE_AT_PROJECT,
    TYPE_HINT_NOT_AVAILABLE_AT_USER,
    USER_ROWS_FOR_PAGINATION,
    ROWS_PER_PAGE,
)


# @case unified-integrations-list_TC_008
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.oss_standalone
def test_project_admin_sees_one_table_with_scope_and_global_marks(
    page, seed_integration
):
    global_alias = seed_integration(IntegrationType.USER, is_global=True)
    user_alias = seed_integration(IntegrationType.USER)
    project_alias = seed_integration(IntegrationType.PROJECT)
    list_page = IntegrationsListPage(page)

    list_page.navigate_to()

    list_page.should_show_rows_in_order([project_alias, user_alias, global_alias])
    list_page.should_show_scope_badge(project_alias, SCOPE_PROJECT)
    list_page.should_show_scope_badge(user_alias, SCOPE_USER)
    list_page.should_show_scope_badge(global_alias, SCOPE_USER)
    list_page.should_show_global_badge(global_alias)
    list_page.should_not_show_global_badge(user_alias)
    list_page.should_not_offer_user_project_switch()


# @case unified-integrations-list_TC_010
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.oss_standalone
def test_scope_filter_limits_table_pagination_and_follows_filters(
    page, seed_integration
):
    user_aliases = [
        seed_integration(IntegrationType.USER) for _ in range(USER_ROWS_FOR_PAGINATION)
    ]
    project_aliases = [
        seed_integration(IntegrationType.PROJECT)
        for _ in range(PROJECT_ROWS_FOR_PAGINATION)
    ]
    list_page = IntegrationsListPage(page)

    list_page.navigate_to()

    list_page.should_have_row_count(ROWS_PER_PAGE)
    list_page.should_have_pages(2)
    list_page.should_not_offer_global_filter()
    list_page.should_not_offer_created_by_filter()
    list_page.should_show_scope_hint()

    list_page.select_scope(SCOPE_USER)

    list_page.should_show_rows(user_aliases)
    list_page.should_have_pages(1)
    list_page.should_offer_global_filter()
    list_page.should_not_offer_created_by_filter()
    list_page.should_not_show_scope_hint()

    list_page.select_scope(SCOPE_PROJECT)

    list_page.should_show_rows(project_aliases)
    list_page.should_have_pages(1)
    list_page.should_offer_created_by_filter()
    list_page.should_not_offer_global_filter()
    list_page.should_not_show_scope_hint()


# @case unified-integrations-list_TC_011
@pytest.mark.integration
@pytest.mark.ui
def test_type_filter_marks_and_disables_scope_bound_types(page):
    list_page = IntegrationsListPage(page)
    list_page.navigate_to()

    list_page.open_type_filter()

    list_page.should_mark_type(DIAL, SCOPE_BADGE_PROJECT_ONLY)
    list_page.should_mark_type(GOOGLE_OAUTH, SCOPE_BADGE_USER_ONLY)
    list_page.should_list_each_type_once(SINGLE_ENTRY_TYPES)
    list_page.close_type_filter()

    list_page.select_scope(SCOPE_USER)
    list_page.open_type_filter()

    list_page.should_disable_type(DIAL, TYPE_HINT_NOT_AVAILABLE_AT_USER)
    list_page.should_not_disable_type(GOOGLE_OAUTH)
    list_page.close_type_filter()

    list_page.select_scope(SCOPE_PROJECT)
    list_page.open_type_filter()

    list_page.should_disable_type(GOOGLE_OAUTH, TYPE_HINT_NOT_AVAILABLE_AT_PROJECT)
    list_page.should_not_disable_type(DIAL)


# @case unified-integrations-list_TC_011
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.oss_standalone
def test_scope_change_removes_a_type_bound_elsewhere_with_a_note(page):
    list_page = IntegrationsListPage(page)
    list_page.navigate_to()
    list_page.open_type_filter()
    list_page.pick_type(DIAL)

    list_page.select_scope(SCOPE_USER)

    list_page.should_show_filter_note(DIAL_REMOVED_NOTE)
    list_page.should_not_filter_by_type_in_url(DIAL)


@pytest.fixture
def form_opened_from_filtered_list(page, seed_integration):
    """The New Integration form, opened from a list at Scope Project filtered to one row.

    Returns the list page, the form page and the alias the list is searched by.
    """
    project_alias = seed_integration(IntegrationType.PROJECT)
    seed_integration(IntegrationType.PROJECT)
    list_page = IntegrationsListPage(page)
    form_page = IntegrationFormPage(page)
    list_page.navigate_to()
    list_page.select_scope(SCOPE_PROJECT)
    list_page.search_for(project_alias)
    list_page.should_show_rows([project_alias])
    list_page.click_new_integration()
    form_page.wait_until_open()
    return list_page, form_page, project_alias


# @case unified-integrations-list_TC_012
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.oss_standalone
def test_filters_survive_create_and_cancel(form_opened_from_filtered_list):
    list_page, form_page, project_alias = form_opened_from_filtered_list

    form_page.cancel()

    list_page.should_have_scope_selected(SCOPE_PROJECT)
    list_page.should_have_search_term(project_alias)
    list_page.should_show_rows([project_alias])


# @case unified-integrations-list_TC_012
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.oss_standalone
def test_filters_survive_create_and_browser_back(form_opened_from_filtered_list):
    list_page, _, project_alias = form_opened_from_filtered_list

    list_page.go_back_in_browser()

    list_page.should_have_scope_selected(SCOPE_PROJECT)
    list_page.should_have_search_term(project_alias)
    list_page.should_show_rows([project_alias])


# @case unified-integrations-list_TC_012
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.oss_standalone
def test_copied_link_reopens_the_same_view(page, ui_login_user, seed_integration):
    project_alias = seed_integration(IntegrationType.PROJECT)
    seed_integration(IntegrationType.PROJECT)
    list_page = IntegrationsListPage(page)
    list_page.navigate_to()
    list_page.select_scope(SCOPE_PROJECT)
    list_page.search_for(project_alias)
    list_page.should_show_rows([project_alias])

    reopened = list_page.open_in_new_page(
        list_page.get_current_url(), ui_login_user.user_id
    )

    reopened.should_have_scope_selected(SCOPE_PROJECT)
    reopened.should_have_search_term(project_alias)
    reopened.should_show_rows([project_alias])


# @case unified-integrations-list_TC_012
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.oss_standalone
def test_link_with_a_type_bound_to_another_scope_drops_the_type(page, seed_integration):
    user_alias = seed_integration(IntegrationType.USER)
    list_page = IntegrationsListPage(page)

    list_page.navigate_to(f"scope=user&type={DIAL}")

    list_page.should_have_scope_selected(SCOPE_USER)
    list_page.should_not_filter_by_type_in_url(DIAL)
    list_page.should_show_row(user_alias)
