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

"""Headroom (context compression) settings stored on assistants and workflows."""

import pytest
from codemie_sdk import HeadroomStrategy
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    has_entries,
    is_,
    none,
)
from requests import HTTPError

from codemie_test_harness.tests.test_data.headroom_test_data import (
    ASSISTANT_HEADROOM_AGGRESSIVE,
    ASSISTANT_HEADROOM_LOSSLESS,
    ASSISTANT_INVALID_STATUS,
    ASSISTANT_INVALID_STRATEGY_FIELD,
    INVALID_WORKFLOW_HEADROOM,
    WORKFLOW_HEADROOM_BALANCED,
    WORKFLOW_INVALID_STATUS,
    assistant_headroom_with_unknown_strategy,
    clean_workflow_error_details,
    workflow_yaml_with_headroom,
    workflows_with_ids,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name


# @case headroom-per-assistant-workflow-configuration_TC_002
@pytest.mark.assistant
@pytest.mark.api
def test_assistant_headroom_config_is_saved_on_that_assistant_only(
    assistant_factory, assistant_utils
):
    with_headroom = assistant_factory.create(
        headroom_config=ASSISTANT_HEADROOM_AGGRESSIVE
    )
    without_headroom = assistant_factory.create()

    # The create response does not echo headroom_config; the stored value is read back.
    assert_that(
        assistant_utils.get_assistant_by_id(with_headroom.id).headroom_config,
        equal_to(ASSISTANT_HEADROOM_AGGRESSIVE),
        "Assistant read does not return the Headroom config it was created with",
    )
    assert_that(
        assistant_utils.get_assistant_by_id(without_headroom.id).headroom_config,
        none(),
        "Assistant created without Headroom config returns one",
    )

    assistant_utils.update_assistant_headroom(
        with_headroom.id, ASSISTANT_HEADROOM_LOSSLESS
    )

    assert_that(
        assistant_utils.get_assistant_by_id(with_headroom.id).headroom_config,
        equal_to(ASSISTANT_HEADROOM_LOSSLESS),
        "Assistant read does not return the updated Headroom config (strategy lossless)",
    )
    assert_that(
        assistant_utils.get_assistant_by_id(without_headroom.id).headroom_config,
        none(),
        "Updating one assistant's Headroom config changed another assistant",
    )


# @case headroom-per-assistant-workflow-configuration_TC_003
@pytest.mark.workflow
@pytest.mark.api
def test_workflow_headroom_block_is_saved_on_that_workflow_only(
    client, workflow_with_virtual_assistant, workflow_utils
):
    with_headroom = workflow_with_virtual_assistant(
        get_random_name(), headroom=WORKFLOW_HEADROOM_BALANCED
    )
    without_headroom = workflow_with_virtual_assistant(get_random_name())

    stored = workflow_utils.get_workflow(with_headroom.id).headroom_config
    assert_that(
        stored.enabled,
        is_(True),
        "Workflow detail does not return headroom_config.enabled from the YAML block",
    )
    assert_that(
        stored.strategy,
        equal_to(HeadroomStrategy.BALANCED),
        "Workflow detail does not return headroom_config.strategy from the YAML block",
    )
    assert_that(
        workflow_utils.get_workflow(without_headroom.id).headroom_config,
        none(),
        "Workflow without a headroom block returns a headroom_config",
    )

    listed = workflows_with_ids(
        client.workflows.list(per_page=200), {with_headroom.id, without_headroom.id}
    )
    assert_that(
        {workflow_id: wf.headroom_config for workflow_id, wf in listed.items()},
        has_entries({with_headroom.id: none(), without_headroom.id: none()}),
        "Workflow list entries carry headroom_config, which only the detail returns",
    )


# @case headroom-per-assistant-workflow-configuration_TC_004
@pytest.mark.assistant
@pytest.mark.api
def test_assistant_with_unknown_headroom_strategy_is_rejected(assistant_utils):
    with pytest.raises(HTTPError) as error:
        assistant_utils.send_create_assistant_request(
            headroom_config=assistant_headroom_with_unknown_strategy()
        )

    assert_that(
        error.value.response.status_code,
        equal_to(ASSISTANT_INVALID_STATUS),
        "Assistant with an unknown Headroom strategy is not rejected by request validation",
    )
    assert_that(
        error.value.response.json()["error"]["message"],
        contains_string(ASSISTANT_INVALID_STRATEGY_FIELD),
        "Validation error does not name headroom_config.strategy",
    )


# @case headroom-per-assistant-workflow-configuration_TC_004
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.parametrize(
    "invalid",
    list(INVALID_WORKFLOW_HEADROOM.values()),
    ids=list(INVALID_WORKFLOW_HEADROOM.keys()),
)
def test_workflow_with_invalid_headroom_block_is_rejected(
    workflow_utils, default_llm, invalid
):
    yaml_config = workflow_yaml_with_headroom(default_llm.base_name, invalid.headroom)

    with pytest.raises(HTTPError) as error:
        workflow_utils.send_create_workflow_request(yaml_config)

    assert_that(
        error.value.response.status_code,
        equal_to(WORKFLOW_INVALID_STATUS),
        "Workflow with an invalid headroom block is not rejected as a configuration error",
    )
    assert_that(
        clean_workflow_error_details(error.value.response.json()["error"]["details"]),
        contains_string(invalid.expected_message),
        "Configuration error does not point at the headroom block",
    )
