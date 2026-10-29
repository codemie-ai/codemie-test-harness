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

"""Tests for the include_in_llm_history feature.

This feature controls whether state output is included in the message history
that LLM assistants see in subsequent states.
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
def test_workflow_include_in_llm_history_true_default(
    information_provider, information_validator, workflow_utils
):
    """Test that state output is included in LLM history by default (include_in_llm_history=true).

    Scenario:
    1. First state outputs important context
    2. Second state asks LLM to recall information from previous state
    3. Verify LLM can see and reference the previous state's output
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        assistants=[
            information_provider("provide_info"),
            information_validator("recall_info"),
        ],
        states=[
            StateModel(
                id="provide_info",
                assistant_id="provide_info",
                task=f"Say: 'The magic number is {TEST_DATA['magic_number']} and the secret word is {TEST_DATA['secret_word']}'",
                next={"state_id": "recall_info"},
            ),
            StateModel(
                id="recall_info",
                assistant_id="recall_info",
                task="What magic number and secret word were mentioned in the previous message? Repeat them.",
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

    # Verify LLM could recall the information from history
    assert_that(output, contains_string(TEST_DATA["magic_number"]))
    assert_that(output.upper(), contains_string(TEST_DATA["secret_word"]))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
def test_workflow_include_in_llm_history_false(
    information_provider, information_validator, workflow_utils
):
    """Test that state output is NOT included in LLM history when include_in_llm_history=false.

    Scenario:
    1. First state outputs information with include_in_llm_history=false
    2. Second state asks LLM to recall that information
    3. Verify LLM cannot see the previous state's output (was not in history)
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        assistants=[
            information_provider("hidden_info"),
            information_validator("try_recall"),
        ],
        states=[
            StateModel(
                id="hidden_info",
                assistant_id="hidden_info",
                task=f"Say: 'The secret code is {TEST_DATA['secret_code']}'",
                next={
                    "state_id": "try_recall",
                    "include_in_llm_history": False,
                    "store_in_context": True,
                },
            ),
            StateModel(
                id="try_recall",
                assistant_id="try_recall",
                task="What code was mentioned in the previous message? If you don't know, say 'No code mentioned in history'",
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
        user_input="Start",
    )

    # Verify LLM could NOT recall the hidden information
    assert_that(output, is_not(contains_string(TEST_DATA["secret_code"])))
