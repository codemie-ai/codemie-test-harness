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

"""API tests for uploading a workflow icon file and saving it on a workflow."""

import logging

import pytest
from codemie_sdk.models.workflow import WorkflowMode, WorkflowUpdateRequest
from hamcrest import (
    any_of,
    assert_that,
    equal_to,
    matches_regexp,
    none,
)
from requests import HTTPError

from codemie_test_harness.tests import PROJECT
from codemie_test_harness.tests.test_data.workflow_icon_test_data import (
    EXTERNAL_ICON_URL,
    INVALID_ICON_PARAMS,
    OTHER_EXTERNAL_ICON_URL,
    VALID_ICON_PARAMS,
    InvalidIconCase,
    ValidIconCase,
    build_png_bytes,
    decode_file_url,
    stored_icon_name_regexp,
    write_png_icon,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.workflow_utils import WorkflowUtils
from codemie_test_harness.tests.utils.yaml_utils import (
    AssistantModel,
    StateModel,
    WorkflowYamlModel,
    prepare_yaml_content,
)

logger = logging.getLogger(__name__)

STATE_NAME = "icon_state"


@pytest.fixture
def workflow_yaml(default_llm):
    assistant = AssistantModel(
        id=STATE_NAME,
        model=default_llm.base_name,
        system_prompt="You are helpful assistant",
    )
    state = StateModel(id=STATE_NAME, assistant_id=STATE_NAME)
    return prepare_yaml_content(
        WorkflowYamlModel(assistants=[assistant], states=[state]).model_dump(
            exclude_none=True
        )
    )


@pytest.fixture
def workflow_factory(workflow_utils, workflow_yaml):
    """Factory creating workflows with an icon; every one is deleted in teardown."""
    created = []

    def _create(utils=None, icon_url=None, shared=False, project_name=None):
        owner_utils = utils or workflow_utils
        listed = owner_utils.create_workflow(
            workflow_type=WorkflowMode.SEQUENTIAL,
            workflow_yaml=workflow_yaml,
            workflow_name=get_random_name(),
            description="Workflow icon upload test",
            shared=shared,
            project_name=project_name,
            icon_url=icon_url,
        )
        workflow = owner_utils.get_workflow(listed.id)
        created.append((owner_utils, workflow))
        return workflow

    yield _create

    for owner_utils, workflow in created:
        try:
            owner_utils.delete_workflow(workflow)
        except Exception as e:
            logger.warning(f"Failed to delete workflow {workflow.id}: {e}")


def _upload_png(utils, directory, name="icon.png"):
    return utils.upload_workflow_icon(write_png_icon(directory, name))


# @case workflow-icon-file-upload_TC_001
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.parametrize("icon_case", VALID_ICON_PARAMS)
def test_upload_icon_and_create_workflow_persists_icon(
    workflow_utils, workflow_factory, tmp_path, icon_case: ValidIconCase
):
    file_url = workflow_utils.upload_workflow_icon(icon_case.write(tmp_path))

    assert_that(
        decode_file_url(file_url),
        matches_regexp(stored_icon_name_regexp(icon_case.stored_extension)),
        "Uploaded icon must be stored under a generated workflow-icons name.",
    )

    workflow = workflow_factory(icon_url=file_url)

    assert_that(
        workflow_utils.get_workflow(workflow.id).icon_url,
        equal_to(file_url),
        "Workflow icon_url returned by GET must be the uploaded file URL.",
    )


# @case workflow-icon-file-upload_TC_002
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.parametrize("invalid_case", INVALID_ICON_PARAMS)
def test_upload_invalid_icon_is_rejected(
    workflow_utils, tmp_path, invalid_case: InvalidIconCase
):
    icon_file = invalid_case.write(tmp_path)

    with pytest.raises(HTTPError) as exc_info:
        workflow_utils.upload_workflow_icon(icon_file)

    response = exc_info.value.response
    error = response.json()["error"]
    assert_that(
        response.status_code, equal_to(400), "Unexpected HTTP status for invalid icon."
    )
    assert_that(
        error["message"],
        equal_to(invalid_case.expected_message),
        "Unexpected error message for invalid icon.",
    )
    assert_that(
        error["details"],
        equal_to(invalid_case.expected_details),
        "Unexpected error details for invalid icon.",
    )


# @case workflow-icon-file-upload_TC_003
@pytest.mark.workflow
@pytest.mark.api
def test_update_workflow_replaces_and_clears_icon(
    workflow_utils, workflow_factory, tmp_path
):
    first_url = _upload_png(workflow_utils, tmp_path, "first.png")
    second_url = _upload_png(workflow_utils, tmp_path, "second.png")
    workflow = workflow_factory(icon_url=first_url)
    assert_that(
        workflow_utils.get_workflow(workflow.id).icon_url,
        equal_to(first_url),
        "Workflow must be created with the first uploaded icon.",
    )

    workflow_utils.update_workflow(workflow, icon_url=second_url)

    assert_that(
        workflow_utils.get_workflow(workflow.id).icon_url,
        equal_to(second_url),
        "Update must replace the icon with the second uploaded one.",
    )

    workflow_utils.update_workflow(workflow, icon_url="")

    assert_that(
        workflow_utils.get_workflow(workflow.id).icon_url,
        any_of(none(), equal_to("")),
        "Update with an empty icon_url must clear the icon.",
    )


# @case workflow-icon-file-upload_TC_004
@pytest.mark.workflow
@pytest.mark.api
def test_external_icon_url_is_stored_unchanged(workflow_utils, workflow_factory):
    workflow = workflow_factory(icon_url=EXTERNAL_ICON_URL)
    assert_that(
        workflow_utils.get_workflow(workflow.id).icon_url,
        equal_to(EXTERNAL_ICON_URL),
        "External icon URL must be stored unchanged on create.",
    )

    workflow_utils.update_workflow(
        workflow, description="Updated description", icon_url=EXTERNAL_ICON_URL
    )
    assert_that(
        workflow_utils.get_workflow(workflow.id).icon_url,
        equal_to(EXTERNAL_ICON_URL),
        "External icon URL must stay unchanged when only the description is updated.",
    )

    workflow_utils.update_workflow(workflow, icon_url=OTHER_EXTERNAL_ICON_URL)
    assert_that(
        workflow_utils.get_workflow(workflow.id).icon_url,
        equal_to(OTHER_EXTERNAL_ICON_URL),
        "A different external icon URL must be stored unchanged on update.",
    )


# @case workflow-icon-file-upload_TC_005
@pytest.mark.workflow
@pytest.mark.api
def test_user_without_write_access_cannot_change_workflow_icon(
    workflow_utils, workflow_factory, platform_user, user_utils, tmp_path
):
    owner_icon_url = _upload_png(workflow_utils, tmp_path, "owner.png")
    workflow = workflow_factory(icon_url=owner_icon_url, shared=True)
    user_utils.assign_user_to_project(platform_user.user_id, PROJECT)
    member_utils = WorkflowUtils(platform_user.client)
    member_icon_url = _upload_png(member_utils, tmp_path, "member.png")
    request = WorkflowUpdateRequest(
        name=workflow.name,
        project=workflow.project,
        description=workflow.description,
        yaml_config=workflow.yaml_config,
        mode=workflow.mode,
        shared=workflow.shared,
        icon_url=member_icon_url,
    )

    with pytest.raises(HTTPError) as exc_info:
        member_utils.send_update_workflow_request(workflow.id, request=request)

    response = exc_info.value.response
    assert_that(
        response.status_code,
        equal_to(401),
        "Update by a user without WRITE access must be denied.",
    )
    assert_that(
        response.json()["error"]["message"],
        equal_to("Access denied"),
        "Update by a user without WRITE access must report access denied.",
    )
    assert_that(
        workflow_utils.get_workflow(workflow.id).icon_url,
        equal_to(owner_icon_url),
        "A denied update must leave the workflow icon unchanged.",
    )


# @case workflow-icon-file-upload_TC_006
@pytest.mark.workflow
@pytest.mark.api
def test_unreadable_uploaded_icon_of_another_user_cannot_be_reused(
    workflow_utils, workflow_factory, workflow_yaml, platform_user, tmp_path
):
    owner_icon_url = _upload_png(workflow_utils, tmp_path)
    workflow_factory(icon_url=owner_icon_url)
    other_utils = WorkflowUtils(platform_user.client)

    with pytest.raises(HTTPError) as exc_info:
        other_utils.send_create_workflow_request(
            workflow_yaml,
            project=platform_user.email,
            icon_url=owner_icon_url,
        )

    response = exc_info.value.response
    error = response.json()["error"]
    assert_that(
        response.status_code,
        equal_to(400),
        "Reusing an icon the user cannot read must be rejected.",
    )
    assert_that(
        error["message"],
        equal_to("Invalid workflow icon"),
        "Unexpected error message for an unreadable icon.",
    )
    assert_that(
        error["details"],
        equal_to("The referenced icon is not available to this user"),
        "Unexpected error details for an unreadable icon.",
    )


# @case workflow-icon-file-upload_TC_007
@pytest.mark.workflow
@pytest.mark.api
def test_workflow_icon_downloads_for_member_not_for_outsider(
    client, workflow_factory, platform_user, unrelated_client, user_utils, tmp_path
):
    icon_url = _upload_png(WorkflowUtils(client), tmp_path)
    workflow_factory(icon_url=icon_url, shared=True)
    user_utils.assign_user_to_project(platform_user.user_id, PROJECT)
    icon_bytes = build_png_bytes()

    assert_that(
        client.files.get_file(icon_url),
        equal_to(icon_bytes),
        "The owner must download the uploaded workflow icon.",
    )
    assert_that(
        platform_user.client.files.get_file(icon_url),
        equal_to(icon_bytes),
        "A project member who can read the shared workflow must download its icon.",
    )

    with pytest.raises(HTTPError) as exc_info:
        unrelated_client.files.get_file(icon_url)

    assert_that(
        exc_info.value.response.status_code,
        equal_to(404),
        "A user with no access to the workflow must not download its icon.",
    )


# @case workflow-icon-file-upload_TC_017
@pytest.mark.workflow
@pytest.mark.api
def test_replacing_icon_keeps_shared_file_downloadable_for_other_workflow(
    client, workflow_utils, workflow_factory, tmp_path
):
    shared_icon_url = _upload_png(workflow_utils, tmp_path, "shared.png")
    replacement_icon_url = _upload_png(workflow_utils, tmp_path, "replacement.png")
    first_workflow = workflow_factory(icon_url=shared_icon_url)
    second_workflow = workflow_factory(icon_url=shared_icon_url)

    workflow_utils.update_workflow(first_workflow, icon_url=replacement_icon_url)

    assert_that(
        workflow_utils.get_workflow(first_workflow.id).icon_url,
        equal_to(replacement_icon_url),
        "The first workflow must carry the replacement icon.",
    )
    assert_that(
        workflow_utils.get_workflow(second_workflow.id).icon_url,
        equal_to(shared_icon_url),
        "The second workflow must keep referencing the original icon.",
    )
    assert_that(
        client.files.get_file(shared_icon_url),
        equal_to(build_png_bytes()),
        "The original icon must stay downloadable while another workflow references it.",
    )
