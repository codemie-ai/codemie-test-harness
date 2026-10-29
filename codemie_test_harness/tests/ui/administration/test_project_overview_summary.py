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

"""UI tests for the Project Details page's Overview tab summary.

Covers:
    TC-01  Integrations card count matches real project-level integrations;
           "View" navigates to the project's Integrations tab with a matching
           row count.

The Chargeback / Routing impact checks that used to live here are in
ui/budgets/test_project_details_overview_sections.py.

TC-01 runs against a disposable project (the API caller becomes that
project's admin, which is required for the Overview tab's Budgets/
Integrations tabs and summary cards to render at all) — never against the
shared "codemie" project. It uses a plain project with no budget group
(`disposable_project`): confirmed via live inspection that the Budgets/
Integrations tabs and the Financial summary card render purely from
project-admin status, with no budget required. This matters because creating
a budget group (via `AdminProjectBudgetUtils.create_budget_group`) auto-creates
a hidden system-level LiteLLM project integration, which would otherwise
inflate the Integrations count by 1 beyond what the test explicitly creates.

Navigation path:
    /settings/administration/projects/{name} → Overview tab (default)
"""

import logging

import pytest
from codemie_sdk.models.integration import CredentialTypes

from codemie_test_harness.tests.ui.pageobject.administration.project_details_page import (
    ProjectDetailsPage,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager

logger = logging.getLogger(__name__)


@pytest.fixture(scope="function")
def project_integrations(integration_utils):
    """Create N project-level integrations via the SDK for a given project.

    Uses the FileSystem credential type with auto-generated credentials — the
    cheapest credential shape that requires no externally-configured secrets,
    since these tests only need the integrations to exist and be counted, not
    to actually connect to anything.
    """
    created_integrations = []

    def _make(project_name: str, count: int):
        made = []
        for _ in range(count):
            integration = integration_utils.create_project_integration(
                credential_type=CredentialTypes.FILESYSTEM,
                credentials=CredentialsManager.file_system_credentials(),
                project_name=project_name,
            )
            created_integrations.append(integration)
            made.append(integration)
        return made

    yield _make

    for integration in created_integrations:
        try:
            integration_utils.delete_integration(integration)
        except Exception as e:
            logger.warning(f"Failed to delete integration {integration.alias}: {e}")


@pytest.mark.project
@pytest.mark.integration
@pytest.mark.ui
def test_integrations_card_count_matches_and_view_navigates_to_integrations_tab(
    page,
    disposable_project,
    project_integrations,
):
    """Overview tab's Integrations card count equals the real number of
    project-level integrations; clicking its "View" button navigates to the
    project's Integrations tab, which lists the same number of rows.
    """
    integrations_count = 3
    test_project = disposable_project()
    project_integrations(test_project.name, integrations_count)

    details_page = ProjectDetailsPage(page)
    details_page.navigate_to(test_project.name)

    details_page.should_have_integrations_count(integrations_count)

    details_page.click_view_integrations()
    details_page.should_be_on_integrations_tab(test_project.name)
    details_page.should_have_integrations_table_row_count(integrations_count)
