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

"""API test for validating disabled_context_tools of a workflow assistant.

A workflow assistant may only deselect the default tool names; an unknown name is
refused when the workflow is created.
"""

import pytest
from hamcrest import assert_that, contains_string
from requests import HTTPError

from codemie_sdk.models.workflow import WorkflowMode
from codemie_test_harness.tests.test_data.default_datasource_tools_test_data import (
    UNKNOWN_TOOL_NAME,
    UNKNOWN_TOOLS_MESSAGE,
)
from codemie_test_harness.tests.utils.yaml_utils import (
    AssistantModel,
    StateModel,
    WorkflowYamlModel,
    prepare_yaml_content,
)


@pytest.mark.workflow
@pytest.mark.api
def test_workflow_refuses_unknown_disabled_context_tool(workflow_utils, default_llm):
    # @case deselect-default-datasource-tools_TC_015
    assistant_model = AssistantModel(
        id="deselect_node",
        model=default_llm.base_name,
        system_prompt="Node listing an unknown deselected default tool",
        disabled_context_tools=[UNKNOWN_TOOL_NAME],
    )
    state_model = StateModel(id="deselect_node", assistant_id="deselect_node")
    workflow_yaml = WorkflowYamlModel(
        assistants=[assistant_model], states=[state_model]
    )

    with pytest.raises(HTTPError) as exc_info:
        workflow_utils.create_workflow(
            workflow_type=WorkflowMode.SEQUENTIAL,
            workflow_yaml=prepare_yaml_content(
                workflow_yaml.model_dump(exclude_none=True)
            ),
            shared=True,
        )

    assert_that(
        exc_info.value.response.text,
        contains_string(f"{UNKNOWN_TOOLS_MESSAGE}: {UNKNOWN_TOOL_NAME}"),
    )
