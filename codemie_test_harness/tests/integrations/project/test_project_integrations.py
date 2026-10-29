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
from hamcrest import assert_that, equal_to
from requests import HTTPError

from codemie_sdk.models.integration import (
    IntegrationType,
    Integration,
    IntegrationTestRequest,
    IntegrationTestResponse,
)
from codemie_test_harness.tests import PROJECT
from codemie_test_harness.tests.test_data.integrations_test_data import (
    valid_integrations,
    invalid_integrations,
    testable_integrations,
    empty_credentials_integrations,
)
from codemie_test_harness.tests.utils.base_utils import (
    get_random_name,
    assert_error_details,
    assert_tool_triggered,
)


@pytest.mark.integration
@pytest.mark.project_integration
@pytest.mark.api
@pytest.mark.smoke
@pytest.mark.parametrize(
    "credential_type, credentials",
    valid_integrations,
)
def test_integration_created(
    credential_type, credentials, general_integration, integration_utils
):
    integration_alias = get_random_name()
    general_integration(
        integration_type=IntegrationType.PROJECT,
        credential_type=credential_type,
        credential_values=credentials,
        integration_alias=integration_alias,
    )
    _integration = integration_utils.get_integration_by_alias(
        integration_alias, IntegrationType.PROJECT
    )
    assert_that(
        _integration.credential_type == credential_type,
        f"Integration with alias '{integration_alias}' has incorrect credential type: "
        f"expected {credential_type}, got {_integration.credential_type}",
    )
    assert_that(
        _integration.setting_type == IntegrationType.PROJECT,
        f"Integration with alias '{integration_alias}' has incorrect integration type: "
        f"expected {IntegrationType.PROJECT}, got {_integration.setting_type}",
    )


@pytest.mark.integration
@pytest.mark.project_integration
@pytest.mark.api
@pytest.mark.smoke
@pytest.mark.parametrize(
    "credential_type, credentials",
    testable_integrations,
)
def test_integration_after_creation(
    credential_type, credentials, general_integration, integration_utils
):
    integration_alias = get_random_name()
    general_integration(
        integration_type=IntegrationType.PROJECT,
        credential_type=credential_type,
        credential_values=credentials,
        integration_alias=integration_alias,
    )
    _integration = integration_utils.get_integration_by_alias(
        integration_alias, IntegrationType.PROJECT
    )
    integration_test_model = IntegrationTestRequest(
        credential_type=_integration.credential_type,
        setting_id=_integration.id,
    )
    test_response = integration_utils.test_integration(
        integration_test_model, IntegrationTestResponse
    )

    successful_test_response = IntegrationTestResponse(message="", success=True)

    assert_that(
        test_response,
        equal_to(successful_test_response),
        "Integration test response is not successful.",
    )


@pytest.mark.integration
@pytest.mark.project_integration
@pytest.mark.api
@pytest.mark.smoke
@pytest.mark.parametrize(
    "credential_type, credentials, error_message",
    invalid_integrations,
)
def test_integration_with_invalid_credentials(
    credential_type, credentials, error_message, integration_utils
):
    integration_alias = get_random_name()
    create_request = Integration(
        project_name=PROJECT,
        credential_type=credential_type,
        credential_values=credentials,
        alias=integration_alias,
        setting_type=IntegrationType.PROJECT,
    )
    create_response = integration_utils.send_create_integration_request(create_request)

    assert_that(
        create_response["message"],
        equal_to("Specified credentials saved"),
        "Integration create response message is not as expected.",
    )
    _integration = integration_utils.get_integration_by_alias(
        integration_alias, IntegrationType.PROJECT
    )

    integration_test_model = IntegrationTestRequest(
        credential_type=_integration.credential_type,
        setting_id=_integration.id,
    )

    try:
        integration_utils.test_integration(integration_test_model)
        raise AssertionError("Integration test response is not expected.")
    except HTTPError as e:
        assert_error_details(e.response, 400, error_message)


@pytest.mark.integration
@pytest.mark.project_integration
@pytest.mark.api
@pytest.mark.smoke
@pytest.mark.parametrize(
    "credential_type, credentials",
    testable_integrations,
)
def test_integration_during_creation(credential_type, credentials, integration_utils):
    integration_test_model = IntegrationTestRequest(
        credential_type=credential_type,
        credential_values=credentials,
    )
    test_response = integration_utils.test_integration(
        integration_test_model, IntegrationTestResponse
    )
    successful_test_response = IntegrationTestResponse(message="", success=True)

    assert_that(
        test_response,
        equal_to(successful_test_response),
        "Integration test response is not successful.",
    )


@pytest.mark.integration
@pytest.mark.project_integration
@pytest.mark.api
@pytest.mark.parametrize(
    "credential_type, credentials, error_message",
    invalid_integrations,
)
def test_integration_during_creation_with_invalid_credentials(
    credential_type, credentials, error_message, integration_utils
):
    integration_test_model = IntegrationTestRequest(
        credential_type=credential_type,
        credential_values=credentials,
    )

    try:
        integration_utils.test_integration(integration_test_model)
        raise AssertionError("Integration test response is not expected.")
    except HTTPError as e:
        assert_error_details(e.response, 400, error_message)


@pytest.mark.integration
@pytest.mark.project_integration
@pytest.mark.api
@pytest.mark.parametrize(
    "credential_type, credentials",
    valid_integrations,
)
def test_delete_integration(
    credential_type, credentials, general_integration, integration_utils
):
    integration_alias = get_random_name()
    general_integration(
        integration_type=IntegrationType.PROJECT,
        credential_type=credential_type,
        credential_values=credentials,
        integration_alias=integration_alias,
    )
    _integration = integration_utils.get_integration_by_alias(
        integration_alias, IntegrationType.PROJECT
    )

    delete_response = integration_utils.delete_integration(_integration)

    assert_that(
        delete_response["message"],
        equal_to("Specified credential removed"),
        "Integration delete response is not as expected.",
    )


@pytest.mark.assistant
@pytest.mark.integration
@pytest.mark.api
@pytest.mark.parametrize(
    "empty_credentials, credential_type, toolkit, tool_name, prompt, expected_response",
    empty_credentials_integrations,
)
def test_assistant_with_empty_credentials(
    assistant_utils,
    assistant,
    integration,
    similarity_check,
    empty_credentials,
    credential_type,
    toolkit,
    tool_name,
    prompt,
    expected_response,
    seeded,
):
    prompt = seeded(prompt)
    expected_response = seeded(expected_response)

    # Create integration with empty credentials
    empty_integration = integration(
        credential_type=credential_type,
        credential_values=empty_credentials,
    )

    assistant_instance = assistant(
        toolkit,
        tool_name,
        settings=empty_integration,
        system_prompt="Always run tool to do the task. Response based on tool result. Do not suggest anything in case of tool error.",
    )

    response, triggered_tools = assistant_utils.ask_assistant(
        assistant_instance,
        prompt,
        minimal_response=False,
        extract_failed_tools=True,
    )

    assert_tool_triggered(tool_name, triggered_tools)

    similarity_check.check_similarity(response, expected_response)
