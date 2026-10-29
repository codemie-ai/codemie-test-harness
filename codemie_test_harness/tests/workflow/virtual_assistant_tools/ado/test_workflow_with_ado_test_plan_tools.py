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

from codemie_test_harness.tests.enums.tools import AzureDevOpsTestPlanTool
from codemie_test_harness.tests.test_data.ado_test_plan_tools_test_data import (
    ado_test_plan_get_test_data,
    ADO_TEST_PLAN_CREATE_TEST_PLAN,
    ADO_TEST_PLAN_CREATE_SUITE,
    ADO_TEST_PLAN_ADD_TEST_CASE,
    ADO_TEST_PLAN_DELETE_SUITE,
    ADO_TEST_PLAN_DELETE_PLAN,
)
from codemie_test_harness.tests.utils.base_utils import (
    get_random_name,
    assert_tool_triggered,
)
from codemie_test_harness.tests.utils.constants import ID_PATTERN
from codemie_test_harness.tests.utils.json_utils import extract_id_from_ado_response


@pytest.mark.workflow
@pytest.mark.virtual_workflow
@pytest.mark.ado
@pytest.mark.api
@pytest.mark.parametrize(
    "toolkit, tool_name, prompt, expected_response",
    ado_test_plan_get_test_data,
    ids=[f"{getattr(row, 'values', row)[1]}" for row in ado_test_plan_get_test_data],
)
def test_workflow_with_ado_test_plan_get_tools(
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
@pytest.mark.skip
def test_workflow_with_ado_test_plan_tools(
    ado_test_plan_seed,
    ado_integration,
    workflow_with_virtual_assistant,
    workflow_utils,
    similarity_check,
):
    test_plan_title = f"Autotest Test Plan {get_random_name()}"

    # 1. Create the test plan
    create_prompt = ADO_TEST_PLAN_CREATE_TEST_PLAN["prompt_to_assistant"].format(
        test_plan_title
    )
    assistant_and_state_name = get_random_name()
    create_test_suite_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name,
        AzureDevOpsTestPlanTool.CREATE_TEST_PLAN,
        integration=ado_integration,
        task=create_prompt,
    )
    create_response = workflow_utils.execute_workflow(
        create_test_suite_workflow.id, assistant_and_state_name
    )
    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        create_test_suite_workflow
    )
    assert_tool_triggered(AzureDevOpsTestPlanTool.CREATE_TEST_PLAN, triggered_tools)

    # Extract the test plan ID from the response
    test_plan_id = extract_id_from_ado_response(create_response, ID_PATTERN)
    create_expected = ADO_TEST_PLAN_CREATE_TEST_PLAN["expected_llm_answer"].format(
        test_plan_title, test_plan_id
    )
    similarity_check.check_similarity(create_response, create_expected)

    # Calculate root suite ID (based on the ADO root suite id implementation)
    root_suite_id = int(test_plan_id) + 1

    # 2. Create test suite
    create_suite_prompt = ADO_TEST_PLAN_CREATE_SUITE["prompt_to_assistant"].format(
        root_suite_id, test_plan_id
    )
    assistant_and_state_name = get_random_name()
    create_test_suite_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name,
        AzureDevOpsTestPlanTool.CREATE_TEST_SUITE,
        integration=ado_integration,
    )
    create_suite_response = workflow_utils.execute_workflow(
        create_test_suite_workflow.id, assistant_and_state_name, create_suite_prompt
    )
    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        create_test_suite_workflow
    )
    assert_tool_triggered(AzureDevOpsTestPlanTool.CREATE_TEST_SUITE, triggered_tools)

    # Extract the test suite ID from the response
    test_suite_id = extract_id_from_ado_response(create_suite_response, ID_PATTERN)
    create_suite_expected = ADO_TEST_PLAN_CREATE_SUITE["expected_llm_answer"].format(
        test_suite_id
    )
    similarity_check.check_similarity(create_suite_response, create_suite_expected)

    # 3. Add test case to the suite
    add_case_prompt = ADO_TEST_PLAN_ADD_TEST_CASE["prompt_to_assistant"].format(
        test_case_id=ado_test_plan_seed.test_case_id,
        suite_id=test_suite_id,
        plan_id=test_plan_id,
    )
    assistant_and_state_name = get_random_name()
    add_test_case_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name,
        AzureDevOpsTestPlanTool.ADD_TEST_CASE,
        integration=ado_integration,
    )
    add_case_response = workflow_utils.execute_workflow(
        add_test_case_workflow.id, assistant_and_state_name, add_case_prompt
    )
    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        add_test_case_workflow
    )
    assert_tool_triggered(AzureDevOpsTestPlanTool.ADD_TEST_CASE, triggered_tools)
    add_case_expected = ADO_TEST_PLAN_ADD_TEST_CASE["expected_llm_answer"].format(
        test_case_id=ado_test_plan_seed.test_case_id,
        suite_id=test_suite_id,
        plan_id=test_plan_id,
    )
    similarity_check.check_similarity(add_case_response, add_case_expected)

    # 4. Delete test suite
    delete_suite_prompt = ADO_TEST_PLAN_DELETE_SUITE["prompt_to_assistant"].format(
        test_suite_id, test_plan_id
    )
    assistant_and_state_name = get_random_name()
    delete_test_suite_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name,
        AzureDevOpsTestPlanTool.DELETE_TEST_SUITE,
        integration=ado_integration,
    )
    delete_suite_response = workflow_utils.execute_workflow(
        delete_test_suite_workflow.id, assistant_and_state_name, delete_suite_prompt
    )
    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        delete_test_suite_workflow
    )
    assert_tool_triggered(AzureDevOpsTestPlanTool.DELETE_TEST_SUITE, triggered_tools)
    delete_suite_expected = ADO_TEST_PLAN_DELETE_SUITE["expected_llm_answer"].format(
        test_suite_id, test_plan_id
    )
    similarity_check.check_similarity(delete_suite_response, delete_suite_expected)

    # 5. Delete test plan
    delete_plan_prompt = ADO_TEST_PLAN_DELETE_PLAN["prompt_to_assistant"].format(
        test_plan_id
    )
    assistant_and_state_name = get_random_name()
    delete_test_plan_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name,
        AzureDevOpsTestPlanTool.DELETE_TEST_PLAN,
        integration=ado_integration,
    )
    delete_plan_response = workflow_utils.execute_workflow(
        delete_test_plan_workflow.id, assistant_and_state_name, delete_plan_prompt
    )
    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        delete_test_plan_workflow
    )
    assert_tool_triggered(AzureDevOpsTestPlanTool.DELETE_TEST_PLAN, triggered_tools)
    delete_plan_expected = ADO_TEST_PLAN_DELETE_PLAN["expected_llm_answer"].format(
        test_plan_id
    )
    similarity_check.check_similarity(delete_plan_response, delete_plan_expected)
