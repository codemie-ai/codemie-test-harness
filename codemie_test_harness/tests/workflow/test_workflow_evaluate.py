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

"""E2E tests for POST /v1/workflows/{workflow_id}/evaluate endpoint.

Feature: Extend Codemie Evaluation Capabilities to Support Workflow Dataset Experiments
"""

import pytest
from codemie_sdk.models.workflow import WorkflowEvaluationRequest, WorkflowMode
from hamcrest import assert_that, equal_to, has_key, is_not, none

from codemie_test_harness.tests.utils.base_utils import (
    assert_error_details,
    assert_response,
    get_random_name,
)
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.workflow_utils import WorkflowUtils
from codemie_test_harness.tests.utils.yaml_utils import (
    AssistantModel,
    StateModel,
    WorkflowYamlModel,
    prepare_yaml_content,
)
from codemie_test_harness.tests.test_data.workflow_evaluation_test_data import (
    VALID_DATASET_ID,
    INVALID_DATASET_ID,
    NONEXISTENT_WORKFLOW_ID,
    MAX_CONCURRENCY_MIN,
    MAX_CONCURRENCY_MAX,
    MAX_CONCURRENCY_ABOVE_MAX,
    MAX_CONCURRENCY_BELOW_MIN,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_workflow_yaml(model_name: str, prefix: str = "eval") -> str:
    assistant = AssistantModel(
        id=f"{prefix}_assistant",
        model=model_name,
        system_prompt="You are a helpful assistant.",
    )
    state = StateModel(id=f"{prefix}_assistant", assistant_id=f"{prefix}_assistant")
    return prepare_yaml_content(
        WorkflowYamlModel(assistants=[assistant], states=[state]).model_dump(
            exclude_none=True
        )
    )


@pytest.fixture
def private_workflow(workflow_utils, default_llm):
    """Non-shared workflow owned by the primary user — used by TC-11 (access-denied)."""
    created = workflow_utils.create_workflow(
        workflow_type=WorkflowMode.SEQUENTIAL,
        workflow_yaml=_make_workflow_yaml(default_llm.base_name, prefix="private_eval"),
        workflow_name=get_random_name(),
        shared=False,
    )
    yield created
    try:
        workflow_utils.delete_workflow(created)
    except Exception:
        pass


@pytest.fixture
def second_user_workflow_utils():
    """WorkflowUtils authenticated as the secondary test user (AUTH_USERNAME_DEFAULT)."""
    second_client = get_client(
        username=CredentialsManager.get_parameter("AUTH_USERNAME_DEFAULT"),
        password=CredentialsManager.get_parameter("AUTH_PASSWORD_DEFAULT"),
    )
    return WorkflowUtils(second_client)


# ---------------------------------------------------------------------------
# TC-01 / TC-03 — Valid request returns 200 (max_concurrency optional)
# ---------------------------------------------------------------------------


@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
def test_evaluate_workflow_returns_200_with_valid_request(
    private_workflow, workflow_utils
):
    """TC-01/TC-03: Valid request returns HTTP 200; max_concurrency is optional (defaults to 1)."""
    request = WorkflowEvaluationRequest(
        dataset_id=VALID_DATASET_ID,
        experiment_name=get_random_name(),
    )
    result = workflow_utils.evaluate_workflow(private_workflow.id, request)
    assert_that(result, has_key("message"))
    assert_that(result, has_key("experimentName"))


# ---------------------------------------------------------------------------
# TC-02 — Response body contains message and experimentName
# ---------------------------------------------------------------------------


@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
def test_evaluate_workflow_response_contains_message_and_experiment_name(
    private_workflow, workflow_utils
):
    """TC-02: Response body has non-null message and experimentName matching the request."""
    experiment_name = get_random_name()
    request = WorkflowEvaluationRequest(
        dataset_id=VALID_DATASET_ID,
        experiment_name=experiment_name,
    )
    result = workflow_utils.evaluate_workflow(private_workflow.id, request)
    assert_that(result["message"], is_not(none()))
    assert_that(result["experimentName"], equal_to(experiment_name))


# ---------------------------------------------------------------------------
# TC-04 / TC-05 — Valid max_concurrency boundary values return 200
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("max_concurrency", [MAX_CONCURRENCY_MIN, MAX_CONCURRENCY_MAX])
@pytest.mark.workflow
@pytest.mark.api
def test_evaluate_workflow_accepts_valid_max_concurrency_values(
    private_workflow, workflow_utils, max_concurrency
):
    """TC-04/TC-05: max_concurrency=1 (min) and max_concurrency=5 (max) both return HTTP 200."""
    request = WorkflowEvaluationRequest(
        dataset_id=VALID_DATASET_ID,
        experiment_name=get_random_name(),
        max_concurrency=max_concurrency,
    )
    result = workflow_utils.evaluate_workflow(private_workflow.id, request)
    assert_that(result, has_key("message"))


# ---------------------------------------------------------------------------
# TC-06 / TC-07 — Invalid max_concurrency boundary values return 422
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "max_concurrency,error",
    [
        (MAX_CONCURRENCY_ABOVE_MAX, "Input should be less than or equal to 5"),
        (MAX_CONCURRENCY_BELOW_MIN, "Input should be greater than or equal to 1"),
    ],
)
@pytest.mark.workflow
@pytest.mark.api
def test_evaluate_workflow_rejects_invalid_max_concurrency_values(
    private_workflow, workflow_utils, max_concurrency, error
):
    """TC-06/TC-07: max_concurrency=6 (above max) and 0 (below min) return HTTP 422."""
    response = workflow_utils.send_evaluate_workflow_request(
        private_workflow.id,
        {
            "dataset_id": VALID_DATASET_ID,
            "experiment_name": get_random_name(),
            "max_concurrency": max_concurrency,
        },
    )
    assert_response(response, 422, error)


# ---------------------------------------------------------------------------
# TC-08 — Missing required dataset_id returns 422
# ---------------------------------------------------------------------------


@pytest.mark.workflow
@pytest.mark.api
def test_evaluate_workflow_rejects_request_missing_dataset_id(
    private_workflow, workflow_utils
):
    """TC-08: POST body without dataset_id returns HTTP 422."""
    response = workflow_utils.send_evaluate_workflow_request(
        private_workflow.id, {"experiment_name": get_random_name()}
    )
    assert_response(response, 422, "Field required")


# ---------------------------------------------------------------------------
# TC-09 — Missing required experiment_name returns 422
# ---------------------------------------------------------------------------


@pytest.mark.workflow
@pytest.mark.api
def test_evaluate_workflow_rejects_request_missing_experiment_name(
    private_workflow, workflow_utils
):
    """TC-09: POST body without experiment_name returns HTTP 422."""
    response = workflow_utils.send_evaluate_workflow_request(
        private_workflow.id, {"dataset_id": VALID_DATASET_ID}
    )
    assert_response(response, 422, "Field required")


# ---------------------------------------------------------------------------
# TC-10 — Non-existent workflow ID returns 404
# ---------------------------------------------------------------------------


@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
def test_evaluate_workflow_returns_404_when_workflow_not_found(workflow_utils):
    """TC-10: POST to a non-existent workflow_id returns HTTP 404."""
    request = WorkflowEvaluationRequest(
        dataset_id=VALID_DATASET_ID,
        experiment_name=get_random_name(),
    )
    with pytest.raises(Exception) as exc_info:
        workflow_utils.evaluate_workflow(NONEXISTENT_WORKFLOW_ID, request)
    assert_response(
        exc_info.value.response,
        404,
        f"The Workflow with ID [{NONEXISTENT_WORKFLOW_ID}] could not be found in the system.",
    )


# ---------------------------------------------------------------------------
# TC-11 — User without READ access returns 401
# ---------------------------------------------------------------------------


@pytest.mark.workflow
@pytest.mark.api
def test_evaluate_workflow_returns_401_when_user_lacks_read_access(
    private_workflow, second_user_workflow_utils
):
    """TC-11: User with no READ grant on the workflow receives HTTP 403."""
    request = WorkflowEvaluationRequest(
        dataset_id=VALID_DATASET_ID,
        experiment_name=get_random_name(),
    )
    with pytest.raises(Exception) as exc_info:
        second_user_workflow_utils.evaluate_workflow(private_workflow.id, request)
    assert_response(
        exc_info.value.response,
        403,
        "You do not have the necessary permissions to evaluate this entity.",
    )


# ---------------------------------------------------------------------------
# TC-13 — dataset_id not resolvable in Langfuse returns 400
# ---------------------------------------------------------------------------


@pytest.mark.workflow
@pytest.mark.api
def test_evaluate_workflow_returns_400_when_dataset_not_found(
    private_workflow, workflow_utils
):
    """TC-13: POST with an unresolvable dataset_id returns HTTP 400."""
    request = WorkflowEvaluationRequest(
        dataset_id=INVALID_DATASET_ID,
        experiment_name=get_random_name(),
    )
    with pytest.raises(Exception) as exc_info:
        workflow_utils.evaluate_workflow(private_workflow.id, request)
    assert_error_details(
        exc_info.value.response,
        400,
        "Please find and specify correct dataset details from Langfuse",
    )
