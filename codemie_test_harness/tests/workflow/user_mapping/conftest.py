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

"""Fixtures for workflow-scoped user mapping API tests.

Covers: Per-workflow scope for personal integration settings.
"""

import logging

import pytest

from codemie_sdk.models.assistant import ToolKitDetails, ToolDetails
from codemie_sdk.models.integration import CredentialTypes
from codemie_sdk.models.workflow import WorkflowMode
from codemie_test_harness.tests.enums.tools import Toolkit, ProjectManagementTool
from codemie_test_harness.tests.test_data.user_mapping_test_data import SlotAssignment
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.yaml_utils import (
    AssistantModel,
    StateModel,
    WorkflowYamlModel,
    prepare_yaml_content,
)

logger = logging.getLogger(__name__)


@pytest.fixture(scope="function")
def workflow_scoped_mapping(client, assistant, workflow_with_assistant):
    """Create a workflow containing an assistant and a workflow-scoped user mapping.

    Pre-creates a workflow-scoped mapping row with an empty tools_config to establish
    the scope, then yields (assistant_obj, workflow_obj, mapping_response). Cleans up
    both the workflow-scoped and assistant-scoped records in teardown.
    """
    assistant_obj = assistant()
    workflow_obj = workflow_with_assistant(assistant_obj, "user mapping scope test")

    mapping_response = None
    try:
        mapping_response = client.assistants.save_user_mapping(
            assistant_id=assistant_obj["id"],
            tools_config=[],
            workflow_id=workflow_obj.id,
        )
    except Exception:
        pass

    yield assistant_obj, workflow_obj, mapping_response
    # DELETE /users/mapping returns 405; cascade cleanup happens via assistant deletion.


@pytest.fixture(scope="function")
def assistant_scoped_mapping(
    client, assistant_factory, workflow_with_assistant, jira_integration
):
    """Create an assistant-scoped user mapping using a Jira-enabled assistant.

    ``jira_integration`` is required: creating a Jira assistant fails integration
    validation when the user has no Jira integration.

    A generic assistant (no integration slots) produces a no-op save and
    has_assistant_scope_selection stays False. A Jira assistant with an
    explicit-none slot saves a real row — has_assistant_scope_selection=True.

    Explicit-none must be sent as ``integration_id=""`` (empty string), not an
    omitted field: the backend validator checks ``integration_id is None``, so an
    omitted value means "not set" (auto-lookup) while "" means "no integration".
    ``SlotAssignment`` encodes this wire format.

    Omitting ``workflow_id`` is what selects assistant scope on the wire;
    ``apply_to_assistant_scope`` is accepted but has no effect on its own.

    Yields (assistant_obj, workflow_obj, mapping_response). Cleans up via assistant deletion.
    """
    toolkits = [
        ToolKitDetails(
            toolkit=Toolkit.PROJECT_MANAGEMENT,
            tools=[ToolDetails(name=ProjectManagementTool.JIRA)],
        )
    ]
    assistant_obj = assistant_factory.create(toolkits=toolkits, shared=True)
    workflow_obj = workflow_with_assistant(assistant_obj, "assistant scope test")

    tools_config = [
        SlotAssignment(
            name=ProjectManagementTool.JIRA.value, explicit_none=True
        ).to_dict()
    ]
    mapping_response = client.assistants.save_user_mapping(
        assistant_id=assistant_obj.id,
        tools_config=tools_config,
        apply_to_assistant_scope=True,
    )

    yield assistant_obj, workflow_obj, mapping_response
    # DELETE /users/mapping returns 405; cascade cleanup happens via assistant deletion.


@pytest.fixture(scope="function")
def user_isolation_context(
    client,
    non_admin_user,
    admin_utils,
    project_utils,
    user_utils,
    integration_utils,
    assistant_utils,
    workflow_utils,
    default_llm,
):
    """Build everything the user-isolation test (S15) needs from scratch.

    User A is the main test ``client``; User B is a disposable non-admin user
    (``non_admin_user``). A fresh project with both users as members holds a Jira
    integration, a shared Jira assistant and a workflow using it. User A then saves
    an explicit-none selection at both workflow and assistant scope, so there is
    real data of A's that B must not see.

    Resources are cleaned up explicitly and in dependency order (workflow,
    assistant, integration, project) because the project cannot be deleted while
    it still contains them. DELETE /users/mapping returns 405; A's mapping rows
    go with the assistant.

    Yields ``(client_a, client_b, assistant_id, workflow_id)``.
    """
    _email, member_id, client_b = non_admin_user

    project_name = get_random_name()
    admin_utils.create_project(project_name)
    user_utils.assign_user_to_project(member_id, project_name)

    integration = assistant = workflow_obj = None
    try:
        integration = integration_utils.create_integration(
            credential_type=CredentialTypes.JIRA,
            credential_values=CredentialsManager.jira_credentials(),
            project_name=project_name,
        )
        assistant = assistant_utils.create_assistant(
            toolkits=[
                ToolKitDetails(
                    toolkit=Toolkit.PROJECT_MANAGEMENT,
                    tools=[ToolDetails(name=ProjectManagementTool.JIRA)],
                )
            ],
            shared=True,
            project_name=project_name,
        )
        workflow_yaml = WorkflowYamlModel(
            assistants=[
                AssistantModel(
                    id=assistant.name,
                    model=default_llm.base_name,
                    assistant_id=assistant.id,
                )
            ],
            states=[
                StateModel(
                    id=assistant.name,
                    assistant_id=assistant.name,
                    task="user isolation test",
                )
            ],
        )
        workflow_obj = workflow_utils.create_workflow(
            workflow_name=get_random_name(),
            workflow_type=WorkflowMode.SEQUENTIAL,
            shared=True,
            workflow_yaml=prepare_yaml_content(
                workflow_yaml.model_dump(exclude_none=True)
            ),
            project_name=project_name,
        )

        jira_slot = SlotAssignment(
            name=ProjectManagementTool.JIRA.value, explicit_none=True
        ).to_dict()
        client.assistants.save_user_mapping(
            assistant_id=assistant.id,
            tools_config=[jira_slot],
            workflow_id=workflow_obj.id,
        )
        client.assistants.save_user_mapping(
            assistant_id=assistant.id,
            tools_config=[jira_slot],
        )

        yield client, client_b, assistant.id, workflow_obj.id
    finally:
        for description, cleanup, resource in (
            ("workflow", workflow_utils.delete_workflow, workflow_obj),
            ("assistant", assistant_utils.delete_assistant, assistant),
            ("integration", integration_utils.delete_integration, integration),
        ):
            if resource is not None:
                try:
                    cleanup(resource)
                except Exception as e:
                    logger.error(f"Failed to delete {description}: {e}")
        try:
            project_utils.delete_project_with_all_members(project_name)
        except Exception as e:
            logger.error(f"Failed to delete project {project_name}: {e}")
