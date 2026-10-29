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

"""API contract of run-start files for a workflow run.

A file given when a run starts is registered in the run's workspace, so the request must pass
the shape rule and be a file the user could download. These checks answer before any
execution is created, so no sandbox is involved.
"""

import uuid

import pytest
from codemie_sdk.models.workflow import ExecutionStatus
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    has_entries,
)

from codemie_test_harness.tests.enums.tools import AgentWorkspaceTool
from codemie_test_harness.tests.test_data.skill_workspace_test_data import (
    single_file_bundle,
)
from codemie_test_harness.tests.test_data.workspace_script_test_data import (
    RUN_FILES_MAX_COUNT,
    UNSAFE_FILE_NAMES,
)
from codemie_test_harness.tests.utils.skill_workspace_utils import skill_blob_token
from codemie_test_harness.tests.utils.workspace_script_utils import (
    SCRIPT_WORKFLOW_EXECUTION_TIMEOUT,
    build_file_token,
    start_run_expecting_rejection,
    tool_state,
    unique_script_name,
    upload_text_file,
)

INVALID_FILES_MESSAGE = "Invalid workflow run files"
NOT_AVAILABLE = "is not available to this user"


@pytest.fixture(scope="module")
def idle_workflow(create_script_workflow):
    """A workflow with one cheap tool step: it never needs the files it is started with."""
    tool, state = tool_state(
        "list_files", AgentWorkspaceTool.LIST_WORKSPACE_FILES.value
    )
    return create_script_workflow([tool], [state])


@pytest.fixture(scope="module")
def own_file_url(client):
    return upload_text_file(client, unique_script_name("own"), "own file")


@pytest.mark.workflow
@pytest.mark.workspace
@pytest.mark.api
@pytest.mark.parametrize(
    "file_name",
    [name for name, _ in UNSAFE_FILE_NAMES],
    ids=[case_id for _, case_id in UNSAFE_FILE_NAMES],
)
def test_run_with_unsafe_file_reference_is_rejected(
    workflow_utils, idle_workflow, own_file_owner, file_name
):
    """A reference whose name could leave the owner's storage is refused with 400."""
    unsafe_token = build_file_token("text/plain", own_file_owner, file_name)

    response = start_run_expecting_rejection(
        workflow_utils, idle_workflow.id, [unsafe_token]
    )

    assert_that(response.status_code, equal_to(400))
    assert_that(
        response.json()["error"],
        has_entries(message=INVALID_FILES_MESSAGE),
    )
    assert_that(response.json()["error"]["details"], contains_string(NOT_AVAILABLE))


@pytest.mark.workflow
@pytest.mark.workspace
@pytest.mark.api
def test_run_with_malformed_file_reference_is_rejected(workflow_utils, idle_workflow):
    """A token that is not a file reference at all is refused with 400."""
    response = start_run_expecting_rejection(
        workflow_utils, idle_workflow.id, ["not-a-file-reference!"]
    )

    assert_that(response.status_code, equal_to(400))
    assert_that(
        response.json()["error"],
        has_entries(message=INVALID_FILES_MESSAGE, details="Invalid file reference"),
    )


@pytest.mark.workflow
@pytest.mark.workspace
@pytest.mark.api
def test_run_with_file_of_another_user_is_rejected(
    workflow_utils, idle_workflow, regular_client
):
    """A file the caller could not download is refused, even though the token itself is valid."""
    foreign_file_url = upload_text_file(
        regular_client, unique_script_name("foreign"), "someone else's file"
    )

    response = start_run_expecting_rejection(
        workflow_utils, idle_workflow.id, [foreign_file_url]
    )

    assert_that(response.status_code, equal_to(400))
    assert_that(
        response.json()["error"],
        has_entries(message=INVALID_FILES_MESSAGE),
    )
    assert_that(response.json()["error"]["details"], contains_string(NOT_AVAILABLE))


@pytest.mark.workflow
@pytest.mark.workspace
@pytest.mark.api
def test_run_with_foreign_owner_reference_is_rejected(workflow_utils, idle_workflow):
    """A reference crafted for an owner id that is not the caller's is refused."""
    foreign_token = build_file_token("text/plain", str(uuid.uuid4()), "secret.txt")

    response = start_run_expecting_rejection(
        workflow_utils, idle_workflow.id, [foreign_token]
    )

    assert_that(response.status_code, equal_to(400))
    assert_that(response.json()["error"]["details"], contains_string(NOT_AVAILABLE))


@pytest.mark.workflow
@pytest.mark.workspace
@pytest.mark.skill
@pytest.mark.api
def test_run_with_skill_owned_file_reference_is_rejected(
    workflow_utils, idle_workflow, create_skill_with_bundle
):
    """A reference to a skill's stored file is refused: only the skill's own seeding may link it."""
    bundle = single_file_bundle()
    skill = create_skill_with_bundle(bundle)
    skill_file_token = skill_blob_token(skill.id, bundle[0].path, bundle[0].content)

    response = start_run_expecting_rejection(
        workflow_utils, idle_workflow.id, [skill_file_token]
    )

    assert_that(response.status_code, equal_to(400))
    assert_that(
        response.json()["error"],
        has_entries(message=INVALID_FILES_MESSAGE),
    )
    assert_that(response.json()["error"]["details"], contains_string(NOT_AVAILABLE))


@pytest.mark.workflow
@pytest.mark.workspace
@pytest.mark.api
def test_run_with_missing_file_is_rejected(
    workflow_utils, idle_workflow, own_file_owner
):
    """A well-formed reference to a file that was never uploaded is refused as a client error."""
    missing_name = unique_script_name("missing")
    missing_token = build_file_token("text/plain", own_file_owner, missing_name)

    response = start_run_expecting_rejection(
        workflow_utils, idle_workflow.id, [missing_token]
    )

    assert_that(response.status_code, equal_to(400))
    assert_that(response.json()["error"]["message"], contains_string(missing_name))
    assert_that(response.json()["error"]["message"], contains_string("was not found"))


@pytest.mark.workflow
@pytest.mark.workspace
@pytest.mark.api
def test_run_with_more_files_than_the_cap_is_rejected(
    workflow_utils, idle_workflow, own_file_url
):
    """One file over the cap is refused with 422 and a message that names the cap.

    The request model rejects the count (same limit of 20) before the router's own 400 check
    can, so the status is 422 and not the 400 that the acceptance criterion describes.
    """
    too_many = [own_file_url] * (RUN_FILES_MAX_COUNT + 1)

    response = start_run_expecting_rejection(workflow_utils, idle_workflow.id, too_many)

    assert_that(response.status_code, equal_to(422))
    assert_that(
        response.text, contains_string(f"Maximum count is {RUN_FILES_MAX_COUNT}")
    )


@pytest.mark.workflow
@pytest.mark.workspace
@pytest.mark.api
def test_run_with_exactly_the_cap_of_files_is_accepted(
    workflow_utils, idle_workflow, own_file_url
):
    """The cap is inclusive: a run with that many files starts and completes."""
    at_cap = [own_file_url] * RUN_FILES_MAX_COUNT

    execution = workflow_utils.create_workflow_execution(
        idle_workflow.id, file_names=at_cap, timeout=SCRIPT_WORKFLOW_EXECUTION_TIMEOUT
    )

    assert_that(execution.status, equal_to(ExecutionStatus.SUCCEEDED))
