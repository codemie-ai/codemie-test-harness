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

"""API tests for listing workflow revisions and rolling back to one, through the SDK."""

import pytest
from codemie_sdk.models.workflow import WorkflowMode
from hamcrest import assert_that, equal_to, greater_than, has_length
from requests import HTTPError

from codemie_test_harness.tests.test_data.workflow_revision_test_data import (
    ACCESS_DENIED_MESSAGE,
    DEFAULT_REVISIONS_PER_PAGE,
    DENIED_ACTIONS,
    INVALID_PAGING_PARAMS,
    OUT_OF_RANGE_ROLLBACK_CASES,
    REVISIONS_ABOVE_DEFAULT_PAGE,
    ROLLBACK_CHANGE_NOTES,
    build_revision_yaml,
    marker_prompt,
    parsed_config,
    revision_prompt,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.workflow_revision_utils import (
    WorkflowRevisionUtils,
)


@pytest.fixture
def revision_utils(client):
    return WorkflowRevisionUtils(client)


@pytest.fixture
def workflow_with_revisions(revision_utils, default_llm):
    """Factory: a workflow created with revision 0 and saved ``saves`` more times.

    Each save carries a different revision marker prompt, so the history holds exactly
    ``saves`` revisions: index 0 is marker ``saves - 1`` and the last index is marker 0,
    while the live config carries marker ``saves``.
    """
    created = []

    def _create(saves):
        workflow = revision_utils.create_workflow(
            workflow_name=get_random_name(),
            workflow_type=WorkflowMode.SEQUENTIAL,
            shared=True,
            workflow_yaml=build_revision_yaml(default_llm.base_name, 0),
        )
        created.append(workflow)
        for number in range(1, saves + 1):
            revision_utils.save_workflow_yaml(
                workflow, build_revision_yaml(default_llm.base_name, number)
            )
        return workflow

    yield _create

    for workflow in created:
        try:
            revision_utils.delete_workflow(workflow)
        except Exception:
            pass


@pytest.mark.workflow
@pytest.mark.api
def test_list_revisions_defaults_to_first_twenty_newest_first(
    workflow_with_revisions, revision_utils
):
    # @case workflow-revision-rollback-via-sdk_TC_001
    saves = REVISIONS_ABOVE_DEFAULT_PAGE
    workflow = workflow_with_revisions(saves)

    history = revision_utils.list_workflow_versions(workflow.id)

    assert_that(
        history.revisions,
        has_length(DEFAULT_REVISIONS_PER_PAGE),
        "A listing without page or per_page must return the default page size",
    )
    assert_that(
        [marker_prompt(revision.yaml_config) for revision in history.revisions],
        equal_to(
            [
                revision_prompt(number)
                for number in range(
                    saves - 1, saves - 1 - DEFAULT_REVISIONS_PER_PAGE, -1
                )
            ]
        ),
        "Revisions must be ordered newest first",
    )
    assert_that(
        history.total_revisions,
        equal_to(saves),
        "total_revisions must count the full history, not the returned page",
    )
    assert_that(history.total_revisions, greater_than(DEFAULT_REVISIONS_PER_PAGE))


@pytest.mark.workflow
@pytest.mark.api
def test_list_revisions_page_and_per_page_slice_history_with_absolute_index(
    workflow_with_revisions, revision_utils
):
    # @case workflow-revision-rollback-via-sdk_TC_002
    saves = 5
    workflow = workflow_with_revisions(saves)

    first_page = revision_utils.list_workflow_versions(workflow.id, page=0, per_page=2)
    second_page = revision_utils.list_workflow_versions(workflow.id, page=1, per_page=2)

    assert_that(
        [revision.revision_index for revision in first_page.revisions],
        equal_to([0, 1]),
        "The first page must start at the newest revision",
    )
    assert_that(
        [revision.revision_index for revision in second_page.revisions],
        equal_to([2, 3]),
        "revision_index must be the absolute position in the full history",
    )
    assert_that(
        [marker_prompt(revision.yaml_config) for revision in second_page.revisions],
        equal_to([revision_prompt(saves - 1 - 2), revision_prompt(saves - 1 - 3)]),
        "Page 1 with per_page 2 must hold the revisions at history positions 2 and 3",
    )
    assert_that(first_page.total_revisions, equal_to(saves))
    assert_that(
        second_page.total_revisions,
        equal_to(first_page.total_revisions),
        "total_revisions must not depend on the page",
    )


@pytest.mark.parametrize("paging", INVALID_PAGING_PARAMS)
@pytest.mark.workflow
@pytest.mark.api
def test_list_revisions_rejects_invalid_paging(
    workflow_with_revisions, revision_utils, paging
):
    # @case workflow-revision-rollback-via-sdk_TC_003
    workflow = workflow_with_revisions(1)

    with pytest.raises(HTTPError) as exc_info:
        revision_utils.list_workflow_versions(workflow.id, **paging)

    assert_that(
        exc_info.value.response.status_code,
        equal_to(422),
        f"Query validation must reject {paging}",
    )


@pytest.mark.workflow
@pytest.mark.api
def test_rollback_to_valid_revision_restores_active_config_immediately(
    workflow_with_revisions, revision_utils
):
    # @case workflow-revision-rollback-via-sdk_TC_004
    workflow = workflow_with_revisions(1)
    target = revision_utils.list_workflow_versions(workflow.id).revisions[0]

    response = revision_utils.rollback_workflow(workflow.id, target.revision_index)

    assert_that(
        response["message"],
        equal_to(
            f"Workflow {workflow.id} rolled back to revision {target.revision_index}."
        ),
    )
    restored = revision_utils.get_workflow(workflow.id)
    assert_that(
        parsed_config(restored.yaml_config),
        equal_to(parsed_config(target.yaml_config)),
        "The live config must equal the target revision right after the response",
    )
    assert_that(
        marker_prompt(restored.yaml_config),
        equal_to(revision_prompt(0)),
        "The live config must hold the original revision, not the saved update",
    )


@pytest.mark.parametrize("saves, expected_message", OUT_OF_RANGE_ROLLBACK_CASES)
@pytest.mark.workflow
@pytest.mark.api
def test_rollback_out_of_range_revision_is_rejected_and_workflow_unchanged(
    workflow_with_revisions, revision_utils, saves, expected_message
):
    # @case workflow-revision-rollback-via-sdk_TC_006
    workflow = workflow_with_revisions(saves)
    config_before = revision_utils.get_workflow(workflow.id).yaml_config
    total_before = revision_utils.list_workflow_versions(workflow.id).total_revisions

    with pytest.raises(HTTPError) as exc_info:
        revision_utils.rollback_workflow(workflow.id, saves)

    response = exc_info.value.response
    assert_that(response.status_code, equal_to(400))
    assert_that(response.json()["error"]["message"], equal_to(expected_message))
    assert_that(
        revision_utils.get_workflow(workflow.id).yaml_config,
        equal_to(config_before),
        "A rejected rollback must leave the live config untouched",
    )
    assert_that(
        revision_utils.list_workflow_versions(workflow.id).total_revisions,
        equal_to(total_before),
        "A rejected rollback must not add a revision",
    )


@pytest.mark.workflow
@pytest.mark.api
def test_rollback_is_recorded_as_new_revision_with_displaced_config(
    workflow_with_revisions, revision_utils, client
):
    # @case workflow-revision-rollback-via-sdk_TC_007
    saves = 2
    workflow = workflow_with_revisions(saves)
    total_before = revision_utils.list_workflow_versions(workflow.id).total_revisions

    revision_utils.rollback_workflow(
        workflow.id, saves - 1, change_notes=ROLLBACK_CHANGE_NOTES
    )

    history = revision_utils.list_workflow_versions(workflow.id)
    newest = history.revisions[0]
    assert_that(
        history.total_revisions,
        equal_to(total_before + 1),
        "A rollback must add exactly one revision",
    )
    assert_that(
        marker_prompt(newest.yaml_config),
        equal_to(revision_prompt(saves)),
        "The newest revision must hold the config the rollback displaced",
    )
    assert_that(newest.change_notes, equal_to(ROLLBACK_CHANGE_NOTES))
    assert_that(newest.created_by.user_id, equal_to(client.users.about_me().user_id))


@pytest.mark.parametrize("denied_action", DENIED_ACTIONS)
@pytest.mark.workflow
@pytest.mark.api
def test_user_without_edit_access_cannot_list_revisions_or_roll_back(
    workflow_with_revisions, revision_utils, regular_client, denied_action
):
    # @case workflow-revision-rollback-via-sdk_TC_008
    workflow = workflow_with_revisions(2)
    config_before = revision_utils.get_workflow(workflow.id).yaml_config
    total_before = revision_utils.list_workflow_versions(workflow.id).total_revisions

    with pytest.raises(HTTPError) as exc_info:
        denied_action(WorkflowRevisionUtils(regular_client), workflow.id)

    response = exc_info.value.response
    assert_that(response.status_code, equal_to(401))
    assert_that(response.json()["error"]["message"], equal_to(ACCESS_DENIED_MESSAGE))
    assert_that(
        revision_utils.get_workflow(workflow.id).yaml_config,
        equal_to(config_before),
        "A denied request must leave the live config untouched",
    )
    assert_that(
        revision_utils.list_workflow_versions(workflow.id).total_revisions,
        equal_to(total_before),
        "A denied request must not add a revision",
    )
