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

from codemie_sdk.models.integration import CredentialTypes, IntegrationType
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.base_utils import get_random_name

ASSERTION_ERROR = "Integration is not found in search results."


@pytest.fixture(scope="session")
def project_integration_name():
    base_name = get_random_name()
    return f"{base_name}_project_integration_for_search"


@pytest.fixture(scope="session")
def user_integration_name():
    base_name = get_random_name()
    return f"{base_name}_user_integration_for_search"


@pytest.fixture(scope="session", autouse=True)
def user_integration(integration_utils, user_integration_name):
    integration = integration_utils.create_integration(
        setting_type=IntegrationType.USER,
        integration_alias=user_integration_name,
        credential_type=CredentialTypes.GIT,
        credential_values=CredentialsManager.gitlab_credentials(),
    )
    yield integration
    integration_utils.delete_integration(integration)


@pytest.fixture(scope="session", autouse=True)
def project_integration(integration_utils, project_integration_name):
    integration = integration_utils.create_integration(
        setting_type=IntegrationType.PROJECT,
        integration_alias=project_integration_name,
        credential_type=CredentialTypes.GIT,
        credential_values=CredentialsManager.gitlab_credentials(),
    )
    yield integration
    if integration:
        integration_utils.delete_integration(integration)


@pytest.fixture
def build_user_search_params(user_integration_name):
    return [
        {"search": user_integration_name},
        {"search": user_integration_name[:8]},
        {"type": [CredentialTypes.GIT]},
        {"type": [CredentialTypes.GIT], "search": user_integration_name},
        {"type": [CredentialTypes.GIT], "search": user_integration_name[:8]},
    ]


@pytest.fixture
def build_project_search_params(project_integration_name):
    return [
        {"search": project_integration_name},
        {"search": project_integration_name[:8]},
        {"type": [CredentialTypes.GIT]},
        {"type": [CredentialTypes.GIT], "search": project_integration_name},
        {"type": [CredentialTypes.GIT], "search": project_integration_name[:8]},
    ]


@pytest.fixture
def user_filters(request, build_user_search_params):
    return build_user_search_params[request.param]


@pytest.fixture
def project_filters(request, build_project_search_params):
    return build_project_search_params[request.param]


def pytest_generate_tests(metafunc):
    if "user_filters" in metafunc.fixturenames:
        metafunc.parametrize(
            "user_filters",
            list(range(5)),  # 5 test cases for user integration
            ids=[
                "search_full_name",
                "search_partial_name",
                "type_only",
                "type_and_full_name",
                "type_and_partial_name",
            ],
            indirect=True,
        )
    elif "project_filters" in metafunc.fixturenames:
        metafunc.parametrize(
            "project_filters",
            list(range(5)),  # 5 test cases for project integration
            ids=[
                "search_full_name",
                "search_partial_name",
                "type_only",
                "type_and_full_name",
                "type_and_partial_name",
            ],
            indirect=True,
        )


@pytest.mark.smoke
@pytest.mark.integration
@pytest.mark.user_integration
@pytest.mark.search
@pytest.mark.api
def test_search_user_integration(search_utils, user_filters, user_integration_name):
    response = search_utils.list_integrations(
        setting_type=IntegrationType.USER, filters=user_filters
    )
    names = list(map(lambda item: item["alias"], response))

    assert_that(user_integration_name in names, ASSERTION_ERROR)


@pytest.mark.smoke
@pytest.mark.integration
@pytest.mark.project_integration
@pytest.mark.search
@pytest.mark.api
def test_search_project_integration(
    search_utils, project_filters, project_integration_name
):
    response = search_utils.list_integrations(
        setting_type=IntegrationType.PROJECT, filters=project_filters
    )
    names = list(map(lambda item: item["alias"], response))

    assert_that(project_integration_name in names, ASSERTION_ERROR)
