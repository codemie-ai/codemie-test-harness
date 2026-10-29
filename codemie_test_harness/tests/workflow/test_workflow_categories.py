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

"""API tests for the workflow Categories field."""

import logging

import pytest
from codemie_sdk.models.workflow import WorkflowMode
from hamcrest import (
    assert_that,
    contains_inanyorder,
    contains_string,
    equal_to,
    greater_than_or_equal_to,
    has_item,
    is_not,
)
from requests import HTTPError

from codemie_test_harness.tests.test_data.workflow_categories_test_data import (
    CREATE_CATEGORIES_PARAMS,
    INVALID_CATEGORIES_PARAMS,
    MAX_WORKFLOW_CATEGORIES,
    UPDATE_CATEGORIES_PARAMS,
    CategoriesUpdateCase,
    InvalidCategoriesCase,
    WorkflowCategoriesDataFactory,
)
from codemie_test_harness.tests.utils.yaml_utils import (
    AssistantModel,
    StateModel,
    WorkflowYamlModel,
    prepare_yaml_content,
)

logger = logging.getLogger(__name__)

STATE_NAME = "categories_state"


@pytest.fixture(scope="module")
def category_ids(categories_utils):
    """IDs of existing categories; the tests never create or delete categories."""
    ids = [category.id for category in categories_utils.get_categories()]
    assert_that(
        len(ids),
        greater_than_or_equal_to(MAX_WORKFLOW_CATEGORIES),
        "Environment must have at least 3 categories",
    )
    return ids


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
def create_workflow(workflow_utils, workflow_yaml):
    """Factory creating workflows with given categories; all are deleted in teardown."""
    created = []

    def _create(categories=None):
        data = WorkflowCategoriesDataFactory.create()
        listed = workflow_utils.create_workflow(
            workflow_name=data.name,
            workflow_type=WorkflowMode.SEQUENTIAL,
            workflow_yaml=workflow_yaml,
            description=data.description,
            categories=categories,
        )
        workflow = workflow_utils.get_workflow(listed.id)
        created.append(workflow)
        return workflow

    yield _create

    for workflow in created:
        try:
            workflow_utils.delete_workflow(workflow)
        except Exception as e:
            logger.warning(f"Failed to delete workflow {workflow.id}: {e}")


@pytest.fixture
def rejected_workflow_name(workflow_utils):
    """Name for a workflow that must be rejected; removes it if it was created anyway."""
    name = WorkflowCategoriesDataFactory.create().name
    yield name
    try:
        for workflow in workflow_utils.client.workflows.list(
            per_page=200, filter_by_user=True
        ):
            if workflow.name == name:
                workflow_utils.delete_workflow(workflow)
    except Exception as e:
        logger.warning(f"Failed to clean up rejected workflow {name}: {e}")


@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.parametrize("categories_count", CREATE_CATEGORIES_PARAMS)
def test_create_workflow_persists_categories(
    create_workflow, category_ids, categories_count
):
    sent_ids = category_ids[:categories_count]

    workflow = create_workflow(categories=sent_ids)

    assert_that(
        workflow.categories,
        contains_inanyorder(*sent_ids),
        "Workflow categories returned by GET do not match the created ones.",
    )


@pytest.mark.workflow
@pytest.mark.api
def test_list_workflows_filtered_by_category(
    create_workflow, workflow_utils, category_ids
):
    category_x, category_y = category_ids[0], category_ids[1]
    workflow_a = create_workflow(categories=[category_x])
    workflow_b = create_workflow(categories=[category_y])
    workflow_c = create_workflow()

    filtered_ids = [
        workflow.id
        for workflow in workflow_utils.client.workflows.list(
            per_page=200, filters={"categories": [category_x]}, filter_by_user=True
        )
    ]
    unfiltered_ids = [
        workflow.id
        for workflow in workflow_utils.client.workflows.list(
            per_page=200, filter_by_user=True
        )
    ]

    assert_that(
        filtered_ids,
        has_item(workflow_a.id),
        "Filtered list must contain the workflow with the category.",
    )
    assert_that(
        filtered_ids,
        is_not(has_item(workflow_b.id)),
        "Filtered list must not contain the workflow with another category.",
    )
    assert_that(
        filtered_ids,
        is_not(has_item(workflow_c.id)),
        "Filtered list must not contain the workflow without categories.",
    )
    for workflow in (workflow_a, workflow_b, workflow_c):
        assert_that(
            unfiltered_ids,
            has_item(workflow.id),
            "Unfiltered list must contain all created workflows.",
        )


@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.parametrize("update_case", UPDATE_CATEGORIES_PARAMS)
def test_update_workflow_categories(
    create_workflow,
    workflow_utils,
    category_ids,
    update_case: CategoriesUpdateCase,
):
    workflow = create_workflow(categories=[category_ids[0]])
    update_ids = (
        None
        if update_case.update_indexes is None
        else [category_ids[i] for i in update_case.update_indexes]
    )
    expected_ids = [category_ids[i] for i in update_case.expected_indexes]

    workflow_utils.update_workflow(workflow, categories=update_ids)
    fetched = workflow_utils.get_workflow(workflow.id)

    assert_that(
        fetched.categories,
        contains_inanyorder(*expected_ids),
        "Workflow categories after update do not match the expected ones.",
    )


@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.parametrize("invalid_case", INVALID_CATEGORIES_PARAMS)
def test_create_workflow_rejects_invalid_categories(
    workflow_utils,
    workflow_yaml,
    category_ids,
    rejected_workflow_name,
    invalid_case: InvalidCategoriesCase,
):
    with pytest.raises(HTTPError) as exc_info:
        workflow_utils.send_create_workflow_request(
            workflow_yaml=workflow_yaml,
            workflow_type=WorkflowMode.SEQUENTIAL,
            description="Invalid categories",
            workflow_name=rejected_workflow_name,
            categories=invalid_case.build_ids(category_ids),
        )

    response = exc_info.value.response
    assert_that(
        response.status_code,
        equal_to(invalid_case.expected_status),
        "Unexpected HTTP status for invalid categories.",
    )
    assert_that(
        response.text,
        contains_string(invalid_case.expected_text),
        "Rejection response does not mention the invalid categories.",
    )
    existing_names = [
        workflow.name
        for workflow in workflow_utils.client.workflows.list(
            per_page=200, filter_by_user=True
        )
    ]
    assert_that(
        existing_names,
        is_not(has_item(rejected_workflow_name)),
        "Workflow must not be created when categories are invalid.",
    )
