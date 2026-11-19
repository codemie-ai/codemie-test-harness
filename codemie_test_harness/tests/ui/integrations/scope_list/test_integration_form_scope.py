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

"""UI tests for the New Integration form as a project admin: Scope first and pre-selected, the
type-driven scope switch and the return to the list after saving."""

import pytest

from codemie_test_harness.tests.ui.pageobject.integrations.integration_form_page import (
    IntegrationFormPage,
)
from codemie_test_harness.tests.ui.pageobject.integrations.integrations_list_page import (
    IntegrationsListPage,
)
from codemie_test_harness.tests.ui.test_data.unified_integrations_ui_test_data import (
    DIAL,
    DIAL_SWITCH_NOTE,
    GOOGLE_OAUTH,
    GOOGLE_OAUTH_SWITCH_NOTE,
    HIDDEN_PROJECT_TOAST,
    NEW_INTEGRATION_FORM_SCOPE_BY_LIST_SCOPE,
    SAME_VIEW_TOAST,
    SAVED_TOAST,
    SCOPE_ALL,
    SCOPE_PROJECT,
    SCOPE_USER,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name


# @case unified-integrations-list_TC_013
@pytest.mark.parametrize(
    "list_scope",
    list(NEW_INTEGRATION_FORM_SCOPE_BY_LIST_SCOPE),
    ids=lambda label: f"list_scope_{label.lower()}",
)
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.oss_standalone
def test_create_opens_one_form_with_scope_first_taken_from_the_list_scope(
    page, list_scope
):
    list_page = IntegrationsListPage(page)
    form_page = IntegrationFormPage(page)
    list_page.navigate_to()
    list_page.select_scope(list_scope)

    list_page.click_new_integration()

    form_page.wait_until_open()
    form_page.should_show_heading()
    form_page.should_have_scope_first()
    form_page.should_have_scope_selected(
        NEW_INTEGRATION_FORM_SCOPE_BY_LIST_SCOPE[list_scope]
    )


# @case unified-integrations-list_TC_013
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.oss_standalone
def test_form_opened_with_scope_in_the_address_preselects_it(page):
    form_page = IntegrationFormPage(page)

    form_page.navigate_to("scope=user")

    form_page.should_have_scope_selected(SCOPE_USER)


# @case unified-integrations-list_TC_016
@pytest.mark.integration
@pytest.mark.ui
def test_picking_dial_switches_scope_to_project_and_google_oauth_switches_back(page):
    form_page = IntegrationFormPage(page)
    form_page.navigate_to("scope=user")

    form_page.pick_credential_type(DIAL)

    form_page.should_have_scope_selected(SCOPE_PROJECT)
    form_page.should_show_note(DIAL_SWITCH_NOTE)

    form_page.pick_credential_type(GOOGLE_OAUTH)

    form_page.should_have_scope_selected(SCOPE_USER)
    form_page.should_show_note(GOOGLE_OAUTH_SWITCH_NOTE)


# @case unified-integrations-list_TC_017
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.oss_standalone
def test_saved_user_integration_keeps_the_filters_and_is_highlighted(
    page, project_admin_integrations, scoped_integrations
):
    alias = scoped_integrations.track_alias(
        project_admin_integrations, get_random_name()
    )
    list_page = IntegrationsListPage(page)
    form_page = IntegrationFormPage(page)
    list_page.navigate_to()
    list_page.select_scope(SCOPE_USER)
    list_page.click_new_integration()
    form_page.wait_until_open()
    form_page.fill_alias(alias)

    form_page.save()

    list_page.should_show_toast(SAVED_TOAST)
    list_page.should_show_toast(SAME_VIEW_TOAST)
    list_page.should_have_scope_selected(SCOPE_USER)
    list_page.should_show_scope_badge(alias, SCOPE_USER)
    list_page.should_mark_row_as_just_saved(alias)


# @case unified-integrations-list_TC_017
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.oss_standalone
def test_saved_project_integration_hidden_by_filters_is_shown_by_the_toast_action(
    page, default_project_member, project_admin_integrations, scoped_integrations
):
    alias = scoped_integrations.track_alias(
        project_admin_integrations, get_random_name()
    )
    list_page = IntegrationsListPage(page)
    form_page = IntegrationFormPage(page)
    list_page.navigate_to()
    list_page.select_scope(SCOPE_USER)
    list_page.click_new_integration()
    form_page.wait_until_open()
    form_page.fill_alias(alias)
    form_page.select_scope(SCOPE_PROJECT)
    form_page.pick_project(default_project_member.project_a)

    form_page.save()

    list_page.should_show_toast(HIDDEN_PROJECT_TOAST)
    list_page.should_offer_show_all_scopes_and_types()
    list_page.should_not_show_row(alias)

    list_page.click_show_all_scopes_and_types()

    list_page.should_have_scope_selected(SCOPE_ALL)
    list_page.should_show_scope_badge(alias, SCOPE_PROJECT)
