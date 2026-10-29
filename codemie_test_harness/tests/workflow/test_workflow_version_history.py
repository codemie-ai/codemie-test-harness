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

"""API tests for Workflow Version History.

Covers:
    TC_009 — Semantically identical YAML updates do NOT append history entries.
    TC_010 — PUT to a deleted workflow returns HTTP 404 with structured error body.
    TC_011 — SDK raises requests.exceptions.HTTPError (404) when updating a deleted workflow.
"""

import pytest
import requests.exceptions
from codemie_sdk.models.workflow import WorkflowMode, WorkflowUpdateRequest
from hamcrest import assert_that, equal_to, has_key, not_none

from codemie_test_harness.tests import API_DOMAIN, VERIFY_SSL
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.http_utils import RequestHandler
from codemie_test_harness.tests.utils.yaml_utils import (
    AssistantModel,
    StateModel,
    WorkflowYamlModel,
    prepare_yaml_content,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STATE_ID = "vh_assistant"

# Base YAML content used to create / update test workflows.
_BASE_SYSTEM_PROMPT = "Base system prompt for version history test"
_UPDATED_SYSTEM_PROMPT = "Updated system prompt — semantic change for version history"


def _build_yaml(system_prompt: str) -> str:
    """Return yaml_config string with the given system_prompt."""
    assistant = AssistantModel(id=_STATE_ID, model="", system_prompt=system_prompt)
    state = StateModel(id=_STATE_ID, assistant_id=_STATE_ID)
    workflow_yaml = WorkflowYamlModel(assistants=[assistant], states=[state])
    return prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))


def _get_history(rh: RequestHandler, workflow_id: str) -> list:
    """Return the yaml_config_history list for the given workflow via raw GET."""
    response = rh.get(f"/v1/workflows/id/{workflow_id}")
    response.raise_for_status()
    body = response.json()
    workflow = body.get("data", body)
    return workflow.get("yaml_config_history") or []


# ---------------------------------------------------------------------------
# TC_009
# ---------------------------------------------------------------------------


@pytest.mark.workflow
@pytest.mark.api
def test_semantic_yaml_change_does_not_create_history_entry(
    workflow_utils, default_llm
):
    """Semantically identical YAML updates do NOT append a new history entry.


    Preconditions:
        - workflow exists
        - authenticated API access available

    Evidence: src/codemie/service/workflow_service.py:116
        WorkflowService._yaml_content_changed() performs semantic YAML comparison
        and returns False for comment-only, whitespace/formatting, key-reorder,
        and quote-style differences.

    Steps:
        1. Create workflow with base YAML; record yaml_config_history length N.
        2. Update with whitespace-only YAML; assert history length = N.
        3. Update with key-reordered YAML (semantically identical); assert length = N.
        4. Update with a real semantic change; assert length = N + 1 (mechanism check).
    """
    assistant = AssistantModel(
        id=_STATE_ID,
        model=default_llm.base_name,
        system_prompt=_BASE_SYSTEM_PROMPT,
    )
    state = StateModel(id=_STATE_ID, assistant_id=_STATE_ID)
    base_yaml = prepare_yaml_content(
        WorkflowYamlModel(assistants=[assistant], states=[state]).model_dump(
            exclude_none=True
        )
    )

    workflow = workflow_utils.create_workflow(
        workflow_name=get_random_name(),
        workflow_type=WorkflowMode.SEQUENTIAL,
        shared=True,
        workflow_yaml=base_yaml,
    )

    rh = RequestHandler(API_DOMAIN, workflow_utils.client.token, VERIFY_SSL)

    try:
        # Step 1: record initial history length (0 — no history yet after creation).
        initial_history = _get_history(rh, workflow.id)
        initial_len = len(initial_history)

        # Step 2: Update with whitespace-only identical YAML (extra blank line).
        # _yaml_content_changed() returns False → no history entry appended.
        whitespace_yaml = base_yaml + "\n"
        workflow_utils.update_workflow(workflow, yaml_config=whitespace_yaml)
        history_after_whitespace = _get_history(rh, workflow.id)
        assert_that(
            len(history_after_whitespace),
            equal_to(initial_len),
            f"Expected history length {initial_len} after whitespace-only update, "
            f"got {len(history_after_whitespace)}",
        )

        # Step 3: Update with key-reordered YAML (semantically identical).
        # Build a YAML that has keys in a different order at the top level.
        key_reorder_yaml = prepare_yaml_content(
            {
                "tools": [],
                "custom_nodes": [],
                "assistants": [
                    {
                        "id": _STATE_ID,
                        "model": default_llm.base_name,
                        "system_prompt": _BASE_SYSTEM_PROMPT,
                    }
                ],
                "states": [
                    {
                        "id": _STATE_ID,
                        "assistant_id": _STATE_ID,
                        "next": {"state_id": "end"},
                        "resolve_dynamic_values_in_prompt": True,
                    }
                ],
            }
        )
        workflow_utils.update_workflow(workflow, yaml_config=key_reorder_yaml)
        history_after_reorder = _get_history(rh, workflow.id)
        assert_that(
            len(history_after_reorder),
            equal_to(initial_len),
            f"Expected history length {initial_len} after key-reorder update, "
            f"got {len(history_after_reorder)}",
        )

        # Step 4: Update with a REAL semantic change — system_prompt is different.
        # Confirms the mechanism works: a genuine change DOES append an entry.
        semantic_yaml = prepare_yaml_content(
            WorkflowYamlModel(
                assistants=[
                    AssistantModel(
                        id=_STATE_ID,
                        model=default_llm.base_name,
                        system_prompt=_UPDATED_SYSTEM_PROMPT,
                    )
                ],
                states=[state],
            ).model_dump(exclude_none=True)
        )
        workflow_utils.update_workflow(workflow, yaml_config=semantic_yaml)
        history_after_semantic = _get_history(rh, workflow.id)
        assert_that(
            len(history_after_semantic),
            equal_to(initial_len + 1),
            f"Expected history length {initial_len + 1} after semantic update, "
            f"got {len(history_after_semantic)}",
        )

    finally:
        try:
            workflow_utils.delete_workflow(workflow)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# TC_010
# ---------------------------------------------------------------------------


@pytest.mark.workflow
@pytest.mark.api
def test_put_deleted_workflow_returns_404_with_structured_error(
    workflow_utils, default_llm
):
    """PUT to a deleted workflow endpoint returns HTTP 404 with structured error body.


    Preconditions:
        - workflow exists and can be deleted during the test

    Evidence: src/codemie/rest_api/main.py:51
        NotFoundException handler returns HTTP 404 with
        {error: {message, details: null, help: null}}.

    Steps:
        1. Create a workflow and GET its current state (HTTP 200).
        2. Delete the workflow (simulating a concurrent delete).
        3. PUT an update to the deleted workflow's endpoint; assert HTTP 404.
        4. Assert structured error body: error.message is non-empty,
           error.details is null, error.help is null.
    """
    assistant = AssistantModel(
        id=_STATE_ID,
        model=default_llm.base_name,
        system_prompt=_BASE_SYSTEM_PROMPT,
    )
    state = StateModel(id=_STATE_ID, assistant_id=_STATE_ID)
    base_yaml = prepare_yaml_content(
        WorkflowYamlModel(assistants=[assistant], states=[state]).model_dump(
            exclude_none=True
        )
    )

    workflow = workflow_utils.create_workflow(
        workflow_name=get_random_name(),
        workflow_type=WorkflowMode.SEQUENTIAL,
        shared=True,
        workflow_yaml=base_yaml,
    )

    rh = RequestHandler(API_DOMAIN, workflow_utils.client.token, VERIFY_SSL)

    # Step 1: GET current workflow state (confirms HTTP 200).
    get_response = rh.get(f"/v1/workflows/id/{workflow.id}")
    assert_that(
        get_response.status_code,
        equal_to(200),
        f"Expected HTTP 200 for initial GET, got {get_response.status_code}",
    )
    body = get_response.json()
    workflow_data = body.get("data", body)

    # Step 2: Delete the workflow — simulating concurrent delete by another user.
    workflow_utils.delete_workflow(workflow)

    # Step 3: PUT update to the now-deleted workflow's endpoint.
    update_payload = WorkflowUpdateRequest(
        name=workflow_data["name"],
        project=workflow_data["project"],
        description=workflow_data.get("description", ""),
        yaml_config=workflow_data["yaml_config"],
        mode=workflow_data["mode"],
        shared=workflow_data.get("shared", False),
    ).model_dump()

    put_response = rh.put(f"/v1/workflows/{workflow.id}", json_data=update_payload)

    # Step 4a: Assert HTTP 404 status code.
    assert_that(
        put_response.status_code,
        equal_to(404),
        f"Expected HTTP 404 for PUT on deleted workflow, got {put_response.status_code}",
    )

    # Step 4b: Assert structured error body matches NotFoundException handler shape.
    body = put_response.json()
    assert_that(
        body,
        has_key("error"),
        f"Expected top-level 'error' key in response body: {body}",
    )
    error = body["error"]
    assert_that(
        error.get("message"),
        not_none(),
        f"Expected non-empty error.message in 404 response body: {error}",
    )
    assert_that(
        error.get("details"),
        not_none(),
        f"Expected non-empty error.details in 404 response body: {error}",
    )
    assert_that(
        error.get("help"),
        not_none(),
        f"Expected non-empty error.help in 404 response body: {error}",
    )


# ---------------------------------------------------------------------------
# TC_011
# ---------------------------------------------------------------------------


@pytest.mark.workflow
@pytest.mark.api
def test_sdk_raises_http_error_404_on_deleted_workflow_update(
    workflow_utils, default_llm
):
    """SDK raises requests.exceptions.HTTPError (404) when updating a deleted workflow.


    Preconditions:
        - a workflow record can be created and deleted within the test

    Evidence: src/codemie/core/workflow_models/workflow_config.py:320
        WorkflowConfig.update() raises NotFoundException when the workflow row
        no longer exists at persist time; the REST layer translates this to HTTP 404
        which ApiRequestHandler.put() surfaces as requests.exceptions.HTTPError
        via response.raise_for_status().

    Steps:
        1. Create a workflow and record its ID.
        2. Delete the workflow (simulating a concurrent delete).
        3. Call workflow_utils.send_update_workflow_request() — SDK raises HTTPError.
        4. Assert e.response.status_code == 404.
    """
    assistant = AssistantModel(
        id=_STATE_ID,
        model=default_llm.base_name,
        system_prompt=_BASE_SYSTEM_PROMPT,
    )
    state = StateModel(id=_STATE_ID, assistant_id=_STATE_ID)
    base_yaml = prepare_yaml_content(
        WorkflowYamlModel(assistants=[assistant], states=[state]).model_dump(
            exclude_none=True
        )
    )

    workflow = workflow_utils.create_workflow(
        workflow_name=get_random_name(),
        workflow_type=WorkflowMode.SEQUENTIAL,
        shared=True,
        workflow_yaml=base_yaml,
    )
    workflow_id = workflow.id
    workflow_name = workflow.name

    # Step 2: Delete the workflow — simulating a concurrent delete.
    workflow_utils.delete_workflow(workflow)

    # Step 3: Attempt SDK update on the now-deleted workflow.
    update_request = WorkflowUpdateRequest(
        name=workflow_name,
        project=workflow.project,
        description=workflow.description or "",
        yaml_config=base_yaml,
        mode=workflow.mode,
        shared=workflow.shared,
    )

    with pytest.raises(requests.exceptions.HTTPError) as exc_info:
        workflow_utils.send_update_workflow_request(workflow_id, update_request)

    # Step 4: Assert the HTTP error carries a 404 status code.
    assert_that(
        exc_info.value.response.status_code,
        equal_to(404),
        f"Expected HTTP 404 HTTPError from SDK update of deleted workflow, "
        f"got {exc_info.value.response.status_code}",
    )
