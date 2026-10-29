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

import pytest

from codemie_test_harness.tests.enums.tools import AzureDevOpsWorkItemTool
from codemie_test_harness.tests.test_data.ado_work_item_tools_test_data import (
    ado_work_item_get_test_data,
    ADO_WORK_ITEM_CREATE,
    ADO_WORK_ITEM_UPDATE,
    ADO_WORK_ITEM_LINK,
)
from codemie_test_harness.tests.utils.base_utils import (
    get_random_name,
    assert_tool_triggered,
)
from codemie_test_harness.tests.utils.constants import WORK_ITEM_ID_PATTERN
from codemie_test_harness.tests.utils.json_utils import extract_id_from_ado_response


@pytest.mark.workflow
@pytest.mark.virtual_workflow
@pytest.mark.ado
@pytest.mark.api
@pytest.mark.parametrize(
    "toolkit, tool_name, prompt, expected_response",
    ado_work_item_get_test_data,
    ids=[f"{getattr(row, 'values', row)[1]}" for row in ado_work_item_get_test_data],
)
def test_workflow_with_ado_work_item_get_tools(
    ado_integration,
    workflow_with_virtual_assistant,
    workflow_utils,
    similarity_check,
    toolkit,
    tool_name,
    prompt,
    expected_response,
    seeded,
):
    prompt = seeded(prompt)
    expected_response = seeded(expected_response)
    assistant_and_state_name = get_random_name()

    test_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name,
        tool_name,
        integration=ado_integration,
    )
    response = workflow_utils.execute_workflow(
        test_workflow.id, assistant_and_state_name, prompt
    )
    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        test_workflow
    )
    assert_tool_triggered(tool_name, triggered_tools)
    similarity_check.check_similarity(response, expected_response)


@pytest.mark.workflow
@pytest.mark.virtual_workflow
@pytest.mark.ado
@pytest.mark.api
def test_workflow_with_ado_work_item_modify_tools(
    ado_seed,
    ado_integration,
    workflow_with_virtual_assistant,
    workflow_utils,
    similarity_check,
    ado_work_item_ids_to_cleanup,
):
    # 1. Create the work item
    work_item_title = f"Autotest Task {get_random_name()}"

    create_prompt = ADO_WORK_ITEM_CREATE["prompt_to_assistant"].format(work_item_title)

    assistant_and_state_name = get_random_name()
    create_item_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name,
        AzureDevOpsWorkItemTool.CREATE_WORK_ITEM,
        integration=ado_integration,
    )
    create_response = workflow_utils.execute_workflow(
        create_item_workflow.id, assistant_and_state_name, create_prompt
    )
    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        create_item_workflow
    )
    assert_tool_triggered(AzureDevOpsWorkItemTool.CREATE_WORK_ITEM, triggered_tools)
    work_item_id = extract_id_from_ado_response(create_response, WORK_ITEM_ID_PATTERN)
    ado_work_item_ids_to_cleanup.append(work_item_id)
    create_expected = ADO_WORK_ITEM_CREATE["expected_llm_answer"].format(
        work_item_title, work_item_id
    )
    similarity_check.check_similarity(create_response, create_expected)

    # 2. Update the item
    new_title = f"Autotest Epic {get_random_name()}"
    update_prompt = ADO_WORK_ITEM_UPDATE["prompt_to_assistant"].format(
        work_item_id, new_title
    )

    update_expected = ADO_WORK_ITEM_UPDATE["expected_llm_answer"].format(
        work_item_id, new_title
    )
    assistant_and_state_name = get_random_name()
    update_item_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name,
        AzureDevOpsWorkItemTool.UPDATE_WORK_ITEM,
        integration=ado_integration,
    )
    update_response = workflow_utils.execute_workflow(
        update_item_workflow.id, assistant_and_state_name, update_prompt
    )
    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        update_item_workflow
    )
    assert_tool_triggered(AzureDevOpsWorkItemTool.UPDATE_WORK_ITEM, triggered_tools)
    similarity_check.check_similarity(update_response, update_expected)

    # 3. Link the item
    link_prompt = ADO_WORK_ITEM_LINK["prompt_to_assistant"].format(
        child_id=work_item_id, parent_id=ado_seed.parent_work_item.id
    )

    link_expected = ADO_WORK_ITEM_LINK["expected_llm_answer"].format(
        child_id=work_item_id, parent_id=ado_seed.parent_work_item.id
    )
    assistant_and_state_name = get_random_name()
    link_item_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name,
        AzureDevOpsWorkItemTool.LINK_WORK_ITEMS,
        integration=ado_integration,
    )
    link_response = workflow_utils.execute_workflow(
        link_item_workflow.id, assistant_and_state_name, link_prompt
    )
    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        link_item_workflow
    )
    assert_tool_triggered(AzureDevOpsWorkItemTool.LINK_WORK_ITEMS, triggered_tools)
    similarity_check.check_similarity(link_response, link_expected)
