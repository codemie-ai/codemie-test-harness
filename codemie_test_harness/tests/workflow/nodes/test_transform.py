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

"""Tests for Transform Node functionality.

These tests verify the behavior of the Transform Node, which allows for
data transformation without LLM calls.

Test coverage:
- Extract mapping (field extraction)
- Array Map mapping (array processing and filtering)
- Condition mapping (boolean logic)
- Template mapping (Jinja2 rendering)
- Constant mapping (static values)
- Script mapping (Python expressions)
- Sequential processing
- Error handling strategies
- Input sources
"""

import json

import pytest
from codemie_sdk.models.workflow import WorkflowMode
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.yaml_utils import (
    StateModel,
    WorkflowYamlModel,
    CustomNodeModel,
    prepare_yaml_content,
)
from hamcrest import assert_that, contains_string


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.transform
def test_extract_mapping(
    data_generator, result_aggregator, workflow_utils, workflow_cleanup
):
    """Test 'extract' mapping type.

    Scenario:
    1. Init state stores nested JSON in context.
    2. Transform node extracts fields using dot notation.
    3. Final state verifies extracted values.
    """
    workflow_name = get_random_name()

    # Input data structure
    input_data = {
        "user": {
            "profile": {"name": "John Doe", "age": 30, "address": {"city": "New York"}}
        }
    }

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("init_assistant"),
            result_aggregator("verifier"),
        ],
        custom_nodes=[
            CustomNodeModel(
                id="extractor",
                custom_node_id="transform_node",
                name="Extract User Data",
                config={
                    "input_source": "context_store",
                    "input_key": "user_data",
                    "mappings": [
                        {
                            "output_field": "user_name",
                            "type": "extract",
                            "source_path": "user.profile.name",
                        },
                        {
                            "output_field": "user_city",
                            "type": "extract",
                            "source_path": "user.profile.address.city",
                        },
                        {
                            "output_field": "missing_field",
                            "type": "extract",
                            "source_path": "user.profile.missing",
                            "default": "N/A",
                        },
                    ],
                },
            )
        ],
        states=[
            StateModel(
                id="init_state",
                assistant_id="init_assistant",
                task=f"Output exactly: {json.dumps(input_data)}",
                output_schema='{"user": "object"}',
                next={
                    "state_id": "transform_state",
                    "output_key": "user_data",
                    "store_in_context": True,
                },
            ),
            StateModel(
                id="transform_state",
                custom_node_id="extractor",
                next={"state_id": "verify_state", "store_in_context": True},
            ),
            StateModel(
                id="verify_state",
                assistant_id="verifier",
                task="Output the values of 'user_name', 'user_city', and 'missing_field'.",
                next={"state_id": "end"},
            ),
        ],
    )

    yaml_content = prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))
    created_workflow = workflow_utils.create_workflow(
        workflow_name=workflow_name,
        workflow_type=WorkflowMode.SEQUENTIAL,
        workflow_yaml=yaml_content,
    )
    workflow_cleanup.append(created_workflow)

    output = workflow_utils.execute_workflow(
        created_workflow.id,
        execution_name="verify_state",
        user_input="Start",
    )

    # Verify the output contains the extracted data
    assert_that(output, contains_string("John Doe"))
    assert_that(output, contains_string("New York"))
    assert_that(output, contains_string("N/A"))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.transform
def test_array_map_mapping(
    data_generator, result_aggregator, workflow_utils, workflow_cleanup
):
    """Test 'array_map' mapping type with filtering.

    Scenario:
    1. Init state stores list of items.
    2. Transform node extracts field from each item and filters.
    3. Final state verifies array content.
    """
    workflow_name = get_random_name()

    input_data = {
        "items": [
            {"id": 1, "status": "active", "value": 10},
            {"id": 2, "status": "inactive", "value": 20},
            {"id": 3, "status": "active", "value": 30},
        ]
    }

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("init_assistant"),
            result_aggregator("verifier"),
        ],
        custom_nodes=[
            CustomNodeModel(
                id="array_processor",
                custom_node_id="transform_node",
                config={
                    "input_source": "context_store",
                    "input_key": "data",
                    "mappings": [
                        {
                            "output_field": "all_ids",
                            "type": "array_map",
                            "source_path": "items",
                            "item_field": "id",
                        },
                        {
                            "output_field": "active_values",
                            "type": "array_map",
                            "source_path": "items",
                            "item_field": "value",
                            "filter_condition": "item.get('status') == 'active'",
                        },
                    ],
                },
            )
        ],
        states=[
            StateModel(
                id="init_state",
                assistant_id="init_assistant",
                task=f"Output exactly: {json.dumps(input_data)}",
                output_schema='{"items": "array"}',
                next={
                    "state_id": "process_array",
                    "output_key": "data",
                    "store_in_context": True,
                },
            ),
            StateModel(
                id="process_array",
                custom_node_id="array_processor",
                next={"state_id": "verify_state", "store_in_context": True},
            ),
            StateModel(
                id="verify_state",
                assistant_id="verifier",
                task="Output the values of 'all_ids' and 'active_values'.",
                next={"state_id": "end"},
            ),
        ],
    )

    yaml_content = prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))
    created_workflow = workflow_utils.create_workflow(
        workflow_name=workflow_name,
        workflow_type=WorkflowMode.SEQUENTIAL,
        workflow_yaml=yaml_content,
    )
    workflow_cleanup.append(created_workflow)

    output = workflow_utils.execute_workflow(
        created_workflow.id,
        execution_name="verify_state",
        user_input="Start",
    )

    # Verify outputs
    # ids should be [1, 2, 3]
    # active_values should be [10, 30]
    assert_that(output, contains_string("[1, 2, 3]"))
    assert_that(output, contains_string("[10, 30]"))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.transform
def test_condition_and_script_mapping(
    data_generator,
    result_aggregator,
    workflow_utils,
    workflow_cleanup,
):
    """Test 'condition' and 'script' mapping types and sequential processing.

    Scenario:
    1. Calculate a value using script.
    2. Use condition based on calculated value.
    """
    workflow_name = get_random_name()

    input_data = {"base": 10, "multiplier": 5}

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("init_assistant"),
            result_aggregator("verifier"),
        ],
        custom_nodes=[
            CustomNodeModel(
                id="logic_processor",
                custom_node_id="transform_node",
                config={
                    "input_source": "context_store",
                    "input_key": "input",
                    "mappings": [
                        # Script: calculate score
                        {
                            "output_field": "score",
                            "type": "script",
                            "script": "base * multiplier",
                        },
                        # Condition: check if score is high
                        {
                            "output_field": "is_high_score",
                            "type": "condition",
                            "condition": "score > 40",
                            "then_value": True,
                            "else_value": False,
                        },
                        # Template: generate message
                        {
                            "output_field": "message",
                            "type": "template",
                            "template": "Score is {{ score }} and is high: {{ is_high_score }}",
                        },
                    ],
                },
            )
        ],
        states=[
            StateModel(
                id="init_state",
                assistant_id="init_assistant",
                task=f"Output exactly: {json.dumps(input_data)}",
                output_schema='{"base": "integer", "multiplier": "integer"}',
                next={
                    "state_id": "process_logic",
                    "output_key": "input",
                    "store_in_context": True,
                },
            ),
            StateModel(
                id="process_logic",
                custom_node_id="logic_processor",
                next={"state_id": "verify_state", "store_in_context": True},
            ),
            StateModel(
                id="verify_state",
                assistant_id="verifier",
                task="Output the value of 'message'.",
                next={"state_id": "end"},
            ),
        ],
    )

    yaml_content = prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))
    created_workflow = workflow_utils.create_workflow(
        workflow_name=workflow_name,
        workflow_type=WorkflowMode.SEQUENTIAL,
        workflow_yaml=yaml_content,
    )
    workflow_cleanup.append(created_workflow)

    output = workflow_utils.execute_workflow(
        created_workflow.id,
        execution_name="verify_state",
        user_input="Start",
    )

    # 10 * 5 = 50, which is > 40, so is_high_score should be True
    expected_msg = "Score is 50 and is high: True"
    assert_that(output, contains_string(expected_msg))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.transform
def test_constant_mapping(
    data_generator, result_aggregator, workflow_utils, workflow_cleanup
):
    """Test 'constant' mapping type."""
    workflow_name = get_random_name()
    static_value = "I am static"
    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("init_assistant"),
            result_aggregator("verifier"),
        ],
        custom_nodes=[
            CustomNodeModel(
                id="constant_adder",
                custom_node_id="transform_node",
                config={
                    "input_source": "context_store",
                    "input_key": "input",
                    "mappings": [
                        {
                            "output_field": "static_val",
                            "type": "constant",
                            "value": static_value,
                        }
                    ],
                },
            )
        ],
        states=[
            StateModel(
                id="init_state",
                assistant_id="init_assistant",
                task='Output exactly: {"foo": "bar"}',
                output_schema='{"foo": "string"}',
                next={
                    "state_id": "process_constant",
                    "output_key": "input",
                    "store_in_context": True,
                },
            ),
            StateModel(
                id="process_constant",
                custom_node_id="constant_adder",
                next={"state_id": "verify_state", "store_in_context": True},
            ),
            StateModel(
                id="verify_state",
                assistant_id="verifier",
                task="Output the value of 'static_val'.",
                next={"state_id": "end"},
            ),
        ],
    )

    yaml_content = prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))
    created_workflow = workflow_utils.create_workflow(
        workflow_name=workflow_name,
        workflow_type=WorkflowMode.SEQUENTIAL,
        workflow_yaml=yaml_content,
    )
    workflow_cleanup.append(created_workflow)

    output = workflow_utils.execute_workflow(
        created_workflow.id,
        execution_name="verify_state",
        user_input="Start",
    )

    assert_that(output, contains_string(static_value))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.transform
@pytest.mark.parametrize(
    "on_error, default_output, expected_string, verifier_task",
    [
        pytest.param(
            "default",
            {"status": "error", "reason": "failed"},
            "error",
            "Output the value of 'status'.",
            id="on_error: default",
        ),
        pytest.param(
            "skip",
            None,
            "MISSING",
            "Output the value of 'val' or say 'MISSING' if it is not found.",
            id="on_error: skip",
        ),
    ],
)
def test_error_handling_strategies(
    data_generator,
    result_aggregator,
    workflow_utils,
    on_error,
    default_output: str,
    expected_string,
    verifier_task,
    workflow_cleanup,
):
    """Test 'on_error' strategies: default and skip.

    Scenario:
    1. Try to execute script that divides by zero.
    2. Should trigger error handling.
    3. Verify output matches strategy (default output or missing field).
    """
    workflow_name = get_random_name()

    config = {
        "input_source": "context_store",
        "input_key": "input",
        "on_error": on_error,
        "mappings": [
            {
                "output_field": "val",
                "type": "script",
                "script": "1 / 0",  # ZeroDivisionError
            }
        ],
    }

    if default_output:
        config["default_output"] = default_output

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("init_assistant"),
            result_aggregator("verifier"),
        ],
        custom_nodes=[
            CustomNodeModel(
                id="faulty_extractor",
                custom_node_id="transform_node",
                config=config,
            )
        ],
        states=[
            StateModel(
                id="init_state",
                assistant_id="init_assistant",
                task='Output exactly: {"foo": "bar"}',
                output_schema='{"foo": "string"}',
                next={
                    "state_id": "process_faulty",
                    "output_key": "input",
                    "store_in_context": True,
                },
            ),
            StateModel(
                id="process_faulty",
                custom_node_id="faulty_extractor",
                next={
                    "state_id": "verify_state",
                    "store_in_context": True,
                },
            ),
            StateModel(
                id="verify_state",
                assistant_id="verifier",
                task=verifier_task,
                next={"state_id": "end"},
            ),
        ],
    )

    yaml_content = prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))
    created_workflow = workflow_utils.create_workflow(
        workflow_name=workflow_name,
        workflow_type=WorkflowMode.SEQUENTIAL,
        workflow_yaml=yaml_content,
    )
    workflow_cleanup.append(created_workflow)

    output = workflow_utils.execute_workflow(
        created_workflow.id,
        execution_name="verify_state",
        user_input="Start",
    )

    assert_that(output, contains_string(expected_string))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.transform
def test_input_source_user_input(
    data_generator, result_aggregator, workflow_utils, workflow_cleanup
):
    """Test 'input_source: user_input'.

    Scenario:
    1. Transform node takes input directly from user_input.
    2. Extract field from JSON string provided in user_input.
    3. Final state verifies extracted value.
    """
    workflow_name = get_random_name()

    # We will pass this JSON as a string in user_input
    user_input_data = {"command": "process", "payload": {"id": 12345, "type": "order"}}
    user_input_str = json.dumps(user_input_data)

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            result_aggregator("verifier"),
        ],
        custom_nodes=[
            CustomNodeModel(
                id="input_processor",
                custom_node_id="transform_node",
                config={
                    "input_source": "user_input",
                    # No input_key needed as we parse the whole string or handle it as is
                    # Let's assume user_input is treated as the root object if it's JSON.
                    "mappings": [
                        {
                            "output_field": "command_type",
                            "type": "extract",
                            "source_path": "command",
                        },
                        {
                            "output_field": "order_id",
                            "type": "extract",
                            "source_path": "payload.id",
                        },
                    ],
                },
            )
        ],
        states=[
            StateModel(
                id="process_input",
                custom_node_id="input_processor",
                next={"state_id": "verify_state", "store_in_context": True},
            ),
            StateModel(
                id="verify_state",
                assistant_id="verifier",
                task="Output the value of 'command_type' and 'order_id'.",
                next={"state_id": "end"},
            ),
        ],
    )

    yaml_content = prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))
    created_workflow = workflow_utils.create_workflow(
        workflow_name=workflow_name,
        workflow_type=WorkflowMode.SEQUENTIAL,
        workflow_yaml=yaml_content,
    )
    workflow_cleanup.append(created_workflow)

    output = workflow_utils.execute_workflow_without_prompt_modification(
        created_workflow.id,
        execution_name="verify_state",
        user_input=user_input_str,
    )

    assert_that(output, contains_string("process"))
    assert_that(output, contains_string("12345"))
