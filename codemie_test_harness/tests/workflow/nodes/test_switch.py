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

"""Tests for switch/case transitions in workflows.

These tests verify the behavior of switch/case transitions that provide multiple
conditional branches evaluated sequentially until one matches.

Test coverage:
- Status-based routing (string equality)
- Numeric range routing (order matters - first match wins)
- Complex conditions with logical operators
- Type-based routing with string methods
- Default state handling when no cases match
- Order evaluation (first match wins with overlapping conditions)
- Case condition evaluation failure (continues to next case)
- Multiple variables in switch conditions
- Required default state
"""

import pytest
from codemie_sdk.models.workflow import WorkflowMode
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.yaml_utils import (
    StateModel,
    WorkflowYamlModel,
    prepare_yaml_content,
)
from hamcrest import (
    assert_that,
    contains_string,
)

status_cases = [
    {
        "condition": "status == 'completed'",
        "state_id": "success_state",
    },
    {
        "condition": "status == 'pending'",
        "state_id": "wait_state",
    },
    {
        "condition": "status == 'failed'",
        "state_id": "retry_state",
    },
]


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.switch
def test_status_based_routing_completed(
    data_generator, result_handler, workflow_utils, workflow_cleanup
):
    """Test switch/case transition with status-based routing - completed status.

    Scenario:
    1. First state outputs: {"status": "completed"}
    2. Switch with cases: completed -> success-state, pending -> wait-state, failed -> retry-state
    3. Should match first case and transition to success-state
    4. Verify correct branch was executed

    Expected behavior:
    - First case matches (status == 'completed')
    - Workflow transitions to success-state
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("check_status"),
            result_handler("success_state"),
            result_handler("wait_state"),
            result_handler("retry_state"),
            result_handler("error_state"),
        ],
        states=[
            StateModel(
                id="check_status",
                assistant_id="check_status",
                task='Output exactly: {"status": "completed"}',
                output_schema='{"status": "string"}',
                next={
                    "switch": {
                        "cases": status_cases,
                        "default": "error_state",
                    }
                },
            ),
            StateModel(
                id="success_state",
                assistant_id="success_state",
                task="Say 'Success state reached' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="wait_state",
                assistant_id="wait_state",
                task="Say 'Wait state reached' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="retry_state",
                assistant_id="retry_state",
                task="Say 'Retry state reached' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="error_state",
                assistant_id="error_state",
                task="Say 'Error state reached' and nothing else.",
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
        execution_name="success_state",
        user_input="Start",
    ).lower()

    # Verify we reached the success state
    assert_that(output, contains_string("success state reached"))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.switch
def test_status_based_routing_pending(
    data_generator, result_handler, workflow_utils, workflow_cleanup
):
    """Test switch/case transition with status-based routing - pending status.

    Scenario:
    1. First state outputs: {"status": "pending"}
    2. Switch evaluates cases in order
    3. Should match second case and transition to wait-state
    4. Verify correct branch was executed

    Expected behavior:
    - Second case matches (status == 'pending')
    - Workflow transitions to wait-state
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("check_status"),
            result_handler("success_state"),
            result_handler("wait_state"),
            result_handler("retry_state"),
            result_handler("error_state"),
        ],
        states=[
            StateModel(
                id="check_status",
                assistant_id="check_status",
                task='Output exactly: {"status": "pending"}',
                output_schema='{"status": "string"}',
                next={
                    "switch": {
                        "cases": status_cases,
                        "default": "error_state",
                    }
                },
            ),
            StateModel(
                id="success_state",
                assistant_id="success_state",
                task="Say 'Success state reached' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="wait_state",
                assistant_id="wait_state",
                task="Say 'Wait state reached' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="retry_state",
                assistant_id="retry_state",
                task="Say 'Retry state reached' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="error_state",
                assistant_id="error_state",
                task="Say 'Error state reached' and nothing else.",
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
        execution_name="wait_state",
        user_input="Start",
    ).lower()

    # Verify we reached the wait state
    assert_that(output, contains_string("wait state reached"))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.switch
def test_default_state_when_no_cases_match(
    data_generator,
    result_handler,
    workflow_utils,
    workflow_cleanup,
):
    """Test switch/case transition with default state when no cases match.

    Scenario:
    1. First state outputs: {"status": "unknown"}
    2. Switch evaluates all cases - none match
    3. Should transition to default state
    4. Verify correct branch was executed

    Expected behavior:
    - No cases match
    - Workflow transitions to default state (error_state)
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("check_status"),
            result_handler("success_state"),
            result_handler("wait_state"),
            result_handler("retry_state"),
            result_handler("error_state"),
        ],
        states=[
            StateModel(
                id="check_status",
                assistant_id="check_status",
                task='Output exactly: {"status": "unknown"}',
                output_schema='{"status": "string"}',
                next={
                    "switch": {
                        "cases": status_cases,
                        "default": "error_state",
                    }
                },
            ),
            StateModel(
                id="success_state",
                assistant_id="success_state",
                task="Say 'Success state reached' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="wait_state",
                assistant_id="wait_state",
                task="Say 'Wait state reached' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="retry_state",
                assistant_id="retry_state",
                task="Say 'Retry state reached' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="error_state",
                assistant_id="error_state",
                task="Say 'Error state reached' and nothing else.",
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
        execution_name="error_state",
        user_input="Start",
    ).lower()

    # Verify we reached the default error state
    assert_that(output, contains_string("error state reached"))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.switch
@pytest.mark.parametrize(
    "score_task, expected_handler, expected_text",
    [
        ('Output exactly: {"score": 95}', "excellent_handler", "excellent"),
        ('Output exactly: {"score": 75}', "good_handler", "good"),
        ('Output exactly: {"score": 30}', "poor_handler", "poor"),
    ],
)
def test_numeric_range_routing(
    data_generator,
    result_handler,
    workflow_utils,
    score_task,
    expected_handler,
    expected_text,
    workflow_cleanup,
):
    """Test switch/case with numeric range routing.

    Scenarios:
    1. Score 95 -> Excellent (>= 90)
    2. Score 75 -> Good (>= 70)
    3. Score 30 -> Poor (Default < 50)
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("evaluate_score"),
            result_handler("excellent_handler"),
            result_handler("good_handler"),
            result_handler("average_handler"),
            result_handler("poor_handler"),
        ],
        states=[
            StateModel(
                id="evaluate_score",
                assistant_id="evaluate_score",
                task=score_task,
                output_schema='{"score": "number"}',
                next={
                    "switch": {
                        "cases": [
                            {
                                "condition": "score >= 90",
                                "state_id": "excellent_handler",
                            },
                            {"condition": "score >= 70", "state_id": "good_handler"},
                            {"condition": "score >= 50", "state_id": "average_handler"},
                        ],
                        "default": "poor_handler",
                    }
                },
            ),
            StateModel(
                id="excellent_handler",
                assistant_id="excellent_handler",
                task="Say 'Excellent grade' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="good_handler",
                assistant_id="good_handler",
                task="Say 'Good grade' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="average_handler",
                assistant_id="average_handler",
                task="Say 'Average grade' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="poor_handler",
                assistant_id="poor_handler",
                task="Say 'Poor grade' and nothing else.",
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
        execution_name=expected_handler,
        user_input="Start",
    ).lower()

    # Verify we reached the expected handler
    assert_that(output, contains_string(expected_text))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.switch
def test_complex_conditions_with_logical_operators(
    data_generator,
    result_handler,
    workflow_utils,
    workflow_cleanup,
):
    """Test switch/case with complex conditions using logical operators.

    Scenario:
    1. First state outputs: {"error_count": 0, "status": "complete"}
    2. Switch with complex conditions:
       - error_count == 0 and status == 'complete' -> success
       - error_count > 0 and error_count < 5 -> partial success
       - error_count >= 5 -> failure
    3. Should match first case
    4. Verify correct branch was executed

    Expected behavior:
    - Complex condition with 'and' evaluates correctly
    - First case matches
    - Workflow transitions to success-state
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("evaluate_results"),
            result_handler("success_state"),
            result_handler("partial_success_state"),
            result_handler("failure_state"),
            result_handler("unknown_state"),
        ],
        states=[
            StateModel(
                id="evaluate_results",
                assistant_id="evaluate_results",
                task='Output exactly: {"error_count": 0, "status": "complete"}',
                output_schema='{"error_count": "number", "status": "string"}',
                next={
                    "switch": {
                        "cases": [
                            {
                                "condition": "error_count == 0 and status == 'complete'",
                                "state_id": "success_state",
                            },
                            {
                                "condition": "error_count > 0 and error_count < 5",
                                "state_id": "partial_success_state",
                            },
                            {
                                "condition": "error_count >= 5",
                                "state_id": "failure_state",
                            },
                        ],
                        "default": "unknown_state",
                    }
                },
            ),
            StateModel(
                id="success_state",
                assistant_id="success_state",
                task="Say 'Complete success' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="partial_success_state",
                assistant_id="partial_success_state",
                task="Say 'Partial success' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="failure_state",
                assistant_id="failure_state",
                task="Say 'Failure state' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="unknown_state",
                assistant_id="unknown_state",
                task="Say 'Unknown state' and nothing else.",
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
        execution_name="success_state",
        user_input="Start",
    ).lower()

    # Verify we reached the success state
    assert_that(output, contains_string("complete success"))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.switch
@pytest.mark.parametrize(
    "type_task, expected_handler, expected_text",
    [
        ('Output exactly: {"type": "EMAIL_NOTIFICATION"}', "email_processor", "email"),
        ('Output exactly: {"type": "sms_alert"}', "sms_processor", "sms"),
        ('Output exactly: {"type": "fax"}', "unsupported_handler", "unsupported"),
    ],
)
def test_type_based_routing(
    data_generator,
    result_handler,
    workflow_utils,
    type_task,
    expected_handler,
    expected_text,
    workflow_cleanup,
):
    """Test switch/case with type-based routing using string methods.

    Scenarios:
    1. Type 'EMAIL_NOTIFICATION' -> Email Processor ('email' in type.lower())
    2. Type 'sms_alert' -> SMS Processor ('sms' in type.lower())
    3. Type 'fax' -> Unsupported (Default - no match)
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("identify_type"),
            result_handler("email_processor"),
            result_handler("sms_processor"),
            result_handler("push_processor"),
            result_handler("unsupported_handler"),
        ],
        states=[
            StateModel(
                id="identify_type",
                assistant_id="identify_type",
                task=type_task,
                output_schema="""
                    {                                                                                                                                                                                                                                
                        "type": "object",                                                                                                                                                                                                              
                        "properties": {                                                                                                                                                                                                                
                            "type": {                                                                                                                                                                                                                    
                                "type": "string"                                                                                                                                                                                                           
                            }                                                                                                                                                                                                                            
                        },
                        "required": ["type"]
                    }
                """,
                next={
                    "switch": {
                        "cases": [
                            {
                                "condition": "'email' in type.lower()",
                                "state_id": "email_processor",
                            },
                            {
                                "condition": "'sms' in type.lower()",
                                "state_id": "sms_processor",
                            },
                            {
                                "condition": "'push' in type.lower()",
                                "state_id": "push_processor",
                            },
                        ],
                        "default": "unsupported_handler",
                    }
                },
            ),
            StateModel(
                id="email_processor",
                assistant_id="email_processor",
                task="Say 'Processing email' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="sms_processor",
                assistant_id="sms_processor",
                task="Say 'Processing SMS' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="push_processor",
                assistant_id="push_processor",
                task="Say 'Processing push notification' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="unsupported_handler",
                assistant_id="unsupported_handler",
                task="Say 'Unsupported type' and nothing else.",
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
        execution_name=expected_handler,
        user_input="Start",
    ).lower()

    # Verify we reached the expected handler
    assert_that(output, contains_string(expected_text))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.switch
def test_first_match_wins_with_overlapping_conditions(
    data_generator,
    result_handler,
    workflow_utils,
    workflow_cleanup,
):
    """Test that first matching case wins when conditions overlap.

    Scenario:
    1. First state outputs: {"value": 95}
    2. Switch with overlapping conditions:
       - value > 90 -> handler_a
       - value > 80 -> handler_b (also matches but shouldn't be reached)
       - value > 70 -> handler_c (also matches but shouldn't be reached)
    3. Should match first case only
    4. Verify correct branch was executed

    Expected behavior:
    - Order matters - first match wins
    - Even though all three conditions are true, only first executes
    - Workflow transitions to handler_a
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("evaluate_value"),
            result_handler("handler_a"),
            result_handler("handler_b"),
            result_handler("handler_c"),
            result_handler("handler_default"),
        ],
        states=[
            StateModel(
                id="evaluate_value",
                assistant_id="evaluate_value",
                task='Output exactly: {"value": 95}',
                output_schema='{"value": "number"}',
                next={
                    "switch": {
                        "cases": [
                            {"condition": "value > 90", "state_id": "handler_a"},
                            {"condition": "value > 80", "state_id": "handler_b"},
                            {"condition": "value > 70", "state_id": "handler_c"},
                        ],
                        "default": "handler_default",
                    }
                },
            ),
            StateModel(
                id="handler_a",
                assistant_id="handler_a",
                task="Say 'Handler A executed' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="handler_b",
                assistant_id="handler_b",
                task="Say 'Handler B executed' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="handler_c",
                assistant_id="handler_c",
                task="Say 'Handler C executed' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="handler_default",
                assistant_id="handler_default",
                task="Say 'Default handler executed' and nothing else.",
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
        execution_name="handler_a",
        user_input="Start",
    ).lower()

    # Verify we reached handler A only (first match)
    assert_that(output, contains_string("handler a"))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.switch
def test_case_condition_evaluation_failure_continues(
    data_generator,
    result_handler,
    workflow_utils,
    workflow_cleanup,
):
    """Test that case condition evaluation failure is treated as false and continues.

    Scenario:
    1. First state outputs: {"value": "text", "status": "success"}
    2. Switch with cases:
       - value > 10 (will fail - can't compare string to int)
       - status == 'success' (should match and execute)
    3. First case fails, second case should match
    4. Verify correct branch was executed

    Expected behavior:
    - First case evaluation fails, treated as false
    - Evaluation continues to next case
    - Second case matches
    - Workflow transitions to success-handler
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("evaluate_data"),
            result_handler("numeric_handler"),
            result_handler("success_handler"),
            result_handler("default_handler"),
        ],
        states=[
            StateModel(
                id="evaluate_data",
                assistant_id="evaluate_data",
                task='Output exactly: {"value": "text", "status": "success"}',
                output_schema='{"value": "string", "status": "string"}',
                next={
                    "switch": {
                        "cases": [
                            {"condition": "value > 10", "state_id": "numeric_handler"},
                            {
                                "condition": "status == 'success'",
                                "state_id": "success_handler",
                            },
                        ],
                        "default": "default_handler",
                    }
                },
            ),
            StateModel(
                id="numeric_handler",
                assistant_id="numeric_handler",
                task="Say 'Numeric handler' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="success_handler",
                assistant_id="success_handler",
                task="Say 'Success handler' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="default_handler",
                assistant_id="default_handler",
                task="Say 'Default handler' and nothing else.",
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
        execution_name="success_handler",
        user_input="Start",
    ).lower()

    # Verify we reached success handler (second case)
    assert_that(output, contains_string("success"))
