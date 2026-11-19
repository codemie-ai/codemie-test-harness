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

"""UI tests for the edit page of the unified Integrations list: Scope is read-only and save and
delete act on the integration's own scope. Rows are seeded and checked through the API."""

import pytest
from hamcrest import assert_that, equal_to, is_, none, not_

from codemie_sdk.models.integration import IntegrationType
from codemie_test_harness.tests.ui.pageobject.integrations.integration_form_page import (
    IntegrationFormPage,
)
from codemie_test_harness.tests.ui.pageobject.integrations.integrations_list_page import (
    IntegrationsListPage,
)
from codemie_test_harness.tests.ui.test_data.unified_integrations_ui_test_data import (
    DELETED_TOAST,
    SCOPE_PROJECT,
    SCOPE_USER,
    UPDATED_TOAST,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name


# @case unified-integrations-list_TC_020
@pytest.mark.integration
@pytest.mark.ui
def test_edit_page_shows_scope_read_only_and_save_and_delete_act_on_that_scope_only(
    page,
    project_admin_user,
    default_project_member,
    project_admin_integrations,
    scoped_integrations,
):
    user_alias = get_random_name()
    project_alias = get_random_name()
    user_row = scoped_integrations.create(
        project_admin_integrations,
        IntegrationType.USER,
        project_admin_user.email,
        user_alias,
    )
    project_row = scoped_integrations.create(
        project_admin_integrations,
        IntegrationType.PROJECT,
        default_project_member.project_a,
        project_alias,
    )
    new_alias = get_random_name()
    list_page = IntegrationsListPage(page)
    form_page = IntegrationFormPage(page)
    list_page.navigate_to()

    list_page.open_row_menu_item(user_alias, "Edit")

    form_page.should_show_edit_heading(SCOPE_USER)
    form_page.should_have_scope_locked_to(SCOPE_USER)

    form_page.fill_alias(new_alias)
    form_page.save()

    list_page.should_show_toast(UPDATED_TOAST)
    list_page.should_show_row(new_alias)
    assert_that(
        project_admin_integrations.get_integration_by_id(
            user_row.id, IntegrationType.USER
        ).alias,
        equal_to(new_alias),
        "The edited user integration kept its old alias",
    )
    assert_that(
        project_admin_integrations.get_integration_by_id(
            project_row.id, IntegrationType.PROJECT
        ).alias,
        equal_to(project_alias),
        "Saving the user integration changed the project integration",
    )

    list_page.open_row_menu_item(project_alias, "Edit")

    form_page.should_show_edit_heading(SCOPE_PROJECT)
    form_page.should_have_scope_locked_to(SCOPE_PROJECT)

    form_page.cancel()
    list_page.delete_row(project_alias)

    list_page.should_show_toast(DELETED_TOAST)
    list_page.should_not_show_row(project_alias)
    assert_that(
        project_admin_integrations.get_integration_by_id(
            project_row.id, IntegrationType.PROJECT
        ),
        is_(none()),
        "The project integration was not deleted",
    )
    assert_that(
        project_admin_integrations.get_integration_by_id(
            user_row.id, IntegrationType.USER
        ),
        is_(not_(none())),
        "Deleting the project integration removed the user integration",
    )
