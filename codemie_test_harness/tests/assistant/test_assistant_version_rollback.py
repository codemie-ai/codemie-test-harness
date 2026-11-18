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

"""API tests for restoring an assistant version whose MCP link became unavailable.

A rollback never blocks on an unavailable catalog link the way a normal save does:
``MCPAccessControlService.restore_mcp_servers`` disables the link instead and the
rollback response reports it in ``disabledMcpServers`` (camelCase at the top level;
each entry's own ``name``/``mcp_config_id``/``reason`` stays snake_case) -- confirmed
live against the backend's raw, unparsed response.
"""

import pytest
from hamcrest import assert_that, equal_to, has_length

from codemie_sdk.models.assistant import AssistantUpdateRequest
from codemie_sdk.models.mcp_config import MCPConfigUpdateRequest
from codemie_test_harness.tests.test_data.mcp_link_test_data import link_server
from codemie_test_harness.tests.utils.base_utils import get_random_name

# The version created at assistant creation time, before the "save a new version"
# step below creates version 2. It is the target of every rollback in this file.
_INITIAL_VERSION_NUMBER = 1


@pytest.mark.parametrize(
    "catalog_state, expected_reason",
    [
        pytest.param("missing", "missing", id="missing"),
        pytest.param("inactive", "inactive", id="inactive"),
        pytest.param("not_public", "not_public", id="not_public"),
        pytest.param("active", None, id="no_disable_needed_empty_list"),
    ],
)
@pytest.mark.assistant
@pytest.mark.mcp
@pytest.mark.api
def test_rollback_disables_and_reports_unavailable_link(
    assistant_factory,
    assistant_utils,
    client,
    catalog_mcp_config,
    catalog_state,
    expected_reason,
):
    # @case mcp-link-predicate-save-validation_TC_005
    config = catalog_mcp_config()
    server_name = get_random_name()
    server = link_server(name=server_name, mcp_config_id=config.id, enabled=True)
    created = assistant_factory.create(mcp_servers=[server])
    # assistant_factory.create() returns the minimal list-response entity
    # (client.assistants.list(minimal_response=True) by default); system_prompt/
    # project/llm_model_type only exist on the full Assistant detail object.
    full_created = assistant_utils.get_assistant_by_id(created.id)

    # Save a new version (version 2) while the catalog entry is still active, so the
    # update's own validate_on_save does not reject it; version 1 still holds the link.
    assistant_utils.update_assistant(
        created.id,
        AssistantUpdateRequest(
            name=full_created.name,
            description="Version 2 - unrelated change",
            system_prompt=full_created.system_prompt,
            project=full_created.project,
            llm_model_type=full_created.llm_model_type,
        ),
    )

    if catalog_state == "missing":
        client.mcp_configs.delete(config.id)
    elif catalog_state == "inactive":
        client.mcp_configs.update(config.id, MCPConfigUpdateRequest(is_active=False))
    elif catalog_state == "not_public":
        client.mcp_configs.update(config.id, MCPConfigUpdateRequest(is_public=False))
    # catalog_state == "active": leave the catalog entry available.

    response = assistant_utils.rollback_to_version(created.id, _INITIAL_VERSION_NUMBER)

    # AssistantService.rollback_to_version() is pre-existing (out of this run's SDK
    # scope) and returns the backend's raw dict unparsed: the wrapper's own field
    # serializes as camelCase (disabledMcpServers) even though its nested entries
    # stay snake_case (name, mcp_config_id, reason) -- confirmed live.
    if expected_reason is None:
        assert_that(response["disabledMcpServers"], equal_to([]))
    else:
        assert_that(response["disabledMcpServers"], has_length(1))
        disabled = response["disabledMcpServers"][0]
        assert_that(disabled["name"], equal_to(server_name))
        assert_that(disabled["mcp_config_id"], equal_to(config.id))
        assert_that(disabled["reason"], equal_to(expected_reason))

    restored = assistant_utils.get_assistant_by_id(created.id)
    restored_server = next(
        entry for entry in restored.mcp_servers if entry.mcp_config_id == config.id
    )
    assert_that(restored_server.enabled, equal_to(expected_reason is None))
