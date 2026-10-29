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

"""Tests for combined context and message clearing operations.

These tests verify how clear_prior_messages and clear_context_store
work together to provide fine-grained control over workflow state.
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
def test_workflow_clear_context_and_messages_combined(
    data_extractor, information_validator, workflow_utils
):
    """Test combination of clear_prior_messages=true and clear_context_store=true.

    Scenario:
    1. First state outputs data in both context and history
    2. Second state clears both context and message history
    3. Third state: LLM has no history, template variables not available
    4. Verify: Complete fresh start (no context, no history)
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        assistants=[
            data_extractor("phase1"),
            information_validator("phase2"),
        ],
        states=[
            StateModel(
                id="phase1_data",
                assistant_id="phase1",
                task=f'Say: "Starting with secret {TEST_DATA["secret_code"]}". Then output JSON: {{"user_id": "{TEST_DATA["user_id"]}"}}',
                output_schema='{"user_id": "string"}',
                next={"state_id": "phase2_transition"},
            ),
            StateModel(
                id="phase2_transition",
                assistant_id="phase2",
                task="Say: 'Preparing for complete reset'",
                next={
                    "state_id": "phase2_fresh",
                    "clear_prior_messages": True,
                    "clear_context_store": True,
                },
            ),
            StateModel(
                id="phase2_fresh",
                assistant_id="phase2",
                task=(
                    "Check context: User ID is {{user_id}}. "
                    "Can you see any secret code in the conversation history? "
                    "If you see {{user_id}} as literal text (not a value), say 'Complete fresh start'"
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
        execution_name="phase2_fresh",
        user_input="Start workflow",
    ).lower()

    # Verify context is empty (no user_id value)
    assert_that(output, contains_string("fresh start"))
    # Verify history is empty (no secret_code visible)
    assert_that(output, is_not(contains_string(TEST_DATA["secret_code"])))


@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
def test_workflow_clear_context_keep_current_with_clear_messages(
    data_extractor, information_validator, workflow_utils
):
    """Test combination of clear_prior_messages=true and clear_context_store='keep_current'.

    Scenario:
    1. First state outputs old data
    2. Second state outputs new data with keep_current + clear_messages
    3. Third state: Has access to new context but not old history
    4. Verify: Fresh history but current context preserved
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        assistants=[
            data_extractor("phase_assistant"),
            information_validator("validator"),
        ],
        states=[
            StateModel(
                id="old_phase",
                assistant_id="phase_assistant",
                task=f'Say "Old phase with secret {TEST_DATA["secret_code"]}". Output: {{"old_data": "deprecated"}}',
                output_schema='{"old_data": "string"}',
                next={"state_id": "new_phase"},
            ),
            StateModel(
                id="new_phase",
                assistant_id="phase_assistant",
                task=f'Output fresh data: {{"new_data": "{TEST_DATA["magic_number"]}", "status": "active"}}',
                output_schema='{"new_data": "string", "status": "string"}',
                next={
                    "state_id": "validate",
                    "clear_context_store": "keep_current",
                    "clear_prior_messages": True,
                },
            ),
            StateModel(
                id="validate",
                assistant_id="validator",
                task=(
                    "Report available data: New Data={{new_data}}, Status={{status}}, Old Data={{old_data}}. "
                    "Can you see any secret code in the conversation history? Answer yes or no. "
                    "Which variables have actual values?"
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
        execution_name="validate",
        user_input="Start workflow",
    ).lower()

    # Verify current context is preserved
    assert_that(output, contains_string(TEST_DATA["magic_number"]))
    assert_that(output, contains_string("active"))
    # Verify old context is cleared
    assert_that(output, is_not(contains_string("deprecated")))
    # Verify history is cleared (no secret visible)
    assert_that(output, is_not(contains_string(TEST_DATA["secret_code"])))
