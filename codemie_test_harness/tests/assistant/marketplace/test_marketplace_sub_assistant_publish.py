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

"""API test for marketplace publish of sub-assistants and an unavailable MCP link.

``_publish_sub_assistants`` now runs ``MCPAccessControlService.validate_on_save`` on
the ``mcp_servers`` settings of every sub-assistant before any of them is saved,
closing the gap where publish could write MCP data with no catalog check.
"""

import pytest
from hamcrest import assert_that, equal_to, has_length
from requests import HTTPError

from codemie_sdk.models.assistant import (
    AssistantUpdateRequest,
    SubAssistantPublishSettings,
)
from codemie_test_harness.tests.test_data.marketplace_approval_gate_test_data import (
    build_marketplace_submission,
)
from codemie_test_harness.tests.test_data.mcp_link_test_data import (
    catalog_unavailable_message,
    link_server,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.mcp
@pytest.mark.api
def test_publish_rejects_unavailable_sub_assistant_mcp_link(
    assistant_factory,
    assistant_utils,
    marketplace_management_utils,
    marketplace_core_gates,
    client,
    catalog_mcp_config,
):
    # @case mcp-link-predicate-save-validation_TC_008
    config = catalog_mcp_config()
    server_name = get_random_name()
    link = link_server(name=server_name, mcp_config_id=config.id, enabled=True)
    sub_submission = build_marketplace_submission(marketplace_core_gates)
    sub = assistant_factory.create(
        description=sub_submission.description,
        system_prompt=sub_submission.system_prompt,
        mcp_servers=[link],
    )
    parent_submission = build_marketplace_submission(marketplace_core_gates)
    parent = assistant_factory.create(
        description=parent_submission.description,
        system_prompt=parent_submission.system_prompt,
        assistant_ids=[sub.id],
    )

    # The catalog config's usage_count only reaches zero once the sub-assistant's own
    # stored mcp_servers no longer references it, so drop that stored link first; the
    # publish call's own SubAssistantPublishSettings payload below re-asserts an
    # enabled link to the (now dead) config id, which is what the publish-time catalog
    # check actually validates -- confirmed live (the payload's mcp_servers are applied
    # to the sub-assistant in-memory before the publish save, not the assistant's own
    # pre-existing stored link).
    full_sub = assistant_utils.get_assistant_by_id(sub.id)
    assistant_utils.update_assistant(
        sub.id,
        AssistantUpdateRequest(
            name=full_sub.name,
            description=full_sub.description or "",
            system_prompt=full_sub.system_prompt,
            project=full_sub.project,
            llm_model_type=full_sub.llm_model_type,
            mcp_servers=[],
        ),
    )

    # The sub-assistant's linked catalog config is now unavailable.
    client.mcp_configs.delete(config.id)

    with pytest.raises(HTTPError) as exc_info:
        marketplace_management_utils.publish(
            parent.id,
            parent_submission.categories,
            sub_assistants_settings=[
                SubAssistantPublishSettings(assistant_id=sub.id, mcp_servers=[link])
            ],
        )

    response = exc_info.value.response
    assert_that(response.status_code, equal_to(400), response.text)
    assert_that(
        response.json()["error"]["message"],
        equal_to(catalog_unavailable_message(server_name)),
    )

    # No sub-assistant copy was saved: the rejected publish must not apply the
    # payload's (dead-link) mcp_servers to the sub-assistant's stored state, which
    # is still the empty list this test set above.
    stored_sub = assistant_utils.get_assistant_by_id(sub.id)
    assert_that(stored_sub.mcp_servers, has_length(0))
