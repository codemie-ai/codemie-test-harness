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

"""UI tests for project display_name feature.

Covers:
  AC-4 — UI shows technical name as primary label with display_name as tooltip (TC-020; admin management page)
  AC-5 — projects without display_name fall back to technical name (no tooltip)
  AC-7 — create/edit modal includes display_name input with validation
  Entity pages — show technical project name; tooltip on hover shows display_name (TC-030 – TC-035)

Known coverage gap (TC-019 deferred):
  TC-019 — ProjectSelector dropdown shows display_name as primary label (AC-4, P1).
  Deferred: no POM written for ProjectSelectorComponent in this sprint.

All tests follow the E2E pattern:
  - API used for setup / teardown (project_utils / entity utils)
  - Browser used to assert UI behaviour only
"""

from __future__ import annotations

import pytest

from codemie_sdk.models.integration import CredentialTypes
from codemie_sdk.models.skill import SkillVisibility
from codemie_test_harness.tests.test_data.projects_test_data import (
    get_project_create_data,
    get_project_create_data_with_display_name,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_management_page import (
    ProjectManagementPage,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_modal_page import (
    ProjectModal,
)
from codemie_test_harness.tests.ui.pageobject.assistants.assistants_page import (
    AssistantsPage,
)
from codemie_test_harness.tests.ui.pageobject.datasources.datasource_page import (
    DataSourcePage,
)
from codemie_test_harness.tests.ui.pageobject.datasources.view_datasource_page import (
    ViewDatasourcePage,
)
from codemie_test_harness.tests.ui.pageobject.integrations.integrations_page import (
    IntegrationsPage,
)
from codemie_test_harness.tests.ui.pageobject.skills.skills_page import SkillsPage
from codemie_test_harness.tests.utils.constants import FILES_PATH
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager

# ── Shared constants ──────────────────────────────────────────────────────────

_DISPLAY_NAME = "Display Name For Test"
_TXT_FILE = str(FILES_PATH / "test.txt")

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="function")
def project_with_display_name(project_utils):
    """Create a project with display_name; delete in teardown."""
    base = get_project_create_data()
    created = project_utils.create_project(
        name=base["name"],
        description=base["description"],
        display_name=_DISPLAY_NAME,
    )
    yield created
    try:
        project_utils.delete_project(created.name)
    except Exception:
        pass


@pytest.fixture(scope="function")
def created_assistant(project_with_display_name, assistant_utils, default_llm):
    """Create an assistant in the display_name project; delete in teardown."""
    proj = project_with_display_name
    assistant = assistant_utils.create_assistant(
        llm_model_type=default_llm.base_name,
        project_name=proj.name,
    )
    yield assistant
    try:
        assistant_utils.delete_assistant(assistant)
    except Exception:
        pass


@pytest.fixture(scope="function")
def created_skill(project_with_display_name, skill_utils):
    """Create a skill in the display_name project; delete in teardown."""
    proj = project_with_display_name
    skill = skill_utils.create_skill(
        project_name=proj.name,
        visibility=SkillVisibility.PROJECT,
    )
    yield skill
    try:
        skill_utils.delete_skill(skill)
    except Exception:
        pass


@pytest.fixture(scope="function")
def created_integration(project_with_display_name, integration_utils):
    """Create a user integration in the display_name project; delete in teardown."""
    proj = project_with_display_name
    credential_values = CredentialsManager.gitlab_credentials()
    integration = integration_utils.create_user_integration(
        credential_type=CredentialTypes.GIT,
        credentials=credential_values,
        project_name=proj.name,
    )
    yield integration
    try:
        integration_utils.delete_integration(integration)
    except Exception:
        pass


@pytest.fixture(scope="function")
def created_datasource(project_with_display_name, datasource_utils):
    """Create a file datasource in the display_name project; delete in teardown."""
    proj = project_with_display_name
    datasource = datasource_utils.create_file_datasource(
        files=[_TXT_FILE],
        project_name=proj.name,
    )
    yield datasource
    try:
        datasource_utils.delete_datasource(datasource)
    except Exception:
        pass


# ── AC-7: Create modal — display_name input, auto-slug, validation ────────────


@pytest.mark.project
@pytest.mark.ui
def test_project_creation_modal_display_name_field(page):
    """TC-021/TC-024/TC-025: Create modal has display_name input, independent Name * field, and validates 150-char limit."""
    mgmt_page = ProjectManagementPage(page)
    modal = ProjectModal(page)

    mgmt_page.navigate_to()
    mgmt_page.click_create_project()

    modal.should_be_visible()
    modal.should_have_display_name_input()  # TC-021
    modal.fill_display_name("My Test Project Display Name")
    modal.should_have_technical_name_input()  # TC-024: Name * is a required primary field (no auto-slug from display_name)
    # The display_name input does NOT carry a maxlength HTML attribute; the 150-char
    # limit is enforced exclusively by Yup form validation. fill() replaces the value.
    modal.fill_display_name("X" * 151)
    modal.click_save()
    modal.should_show_display_name_validation_error()  # TC-025


# ── AC-4 / AC-5 / AC-7: Management page labels + edit modal ──────────────────


@pytest.mark.project
@pytest.mark.ui
def test_project_management_page_and_edit_modal(page, project):
    """TC-020/TC-022/TC-023: Management page shows display_name or technical name; edit modal prefills display_name."""
    data_with = get_project_create_data_with_display_name()
    created_with = project(
        name=data_with["name"],
        description=data_with["description"],
        display_name=data_with["display_name"],
    )
    data_without = get_project_create_data()
    created_without = project(
        name=data_without["name"], description=data_without["description"]
    )

    mgmt_page = ProjectManagementPage(page)
    modal = ProjectModal(page)

    mgmt_page.navigate_to()
    mgmt_page.should_see_project_technical_name_only(
        project_name=created_without.name
    )  # TC-023
    mgmt_page.should_see_project_display_name(
        project_name=created_with.name,
        display_name=data_with["display_name"],
    )  # TC-020
    mgmt_page.click_edit_project(created_with.name)
    modal.should_have_display_name_value(data_with["display_name"])  # TC-022
    modal.should_have_technical_name_disabled()  # TC-022


# ── Defect tests: entities show technical name instead of display_name ────────


@pytest.mark.project
@pytest.mark.assistant
@pytest.mark.ui
def test_assistant_detail_shows_project_display_name(
    page, project_with_display_name, created_assistant
):
    """TC-030: AssistantViewPage Overview shows technical name; hovering Project field shows display_name tooltip."""
    assistants_page = AssistantsPage(page)
    assistants_page.search_assistants(created_assistant.name)
    view_page = assistants_page.open_assistant_details(created_assistant.name)
    view_page.should_show_project_display_name(_DISPLAY_NAME)


@pytest.mark.project
@pytest.mark.skill
@pytest.mark.ui
def test_skill_detail_shows_project_display_name(
    page, project_with_display_name, created_skill
):
    """TC-031: Skill detail page shows technical name; hovering Project field shows display_name tooltip."""
    skills_page = SkillsPage(page)
    skills_page.navigate_to()
    skills_page.switch_to_project_skills_tab()
    skills_page.search_skill(created_skill.name)
    detail_page = skills_page.open_skill_details(created_skill.name)
    detail_page.should_show_project_display_name(_DISPLAY_NAME)


@pytest.mark.project
@pytest.mark.datasource
@pytest.mark.ui
def test_datasource_detail_shows_project_display_name(
    page, project_with_display_name, created_datasource
):
    """TC-033: Datasource view page shows technical name; hovering Project field shows display_name tooltip."""
    ds_page = DataSourcePage(page)
    view_page = ViewDatasourcePage(page)
    ds_page.navigate_to()
    ds_page.search_for(created_datasource.name)
    ds_page.click_datasource_row_by_name(created_datasource.name)
    view_page.should_show_project_display_name(_DISPLAY_NAME)


@pytest.mark.project
@pytest.mark.integration
@pytest.mark.ui
def test_integrations_table_shows_project_display_name(
    page, project_with_display_name, created_integration
):
    """TC-034: Integrations list table shows technical name; hovering project cell shows display_name tooltip."""
    integrations_page = IntegrationsPage(page)
    integrations_page.navigate_to()
    integrations_page.search_integrations(created_integration.alias)
    integrations_page.should_show_project_display_name_in_table_row(
        created_integration.alias, _DISPLAY_NAME
    )


@pytest.mark.project
@pytest.mark.datasource
@pytest.mark.ui
def test_datasources_table_shows_project_display_name(
    page, project_with_display_name, created_datasource
):
    """TC-035: Datasources list table shows technical name; hovering project cell shows display_name tooltip."""
    ds_page = DataSourcePage(page)
    ds_page.navigate_to()
    ds_page.should_show_project_display_name_in_table_row(
        created_datasource.name, _DISPLAY_NAME
    )
