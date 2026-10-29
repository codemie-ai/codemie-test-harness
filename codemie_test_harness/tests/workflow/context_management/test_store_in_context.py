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

"""Tests for the store_in_context feature.

This feature controls whether state output is stored in the context store
and made available to subsequent states via {{variable}} template syntax.

Note: store_in_context=true (default) behavior is covered by test_workflow_multi_state_context_propagation
in test_context_combinations.py which is more reliable.
"""

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
def test_workflow_store_in_context_true_default(
    data_extractor, data_processor, workflow_utils
):
    """Test that state output is stored in context by default (store_in_context=true).

    Scenario:
    1. First state outputs JSON with a variable: {"user_id": "12345"}
    2. Second state references that variable using {{user_id}}
    3. Verify second state can access the variable (confirms it was stored in context)
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        assistants=[
            data_extractor("extract_data"),
            data_processor("process_data"),
        ],
        states=[
            StateModel(
                id="extract_data",
                assistant_id="extract_data",
                task=f'Extract the user ID from the input and output it as JSON: {{"user_id": "{TEST_DATA["user_id"]}"}}',
                output_schema='{"user_id": "string"}',
                next={"state_id": "process_data"},
            ),
            StateModel(
                id="process_data",
                assistant_id="process_data",
                task=(
                    "Access the user_id from context: {{user_id}}. "
                    "If you see the actual value (not {{user_id}} as literal text), "
                    "say 'Context variable resolved: ' followed by the actual user_id value. "
                    "If you see {{user_id}} as literal curly braces, say 'Variable not resolved'."
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
        execution_name="process_data",
        user_input="Please extract the user ID",
    ).lower()

    # Verify the context variable was resolved (store_in_context worked)
    assert_that(output, contains_string("context variable resolved"))
    assert_that(output, contains_string(TEST_DATA["user_id"]))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
def test_workflow_store_in_context_false(data_extractor, workflow_utils):
    """Test that state output is NOT stored in context when store_in_context=false.

    Scenario:
    1. First state outputs JSON with a variable: {"secret_data": "hidden123"}
    2. Explicitly set store_in_context=false for first state
    3. Second state tries to reference {{secret_data}}
    4. Verify second state cannot access the variable (it was not stored)
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        assistants=[
            data_extractor("data_generator"),
        ],
        states=[
            StateModel(
                id="generate_secret",
                assistant_id="data_generator",
                task=f'Output this exact JSON: {{"secret_code": "{TEST_DATA["secret_code"]}"}}',
                output_schema='{"secret_code": "string"}',
                next={
                    "state_id": "try_access_secret",
                    "store_in_context": False,
                    "include_in_llm_history": False,
                },
            ),
            StateModel(
                id="try_access_secret",
                assistant_id="data_generator",
                task=(
                    "Try to access the secret_code variable: {{secret_code}}. "
                    "If you see the literal '{{secret_code}}' text (not a value), say 'Variable not in context'. "
                    "Otherwise, confirm the secret_code value."
                ),
                resolve_dynamic_values_in_prompt=True,
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
        execution_name="try_access_secret",
        user_input="Start the workflow",
    ).lower()

    # Verify the variable was NOT resolved (store_in_context=false prevented storage)
    assert_that(output, contains_string("not in context"))
    # Verify the actual value is NOT present (it wasn't stored)
    assert_that(output, is_not(contains_string(TEST_DATA["secret_code"])))
