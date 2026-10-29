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

"""Behavioral tests for reset_keys_in_context_store.

SC-02: Keys listed in reset_keys_in_context_store are removed from the context
store on the transition that declares them; unlisted keys are preserved.
Covers AC-4 — existing YAML-based configuration for reset context keys works.
"""

import pytest
from hamcrest import assert_that, has_entry, is_not, has_key

from codemie_test_harness.tests.workflow.context_management import TEST_DATA

_RESET_STATE_STATUS = "reset done"


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
def test_reset_keys_removes_specified_key_preserves_others(
    reset_keys_workflow, workflow_utils
):
    """Verify reset_keys_in_context_store removes only the listed key; others remain.

    Scenario:
        1. State 1 (seed_context) outputs user_id and secret_code into context.
        2. Its transition declares reset_keys_in_context_store: ["user_id"].
        3. State 2 (reset_state) runs and transitions to verify_context.
        4. Fetch the transition into verify_context and inspect workflow_context.context_store.
        5. Assert secret_code value is preserved, status value is present,
           and user_id key is absent (removed).
    """
    created_workflow = reset_keys_workflow

    workflow_utils.execute_workflow(
        created_workflow.id,
        execution_name="verify_context",
        user_input="Start",
    )

    execution = workflow_utils.get_first_execution(created_workflow)
    execution_id = execution.execution_id

    states_service = workflow_utils.get_workflow_executions_states(
        created_workflow.id, execution_id
    )
    states = states_service.list(per_page=20)
    verify_state = next((s for s in states if s.name == "verify_context"), None)
    assert verify_state is not None, (
        "verify_context state not found in execution states"
    )

    executions_service = workflow_utils.client.workflows.executions(created_workflow.id)
    transition = executions_service.get_transition_to(execution_id, verify_state.id)
    context_store = transition.workflow_context.context_store

    assert_that(
        context_store,
        has_entry("secret_code", TEST_DATA["secret_code"]),
        "secret_code must be preserved with its original value after selective reset",
    )
    assert_that(
        context_store,
        has_entry("status", _RESET_STATE_STATUS),
        "status from reset_state must be present in context store",
    )
    assert_that(
        context_store,
        is_not(has_key("user_id")),
        "user_id must be removed from context by reset_keys_in_context_store",
    )
