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

"""Tests for conditional transitions in workflows.

These tests verify the behavior of conditional transitions that allow branching
based on the execution result from the previous state.

Test coverage:
- Simple numeric comparisons (>, <, >=, <=, ==, !=)
- String comparisons (==, !=)
- Logical operators (and, or, not)
- String methods (.startswith(), .endswith(), in operator)
- Special variable 'keys' for checking key existence
- Complex logical expressions
- Expression evaluation failure handling
- String boolean conversion ('true'/'false' -> boolean)
- Direct variable references (no {{}} in expressions)
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


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.conditional
def test_simple_numeric_comparison_greater_than(
    data_generator,
    result_handler,
    workflow_utils,
    workflow_cleanup,
):
    """Test conditional transition with simple numeric comparison (>).

    Scenario:
    1. First state outputs: {"count": 15}
    2. Condition: count > 10
    3. Should transition to 'then' branch
    4. Verify correct branch was executed

    Expected behavior:
    - Expression evaluates to true
    - Workflow transitions to 'then' state
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("generate_data"),
            result_handler("process_large"),
            result_handler("process_small"),
        ],
        states=[
            StateModel(
                id="generate_data",
                assistant_id="generate_data",
                task='Output exactly: {"count": 15}',
                output_schema='{"count": "number"}',
                next={
                    "condition": {
                        "expression": "count > 10",
                        "then": "process_large",
                        "otherwise": "process_small",
                    }
                },
            ),
            StateModel(
                id="process_large",
                assistant_id="process_large",
                task="Say 'Processing large batch' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="process_small",
                assistant_id="process_small",
                task="Say 'Processing small batch' and nothing else.",
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
        execution_name="process_large",
        user_input="Start",
    ).lower()

    # Verify we took the 'then' branch
    assert_that(output, contains_string("large"))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.conditional
def test_simple_numeric_comparison_less_than(
    data_generator,
    result_handler,
    workflow_utils,
    workflow_cleanup,
):
    """Test conditional transition with simple numeric comparison (<).

    Scenario:
    1. First state outputs: {"count": 5}
    2. Condition: count > 10
    3. Should transition to 'otherwise' branch
    4. Verify correct branch was executed

    Expected behavior:
    - Expression evaluates to false
    - Workflow transitions to 'otherwise' state
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("generate_data"),
            result_handler("process_large"),
            result_handler("process_small"),
        ],
        states=[
            StateModel(
                id="generate_data",
                assistant_id="generate_data",
                task='Output exactly: {"count": 5}',
                output_schema='{"count": "number"}',
                next={
                    "condition": {
                        "expression": "count > 10",
                        "then": "process_large",
                        "otherwise": "process_small",
                    }
                },
            ),
            StateModel(
                id="process_large",
                assistant_id="process_large",
                task="Say 'Processing large batch' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="process_small",
                assistant_id="process_small",
                task="Say 'Processing small batch' and nothing else.",
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
        execution_name="process_small",
        user_input="Start",
    ).lower()

    # Verify we took the 'otherwise' branch
    assert_that(output, contains_string("small"))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.conditional
def test_string_equality_comparison(
    data_generator, result_handler, workflow_utils, workflow_cleanup
):
    """Test conditional transition with string equality comparison.

    Scenario:
    1. First state outputs: {"status": "success"}
    2. Condition: status == 'success'
    3. Should transition to 'then' branch
    4. Verify correct branch was executed

    Expected behavior:
    - String comparison evaluates to true
    - Workflow transitions to 'then' state
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("check_status"),
            result_handler("next_step"),
            result_handler("error_handler"),
        ],
        states=[
            StateModel(
                id="check_status",
                assistant_id="check_status",
                task='Output exactly: {"status": "success"}',
                output_schema='{"status": "string"}',
                next={
                    "condition": {
                        "expression": "status == 'success'",
                        "then": "next_step",
                        "otherwise": "error_handler",
                    }
                },
            ),
            StateModel(
                id="next_step",
                assistant_id="next_step",
                task="Say 'Proceeding to next step' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="error_handler",
                assistant_id="error_handler",
                task="Say 'Handling error' and nothing else.",
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
        execution_name="next_step",
        user_input="Start",
    ).lower()

    # Verify we took the 'then' branch
    assert_that(output, contains_string("next step"))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.conditional
def test_complex_logical_expression_and(
    data_generator, result_handler, workflow_utils, workflow_cleanup
):
    """Test conditional transition with complex logical expression using 'and'.

    Scenario:
    1. First state outputs: {"count": 15, "status": "active"}
    2. Condition: count > 10 and status == 'active'
    3. Both conditions are true, should transition to 'then' branch
    4. Verify correct branch was executed

    Expected behavior:
    - Complex expression with 'and' evaluates to true
    - Workflow transitions to 'then' state
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("evaluate_data"),
            result_handler("process_state"),
            result_handler("skip_state"),
        ],
        states=[
            StateModel(
                id="evaluate_data",
                assistant_id="evaluate_data",
                task='Output exactly: {"count": 15, "status": "active"}',
                output_schema='{"count": "number", "status": "string"}',
                next={
                    "condition": {
                        "expression": "count > 10 and status == 'active'",
                        "then": "process_state",
                        "otherwise": "skip_state",
                    }
                },
            ),
            StateModel(
                id="process_state",
                assistant_id="process_state",
                task="Say 'Processing active state' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="skip_state",
                assistant_id="skip_state",
                task="Say 'Skipping state' and nothing else.",
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
        execution_name="process_state",
        user_input="Start",
    ).lower()

    # Verify we took the 'then' branch
    assert_that(output, contains_string("processing"))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.conditional
def test_complex_logical_expression_or(
    data_generator, result_handler, workflow_utils, workflow_cleanup
):
    """Test conditional transition with complex logical expression using 'or'.

    Scenario:
    1. First state outputs: {"count": 5, "status": "active"}
    2. Condition: count > 10 or status == 'active'
    3. First condition false, second true, should transition to 'then' branch
    4. Verify correct branch was executed

    Expected behavior:
    - Complex expression with 'or' evaluates to true
    - Workflow transitions to 'then' state
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("evaluate_data"),
            result_handler("process_state"),
            result_handler("skip_state"),
        ],
        states=[
            StateModel(
                id="evaluate_data",
                assistant_id="evaluate_data",
                task='Output exactly: {"count": 5, "status": "active"}',
                output_schema='{"count": "number", "status": "string"}',
                next={
                    "condition": {
                        "expression": "count > 10 or status == 'active'",
                        "then": "process_state",
                        "otherwise": "skip_state",
                    }
                },
            ),
            StateModel(
                id="process_state",
                assistant_id="process_state",
                task="Say 'Processing state' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="skip_state",
                assistant_id="skip_state",
                task="Say 'Skipping state' and nothing else.",
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
        execution_name="process_state",
        user_input="Start",
    ).lower()

    # Verify we took the 'then' branch
    assert_that(output, contains_string("processing"))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.conditional
def test_string_contains_check(
    data_generator, result_handler, workflow_utils, workflow_cleanup
):
    """Test conditional transition with string contains check using 'in' operator.

    Scenario:
    1. First state outputs: {"message": "Error occurred during processing"}
    2. Condition: 'error' in message.lower()
    3. Should transition to 'then' branch (error handler)
    4. Verify correct branch was executed

    Expected behavior:
    - String contains check evaluates to true
    - Workflow transitions to error handler
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("check_message"),
            result_handler("error_handler"),
            result_handler("success_state"),
        ],
        states=[
            StateModel(
                id="check_message",
                assistant_id="check_message",
                task='Output exactly: {"message": "Error occurred during processing"}',
                output_schema='{"message": "string"}',
                next={
                    "condition": {
                        "expression": "'error' in message.lower()",
                        "then": "error_handler",
                        "otherwise": "success_state",
                    }
                },
            ),
            StateModel(
                id="error_handler",
                assistant_id="error_handler",
                task="Say 'Handling error' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="success_state",
                assistant_id="success_state",
                task="Say 'Success' and nothing else.",
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
        execution_name="error_handler",
        user_input="Start",
    ).lower()

    # Verify we took the error handler branch
    assert_that(output, contains_string("error"))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.conditional
def test_key_existence_check_with_keys_variable(
    data_generator,
    result_handler,
    workflow_utils,
    workflow_cleanup,
):
    """Test conditional transition checking key existence using special 'keys' variable.

    Scenario:
    1. First state outputs: {"result": "completed", "timestamp": "2024-01-01"}
    2. Condition: 'result' in keys
    3. Should transition to 'then' branch
    4. Verify correct branch was executed

    Expected behavior:
    - Special 'keys' variable contains all dictionary keys
    - Expression evaluates to true
    - Workflow transitions to 'then' state
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("check_data"),
            result_handler("has_result"),
            result_handler("no_result"),
        ],
        states=[
            StateModel(
                id="check_data",
                assistant_id="check_data",
                task='Output exactly: {"result": "completed", "timestamp": "2024-01-01"}',
                output_schema='{"result": "string", "timestamp": "string"}',
                next={
                    "condition": {
                        "expression": "'result' in keys",
                        "then": "has_result",
                        "otherwise": "no_result",
                    }
                },
            ),
            StateModel(
                id="has_result",
                assistant_id="has_result",
                task="Say 'Result exists' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="no_result",
                assistant_id="no_result",
                task="Say 'No result' and nothing else.",
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
        execution_name="has_result",
        user_input="Start",
    ).lower()

    # Verify we took the 'has_result' branch
    assert_that(output, contains_string("result exists"))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.conditional
def test_key_existence_check_missing_key(
    data_generator,
    result_handler,
    workflow_utils,
    workflow_cleanup,
):
    """Test conditional transition checking for missing key using 'keys' variable.

    Scenario:
    1. First state outputs: {"status": "completed"}
    2. Condition: 'result' in keys
    3. Key doesn't exist, should transition to 'otherwise' branch
    4. Verify correct branch was executed

    Expected behavior:
    - Special 'keys' variable doesn't contain 'result'
    - Expression evaluates to false
    - Workflow transitions to 'otherwise' state
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("check_data"),
            result_handler("has_result"),
            result_handler("no_result"),
        ],
        states=[
            StateModel(
                id="check_data",
                assistant_id="check_data",
                task='Output exactly: {"status": "completed"}',
                output_schema='{"status": "string"}',
                next={
                    "condition": {
                        "expression": "'result' in keys",
                        "then": "has_result",
                        "otherwise": "no_result",
                    }
                },
            ),
            StateModel(
                id="has_result",
                assistant_id="has_result",
                task="Say 'Result exists' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="no_result",
                assistant_id="no_result",
                task="Say 'No result found' and nothing else.",
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
        execution_name="no_result",
        user_input="Start",
    ).lower()

    # Verify we took the 'no_result' branch
    assert_that(output, contains_string("no result"))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.conditional
def test_string_startswith_method(
    data_generator, result_handler, workflow_utils, workflow_cleanup
):
    """Test conditional transition with string .startswith() method.

    Scenario:
    1. First state outputs: {"prefix": "ERROR: System failure"}
    2. Condition: prefix.startswith('ERROR')
    3. Should transition to 'then' branch
    4. Verify correct branch was executed

    Expected behavior:
    - String method .startswith() evaluates to true
    - Workflow transitions to 'then' state
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("check_prefix"),
            result_handler("handle_error"),
            result_handler("handle_success"),
        ],
        states=[
            StateModel(
                id="check_prefix",
                assistant_id="check_prefix",
                task='Output exactly: {"prefix": "ERROR: System failure"}',
                output_schema='{"prefix": "string"}',
                next={
                    "condition": {
                        "expression": "prefix.startswith('ERROR')",
                        "then": "handle_error",
                        "otherwise": "handle_success",
                    }
                },
            ),
            StateModel(
                id="handle_error",
                assistant_id="handle_error",
                task="Say 'Error prefix detected' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="handle_success",
                assistant_id="handle_success",
                task="Say 'Success prefix detected' and nothing else.",
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
        execution_name="handle_error",
        user_input="Start",
    ).lower()

    # Verify we took the error handler branch
    assert_that(output, contains_string("error prefix"))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.conditional
def test_string_endswith_method(
    data_generator, result_handler, workflow_utils, workflow_cleanup
):
    """Test conditional transition with string .endswith() method.

    Scenario:
    1. First state outputs: {"filename": "report.pdf"}
    2. Condition: filename.endswith('.pdf')
    3. Should transition to 'then' branch
    4. Verify correct branch was executed

    Expected behavior:
    - String method .endswith() evaluates to true
    - Workflow transitions to 'then' state
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("check_filename"),
            result_handler("process_pdf"),
            result_handler("process_other"),
        ],
        states=[
            StateModel(
                id="check_filename",
                assistant_id="check_filename",
                task='Output exactly: {"filename": "report.pdf"}',
                output_schema='{"filename": "string"}',
                next={
                    "condition": {
                        "expression": "filename.endswith('.pdf')",
                        "then": "process_pdf",
                        "otherwise": "process_other",
                    }
                },
            ),
            StateModel(
                id="process_pdf",
                assistant_id="process_pdf",
                task="Say 'Processing PDF file' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="process_other",
                assistant_id="process_other",
                task="Say 'Processing other file' and nothing else.",
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
        execution_name="process_pdf",
        user_input="Start",
    ).lower()

    # Verify we took the PDF processing branch
    assert_that(output, contains_string("pdf"))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.conditional
def test_numeric_comparison_operators(
    data_generator, result_handler, workflow_utils, workflow_cleanup
):
    """Test conditional transition with various numeric comparison operators (>=, <=, !=).

    Scenario:
    1. First state outputs: {"score": 85}
    2. Condition: score >= 80 and score <= 90 and score != 75
    3. Should transition to 'then' branch
    4. Verify correct branch was executed

    Expected behavior:
    - Multiple comparison operators work correctly
    - Workflow transitions to 'then' state
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("evaluate_score"),
            result_handler("grade_b"),
            result_handler("other_grade"),
        ],
        states=[
            StateModel(
                id="evaluate_score",
                assistant_id="evaluate_score",
                task='Output exactly: {"score": 85}',
                output_schema='{"score": "number"}',
                next={
                    "condition": {
                        "expression": "score >= 80 and score <= 90 and score != 75",
                        "then": "grade_b",
                        "otherwise": "other_grade",
                    }
                },
            ),
            StateModel(
                id="grade_b",
                assistant_id="grade_b",
                task="Say 'Grade B range' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="other_grade",
                assistant_id="other_grade",
                task="Say 'Other grade range' and nothing else.",
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
        execution_name="grade_b",
        user_input="Start",
    ).lower()

    # Verify we took the grade B branch
    assert_that(output, contains_string("grade b"))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.conditional
def test_logical_not_operator(
    data_generator, result_handler, workflow_utils, workflow_cleanup
):
    """Test conditional transition with logical 'not' operator.

    Scenario:
    1. First state outputs: {"enabled": false}
    2. Condition: not enabled
    3. Should transition to 'then' branch
    4. Verify correct branch was executed

    Expected behavior:
    - Logical 'not' operator works correctly
    - Workflow transitions to 'then' state when enabled is false
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("check_enabled"),
            result_handler("handle_disabled"),
            result_handler("handle_enabled"),
        ],
        states=[
            StateModel(
                id="check_enabled",
                assistant_id="check_enabled",
                task='Output exactly: {"enabled": false}',
                output_schema='{"enabled": "boolean"}',
                next={
                    "condition": {
                        "expression": "not enabled",
                        "then": "handle_disabled",
                        "otherwise": "handle_enabled",
                    }
                },
            ),
            StateModel(
                id="handle_disabled",
                assistant_id="handle_disabled",
                task="Say 'Feature is disabled' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="handle_enabled",
                assistant_id="handle_enabled",
                task="Say 'Feature is enabled' and nothing else.",
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
        execution_name="handle_disabled",
        user_input="Start",
    ).lower()

    # Verify we took the disabled branch
    assert_that(output, contains_string("disabled"))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.conditional
def test_string_boolean_conversion(
    data_generator, result_handler, workflow_utils, workflow_cleanup
):
    """Test conditional transition with string boolean conversion.

    Scenario:
    1. First state outputs: {"flag": "true"}
    2. Condition: flag (string 'true' should convert to boolean true)
    3. Should transition to 'then' branch
    4. Verify correct branch was executed

    Expected behavior:
    - String value 'true' is converted to boolean true
    - Workflow transitions to 'then' state
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("check_flag"),
            result_handler("flag_true"),
            result_handler("flag_false"),
        ],
        states=[
            StateModel(
                id="check_flag",
                assistant_id="check_flag",
                task='Output exactly: {"flag": "true"}',
                output_schema='{"flag": "string"}',
                next={
                    "condition": {
                        "expression": "flag == True",
                        "then": "flag_true",
                        "otherwise": "flag_false",
                    }
                },
            ),
            StateModel(
                id="flag_true",
                assistant_id="flag_true",
                task="Say 'Flag is true' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="flag_false",
                assistant_id="flag_false",
                task="Say 'Flag is false' and nothing else.",
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
        execution_name="flag_true",
        user_input="Start",
    ).lower()

    # Verify we took the true branch
    assert_that(output, contains_string("flag is true"))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.conditional
def test_expression_evaluation_failure_defaults_to_otherwise(
    data_generator,
    result_handler,
    workflow_utils,
    workflow_cleanup,
):
    """Test that expression evaluation failure transitions to 'otherwise' state.

    Scenario:
    1. First state outputs: {"value": "text"}
    2. Condition: value > 10 (invalid comparison - string vs number)
    3. Expression evaluation should fail
    4. Should default to 'otherwise' branch
    5. Verify correct branch was executed

    Expected behavior:
    - Expression evaluation fails
    - Workflow transitions to 'otherwise' state as fallback
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("generate_data"),
            result_handler("success_handler"),
            result_handler("fallback_handler"),
        ],
        states=[
            StateModel(
                id="generate_data",
                assistant_id="generate_data",
                task='Output exactly: {"value": "text"}',
                output_schema='{"value": "string"}',
                next={
                    "condition": {
                        "expression": "value > 10",  # This will fail: can't compare string > int
                        "then": "success_handler",
                        "otherwise": "fallback_handler",
                    }
                },
            ),
            StateModel(
                id="success_handler",
                assistant_id="success_handler",
                task="Say 'Expression evaluated successfully' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="fallback_handler",
                assistant_id="fallback_handler",
                task="Say 'Fallback handler executed' and nothing else.",
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
        execution_name="fallback_handler",
        user_input="Start",
    ).lower()

    # Verify we took the fallback (otherwise) branch due to evaluation failure
    assert_that(output, contains_string("fallback"))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.conditional
def test_direct_variable_reference_no_curly_braces(
    data_generator,
    result_handler,
    workflow_utils,
    workflow_cleanup,
):
    """Test that variables are referenced directly without {{}} in expressions.

    Scenario:
    1. First state outputs: {"priority": "high", "level": 3}
    2. Condition: priority == 'high' and level > 2
    3. Variables referenced without {{}}
    4. Should transition to 'then' branch
    5. Verify correct branch was executed

    Expected behavior:
    - Variables referenced by name only (no {{}})
    - Expression evaluates correctly
    - Workflow transitions to 'then' state
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("evaluate_priority"),
            result_handler("high_priority_handler"),
            result_handler("low_priority_handler"),
        ],
        states=[
            StateModel(
                id="evaluate_priority",
                assistant_id="evaluate_priority",
                task='Output exactly: {"priority": "high", "level": 3}',
                output_schema='{"priority": "string", "level": "number"}',
                next={
                    "condition": {
                        "expression": "priority == 'high' and level > 2",
                        "then": "high_priority_handler",
                        "otherwise": "low_priority_handler",
                    }
                },
            ),
            StateModel(
                id="high_priority_handler",
                assistant_id="high_priority_handler",
                task="Say 'Handling high priority' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="low_priority_handler",
                assistant_id="low_priority_handler",
                task="Say 'Handling low priority' and nothing else.",
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
        execution_name="high_priority_handler",
        user_input="Start",
    ).lower()

    # Verify we took the high priority branch
    assert_that(output, contains_string("high priority"))


@pytest.mark.parametrize(
    "expression",
    [
        "value in {1, 2, 3, 4}",
        "value in [1, 2, 3, 4]",
        "value in (1, 2, 3, 4)",
    ],
    ids=["inline-set", "inline-list", "inline-tuple"],
)
@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.conditional
@pytest.mark.api
def test_conditional_inline_collection_membership_evaluates_correctly(
    expression,
    data_generator,
    result_handler,
    workflow_utils,
    workflow_cleanup,
):
    """TC-001: Conditional node correctly evaluates inline collection literal membership expressions.

    Regression test: inline set literal `value in {1,2,3,4}` raised
    SafeEvalError("Disallowed expression type: Set") before the fix.

    Scenario:
    1. First state outputs: {"value": 2}
    2. Condition: <expression> (value 2 is a member of all three literal variants)
    3. Should transition to 'then' branch (member_handler)
    4. Verify the "then"-branch response contains "set member found"

    Variants:
    - inline-set:   value in {1, 2, 3, 4}  (the bug fix — ast.Set now handled)
    - inline-list:  value in [1, 2, 3, 4]  (backward compat regression)
    - inline-tuple: value in (1, 2, 3, 4)  (backward compat regression)
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("check_membership"),
            result_handler("member_handler"),
            result_handler("nonmember_handler"),
        ],
        states=[
            StateModel(
                id="check_membership",
                assistant_id="check_membership",
                task='Output exactly: {"value": 2}',
                output_schema='{"value": "number"}',
                next={
                    "condition": {
                        "expression": expression,
                        "then": "member_handler",
                        "otherwise": "nonmember_handler",
                    }
                },
            ),
            StateModel(
                id="member_handler",
                assistant_id="member_handler",
                task="Say 'Set member found' and nothing else.",
                next={"state_id": "end"},
            ),
            StateModel(
                id="nonmember_handler",
                assistant_id="nonmember_handler",
                task="Say 'Not a set member' and nothing else.",
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

    try:
        output = workflow_utils.execute_workflow(
            created_workflow.id,
            execution_name="member_handler",
            user_input="Start",
        ).lower()
        assert_that(
            output,
            contains_string("set member found"),
            f"Expected then-branch for expression: {expression!r}",
        )
    finally:
        try:
            workflow_utils.delete_workflow(created_workflow)
        except Exception:
            pass
