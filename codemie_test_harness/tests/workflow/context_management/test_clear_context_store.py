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

"""Tests for the clear_context_store feature.

This feature controls whether the context store is cleared before
transitioning to the next state. Supports three modes:
- false (default): Context accumulates
- true: Entire context cleared (including current output)
- "keep_current": Clear old context but preserve current state output
"""

import pytest
from codemie_sdk.models.workflow import WorkflowMode
from hamcrest import assert_that, contains_string, any_of, all_of, is_not

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
def test_workflow_clear_context_store_false_default(
    data_extractor, data_processor, workflow_utils
):
    """Test that context store is preserved by default (clear_context_store=false).

    Scenario:
    1. First state outputs JSON with variables
    2. Second state outputs additional JSON (clear_context_store defaults to false)
    3. Third state accesses variables from both previous states
    4. Verify: All context accumulates (context store not cleared)
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        assistants=[
            data_extractor("data_gen"),
            data_processor("data_processor"),
        ],
        states=[
            StateModel(
                id="generate_user",
                assistant_id="data_gen",
                task=f'Output JSON: {{"user_id": "{TEST_DATA["user_id"]}"}}',
                output_schema='{"user_id": "string"}',
                next={"state_id": "generate_project"},
            ),
            StateModel(
                id="generate_project",
                assistant_id="data_gen",
                task=f'Output JSON: {{"project_id": "{TEST_DATA["project_id"]}"}}',
                output_schema='{"project_id": "string"}',
                next={"state_id": "use_both"},
            ),
            StateModel(
                id="use_both",
                assistant_id="data_processor",
                task="Confirm you have both: User ID {{user_id}} and Project ID {{project_id}}",
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
        execution_name="use_both",
        user_input="Generate data",
    )

    # Verify both variables are accessible (context preserved)
    assert_that(output, contains_string(TEST_DATA["user_id"]))
    assert_that(output, contains_string(TEST_DATA["project_id"]))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
def test_workflow_clear_context_store_true(
    data_extractor, data_processor, workflow_utils
):
    """Test that entire context store is cleared when clear_context_store=true.

    Scenario:
    1. First state outputs JSON with user_id
    2. Second state outputs JSON with project_id, sets clear_context_store=true
    3. Third state tries to access both {{user_id}} and {{project_id}}
    4. Verify: Neither variable is accessible (entire context cleared, including current)
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        assistants=[
            data_extractor("data_gen"),
            data_processor("data_processor"),
        ],
        states=[
            StateModel(
                id="generate_user",
                assistant_id="data_gen",
                task=f'Output JSON: {{"user_id": "{TEST_DATA["user_id"]}"}}',
                output_schema='{"user_id": "string"}',
                next={"state_id": "generate_project"},
            ),
            StateModel(
                id="generate_project",
                assistant_id="data_gen",
                task=f'Output JSON: {{"project_id": "{TEST_DATA["project_id"]}"}}',
                output_schema='{"project_id": "string"}',
                next={
                    "state_id": "try_access",
                    "clear_context_store": True,
                    "clear_prior_messages": True,
                },
            ),
            StateModel(
                id="try_access",
                assistant_id="data_processor",
                task=(
                    "IMPORTANT: Your task is to output JSON with two fields: user_id and project_id. "
                    "These values should be available in the workflow context. "
                    "Try to access them using template syntax: {user_id: '{{user_id}}', project_id: '{{project_id}}'}"
                ),
                output_schema='{"user_id": "string", "project_id": "string"}',
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
        execution_name="try_access",
        user_input="Generate data",
    )

    assert_that(
        output,
        any_of(
            contains_string("{{user_id}}"),
            contains_string("{{project_id}}"),
            all_of(
                is_not(contains_string(TEST_DATA["user_id"].lower())),
                is_not(contains_string(TEST_DATA["project_id"].lower())),
            ),
        ),
        "Expected context to be cleared (unresolved template syntax or no actual values present)",
    )
