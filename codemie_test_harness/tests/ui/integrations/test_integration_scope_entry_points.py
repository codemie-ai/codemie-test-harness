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

"""UI tests for the other entry points of the integration form: the admin project page, the
quick-create popup and the Schedulers forms. Runs as the harness admin (default login)."""

import pytest

from codemie_test_harness.tests.ui.pageobject.administration.project_details_page import (
    ProjectDetailsPage,
)
from codemie_test_harness.tests.ui.pageobject.datasources.create_edit_datasource_page import (
    CreateEditDatasourcePage,
)
from codemie_test_harness.tests.ui.pageobject.integrations.integration_form_page import (
    IntegrationFormPage,
)
from codemie_test_harness.tests.ui.pageobject.integrations.schedulers_page import (
    SchedulersPage,
)
from codemie_test_harness.tests.ui.test_data.datasource_test_data import (
    DataSourceFilterType,
)
from codemie_test_harness.tests.ui.test_data.unified_integrations_ui_test_data import (
    CREATED_TOAST,
    SCHEDULER_KINDS,
    SCOPE_PROJECT,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name


@pytest.fixture
def form_opened_from_project_page(page, project):
    """The New Integration form, opened from the Integrations tab of a fresh project.

    Returns the project details page, the form page and the project name.
    """
    created_project = project()
    details_page = ProjectDetailsPage(page)
    form_page = IntegrationFormPage(page)
    details_page.navigate_to(created_project.name)
    details_page.open_integrations_tab()
    details_page.click_create_integration()
    form_page.wait_until_open()
    return details_page, form_page, created_project.name


# @case unified-integrations-list_TC_018
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.oss_standalone
def test_form_from_the_project_page_is_locked_and_cancel_returns_to_the_project(
    form_opened_from_project_page,
):
    details_page, form_page, project_name = form_opened_from_project_page

    form_page.should_have_scope_locked_to(SCOPE_PROJECT)
    form_page.should_have_project_locked_to(project_name)

    form_page.cancel()

    details_page.should_be_on_integrations_tab(project_name)


# @case unified-integrations-list_TC_018
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.oss_standalone
def test_back_from_the_form_of_the_project_page_returns_to_the_project(
    form_opened_from_project_page,
):
    details_page, form_page, project_name = form_opened_from_project_page

    form_page.go_back()

    details_page.should_be_on_integrations_tab(project_name)


# @case unified-integrations-list_TC_018
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.oss_standalone
def test_saving_the_form_from_the_project_page_returns_to_the_project_tab(
    page, project, integration_utils, scoped_integrations
):
    created_project = project()
    alias = scoped_integrations.track_alias(integration_utils, get_random_name())
    details_page = ProjectDetailsPage(page)
    form_page = IntegrationFormPage(page)
    details_page.navigate_to(created_project.name)
    details_page.open_integrations_tab()
    details_page.click_create_integration()
    form_page.wait_until_open()
    form_page.fill_alias(alias)

    form_page.save()

    details_page.should_show_toast(CREATED_TOAST)
    details_page.should_be_on_integrations_tab(created_project.name)


# @case unified-integrations-list_TC_019
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.oss_standalone
def test_quick_create_popup_shows_no_scope_field(page):
    create_page = CreateEditDatasourcePage(page)
    dialog = create_page.create_user_integration_dialog
    create_page.navigate_to()
    create_page.select_datasource_type(DataSourceFilterType.GOOGLE)
    create_page.should_see_add_integration_button()

    create_page.click_add_integration_button()

    dialog.should_be_visible()
    dialog.should_have_no_scope_field()


# @case unified-integrations-list_TC_019
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.parametrize(
    "kind", SCHEDULER_KINDS, ids=lambda kind: f"{kind.lower()}_scheduler"
)
@pytest.mark.oss_standalone
def test_schedulers_forms_show_no_scope_field(page, kind):
    schedulers_page = SchedulersPage(page)
    schedulers_page.navigate_to()

    schedulers_page.open_scheduler_form(kind)

    schedulers_page.should_show_form(kind)
    schedulers_page.should_have_no_scope_field()
