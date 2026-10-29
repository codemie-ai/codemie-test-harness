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

"""Tests for combinations of store_in_context and include_in_llm_history.

These tests verify that the two features work correctly together and
independently control different aspects of context management.
"""

import json

import pytest
from codemie_sdk.models.workflow import WorkflowMode
from hamcrest import assert_that, contains_string, is_not

from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.yaml_utils import (
    StateModel,
    WorkflowYamlModel,
    prepare_yaml_content,
)
from codemie_test_harness.tests.workflow.context_management import TEST_DATA


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
def test_workflow_context_combination_store_true_history_false(
    data_extractor, information_validator, workflow_utils
):
    """Test combination: store_in_context defaults to true, include_in_llm_history=false.

    Use case: Store data in context while hiding from LLM history.

    Scenario:
    1. First state outputs JSON with metadata
    2. Set include_in_llm_history=false (store_in_context defaults to true)
    3. Second state asks LLM about previous messages
    4. Verify: LLM doesn't see the JSON in history, workflow completes successfully

    Note: Context variable resolution behavior may vary by platform implementation.
    This test primarily verifies that include_in_llm_history=false works correctly.
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        assistants=[
            data_extractor("generate_file_data"),
            information_validator("check_history"),
        ],
        states=[
            StateModel(
                id="generate_file_data",
                assistant_id="generate_file_data",
                task=f'Output this JSON exactly: {{"file_id": "{TEST_DATA["file_id"]}", "metadata": "Metadata for {TEST_DATA["file_id"]}"}}',
                output_schema='{"file_id": "string", "metadata": "string"}',
                next={
                    "state_id": "check_history",
                    "include_in_llm_history": False,
                },
            ),
            StateModel(
                id="check_history",
                assistant_id="check_history",
                task=(
                    "Was any specific metadata mentioned in the previous message? "
                    "Answer with yes or no and explain what you see in the conversation history."
                ),
                next={"state_id": "end"},
            ),
        ],
    )

    # Create workflow
    yaml_content = prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))
    created_workflow = workflow_utils.create_workflow(
        workflow_name=workflow_name,
        workflow_type=WorkflowMode.SEQUENTIAL,
        workflow_yaml=yaml_content,
    )

    # Execute workflow
    output = workflow_utils.execute_workflow(
        created_workflow.id,
        execution_name="check_history",
        user_input="Start",
    ).lower()

    # LLM shouldn't have seen the metadata (not in history due to include_in_llm_history=false)
    # It should indicate it didn't see specific metadata in the conversation
    assert_that(
        output,
        is_not(contains_string(f"metadata for {TEST_DATA['file_id']}")),
    )


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
def test_workflow_context_combination_store_false_history_true(
    data_extractor, workflow_utils
):
    """Test combination: store_in_context=false, include_in_llm_history=true.

    Use case: Output is stored in LLM history but not in context store.

    Scenario:
    1. First state outputs data: {"analysis": "Use approach ALPHA"}
    2. Set store_in_context=false, include_in_llm_history=true
    3. Second state tries to use {{analysis}} template variable
    4. Verify: Template substitution doesn't work (not in context)
    5. Verify: Workflow completes successfully (LLM history doesn't break execution)

    Note: This tests that include_in_llm_history=true works even when store_in_context=false.
    The exact LLM history behavior may vary by implementation.
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        assistants=[
            data_extractor("data_generator"),
        ],
        states=[
            StateModel(
                id="generate_project_data",
                assistant_id="data_generator",
                task=f'Output this JSON: {{"project_id": "{TEST_DATA["project_id"]}", "file_id": "{TEST_DATA["file_id"]}"}}',
                output_schema='{"project_id": "string", "file_id": "string"}',
                next={
                    "state_id": "try_use_project_data",
                    "store_in_context": False,
                    "include_in_llm_history": True,
                },
            ),
            StateModel(
                id="try_use_project_data",
                assistant_id="data_generator",
                task=(
                    "Try to access the project_id variable: {{project_id}}. "
                    "If you see the literal '{{project_id}}' text (not a value), say 'Variable not in context'. "
                    "Otherwise, confirm the project_id value."
                ),
                next={"state_id": "end"},
            ),
        ],
    )

    # Create workflow
    yaml_content = prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))
    created_workflow = workflow_utils.create_workflow(
        workflow_name=workflow_name,
        workflow_type=WorkflowMode.SEQUENTIAL,
        workflow_yaml=yaml_content,
    )

    # Execute workflow
    output = workflow_utils.execute_workflow(
        created_workflow.id,
        execution_name="try_use_project_data",
        user_input="Generate project data",
    ).lower()

    # Verify the variable was NOT available in context store
    # (because store_in_context was false)
    assert_that(output, contains_string("not in context"))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
def test_workflow_multi_state_context_propagation(
    data_extractor, data_processor, workflow_utils
):
    """Test context propagation across multiple states with different configurations.

    Scenario with 3 states:
    1. State 1: Generate user data -> store_in_context=true
    2. State 2: Generate additional data -> store_in_context=true
    3. State 3: Use both variables from previous states
    4. Verify all context accumulates and is accessible
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        assistants=[
            data_extractor("generate_user"),
            data_extractor("generate_project"),
            data_processor("combine_data"),
        ],
        states=[
            StateModel(
                id="generate_user",
                assistant_id="generate_user",
                task=f'Output JSON: {{"user_id": "{TEST_DATA["user_id"]}", "secret_code": "{TEST_DATA["secret_code"]}"}}',
                output_schema='{"user_id": "string", "secret_code": "string"}',
                next={
                    "state_id": "generate_project",
                    "store_in_context": True,
                    "include_in_llm_history": True,
                },
            ),
            StateModel(
                id="generate_project",
                assistant_id="generate_project",
                task=f'Output JSON: {{"project_id": "{TEST_DATA["project_id"]}", "file_id": "{TEST_DATA["file_id"]}"}}',
                output_schema='{"project_id": "string", "file_id": "string"}',
                next={
                    "state_id": "combine_data",
                    "store_in_context": True,
                    "include_in_llm_history": True,
                },
            ),
            StateModel(
                id="combine_data",
                assistant_id="combine_data",
                task=(
                    "Create a summary using these variables: "
                    "User ID: {{user_id}}, Secret Code: {{secret_code}}, "
                    "Project ID: {{project_id}}, File ID: {{file_id}}. "
                    "Confirm you have all four pieces of information."
                ),
                next={"state_id": "end"},
            ),
        ],
    )

    # Create workflow
    yaml_content = prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))
    created_workflow = workflow_utils.create_workflow(
        workflow_name=workflow_name,
        workflow_type=WorkflowMode.SEQUENTIAL,
        workflow_yaml=yaml_content,
    )

    # Execute workflow
    output = workflow_utils.execute_workflow(
        created_workflow.id,
        execution_name="combine_data",
        user_input="Generate data",
    )

    # Verify all variables were accessible
    assert_that(output, contains_string(TEST_DATA["user_id"]))
    assert_that(output, contains_string(TEST_DATA["secret_code"]))
    assert_that(output, contains_string(TEST_DATA["project_id"]))
    assert_that(output, contains_string(TEST_DATA["file_id"]))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
def test_workflow_context_with_json_output_schema(
    data_extractor, data_processor, workflow_utils
):
    """Test that structured JSON output with output_schema properly populates context store.

    Scenario:
    1. First state uses output_schema to enforce JSON structure
    2. Output: {"status": "success", "code": "200", "message": "OK"}
    3. Second state references all three variables
    4. Verify all root-level keys are accessible as context variables
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        assistants=[
            data_extractor("generate_response"),
            data_processor("process_response"),
        ],
        states=[
            StateModel(
                id="generate_response",
                assistant_id="generate_response",
                task=f'Generate a response with user_id "{TEST_DATA["user_id"]}", project_id "{TEST_DATA["project_id"]}", and file_id "{TEST_DATA["file_id"]}"',
                output_schema=json.dumps(
                    {"user_id": "string", "project_id": "string", "file_id": "string"}
                ),
                next={"state_id": "process_response", "store_in_context": True},
            ),
            StateModel(
                id="process_response",
                assistant_id="process_response",
                task=(
                    "Process the response data: "
                    "User ID: {{user_id}}, Project ID: {{project_id}}, File ID: {{file_id}}. "
                    "Confirm all three values."
                ),
                next={"state_id": "end"},
            ),
        ],
    )

    # Create workflow
    yaml_content = prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))
    created_workflow = workflow_utils.create_workflow(
        workflow_name=workflow_name,
        workflow_type=WorkflowMode.SEQUENTIAL,
        workflow_yaml=yaml_content,
    )

    # Execute workflow
    output = workflow_utils.execute_workflow(
        created_workflow.id,
        execution_name="process_response",
        user_input="Generate response data",
    )

    # Verify all JSON keys were accessible as context variables
    assert_that(output, contains_string(TEST_DATA["user_id"]))
    assert_that(output, contains_string(TEST_DATA["project_id"]))
    assert_that(output, contains_string(TEST_DATA["file_id"]))
