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

import pytest
from hamcrest import assert_that

from codemie_test_harness.tests import PROJECT
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.yaml_utils import AssistantModel, StateModel


@pytest.fixture(scope="session")
def workflow_name_for_search():
    base_name = get_random_name()
    return f"{base_name}_workflow_for_search_test"


@pytest.fixture(scope="session")
def partial_workflow_name(workflow_name_for_search):
    return workflow_name_for_search[:8]


@pytest.fixture(scope="function", autouse=True)
def workflow_for_search(
    workflow, default_llm, workflow_name_for_search, workflow_utils
):
    assistant_and_state_name = "branch_creator"

    assistant = AssistantModel(
        id=assistant_and_state_name,
        model=default_llm.base_name,
        system_prompt="You are a Git assistant.",
    )

    state = StateModel(
        id=assistant_and_state_name,
        assistant_id=assistant_and_state_name,
    )

    return workflow(
        workflow_name=workflow_name_for_search,
        tool_model=[],
        assistant_model=assistant,
        state_model=state,
    )


@pytest.fixture
def test_data(workflow_name_for_search, partial_workflow_name):
    return [
        (None, {"name": workflow_name_for_search}),
        (PROJECT, None),
        (PROJECT, {"name": workflow_name_for_search}),
        (None, {"shared": True}),
        (None, {"shared": True, "name": workflow_name_for_search}),
        (None, {"name": partial_workflow_name}),
        (PROJECT, {"name": partial_workflow_name}),
    ]


@pytest.fixture
def test_case_data(request, test_data):
    return test_data[request.param]


def pytest_generate_tests(metafunc):
    if "test_case_data" in metafunc.fixturenames:
        metafunc.parametrize(
            "test_case_data",
            list(range(7)),  # 7 test cases
            ids=[
                "name_only",
                "project_only",
                "project_and_name",
                "shared_only",
                "shared_and_name",
                "partial_name",
                "project_and_partial_name",
            ],
            indirect=True,
        )


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.search
@pytest.mark.api
def test_search_workflows_by_filters(
    search_utils, test_case_data, workflow_name_for_search
):
    project, filters = test_case_data
    response = search_utils.list_workflows(projects=project, filters=filters)
    names = list(map(lambda work_flow: work_flow["name"], response))

    assert_that(
        workflow_name_for_search in names, "Workflow is not found in search results"
    )
