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

"""
UI test for changing the project of an existing integration.

The integration is created and verified through the API; the browser performs the
edit: pick another project, confirm the 'Change integration project?' modal, save.
"""

from collections import namedtuple

import pytest
from hamcrest import assert_that, equal_to, not_none
from playwright.sync_api import Page

from codemie_sdk.models.integration import CredentialTypes, IntegrationType
from codemie_test_harness.tests.ui.pageobject.integrations.edit_integration_page import (
    EditIntegrationPage,
)
from codemie_test_harness.tests.ui.pageobject.integrations.integrations_page import (
    IntegrationsPage,
)
from codemie_test_harness.tests.ui.test_data.integration_test_data import (
    IntegrationTestDataFactory,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager

IntegrationToMove = namedtuple("IntegrationToMove", "source target integration")


@pytest.fixture
def project_integration_to_move(project, integration_utils):
    """A project integration in a fresh source project plus an empty target project."""
    source = project()
    target = project()
    integration = integration_utils.create_integration(
        credential_type=CredentialTypes.GIT,
        credential_values=CredentialsManager.gitlab_credentials(),
        setting_type=IntegrationType.PROJECT,
        project_name=source.name,
    )
    yield IntegrationToMove(source, target, integration)
    try:
        integration_utils.delete_integration_by_id(
            integration.id, IntegrationType.PROJECT
        )
    except Exception:
        pass


@pytest.mark.gitlab
@pytest.mark.integration
@pytest.mark.ui
def test_edit_integration_change_project_after_confirmation(
    page: Page, project_integration_to_move, integration_utils
):
    # @case integration-project-change_TC_001
    """Project dropdown is enabled on edit; after choosing another project the confirmation modal
    warns about the source project and, once confirmed, the integration is saved in the new project."""
    source, target, integration = project_integration_to_move

    edit_integration_page = EditIntegrationPage(page)
    edit_integration_page.navigate_to_edit_project_integration(
        project_name=source.name,
        credential_type=CredentialTypes.GIT.value,
        alias=integration.alias,
    )
    edit_integration_page.should_be_on_edit_project_integration_page()
    edit_integration_page.should_have_project_selector_enabled()

    edit_integration_page.change_project(target.name)
    edit_integration_page.should_have_project_selected(target.name)
    edit_integration_page.save_changes()
    edit_integration_page.should_show_project_change_confirmation(source.name)
    edit_integration_page.confirm_project_change()

    integrations_page = IntegrationsPage(page)
    integrations_page.should_see_message(
        IntegrationTestDataFactory.success_messages["integration_updated"]
    )

    moved = integration_utils.get_integration_by_id(
        integration.id, IntegrationType.PROJECT
    )
    assert_that(moved, not_none(), "Integration is missing after the project change.")
    assert_that(
        moved.project_name,
        equal_to(target.name),
        "Integration was not saved in the project chosen in the edit form.",
    )
    assert_that(moved.alias, equal_to(integration.alias))
