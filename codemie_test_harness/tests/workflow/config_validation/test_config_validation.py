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

import re

import pytest
from hamcrest import assert_that, equal_to, is_in

from codemie_sdk.models.workflow import WorkflowCreateRequest
from codemie_test_harness.tests import PROJECT
from codemie_test_harness.tests.test_data.workflow_validation_messages import (
    ASSISTANT_NOT_EXIST,
    ASSISTANT_NOT_EXIST_IN_STATE,
    INVALID_YAML,
    INVALID_DATA_SOURCE,
    INVALID_TOOL,
    INVALID_STATE,
    MISSING_STATES,
    MISSING_ASSISTANT_ID,
    MISSING_SYSTEM_PROMPT,
    MISSING_TOOL_NAME,
    MISSING_TOOLS_ID,
    MISSING_TOOLS_NAME,
    MISSING_STATES_ID,
    MISSING_STATES_NEXT,
    MISSING_STATES_NEXT_CONDITION_EXPRESSION,
    MISSING_STATES_NEXT_CONDITION_THEN,
    MISSING_STATES_NEXT_CONDITION_OTHERWISE,
    MISSING_STATES_NEXT_SWITCH_CASES,
    MISSING_STATES_NEXT_SWITCH_DEFAULT,
    MISSING_STATES_NEXT_SWITCH_CASES_CONDITION,
    MISSING_STATES_NEXT_SWITCH_CASES_STATE_ID,
    INVALID_YAML_FORMAT_PROVIDED,
    # JSON format error structures
    JSON_INVALID_ASSISTANT_ID,
    JSON_INVALID_ASSISTANT_IN_STATE,
    JSON_INVALID_YAML,
    JSON_INVALID_DATA_SOURCE,
    JSON_INVALID_TOOL,
    JSON_INVALID_STATE,
    JSON_MISSING_STATES,
    JSON_MISSING_ASSISTANT_ID,
    JSON_MISSING_SYSTEM_PROMPT,
    JSON_MISSING_TOOL_NAME,
    JSON_MISSING_TOOLS_ID,
    JSON_MISSING_TOOLS_NAME,
    JSON_MISSING_STATES_ID,
    JSON_MISSING_STATES_NEXT,
    JSON_MISSING_STATES_NEXT_CONDITION_EXPRESSION,
    JSON_MISSING_STATES_NEXT_CONDITION_THEN,
    JSON_MISSING_STATES_NEXT_CONDITION_OTHERWISE,
    JSON_MISSING_STATES_NEXT_SWITCH_CASES,
    JSON_MISSING_STATES_NEXT_SWITCH_DEFAULT,
    JSON_MISSING_STATES_NEXT_SWITCH_CASES_CONDITION,
    JSON_MISSING_STATES_NEXT_SWITCH_CASES_STATE_ID,
    JSON_INVALID_YAML_FORMAT,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name

# Map of test yaml file names to expected error messages (as in Java test)
VALIDATION_TEST_DATA = [
    ("invalid_assistant_id.yaml", ASSISTANT_NOT_EXIST),
    ("invalid_assistant_in_state.yaml", ASSISTANT_NOT_EXIST_IN_STATE),
    ("invalid_yaml.yaml", INVALID_YAML),
    ("invalid_data_source.yaml", INVALID_DATA_SOURCE),
    ("invalid_tool.yaml", INVALID_TOOL),
    ("invalid_state.yaml", INVALID_STATE),
    ("missing_required_states.yaml", MISSING_STATES),
    ("missing_required_assistant_id.yaml", MISSING_ASSISTANT_ID),
    ("missing_required_system_prompt.yaml", MISSING_SYSTEM_PROMPT),
    ("missing_required_assistant_tools_name.yaml", MISSING_TOOL_NAME),
    ("missing_required_tools_id.yaml", MISSING_TOOLS_ID),
    ("missing_required_tools_name.yaml", MISSING_TOOLS_NAME),
    ("missing_required_states_id.yaml", MISSING_STATES_ID),
    ("missing_required_states_next.yaml", MISSING_STATES_NEXT),
    (
        "missing_required_states_next_condition_expression.yaml",
        MISSING_STATES_NEXT_CONDITION_EXPRESSION,
    ),
    (
        "missing_required_states_next_condition_then.yaml",
        MISSING_STATES_NEXT_CONDITION_THEN,
    ),
    (
        "missing_required_states_next_condition_otherwise.yaml",
        MISSING_STATES_NEXT_CONDITION_OTHERWISE,
    ),
    (
        "missing_required_states_next_switch_cases.yaml",
        MISSING_STATES_NEXT_SWITCH_CASES,
    ),
    (
        "missing_required_states_next_switch_default.yaml",
        MISSING_STATES_NEXT_SWITCH_DEFAULT,
    ),
    (
        "missing_required_states_next_switch_cases_condition.yaml",
        MISSING_STATES_NEXT_SWITCH_CASES_CONDITION,
    ),
    (
        "missing_required_states_next_switch_cases_state_id.yaml",
        MISSING_STATES_NEXT_SWITCH_CASES_STATE_ID,
    ),
    ("invalid_yaml_format.yaml", INVALID_YAML_FORMAT_PROVIDED),
]

# Expected error JSON structures for JSON format (error_format=json)
# These reference constants from workflow_validation_messages.py
JSON_VALIDATION_TEST_DATA = [
    ("invalid_assistant_id.yaml", JSON_INVALID_ASSISTANT_ID),
    ("invalid_assistant_in_state.yaml", JSON_INVALID_ASSISTANT_IN_STATE),
    ("invalid_yaml.yaml", JSON_INVALID_YAML),
    ("invalid_data_source.yaml", JSON_INVALID_DATA_SOURCE),
    ("invalid_tool.yaml", JSON_INVALID_TOOL),
    ("invalid_state.yaml", JSON_INVALID_STATE),
    ("missing_required_states.yaml", JSON_MISSING_STATES),
    ("missing_required_assistant_id.yaml", JSON_MISSING_ASSISTANT_ID),
    ("missing_required_system_prompt.yaml", JSON_MISSING_SYSTEM_PROMPT),
    ("missing_required_assistant_tools_name.yaml", JSON_MISSING_TOOL_NAME),
    ("missing_required_tools_id.yaml", JSON_MISSING_TOOLS_ID),
    ("missing_required_tools_name.yaml", JSON_MISSING_TOOLS_NAME),
    ("missing_required_states_id.yaml", JSON_MISSING_STATES_ID),
    ("missing_required_states_next.yaml", JSON_MISSING_STATES_NEXT),
    (
        "missing_required_states_next_condition_expression.yaml",
        JSON_MISSING_STATES_NEXT_CONDITION_EXPRESSION,
    ),
    (
        "missing_required_states_next_condition_then.yaml",
        JSON_MISSING_STATES_NEXT_CONDITION_THEN,
    ),
    (
        "missing_required_states_next_condition_otherwise.yaml",
        JSON_MISSING_STATES_NEXT_CONDITION_OTHERWISE,
    ),
    (
        "missing_required_states_next_switch_cases.yaml",
        JSON_MISSING_STATES_NEXT_SWITCH_CASES,
    ),
    (
        "missing_required_states_next_switch_default.yaml",
        JSON_MISSING_STATES_NEXT_SWITCH_DEFAULT,
    ),
    (
        "missing_required_states_next_switch_cases_condition.yaml",
        JSON_MISSING_STATES_NEXT_SWITCH_CASES_CONDITION,
    ),
    (
        "missing_required_states_next_switch_cases_state_id.yaml",
        JSON_MISSING_STATES_NEXT_SWITCH_CASES_STATE_ID,
    ),
    ("invalid_yaml_format.yaml", JSON_INVALID_YAML_FORMAT),
]

# Path to invalid config yamls (relative to repo root)
INVALID_CONFIG_PATH = "test_data/workflow/invalid_config/"


@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.parametrize(
    "file_name, expected_errors",
    VALIDATION_TEST_DATA,
    ids=[f"{getattr(row, 'values', row)[0]}" for row in VALIDATION_TEST_DATA],
)
def test_create_workflow_with_invalid_config(
    workflow_utils, file_name, expected_errors
):
    yaml_config = workflow_utils.open_workflow_yaml(INVALID_CONFIG_PATH, file_name)

    request = WorkflowCreateRequest(
        name=get_random_name(),
        description="Test Workflow",
        project=PROJECT,
        yaml_config=yaml_config,
    )

    # Attempt to create workflow with invalid YAML config
    response = workflow_utils.send_request_to_create_workflow_endpoint(request)

    message = response.get("error").get("details")
    cleaned_message = re.sub(r" {2,}", " ", message).replace("<br>", "")

    # Check if the error message matches the expected error
    assert_that(
        any(item in cleaned_message for item in expected_errors),
        "Unexpected error message in workflow creation response",
    )


@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.parametrize(
    "file_name, expected_structure",
    JSON_VALIDATION_TEST_DATA,
    ids=[
        f"{getattr(row, 'values', row)[0]}_json_format"
        for row in JSON_VALIDATION_TEST_DATA
    ],
)
def test_create_workflow_with_invalid_config_json_error_format(
    workflow_utils, file_name, expected_structure
):
    yaml_config = workflow_utils.open_workflow_yaml(INVALID_CONFIG_PATH, file_name)

    request = WorkflowCreateRequest(
        name=get_random_name(),
        description="Test Workflow",
        project=PROJECT,
        yaml_config=yaml_config,
    )

    response = workflow_utils.send_request_to_create_workflow_endpoint(
        request, error_format="json"
    )

    error = response.get("error")
    assert_that(error is not None, "Expected error in response")

    error_details = error.get("details")
    assert_that(error_details is not None, "Expected error details in response")

    # Verify that error_details is a dict (JSON format) not a string
    assert_that(
        isinstance(error_details, dict),
        f"Expected error details to be a dictionary when error_format=json, but got {type(error_details)}",
    )

    # Validate error_type
    expected_error_type = expected_structure.get("error_type")
    assert_that(error_details.get("error_type"), equal_to(expected_error_type))

    # Validate message
    expected_message = expected_structure.get("message")
    if expected_message:
        assert_that(error_details.get("message"), equal_to(expected_message))

    # Validate errors array (if specified)
    if "errors" in expected_structure:
        actual_errors = error_details.get("errors", [])
        expected_errors = expected_structure["errors"]

        assert_that(len(actual_errors), equal_to(len(expected_errors)))

        # Validate each error object
        for idx, expected_error in enumerate(expected_errors):
            actual_error = actual_errors[idx]

            for key, expected_value in expected_error.items():
                # Handle details_any for fields with multiple valid variations
                if key == "details_any":
                    actual_details = actual_error.get("details")
                    assert_that(actual_details, is_in(expected_value))
                else:
                    actual_value = actual_error.get(key)
                    assert_that(actual_value, equal_to(expected_value))
