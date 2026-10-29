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
from codemie_sdk import Category
from codemie_sdk.models.assistant import AssistantUpdateRequest
from codemie_sdk.models.integration import IntegrationType, CredentialTypes
from hamcrest import (
    assert_that,
    has_length,
    greater_than,
    only_contains,
    instance_of,
    equal_to,
    is_,
)

from codemie_test_harness.tests import CredentialsManager, PROJECT
from codemie_test_harness.tests.utils.admin_utils import AdminUtils
from codemie_test_harness.tests.utils.assistant_utils import AssistantUtils
from codemie_test_harness.tests.utils.base_utils import (
    assert_error_details,
    get_random_name,
)
from codemie_test_harness.tests.utils.categories_utils import CategoriesUtils
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver
from codemie_test_harness.tests.utils.integration_utils import IntegrationUtils
from codemie_test_harness.tests.utils.provider_utils import ProviderUtils


ADMIN_OR_MAINTAINER_REQUIRED = (
    "This action requires administrator or maintainer privileges."
)

ADMIN_OR_MAINTAINER_OR_AUDITOR_REQUIRED = (
    "This action requires administrator, maintainer, or auditor privileges."
)

DEFAULT_USER = {
    "username": CredentialsManager.get_parameter("AUTH_USERNAME_DEFAULT"),
    "password": CredentialsManager.get_parameter("AUTH_PASSWORD_DEFAULT"),
}

PROJECT_USER = {
    "username": CredentialsManager.get_parameter("AUTH_USERNAME_PROJECT"),
    "password": CredentialsManager.get_parameter("AUTH_PASSWORD_PROJECT"),
}


@pytest.mark.roles
@pytest.mark.api
@pytest.mark.skipif(
    not EnvironmentResolver.is_preview(),
    reason="Default test user and project admin user created only on preview environment",
)
@pytest.mark.parametrize(
    "test_user",
    [DEFAULT_USER, PROJECT_USER],
    ids=["default_user", "project_user"],
)
def test_administration_management_denied(test_user):
    """Test verifies user without role can't get or create project."""
    user_client = get_client(
        username=test_user["username"],
        password=test_user["password"],
    )
    admin_utils = AdminUtils(user_client)

    # Verify default/project-admin user can't list available projects
    with pytest.raises(Exception) as exec_info:
        admin_utils.list_projects()

    assert_error_details(
        exec_info.value.response,
        403,
        ADMIN_OR_MAINTAINER_OR_AUDITOR_REQUIRED,
    )

    # Verify default/project-admin user can't create projects
    with pytest.raises(Exception) as exec_info:
        admin_utils.create_project(get_random_name())

    assert_error_details(
        exec_info.value.response,
        403,
        ADMIN_OR_MAINTAINER_REQUIRED,
    )


@pytest.mark.roles
@pytest.mark.api
@pytest.mark.skipif(
    not EnvironmentResolver.is_preview(),
    reason="Default test user and project admin user created only on preview environment",
)
@pytest.mark.parametrize(
    "test_user",
    [DEFAULT_USER, PROJECT_USER],
    ids=["default_user", "project_user"],
)
def test_categories_management_denied(test_user):
    user_client = get_client(
        username=test_user["username"],
        password=test_user["password"],
    )
    categories_utils = CategoriesUtils(user_client)

    categories_list = categories_utils.get_categories()

    # Verify default/project-admin user can get available categories
    assert_that(categories_list, has_length(greater_than(0)))
    assert_that(categories_list, only_contains(instance_of(Category)))

    # Verify default/project-admin user can't create new category
    with pytest.raises(Exception) as exec_info:
        categories_utils.create_category(get_random_name(), get_random_name())
    assert_error_details(
        exec_info.value.response,
        403,
        ADMIN_OR_MAINTAINER_REQUIRED,
    )

    # Verify default/project-admin user can't update category
    with pytest.raises(Exception) as exec_info:
        categories_utils.update_category("1", get_random_name(), get_random_name())
    assert_error_details(
        exec_info.value.response,
        403,
        ADMIN_OR_MAINTAINER_REQUIRED,
    )

    # Verify default/project-admin user can't delete category
    with pytest.raises(Exception) as exec_info:
        categories_utils.delete_category("1")
    assert_error_details(
        exec_info.value.response,
        403,
        ADMIN_OR_MAINTAINER_REQUIRED,
    )


@pytest.mark.roles
@pytest.mark.api
@pytest.mark.skipif(
    not EnvironmentResolver.is_preview(),
    reason="Default test user and project admin user created only on preview environment",
)
@pytest.mark.parametrize(
    "test_user",
    [DEFAULT_USER, PROJECT_USER],
    ids=["default_user", "project_user"],
)
def test_provider_management_denied(test_user):
    user_client = get_client(
        username=test_user["username"],
        password=test_user["password"],
    )
    provider_utils = ProviderUtils(user_client)

    list_response = provider_utils.send_get_request_to_providers_endpoint()

    # Verify default/project-admin user can get providers list
    assert_that(list_response.status_code, equal_to(200))
    response_data = list_response.json()
    assert_that(isinstance(response_data, list), is_(True))
    assert_that(response_data, has_length(greater_than(0)))

    request_json = provider_utils.provider_request_json()
    create_response = provider_utils.send_post_request_to_providers_endpoint(
        request_json
    )

    # Verify default/project-admin user can't create provider
    assert_that(create_response.status_code, equal_to(403))
    response_data = create_response.json()
    assert_that(
        response_data["error"]["details"],
        equal_to(ADMIN_OR_MAINTAINER_REQUIRED),
    )

    delete_response = provider_utils.send_delete_provider_request("1")

    # Verify default/project-admin user can't delete provider
    assert_that(delete_response.status_code, equal_to(403))
    response_data = delete_response.json()
    assert_that(
        response_data["error"]["details"],
        equal_to(ADMIN_OR_MAINTAINER_REQUIRED),
    )


@pytest.mark.roles
@pytest.mark.api
@pytest.mark.skipif(
    not EnvironmentResolver.is_preview(),
    reason="Default test user and project admin user created only on preview environment",
)
def test_default_user_project_integrations_denied():
    default_user_client = get_client(
        username=DEFAULT_USER["username"],
        password=DEFAULT_USER["password"],
    )

    default_user_client = IntegrationUtils(default_user_client)

    integration_list = default_user_client.list_integrations(IntegrationType.PROJECT)

    # Verify default user can't get list of project integrations
    assert_that(integration_list, has_length(0))

    # Verify default user can't create project integration
    with pytest.raises(Exception) as exec_info:
        default_user_client.create_project_integration(
            CredentialTypes.JIRA, CredentialsManager.jira_credentials(), PROJECT
        )
    assert_error_details(
        exec_info.value.response,
        403,
        f"You do not have sufficient permissions to access the project '{PROJECT}'.",
    )


@pytest.mark.roles
@pytest.mark.api
@pytest.mark.skipif(
    not EnvironmentResolver.is_preview(),
    reason="Default test user and project admin user created only on preview environment",
)
def test_assistant_edit_denied_for_non_creator():
    default_user_client = get_client(
        username=DEFAULT_USER["username"],
        password=DEFAULT_USER["password"],
    )

    default_user_client = AssistantUtils(default_user_client)

    selected_assistant = default_user_client.get_assistant_by_name(
        assistant_name="AI/Run FAQ",
        scope="marketplace",
    )
    request = AssistantUpdateRequest(
        name=get_random_name(),
        description=get_random_name(),
        system_prompt=get_random_name(),
        project=PROJECT,
        llm_model_type=get_random_name(),
    )

    # Verify default user can't edit assistant which he didn't create
    with pytest.raises(Exception) as exec_info:
        default_user_client.update_assistant(selected_assistant.id, request)
    assert_error_details(
        exec_info.value.response,
        401,
        "You do not have the necessary permissions to update this entity.",
    )
