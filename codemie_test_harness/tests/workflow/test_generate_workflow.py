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

"""API tests for POST /v1/workflows/generate.

Happy-path coverage only (TC-04..TC-08 of the reduced test plan). Generation is
an LLM-driven multi-step LangGraph chain, so assertions only ever check
structure/schema (node count, node types, required fields, tool-reference
resolution, output range) — never exact generated wording/content, per the
test plan's non-determinism guidance.
"""

import json

import pytest
from hamcrest import (
    assert_that,
    empty,
    equal_to,
    greater_than_or_equal_to,
    has_length,
    instance_of,
    is_in,
    is_not,
    less_than_or_equal_to,
    none,
)

from codemie_sdk.models.workflow import (
    Workflow,
    WorkflowCreateRequest,
    WorkflowGeneratorConfig,
    WorkflowGeneratorResponse,
)
from codemie_test_harness.tests import PROJECT
from codemie_test_harness.tests.test_data.workflow_generator_test_data import (
    ALTERNATE_NL_WORKFLOW_DESCRIPTION,
    EXPECTED_WORKFLOW_CONFIG_KEYS,
    RANDOM_NUMBER_NL_WORKFLOW_DESCRIPTION,
    VALID_NL_WORKFLOW_DESCRIPTION,
)
from codemie_test_harness.tests.utils.base_utils import (
    extract_last_integer,
    get_random_name,
    wait_for_entity,
)


@pytest.fixture
def generated_workflow_cleanup(client, workflow_utils):
    """Delete any workflows persisted by generate(persist=True)/create_workflow() calls.

    Supports two registration styles:
    - ``.append(workflow)`` — the Workflow object is already known.
    - ``.append_by_name(name)`` — only the name is known yet (e.g. registered
      immediately after ``create_workflow()``, before a subsequent
      list-lookup that could itself fail/time out and would otherwise leave
      the real, persisted workflow untracked).
    """
    pending_names = []

    class _Cleanup(list):
        def append_by_name(self, name: str):
            pending_names.append(name)

    tracker = _Cleanup()
    yield tracker

    for wf in tracker:
        try:
            workflow_utils.delete_workflow(wf)
        except Exception:
            pass

    for name in pending_names:
        try:
            match = None
            page_num = 0
            while True:
                workflows_page = client.workflows.list(
                    page=page_num, per_page=200, filter_by_user=True
                )
                if not workflows_page:
                    break
                match = next((w for w in workflows_page if w.name == name), None)
                if match or len(workflows_page) < 200:
                    break
                page_num += 1
            if match:
                workflow_utils.delete_workflow(match)
        except Exception:
            pass


def _extract_integer(output) -> int:
    """Extract the integer found in a workflow's raw output.

    Handles plain numeric text, JSON scalars, and single-key JSON objects,
    without assuming a specific output schema (the schema is LLM-generated).
    Text extraction is delegated to ``extract_last_integer``, which prefers
    the LAST digit sequence over the first: a response that echoes the
    "0 to 10" prompt bound (e.g. "a number between 0 and 10: 7") would
    otherwise be misread as "0" by a first-match regex.
    """
    try:
        parsed = json.loads(output) if isinstance(output, str) else output
        if isinstance(parsed, bool):
            pass
        elif isinstance(parsed, (int, float)):
            return int(parsed)
        elif isinstance(parsed, dict):
            for value in parsed.values():
                if isinstance(value, bool):
                    continue
                if isinstance(value, (int, float)):
                    return int(value)
                if isinstance(value, str):
                    return extract_last_integer(value)
    except (TypeError, ValueError):
        pass

    return extract_last_integer(output)


@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.xfail(
    reason="POST /v1/workflows/generate not deployed on backend",
    strict=False,
)
def test_generate_workflow_without_persist_returns_workflow_config(client):
    """TC-04: persist=false returns 200 with a schema-valid workflow_config, no workflow_id."""
    response = client.workflows.generate(
        text=VALID_NL_WORKFLOW_DESCRIPTION, persist=False
    )

    assert_that(response, instance_of(WorkflowGeneratorResponse))
    assert_that(response.workflow_id, none())
    assert_that(response.workflow_config, instance_of(WorkflowGeneratorConfig))
    assert_that(response.workflow_config.name, is_not(none()))
    assert_that(
        response.workflow_config.states, has_length(greater_than_or_equal_to(1))
    )

    # Schema-valid: every expected top-level key was actually present in the
    # backend's response body. `exclude_unset=True` reflects what the server
    # sent (not just the model's declared field names, which `model_dump()`
    # would return unconditionally regardless of the real payload).
    config_keys = set(response.workflow_config.model_dump(exclude_unset=True))
    missing_keys = EXPECTED_WORKFLOW_CONFIG_KEYS - config_keys
    assert_that(
        missing_keys,
        empty(),
        f"Generated workflow_config is missing expected schema keys: {missing_keys}",
    )


@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.not_for_parallel_run
@pytest.mark.xfail(
    reason="POST /v1/workflows/generate not deployed on backend",
    strict=False,
)
def test_generate_workflow_with_persist_creates_retrievable_workflow(
    client, generated_workflow_cleanup
):
    """TC-05: persist=true returns 200 with workflow_id; workflow is retrievable via get()."""
    response = client.workflows.generate(
        text=ALTERNATE_NL_WORKFLOW_DESCRIPTION, persist=True
    )

    assert_that(response.workflow_id, is_not(none()))

    workflow = client.workflows.get(response.workflow_id)
    generated_workflow_cleanup.append(workflow)

    assert_that(workflow, instance_of(Workflow))
    assert_that(workflow.id, equal_to(response.workflow_id))
    assert_that(workflow.name, equal_to(response.workflow_config.name))


@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.xfail(
    reason="POST /v1/workflows/generate not deployed on backend",
    strict=False,
)
def test_generated_workflow_config_passes_structural_validation(client):
    """TC-06: generated workflow_config has >=1 valid node with resolvable references."""
    response = client.workflows.generate(
        text=VALID_NL_WORKFLOW_DESCRIPTION, persist=False
    )
    config = response.workflow_config

    assert_that(config.states, has_length(greater_than_or_equal_to(1)))

    # A state's `assistant_id` is expected to resolve against the generated
    # assistant reference's own `id` (the state-graph node key), not the
    # `assistant_id` field on WorkflowGeneratedAssistant (which points at the
    # underlying platform assistant entity, a different identifier space).
    assistant_ids = {a.id for a in config.assistants if a.id}
    tool_ids = {
        t.get("id") for t in config.tools if isinstance(t, dict) and t.get("id")
    }

    for state in config.states:
        node_refs = [state.assistant_id, state.tool_id, state.custom_node_id]
        set_refs = [ref for ref in node_refs if ref]
        # A state may legitimately reference none of assistant_id/tool_id/
        # custom_node_id (e.g. a pure routing/decision node driven only by
        # task/next), so at most one ref is required, not exactly one.
        assert_that(
            len(set_refs),
            less_than_or_equal_to(1),
            f"State '{state.id}' must reference at most one of "
            f"assistant_id/tool_id/custom_node_id, got: {node_refs}",
        )
        if state.assistant_id:
            assert_that(
                state.assistant_id,
                is_in(assistant_ids),
                f"State '{state.id}' references unknown assistant_id '{state.assistant_id}'",
            )
        if state.tool_id:
            assert_that(
                state.tool_id,
                is_in(tool_ids),
                f"State '{state.id}' references unknown tool_id '{state.tool_id}'",
            )


@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.not_for_parallel_run
@pytest.mark.xfail(
    reason="POST /v1/workflows/generate not deployed on backend",
    strict=False,
)
def test_generated_workflow_config_can_be_saved_explicitly(
    client, workflow_utils, generated_workflow_cleanup
):
    """TC-07: a persist=false workflow_config can be passed to create_workflow() explicitly."""
    response = client.workflows.generate(
        text=VALID_NL_WORKFLOW_DESCRIPTION, persist=False
    )
    config = response.workflow_config

    assert_that(response.workflow_id, none())
    assert_that(config.yaml_config, is_not(none()))
    assert_that(config.yaml_config, is_not(empty()))

    # Review -> EDIT -> save: actually mutate the reviewed config before
    # saving, rather than forwarding it unchanged, so this test exercises the
    # "edit" half of the round trip (AC-5).
    workflow_name = get_random_name()
    edited_description = f"{config.description or 'Generated workflow'} (edited)"
    create_request = WorkflowCreateRequest(
        name=workflow_name,
        description=edited_description,
        project=config.project or PROJECT,
        yaml_config=config.yaml_config,
        mode=config.mode,
    )
    client.workflows.create_workflow(create_request)

    # Register cleanup by name immediately after the workflow is known to be
    # persisted, before the list-lookup below (which could itself time out
    # and would otherwise leave a real, persisted workflow untracked).
    generated_workflow_cleanup.append_by_name(workflow_name)

    created = wait_for_entity(
        lambda: client.workflows.list(per_page=200), entity_name=workflow_name
    )

    # The list endpoint omits yaml_config (confirmed via a live run);
    # fetch the single workflow to verify the saved content.
    saved = client.workflows.get(created.id)
    assert_that(saved.name, equal_to(workflow_name))
    assert_that(saved.description, equal_to(edited_description))
    assert_that(saved.yaml_config, is_not(none()))
    assert_that(saved.yaml_config, is_not(empty()))


@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.not_for_parallel_run
@pytest.mark.xfail(
    reason="POST /v1/workflows/generate not deployed on backend",
    strict=False,
)
def test_generated_random_number_workflow_returns_integer_in_range(
    client, workflow_utils, generated_workflow_cleanup
):
    """TC-08 (API half): generate + run a "random number 0-10" workflow; assert range only."""
    response = client.workflows.generate(
        text=RANDOM_NUMBER_NL_WORKFLOW_DESCRIPTION, persist=True
    )
    assert_that(response.workflow_id, is_not(none()))

    workflow = client.workflows.get(response.workflow_id)
    generated_workflow_cleanup.append(workflow)

    # Unique per run so wait_for_entity below can't match a stale execution
    # left behind by a prior failed/aborted run of this test.
    user_input = f"Generate the number now. [{get_random_name()}]"
    client.workflows.run(workflow.id, user_input=user_input)

    executions_service = client.workflows.executions(workflow.id)
    execution = wait_for_entity(
        lambda: executions_service.list(), entity_name=user_input
    )
    workflow_utils.wait_for_completion(
        service=executions_service, _id=execution.execution_id
    )

    states_service = executions_service.states(execution.execution_id)
    states = states_service.list(per_page=20)
    assert_that(states, has_length(greater_than_or_equal_to(1)))

    final_state = states[-1]
    workflow_utils.wait_for_completion(service=states_service, _id=final_state.id)
    output = states_service.get_output(state_id=final_state.id).output

    number = _extract_integer(output)
    assert_that(number, greater_than_or_equal_to(0))
    assert_that(number, less_than_or_equal_to(10))
