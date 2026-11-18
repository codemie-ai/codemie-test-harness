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

"""API tests for workflow save-time MCP link validation.

``MCPAccessControlService.validate_workflow_mcp`` collects every mcp_servers entry
across a workflow's nodes, filters to "links" (enabled, carries ``mcp_config_id``,
not ``use_custom_config``) and checks the catalog over every link but duplicates
only *within* one node -- the same catalog entry used by two different nodes saves.
Deleting a catalog config, separately, must never rewrite a workflow's stored YAML.
"""

import yaml
import pytest
from hamcrest import assert_that, equal_to
from requests import HTTPError

from codemie_sdk.models.workflow import WorkflowMode
from codemie_test_harness.tests.test_data.mcp_link_test_data import (
    DUPLICATE_CATALOG_MESSAGE,
    link_server,
)
from codemie_test_harness.tests.utils.yaml_utils import (
    AssistantModel,
    StateModel,
    WorkflowYamlModel,
    prepare_yaml_content,
)


@pytest.fixture
def dead_catalog_config_id(client, catalog_mcp_config):
    """A catalog config id that existed, then was deleted: resolves to no catalog entry."""
    config = catalog_mcp_config()
    client.mcp_configs.delete(config.id)
    return config.id


def _workflow_yaml(assistants, states) -> str:
    workflow_yaml = WorkflowYamlModel(assistants=assistants, states=states)
    return prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))


@pytest.fixture
def workflow_factory(workflow_utils):
    """Factory: a workflow built from explicit assistants/states, cleaned up on teardown."""
    created = []

    def _create(assistants, states):
        workflow = workflow_utils.create_workflow(
            workflow_type=WorkflowMode.SEQUENTIAL,
            workflow_yaml=_workflow_yaml(assistants, states),
            shared=True,
        )
        created.append(workflow)
        return workflow

    yield _create

    for workflow in created:
        try:
            workflow_utils.delete_workflow(workflow)
        except Exception:
            pass


@pytest.mark.workflow
@pytest.mark.mcp
@pytest.mark.api
@pytest.mark.parametrize(
    "enabled, use_custom_config",
    [
        pytest.param(False, False, id="disabled_dead_id_saves"),
        pytest.param(True, True, id="custom_config_dead_id_saves"),
    ],
)
def test_disabled_or_custom_config_dead_catalog_id_node_saves(
    workflow_factory,
    workflow_utils,
    default_llm,
    dead_catalog_config_id,
    enabled,
    use_custom_config,
):
    # @case mcp-link-predicate-save-validation_TC_003
    server = link_server(
        mcp_config_id=dead_catalog_config_id,
        enabled=enabled,
        use_custom_config=use_custom_config,
    )
    assistant_model = AssistantModel(
        id="mcp_link_node",
        model=default_llm.base_name,
        system_prompt="Node carrying a dead-id MCP server entry",
        mcp_servers=[server],
    )
    state_model = StateModel(id="mcp_link_node", assistant_id="mcp_link_node")

    created = workflow_factory([assistant_model], [state_model])

    stored = yaml.safe_load(workflow_utils.get_workflow(created.id).yaml_config)
    stored_server = stored["assistants"][0]["mcp_servers"][0]
    assert_that(stored_server["mcp_config_id"], equal_to(dead_catalog_config_id))
    assert_that(stored_server["enabled"], equal_to(enabled))
    assert_that(stored_server["use_custom_config"], equal_to(use_custom_config))


@pytest.mark.workflow
@pytest.mark.mcp
@pytest.mark.api
def test_same_catalog_id_across_two_nodes_saves(
    workflow_factory, workflow_utils, default_llm, catalog_mcp_config
):
    # @case mcp-link-predicate-save-validation_TC_004
    config = catalog_mcp_config()
    first_assistant = AssistantModel(
        id="node_one",
        model=default_llm.base_name,
        system_prompt="First node linking the shared catalog entry",
        mcp_servers=[link_server(mcp_config_id=config.id)],
    )
    second_assistant = AssistantModel(
        id="node_two",
        model=default_llm.base_name,
        system_prompt="Second node linking the same catalog entry",
        mcp_servers=[link_server(mcp_config_id=config.id)],
    )
    first_state = StateModel(
        id="node_one", assistant_id="node_one", next={"state_id": "node_two"}
    )
    second_state = StateModel(id="node_two", assistant_id="node_two")

    created = workflow_factory(
        [first_assistant, second_assistant], [first_state, second_state]
    )

    stored = yaml.safe_load(workflow_utils.get_workflow(created.id).yaml_config)
    assert_that(
        [
            assistant["mcp_servers"][0]["mcp_config_id"]
            for assistant in stored["assistants"]
        ],
        equal_to([config.id, config.id]),
        "the same catalog entry must be stored as a link on both nodes",
    )


@pytest.mark.workflow
@pytest.mark.mcp
@pytest.mark.api
def test_same_catalog_id_twice_in_one_node_refused(
    workflow_utils, default_llm, catalog_mcp_config
):
    # @case mcp-link-predicate-save-validation_TC_004
    config = catalog_mcp_config()
    assistant_model = AssistantModel(
        id="node_one",
        model=default_llm.base_name,
        system_prompt="Node linking the same catalog entry twice",
        mcp_servers=[
            link_server(mcp_config_id=config.id),
            link_server(mcp_config_id=config.id),
        ],
    )
    state_model = StateModel(id="node_one", assistant_id="node_one")

    with pytest.raises(HTTPError) as exc_info:
        workflow_utils.create_workflow(
            workflow_type=WorkflowMode.SEQUENTIAL,
            workflow_yaml=_workflow_yaml([assistant_model], [state_model]),
            shared=True,
        )

    response = exc_info.value.response
    assert_that(response.status_code, equal_to(400), response.text)
    assert_that(
        response.json()["error"]["message"], equal_to(DUPLICATE_CATALOG_MESSAGE)
    )


@pytest.mark.workflow
@pytest.mark.mcp
@pytest.mark.api
def test_deleting_catalog_config_does_not_rewrite_workflow_yaml(
    workflow_factory, workflow_utils, default_llm, client, catalog_mcp_config
):
    # @case mcp-link-predicate-save-validation_TC_007
    config = catalog_mcp_config()
    assistant_model = AssistantModel(
        id="node_one",
        model=default_llm.base_name,
        system_prompt="Node linking the catalog entry that will be deleted",
        mcp_servers=[link_server(mcp_config_id=config.id)],
    )
    state_model = StateModel(id="node_one", assistant_id="node_one")
    created = workflow_factory([assistant_model], [state_model])
    baseline_yaml_config = workflow_utils.get_workflow(created.id).yaml_config

    client.mcp_configs.delete(config.id)

    refetched_yaml_config = workflow_utils.get_workflow(created.id).yaml_config
    assert_that(
        refetched_yaml_config,
        equal_to(baseline_yaml_config),
        "deleting the linked catalog entry must not rewrite the workflow's stored YAML",
    )
