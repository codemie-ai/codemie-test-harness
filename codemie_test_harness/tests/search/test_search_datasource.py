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

from codemie_sdk.models.datasource import DataSourceType, DataSourceStatus
from codemie_sdk.models.integration import CredentialTypes
from codemie_test_harness.tests import TEST_USER, PROJECT
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.base_utils import get_random_name

ASSERTION_ERROR = "Datasource is not found in search results."


@pytest.fixture(scope="session")
def datasource_name_for_search():
    base_name = get_random_name()
    return f"{base_name}_ds"


@pytest.fixture(scope="session")
def partial_datasource_name(datasource_name_for_search):
    return datasource_name_for_search[:8]


@pytest.fixture(scope="session", autouse=True)
def datasource(
    datasource_utils,
    integration_utils,
    default_embedding_llm,
    datasource_name_for_search,
):
    code_integration = integration_utils.create_integration(
        credential_type=CredentialTypes.GIT,
        credential_values=CredentialsManager.gitlab_credentials(),
    )

    datasource = datasource_utils.create_gitlab_datasource(
        name=datasource_name_for_search,
        setting_id=code_integration.id,
        embeddings_model=default_embedding_llm.base_name,
    )
    yield datasource
    if datasource:
        datasource_utils.delete_datasource(datasource)
    integration_utils.delete_integration(code_integration)


@pytest.fixture
def search_by_name_data(datasource_name_for_search, partial_datasource_name):
    return [
        {"name": datasource_name_for_search},
        {"name": partial_datasource_name},
    ]


@pytest.fixture
def name_filters(request, search_by_name_data):
    return search_by_name_data[request.param]


@pytest.fixture
def search_by_type_data(datasource_name_for_search):
    return [
        ([DataSourceType.CODE], None),
        ([DataSourceType.CODE], {"name": datasource_name_for_search}),
        ([DataSourceType.CODE, DataSourceType.CONFLUENCE], None),
    ]


@pytest.fixture
def type_test_data(request, search_by_type_data):
    return search_by_type_data[request.param]


@pytest.fixture
def search_by_owner_data(datasource_name_for_search):
    return [
        (TEST_USER, None, None),
        (TEST_USER, None, {"name": datasource_name_for_search}),
        (TEST_USER, DataSourceStatus.COMPLETED, None),
    ]


@pytest.fixture
def owner_test_data(request, search_by_owner_data):
    return search_by_owner_data[request.param]


@pytest.fixture
def search_by_status_data(datasource_name_for_search):
    return [
        (DataSourceStatus.COMPLETED, None),
        (DataSourceStatus.COMPLETED, {"name": datasource_name_for_search}),
    ]


@pytest.fixture
def status_test_data(request, search_by_status_data):
    return search_by_status_data[request.param]


@pytest.fixture
def search_by_project_data(datasource_name_for_search):
    return [
        (PROJECT, None, None),
        (PROJECT, DataSourceStatus.COMPLETED, None),
        (PROJECT, None, {"name": datasource_name_for_search}),
    ]


@pytest.fixture
def project_test_data(request, search_by_project_data):
    return search_by_project_data[request.param]


def pytest_generate_tests(metafunc):
    # Check if we're running with smoke marker
    mark_expr = metafunc.config.getoption("-m", "")
    is_smoke = "smoke" in mark_expr if mark_expr else False

    if "name_filters" in metafunc.fixturenames:
        metafunc.parametrize(
            "name_filters",
            list(range(2)),  # 2 test cases for name search
            ids=["full_name", "partial_name"],
            indirect=True,
        )
    elif "type_test_data" in metafunc.fixturenames:
        metafunc.parametrize(
            "type_test_data",
            list(range(3)),  # 3 test cases for type search
            ids=["code_type_only", "code_type_with_name", "multiple_types"],
            indirect=True,
        )
    elif "owner_test_data" in metafunc.fixturenames:
        # All owner test cases are excluded from smoke suite
        ids = ["owner_only", "owner_with_name", "owner_with_status"]
        params = []
        for i in range(3):
            if is_smoke:
                # Skip all owner test cases in smoke suite
                params.append(
                    pytest.param(
                        i,
                        marks=pytest.mark.skip(reason="Excluded from smoke suite"),
                    )
                )
            else:
                params.append(i)

        metafunc.parametrize(
            "owner_test_data",
            params,
            ids=ids,
            indirect=True,
        )
    elif "status_test_data" in metafunc.fixturenames:
        metafunc.parametrize(
            "status_test_data",
            list(range(2)),  # 2 test cases for status search
            ids=["status_only", "status_with_name"],
            indirect=True,
        )
    elif "project_test_data" in metafunc.fixturenames:
        metafunc.parametrize(
            "project_test_data",
            list(range(3)),  # 3 test cases for project search
            ids=["project_only", "project_with_status", "project_with_name"],
            indirect=True,
        )


@pytest.mark.gitlab
@pytest.mark.smoke
@pytest.mark.datasource
@pytest.mark.search
@pytest.mark.api
def test_search_datasource_by_name(
    search_utils, name_filters, datasource_name_for_search
):
    response = search_utils.list_data_sources(filters=name_filters)
    names = list(map(lambda item: item["name"], response))

    assert_that(datasource_name_for_search in names, ASSERTION_ERROR)


@pytest.mark.gitlab
@pytest.mark.smoke
@pytest.mark.datasource
@pytest.mark.search
@pytest.mark.api
def test_search_datasource_by_type(
    search_utils, type_test_data, datasource_name_for_search
):
    datasource_types, filters = type_test_data
    response = search_utils.list_data_sources(
        datasource_types=datasource_types, filters=filters
    )
    names = list(map(lambda item: item["name"], response))

    assert_that(datasource_name_for_search in names, ASSERTION_ERROR)


@pytest.mark.gitlab
@pytest.mark.smoke
@pytest.mark.datasource
@pytest.mark.search
@pytest.mark.api
def test_search_datasource_by_owner(
    search_utils, owner_test_data, datasource_name_for_search
):
    owner, status, filters = owner_test_data
    response = search_utils.list_data_sources(
        owner=owner, status=status, filters=filters
    )
    names = list(map(lambda item: item["name"], response))

    assert_that(datasource_name_for_search in names, ASSERTION_ERROR)


@pytest.mark.gitlab
@pytest.mark.smoke
@pytest.mark.datasource
@pytest.mark.search
@pytest.mark.api
def test_search_datasource_by_status(
    search_utils, status_test_data, datasource_name_for_search
):
    status, filters = status_test_data
    response = search_utils.list_data_sources(status=status, filters=filters)
    names = list(map(lambda item: item["name"], response))

    assert_that(datasource_name_for_search in names, ASSERTION_ERROR)


@pytest.mark.gitlab
@pytest.mark.smoke
@pytest.mark.datasource
@pytest.mark.search
@pytest.mark.api
def test_search_datasource_by_project(
    search_utils, project_test_data, datasource_name_for_search
):
    project, status, filters = project_test_data
    response = search_utils.list_data_sources(
        projects=project, status=status, filters=filters
    )
    names = list(map(lambda item: item["name"], response))

    assert_that(datasource_name_for_search in names, ASSERTION_ERROR)
