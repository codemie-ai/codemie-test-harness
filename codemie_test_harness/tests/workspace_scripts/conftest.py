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

"""Fixtures for workspace-script tests."""

import uuid
from typing import Optional

import pytest
from codemie_sdk.models.assistant import ToolDetails, ToolKitDetails
from codemie_sdk.models.integration import CredentialTypes
from codemie_sdk.models.workflow import WorkflowMode

from codemie_test_harness.tests.enums.tools import AgentWorkspaceTool, Toolkit

from codemie_test_harness.tests.test_data.marketplace_test_data import (
    COMPLETE_CATEGORIES,
)
from codemie_test_harness.tests.test_data.workspace_script_test_data import (
    FEATURE_COMPONENT_ID,
)
from codemie_test_harness.tests.utils.skill_utils import SkillsUtils
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.integration_utils import IntegrationUtils
from codemie_test_harness.tests.utils.workspace_script_utils import (
    parse_file_token,
    unique_script_name,
    upload_text_file,
)
from codemie_test_harness.tests.utils.yaml_utils import (
    WorkflowYamlModel,
    prepare_yaml_content,
)


@pytest.fixture(scope="module", autouse=True)
def require_script_tool_calling(resolver_runtime_capabilities):
    """Skip the module when the environment has the workspace script bridge switched off."""
    if not resolver_runtime_capabilities.get(FEATURE_COMPONENT_ID):
        pytest.skip(f"{FEATURE_COMPONENT_ID} is disabled in this environment")


@pytest.fixture(scope="module")
def create_script_workflow(workflow_utils):
    """Factory ``(tools, states, assistants=None) -> workflow``; every workflow is deleted at module end."""
    created = []

    def _create(tools, states, assistants=None):
        workflow_yaml = WorkflowYamlModel(
            enable_summarization_node=False,
            tools=tools,
            assistants=assistants or [],
            states=states,
        )
        workflow = workflow_utils.create_workflow(
            workflow_name=get_random_name(),
            workflow_type=WorkflowMode.SEQUENTIAL,
            shared=True,
            workflow_yaml=prepare_yaml_content(
                workflow_yaml.model_dump(exclude_none=True)
            ),
        )
        created.append(workflow)
        return workflow

    yield _create
    for workflow in created:
        workflow_utils.delete_workflow(workflow)


@pytest.fixture(scope="module")
def upload_script(client):
    """Factory ``(content, prefix="script") -> (script_name, file_url)``."""

    def _upload(content: str, prefix: str = "script", uploader=None):
        script_name = unique_script_name(prefix)
        file_url = upload_text_file(uploader or client, script_name, content)
        return script_name, file_url

    return _upload


@pytest.fixture(scope="module")
def own_file_owner(client):
    """Id under which the caller's uploaded files are stored (the owner part of a file reference)."""
    file_url = upload_text_file(client, unique_script_name("owner"), "owner probe")
    return parse_file_token(file_url)[1]


@pytest.fixture(scope="session")
def jira_user_integration(client):
    """One USER-type Jira integration of the running user, shared by all tests of the run.

    A single integration for the whole run keeps tests that run side by side from deleting the
    integration another test is calling through."""
    integration_utils = IntegrationUtils(client)
    integration = integration_utils.create_user_integration(
        CredentialTypes.JIRA, CredentialsManager.jira_credentials()
    )
    yield integration
    integration_utils.delete_integration(integration)


@pytest.fixture(scope="session")
def jira_user_integration_runner(regular_client):
    """One USER-type Jira integration of the regular (non-creator) test user, shared by the run.

    Mirrors ``jira_user_integration`` but for ``regular_client`` — lets a test prove the
    running user's own automatic lookup still serves a tool_access entry that pins no alias,
    even on a workflow a different user created and published globally."""
    integration_utils = IntegrationUtils(regular_client)
    integration = integration_utils.create_user_integration(
        CredentialTypes.JIRA, CredentialsManager.jira_credentials()
    )
    yield integration
    integration_utils.delete_integration(integration)


@pytest.fixture
def publish_workflow_as_global(workflow_utils):
    """Factory ``(workflow_id, categories=None) -> dict``; publishes a workflow to the
    marketplace, which is the only way the public API sets ``is_global=True``.

    Unpublishes every workflow it published at teardown, so ``is_global`` reverts even
    when the test fails.
    """
    published_ids: list[str] = []

    def _publish(workflow_id: str, categories: Optional[list[str]] = None) -> dict:
        response = workflow_utils.publish_workflow_to_marketplace(
            workflow_id, categories or [COMPLETE_CATEGORIES]
        )
        published_ids.append(workflow_id)
        return response

    yield _publish
    for workflow_id in published_ids:
        try:
            workflow_utils.unpublish_workflow_from_marketplace(workflow_id)
        except Exception:
            pass


@pytest.fixture
def script_bridge_disabled(customer_config_utils):
    """Switch the bridge off for one test and restore the environment's own value afterwards."""
    declaration = customer_config_utils.get_declaration(FEATURE_COMPONENT_ID)
    if declaration["overridden"]:
        pytest.skip(
            f"{FEATURE_COMPONENT_ID} already has an admin override; not changing it"
        )
    original = declaration["value"]
    customer_config_utils.save_setting(
        FEATURE_COMPONENT_ID, {**original, "enabled": False}
    )
    yield
    customer_config_utils.reset_setting(FEATURE_COMPONENT_ID)
    restored = customer_config_utils.get_declaration(FEATURE_COMPONENT_ID)
    assert restored["value"]["enabled"] == original["enabled"]


@pytest.fixture
def create_skill_with_bundle(skill_utils):
    """Factory ``(bundle, name=None, owner=None) -> skill``; every skill is deleted at teardown.

    ``bundle`` is a list of ``BundleFile``. ``owner`` is the client that creates the skill
    (default: the running user)."""
    created = []

    def _create(bundle, name=None, owner=None):
        utils = SkillsUtils(owner) if owner is not None else skill_utils
        skill = utils.create_skill_with_files(
            [bundle_file.payload() for bundle_file in bundle], skill_name=name
        )
        created.append((utils, skill.id))
        return skill

    yield _create
    for utils, skill_id in created:
        try:
            utils.delete_skill_by_id(skill_id)
        except Exception:
            pass


@pytest.fixture
def create_skill_assistant(default_llm, assistant_utils, skill_utils):
    """Factory ``(skills=(), tool_names=(execute_workspace_script,)) -> assistant``.

    The assistant gets the workspace toolkit with ``tool_names`` (no toolkit when empty) and every
    skill of ``skills`` attached; it is deleted at teardown."""
    created = []

    def _create(
        skills=(), tool_names=(AgentWorkspaceTool.EXECUTE_WORKSPACE_SCRIPT.value,)
    ):
        toolkits = (
            [
                ToolKitDetails(
                    toolkit=Toolkit.AGENT_WORKSPACE,
                    tools=[ToolDetails(name=tool_name) for tool_name in tool_names],
                )
            ]
            if tool_names
            else []
        )
        assistant = assistant_utils.create_assistant(
            llm_model_type=default_llm.base_name,
            toolkits=toolkits,
            system_prompt="Answer briefly and never call a tool unless asked.",
        )
        created.append(assistant)
        for skill in skills:
            skill_utils.attach_skill_to_assistant(assistant.id, skill.id)
        return assistant

    yield _create
    for assistant in created:
        try:
            assistant_utils.delete_assistant(assistant)
        except Exception:
            pass


@pytest.fixture
def new_conversation(conversation_utils):
    """Factory ``(assistant) -> conversation id``; every conversation is deleted at teardown."""
    created = []

    def _create(assistant) -> str:
        conversation_id = conversation_utils.create_conversation(
            initial_assistant_id=assistant.id, folder=""
        ).get("id")
        created.append(conversation_id)
        return conversation_id

    yield _create
    for conversation_id in created:
        try:
            conversation_utils.delete_conversation(conversation_id)
        except Exception:
            pass


@pytest.fixture
def empty_workspace(client):
    """A workspace of a fresh conversation id with no files.

    The API has no call that deletes a workspace, so it is left in place; its conversation
    id is random and never reused."""
    return client.workspaces.create(str(uuid.uuid4()), name="skill-files-test")
