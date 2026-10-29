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

"""Tests for the clear_prior_messages feature.

This feature controls whether the message history is cleared before
transitioning to the next state, creating a fresh LLM context.
"""

import pytest
from codemie_sdk.models.workflow import WorkflowMode
from hamcrest import assert_that, contains_string, is_not, any_of, all_of

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
def test_workflow_clear_prior_messages_false_default(
    information_provider, information_validator, workflow_utils
):
    """Test that message history is preserved by default (clear_prior_messages=false).

    Scenario:
    1. First state outputs important information
    2. Second state (default: clear_prior_messages=false)
    3. Third state asks LLM to recall information from first state
    4. Verify: LLM can see all previous messages in history
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        assistants=[
            information_provider("phase1_assistant"),
            information_validator("phase2_assistant"),
        ],
        states=[
            StateModel(
                id="provide_info",
                assistant_id="phase1_assistant",
                task=f"Say: 'The magic number is {TEST_DATA['magic_number']} and the secret word is {TEST_DATA['secret_word']}'",
                next={"state_id": "intermediate_state"},
            ),
            StateModel(
                id="intermediate_state",
                assistant_id="phase1_assistant",
                task="Say: 'Intermediate processing step'",
                next={"state_id": "recall_info"},
            ),
            StateModel(
                id="recall_info",
                assistant_id="phase2_assistant",
                task="What magic number and secret word were mentioned at the very beginning? Repeat them.",
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
        execution_name="recall_info",
        user_input="Start workflow",
    )

    # Verify LLM could recall information from first state (history preserved)
    assert_that(output, contains_string(TEST_DATA["magic_number"]))
    assert_that(output.upper(), contains_string(TEST_DATA["secret_word"]))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
def test_workflow_clear_prior_messages_true(
    information_provider, information_validator, workflow_utils
):
    """Test that message history is cleared when clear_prior_messages=true.

    Scenario:
    1. First state outputs important information
    2. Second state with clear_prior_messages=true creates fresh start
    3. Third state asks LLM to recall information from first state
    4. Verify: LLM cannot see first state's messages (history was cleared)
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        assistants=[
            information_provider("phase1_assistant"),
            information_validator("phase2_assistant"),
        ],
        states=[
            StateModel(
                id="provide_secret",
                assistant_id="phase1_assistant",
                task=f"Say: 'The secret code is {TEST_DATA['secret_code']} and file ID is {TEST_DATA['file_id']}'",
                next={"state_id": "start_new_phase"},
            ),
            StateModel(
                id="start_new_phase",
                assistant_id="phase2_assistant",
                task="Say: 'Starting new phase with fresh context'",
                next={
                    "state_id": "try_recall",
                    "clear_prior_messages": True,
                },
            ),
            StateModel(
                id="try_recall",
                assistant_id="phase2_assistant",
                task="What secret code and file ID were mentioned earlier? If you don't see them in the conversation history, say 'No previous messages visible'",
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
        execution_name="try_recall",
        user_input="Start workflow",
    ).lower()

    # Verify LLM could NOT see previous messages (history was cleared)
    assert_that(output, is_not(contains_string(TEST_DATA["secret_code"])))
    assert_that(output, is_not(contains_string(TEST_DATA["file_id"])))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
def test_workflow_clear_prior_messages_multi_phase(
    information_validator, workflow_utils
):
    """Test clear_prior_messages in multi-phase workflow with multiple clears.

    Scenario:
    1. Phase 1: State outputs data A
    2. Phase 2: Clear history, output different data B (can't see A)
    3. Phase 3: Clear history again, verify no previous data visible
    4. Verify: Each phase has isolated message history
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        assistants=[
            information_validator("multi_phase"),
        ],
        states=[
            StateModel(
                id="phase1",
                assistant_id="multi_phase",
                task=f"Say EXACTLY: 'Phase 1 complete. User: {TEST_DATA['user_id']}, Project: {TEST_DATA['project_id']}'",
                next={"state_id": "phase2", "clear_prior_messages": True},
            ),
            StateModel(
                id="phase2",
                assistant_id="multi_phase",
                task=(
                    "Say EXACTLY: 'Phase 2 starting fresh. Ready for next phase.' "
                    "Do NOT mention any IDs or previous information."
                ),
                next={"state_id": "phase3", "clear_prior_messages": True},
            ),
            StateModel(
                id="phase3",
                assistant_id="multi_phase",
                task=(
                    "IMPORTANT: Look through your entire conversation history. "
                    "List any user IDs or project IDs that you can see in previous messages. "
                    "If you cannot find ANY IDs in your conversation history, "
                    "respond with EXACTLY: 'HISTORY_CLEARED_NO_IDS_FOUND'"
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
        execution_name="phase3",
        user_input="Start workflow",
    ).lower()

    assert_that(
        output,
        any_of(
            contains_string("history_cleared_no_ids_found"),
            all_of(
                is_not(contains_string(TEST_DATA["user_id"].lower())),
                is_not(contains_string(TEST_DATA["project_id"].lower())),
            ),
        ),
        "Expected cleared history (marker present or no IDs found)",
    )
