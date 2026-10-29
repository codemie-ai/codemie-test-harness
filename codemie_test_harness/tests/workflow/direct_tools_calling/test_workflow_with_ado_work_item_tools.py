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

import copy
import json
import random

import pytest
from hamcrest import assert_that, is_not, matches_regexp

from codemie_test_harness.tests.enums.tools import AzureDevOpsWorkItemTool
from codemie_test_harness.tests.test_data.direct_tools.ado_work_item_tools_test_data import (
    ADO_WORK_ITEM_CREATE_MALFORMED_JSON_DIRECT,
    ADO_WORK_ITEM_UPDATE_MALFORMED_JSON_DIRECT,
    ado_work_item_get_test_data,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.constants import WORK_ITEM_ID_PATTERN
from codemie_test_harness.tests.utils.json_utils import extract_id_from_ado_response


@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.ado
@pytest.mark.api
@pytest.mark.smoke
@pytest.mark.parametrize(
    "toolkit,tool_name,prompt,expected_response",
    ado_work_item_get_test_data,
    ids=[f"{getattr(row, 'values', row)[1]}" for row in ado_work_item_get_test_data],
)
def test_workflow_with_ado_work_item_get_tools_direct(
    ado_integration,
    workflow_utils,
    similarity_check,
    workflow_with_tool,
    toolkit,
    tool_name,
    prompt,
    expected_response,
    seeded,
):
    prompt = seeded(prompt)
    expected_response = seeded(expected_response)
    tool_and_state_name = get_random_name()

    _workflow = workflow_with_tool(
        tool_and_state_name, tool_name, integration=ado_integration
    )
    response = workflow_utils.execute_workflow_without_prompt_modification(
        _workflow.id, tool_and_state_name, user_input=json.dumps(prompt)
    )

    similarity_check.check_similarity(response, expected_response, 75)


@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.ado
@pytest.mark.api
@pytest.mark.parametrize(
    "toolkit,tool_name,prompt,expected_response",
    ado_work_item_get_test_data,
    ids=[
        f"{getattr(row, 'values', row)[1]}_hardcoded"
        for row in ado_work_item_get_test_data
    ],
)
def test_workflow_with_ado_work_item_get_tools_with_hardcoded_args(
    ado_integration,
    workflow_utils,
    similarity_check,
    workflow_with_tool,
    toolkit,
    tool_name,
    prompt,
    expected_response,
    seeded,
):
    prompt = seeded(prompt)
    expected_response = seeded(expected_response)
    tool_and_state_name = get_random_name()

    _workflow = workflow_with_tool(
        tool_and_state_name, tool_name, integration=ado_integration, tool_args=prompt
    )
    response = workflow_utils.execute_workflow_without_prompt_modification(
        _workflow.id, tool_and_state_name
    )

    similarity_check.check_similarity(response, expected_response, 75)


@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.ado
@pytest.mark.api
@pytest.mark.parametrize(
    "toolkit,tool_name,prompt,expected_response",
    ado_work_item_get_test_data,
    ids=[
        f"{getattr(row, 'values', row)[1]}_overriding"
        for row in ado_work_item_get_test_data
    ],
)
def test_workflow_with_ado_work_item_get_tools_with_overriding_args(
    ado_integration,
    workflow_utils,
    similarity_check,
    workflow_with_tool,
    toolkit,
    tool_name,
    prompt,
    expected_response,
    seeded,
):
    prompt = seeded(prompt)
    expected_response = seeded(expected_response)
    tool_and_state_name = get_random_name()

    args_copy = copy.deepcopy(prompt)
    args_copy = {key: random.randint(1, 10) for key in args_copy}

    _workflow = workflow_with_tool(
        tool_and_state_name, tool_name, integration=ado_integration, tool_args=args_copy
    )
    response = workflow_utils.execute_workflow_without_prompt_modification(
        _workflow.id, tool_and_state_name, user_input=json.dumps(prompt)
    )

    similarity_check.check_similarity(response, expected_response, 75)


@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.ado
@pytest.mark.api
def test_workflow_with_ado_create_and_update_work_item_malformed_json_direct(
    ado_integration,
    workflow_utils,
    workflow_with_tool,
    ado_work_item_ids_to_cleanup,
):
    """Regression: create_work_item and update_work_item
    must accept a work_item_json payload containing literal (unescaped)
    newlines inside HTML field values -- the real-world shape of the
    LLM-generated payload that used to fail with "Issues during attempt to
    parse work_item_json: Expecting ',' delimiter" before
    _sanitize_json_control_chars (codemie tools.py) was added by MR !4249.
    Tool args are hardcoded directly on the workflow tool node (bypassing
    the LLM), so the malformed JSON is reproduced deterministically instead
    of depending on the LLM to regenerate the same malformed shape.
    """
    create_title = f"Autotest ADO JSON Parsing Task {get_random_name()}"
    create_args = copy.deepcopy(ADO_WORK_ITEM_CREATE_MALFORMED_JSON_DIRECT)
    create_args["work_item_json"] = create_args["work_item_json"].format(
        title=create_title
    )

    create_state = get_random_name()
    create_workflow = workflow_with_tool(
        create_state,
        AzureDevOpsWorkItemTool.CREATE_WORK_ITEM,
        integration=ado_integration,
        tool_args=create_args,
    )
    create_response = workflow_utils.execute_workflow_without_prompt_modification(
        create_workflow.id, create_state
    )

    # A full-string regex match rules out any parse-error text on its own:
    # "Issues during attempt to parse..."/"Failed to parse..." cannot match
    # this shape. The \1 backreference ties the message's work item id to
    # the one in the ADO URL.
    assert_that(
        create_response,
        matches_regexp(
            r"^Work item (\d+) created successfully\. View it at "
            r"https://dev\.azure\.com/[^/]+/[0-9a-f-]+/_apis/wit/workItems/\1\.$"
        ),
    )

    work_item_id = extract_id_from_ado_response(create_response, WORK_ITEM_ID_PATTERN)
    assert_that(work_item_id, is_not(None))
    ado_work_item_ids_to_cleanup.append(work_item_id)

    update_title = f"Autotest ADO JSON Parsing Task Updated {get_random_name()}"
    update_args = copy.deepcopy(ADO_WORK_ITEM_UPDATE_MALFORMED_JSON_DIRECT)
    update_args["work_item_json"] = update_args["work_item_json"].format(
        title=update_title
    )
    update_args["id"] = int(work_item_id)

    update_state = get_random_name()
    update_workflow = workflow_with_tool(
        update_state,
        AzureDevOpsWorkItemTool.UPDATE_WORK_ITEM,
        integration=ado_integration,
        tool_args=update_args,
    )
    update_response = workflow_utils.execute_workflow_without_prompt_modification(
        update_workflow.id, update_state
    )

    assert_that(
        update_response,
        matches_regexp(rf"^Work item \({work_item_id}\) was updated\.$"),
    )
