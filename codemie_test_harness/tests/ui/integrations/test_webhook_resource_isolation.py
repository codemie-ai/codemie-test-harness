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
UI tests for Project-scoped resource dropdown isolation.

Covers:
- TC-06: The Resource dropdown shows only resources that belong to the selected project;
  resources from other projects are not visible.

Setup (API-side):
- Creates two separate projects.
- Creates one Assistant per project.
- Creates one Workflow per project.
- Creates one file-backed Datasource per project.

The test navigates the Webhook creation form, selects each project in turn, and for
each Resource Type (Assistant, Workflow, Datasource) asserts that:
  - The resource from the active project IS visible in the dropdown.
  - The resource from the other project is NOT visible.

AC-13, AC-14: Resource dropdown shows entity names (not GUIDs), scoped to the project.
"""

import pytest
from codemie_sdk.models.workflow import WorkflowMode
from playwright.sync_api import Page, expect

from codemie_test_harness.tests.ui.pageobject.integrations.create_integration_page import (
    CreateIntegrationPage,
)
from codemie_test_harness.tests.ui.pageobject.integrations.integrations_page import (
    IntegrationsPage,
)
from codemie_test_harness.tests.ui.test_data.integration_test_data import (
    IntegrationTestDataFactory,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.constants import FILES_PATH
from codemie_test_harness.tests.test_data.file_test_data import file_test_data
from codemie_test_harness.tests.utils.yaml_utils import (
    AssistantModel as WfAssistantModel,
    StateModel as WfStateModel,
    WorkflowYamlModel,
    prepare_yaml_content,
)


# ---------------------------------------------------------------------------
# Fixture: full resource setup for both projects
# ---------------------------------------------------------------------------


@pytest.fixture
def tc06_resources(
    project,
    assistant_factory,
    workflow_utils,
    datasource_utils,
    default_llm,
    default_embedding_llm,
):
    """Create two projects, each with one assistant, one workflow, and one datasource.

    Yields a tuple:
        (project1, project2, asst1, asst2, wf1, wf2, ds1, ds2)

    Cleanup of workflows and datasources is performed in a try/finally block inside
    the fixture; projects and assistants are cleaned up by their own factory fixtures.
    """
    project1 = project()
    project2 = project()

    # Assistants — cleaned up by assistant_factory fixture teardown.
    asst1 = assistant_factory.create(
        llm_model_type=default_llm.base_name,
        project_name=project1.name,
        assistant_name=f"tc06-asst-p1-{get_random_name()}",
    )
    asst2 = assistant_factory.create(
        llm_model_type=default_llm.base_name,
        project_name=project2.name,
        assistant_name=f"tc06-asst-p2-{get_random_name()}",
    )

    # Workflows and datasources — need explicit cleanup.
    created_workflows = []
    created_datasources = []

    # Minimal single-assistant workflow YAML required by WorkflowUtils.create_workflow().
    # The id references are internal to the workflow graph definition; they do not
    # correspond to real assistants on the server.
    _WF_ASSISTANT_ID = "tc06_helper"
    _wf_assistant = WfAssistantModel(
        id=_WF_ASSISTANT_ID,
        model=default_llm.base_name,
        system_prompt="Helper assistant for TC-06 resource-isolation fixture.",
    )
    _wf_state = WfStateModel(id=_WF_ASSISTANT_ID, assistant_id=_WF_ASSISTANT_ID)
    _wf_yaml = prepare_yaml_content(
        WorkflowYamlModel(assistants=[_wf_assistant], states=[_wf_state]).model_dump(
            exclude_none=True
        )
    )

    try:
        wf1 = workflow_utils.create_workflow(
            workflow_name=f"tc06-wf-p1-{get_random_name()}",
            workflow_type=WorkflowMode.SEQUENTIAL,
            workflow_yaml=_wf_yaml,
            project_name=project1.name,
        )
        created_workflows.append(wf1)

        wf2 = workflow_utils.create_workflow(
            workflow_name=f"tc06-wf-p2-{get_random_name()}",
            workflow_type=WorkflowMode.SEQUENTIAL,
            workflow_yaml=_wf_yaml,
            project_name=project2.name,
        )
        created_workflows.append(wf2)

        # Use the same small CSV test file used by the shared file_datasource fixture.
        test_file = str(FILES_PATH / file_test_data[2][0])
        embedding_model = default_embedding_llm.base_name

        ds1 = datasource_utils.create_file_datasource(
            name=f"tc_ds_pa_{get_random_name()}",
            description="[Autotest] TC-06 project1 datasource",
            files=[test_file],
            embeddings_model=embedding_model,
            project_name=project1.name,
        )
        created_datasources.append(ds1)

        ds2 = datasource_utils.create_file_datasource(
            name=f"tc_ds_pb_{get_random_name()}",
            description="[Autotest] TC-06 project2 datasource",
            files=[test_file],
            embeddings_model=embedding_model,
            project_name=project2.name,
        )
        created_datasources.append(ds2)

        yield project1, project2, asst1, asst2, wf1, wf2, ds1, ds2

    finally:
        for wf in created_workflows:
            try:
                workflow_utils.delete_workflow(wf)
            except Exception:
                pass
        for ds in created_datasources:
            try:
                datasource_utils.delete_datasource(ds)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _assert_resource_visible_and_other_hidden(
    create_integration_page: CreateIntegrationPage,
    page: Page,
    resource_type_label: str,
    visible_name: str,
    hidden_name: str,
):
    """Select a Resource Type, open the dropdown, and assert visibility of options.

    Args:
        resource_type_label: UI label for the resource type ('Assistant', 'Workflow',
            'Datasource').
        visible_name: Name of the resource that SHOULD be visible in the dropdown.
        hidden_name: Name of the resource that should NOT be visible.
    """
    create_integration_page.select_resource_type(resource_type_label)

    # Dropdown becomes enabled after Resource Type is selected.
    create_integration_page.should_have_resource_dropdown_enabled()

    # Open the dropdown.
    create_integration_page.resource_dropdown.click()

    # Assert target resource is visible.
    expect(page.get_by_role("option", name=visible_name)).to_be_visible(timeout=5000)

    # Assert other-project resource is NOT visible.
    expect(page.get_by_role("option", name=hidden_name)).not_to_be_visible()

    # Close dropdown without selecting.
    page.keyboard.press("Escape")

    # Reset resource_type so next iteration starts fresh.
    # Selecting a different type clears the resource dropdown (handled by the useEffect).
    page.wait_for_timeout(300)


# ---------------------------------------------------------------------------
# TC-06
# ---------------------------------------------------------------------------


@pytest.mark.sanity
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.datasource
def test_resource_dropdown_shows_only_project_scoped_resources(
    page: Page,
    tc06_resources,
):
    """TC-06 — Resource dropdown is isolated per project.

    AC-13, AC-14:
    - Selecting project1 in the Webhook form shows only project1 resources.
    - Selecting project2 shows only project2 resources.
    - Applies to all three Resource Types: Assistant, Workflow, Datasource.
    """
    (
        project1,
        project2,
        asst1,
        asst2,
        wf1,
        wf2,
        ds1,
        ds2,
    ) = tc06_resources

    integrations_page = IntegrationsPage(page)
    create_integration_page = CreateIntegrationPage(page)

    integrations_page.navigate_to()
    integrations_page.navigate_to_user_integration_creation()

    # ----------------------------------------------------------------
    # Round 1 — Select project1; verify project1 resources visible,
    #            project2 resources NOT visible.
    # ----------------------------------------------------------------
    test_data_p1 = IntegrationTestDataFactory.webhook_integration()
    test_data_p1.project = project1.name

    create_integration_page.select_project(project1.name)
    create_integration_page.fill_alias(test_data_p1.alias)
    create_integration_page.select_credential_type(test_data_p1.credential_type)

    # Before selecting Resource Type, dropdown must be disabled.
    create_integration_page.should_have_resource_dropdown_disabled()

    # Assert each Resource Type is project-scoped.
    for res_type, p1_name, p2_name in [
        ("Assistant", asst1.name, asst2.name),
        ("Workflow", wf1.name, wf2.name),
        ("Datasource", ds1.name, ds2.name),
    ]:
        _assert_resource_visible_and_other_hidden(
            create_integration_page=create_integration_page,
            page=page,
            resource_type_label=res_type,
            visible_name=p1_name,
            hidden_name=p2_name,
        )

    # ----------------------------------------------------------------
    # Round 2 — Navigate to a fresh form for project2; verify inverse.
    # ----------------------------------------------------------------
    integrations_page.navigate_to()
    integrations_page.navigate_to_user_integration_creation()

    test_data_p2 = IntegrationTestDataFactory.webhook_integration()
    test_data_p2.project = project2.name

    create_integration_page.select_project(project2.name)
    create_integration_page.fill_alias(test_data_p2.alias)
    create_integration_page.select_credential_type(test_data_p2.credential_type)

    create_integration_page.should_have_resource_dropdown_disabled()

    for res_type, p2_name, p1_name in [
        ("Assistant", asst2.name, asst1.name),
        ("Workflow", wf2.name, wf1.name),
        ("Datasource", ds2.name, ds1.name),
    ]:
        _assert_resource_visible_and_other_hidden(
            create_integration_page=create_integration_page,
            page=page,
            resource_type_label=res_type,
            visible_name=p2_name,
            hidden_name=p1_name,
        )
