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

"""
Test for integration update covering all integration types.
Each integration has common fields (alias) and unique credential fields.
Tests also verify that updated integration works by creating assistant with tool.
"""

import pytest
from codemie_sdk.models.integration import (
    IntegrationType,
    Integration,
    CredentialTypes,
    CredentialValues,
)
from hamcrest import assert_that, equal_to

from codemie_test_harness.tests import PROJECT
from codemie_test_harness.tests.enums.tools import Toolkit
from codemie_test_harness.tests.test_data.integrations_update_test_data import (
    integration_update_data,
)
from codemie_test_harness.tests.test_data.open_api_tools_test_data import (
    open_api_tools_test_data,
)
from codemie_test_harness.tests.utils.base_utils import (
    get_random_name,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver


@pytest.mark.integration
@pytest.mark.project_integration
@pytest.mark.api
@pytest.mark.parametrize(
    "credential_type, initial_credentials, updated_credentials, fields_to_validate, "
    "toolkit, tool_name, prompt, expected_response",
    integration_update_data,
)
def test_project_integration_update(
    credential_type,
    initial_credentials,
    updated_credentials,
    fields_to_validate,
    toolkit,
    tool_name,
    prompt,
    expected_response,
    general_integration,
    integration_utils,
    assistant_utils,
    assistant,
    similarity_check,
    seeded,
):
    """
    Test that verifies updating all possible fields for each integration type
    and validates that the updated integration works by testing it with an assistant.

    Steps:
    1. Create an integration with initial (fake) credentials
    2. Update all possible fields (alias + all credential fields) with real credentials
    3. Validate all fields are updated correctly
    4. Create an assistant with the updated integration and verify it works

    Args:
        credential_type: Type of credential (e.g., CredentialTypes.JIRA)
        initial_credentials: List of CredentialValues for initial creation (fake)
        updated_credentials: List of CredentialValues with updated values (real)
        fields_to_validate: Dictionary mapping field keys to expected updated values
        toolkit: The toolkit to use for testing (e.g., Toolkit.CLOUD)
        tool_name: The specific tool to test (e.g., CloudTool.AWS)
        prompt: The prompt to send to the assistant
        expected_response: The expected response pattern
        general_integration: Fixture for creating integrations
        integration_utils: Utility methods for integration operations
        assistant_utils: Utility methods for assistant operations
        assistant: Factory fixture for creating assistants
        similarity_check: Utility for checking response similarity
    """
    prompt = seeded(prompt)
    expected_response = seeded(expected_response)

    # Step 1: Create integration with initial credentials
    initial_alias = get_random_name()
    general_integration(
        integration_type=IntegrationType.PROJECT,
        credential_type=credential_type,
        credential_values=initial_credentials,
        integration_alias=initial_alias,
    )

    created_integration = integration_utils.get_integration_by_alias(
        initial_alias, IntegrationType.PROJECT
    )

    # Step 2: Update all possible fields (alias + all credential fields)
    updated_alias = f"{get_random_name()}-updated"
    update_request = Integration(
        id=created_integration.id,
        project_name=PROJECT,
        credential_type=credential_type,
        credential_values=updated_credentials,
        alias=updated_alias,
        setting_type=IntegrationType.PROJECT,
    )

    update_response = integration_utils.update_integration(update_request)

    assert_that(
        update_response["message"],
        equal_to("Specified credentials updated"),
        f"Integration update response message is not as expected for {credential_type}.",
    )

    # Step 3: Validate all fields are updated correctly
    updated_integration = integration_utils.get_integration_by_alias(
        updated_alias, IntegrationType.PROJECT
    )

    # Validate alias was updated
    assert_that(
        updated_integration.alias,
        equal_to(updated_alias),
        f"Integration alias was not updated correctly for {credential_type}",
    )

    # Validate all credential fields are updated
    # Note: Sensitive fields (password, token, key, secret) are masked with '******'
    # and cannot be verified
    credential_values_dict = {
        cv.key: cv.value for cv in updated_integration.credential_values
    }

    for field_key, expected_value in fields_to_validate.items():
        actual_value = credential_values_dict.get(field_key)

        if isinstance(actual_value, str) and actual_value.startswith("*"):
            # Sensitive field is masked, skip validation
            continue

        assert_that(
            actual_value,
            equal_to(expected_value),
            f"Field '{field_key}' was not updated correctly for {credential_type}. "
            f"Expected: {expected_value}, Got: {actual_value}",
        )

    # Step 4: Verify updated integration works by creating assistant with tool
    # Only test if toolkit and tool_name are provided (some integrations don't have tools)
    if toolkit and tool_name and prompt and expected_response:
        # Create assistant with the updated integration
        test_assistant = assistant(toolkit, tool_name, settings=updated_integration)

        # Ask the assistant using the provided prompt
        response = assistant_utils.ask_assistant(
            test_assistant, prompt, minimal_response=False
        )

        # Verify the response contains expected content
        similarity_check.check_similarity(response, expected_response)


@pytest.mark.integration
@pytest.mark.user_integration
@pytest.mark.api
@pytest.mark.parametrize(
    "credential_type, initial_credentials, updated_credentials, fields_to_validate, "
    "toolkit, tool_name, prompt, expected_response",
    integration_update_data,
)
def test_user_integration_update(
    credential_type,
    initial_credentials,
    updated_credentials,
    fields_to_validate,
    toolkit,
    tool_name,
    prompt,
    expected_response,
    general_integration,
    integration_utils,
    assistant_utils,
    assistant,
    similarity_check,
    seeded,
):
    """
    Test that verifies updating all possible fields for each integration type
    and validates that the updated integration works by testing it with an assistant.

    Steps:
    1. Create an integration with initial (fake) credentials
    2. Update all possible fields (alias + all credential fields) with real credentials
    3. Validate all fields are updated correctly
    4. Create an assistant with the updated integration and verify it works

    Args:
        credential_type: Type of credential (e.g., CredentialTypes.JIRA)
        initial_credentials: List of CredentialValues for initial creation (fake)
        updated_credentials: List of CredentialValues with updated values (real)
        fields_to_validate: Dictionary mapping field keys to expected updated values
        toolkit: The toolkit to use for testing (e.g., Toolkit.CLOUD)
        tool_name: The specific tool to test (e.g., CloudTool.AWS)
        prompt: The prompt to send to the assistant
        expected_response: The expected response pattern
        general_integration: Fixture for creating integrations
        integration_utils: Utility methods for integration operations
        assistant_utils: Utility methods for assistant operations
        assistant: Factory fixture for creating assistants
        similarity_check: Utility for checking response similarity
    """
    prompt = seeded(prompt)
    expected_response = seeded(expected_response)

    # Step 1: Create user integration with initial credentials
    initial_alias = get_random_name()
    general_integration(
        integration_type=IntegrationType.USER,
        credential_type=credential_type,
        credential_values=initial_credentials,
        integration_alias=initial_alias,
    )

    created_integration = integration_utils.get_integration_by_alias(
        initial_alias, IntegrationType.USER
    )

    # Step 2: Update all possible fields (alias + all credential fields)
    updated_alias = f"{get_random_name()}-updated"
    update_request = Integration(
        id=created_integration.id,
        project_name=PROJECT,
        credential_type=credential_type,
        credential_values=updated_credentials,
        alias=updated_alias,
        setting_type=IntegrationType.USER,
    )

    update_response = integration_utils.update_integration(update_request)

    assert_that(
        update_response["message"],
        equal_to("Specified credentials updated"),
        f"Integration update response message is not as expected for {credential_type}.",
    )

    # Step 3: Validate all fields are updated correctly
    updated_integration = integration_utils.get_integration_by_alias(
        updated_alias, IntegrationType.USER
    )

    # Validate alias was updated
    assert_that(
        updated_integration.alias,
        equal_to(updated_alias),
        f"Integration alias was not updated correctly for {credential_type}",
    )

    # Validate all credential fields are updated
    # Note: Sensitive fields (password, token, key, secret) are masked with '******'
    # and cannot be verified
    credential_values_dict = {
        cv.key: cv.value for cv in updated_integration.credential_values
    }

    for field_key, expected_value in fields_to_validate.items():
        actual_value = credential_values_dict.get(field_key)

        if isinstance(actual_value, str) and actual_value.startswith("*"):
            # Sensitive field is masked, skip validation
            continue

        assert_that(
            actual_value,
            equal_to(expected_value),
            f"Field '{field_key}' was not updated correctly for {credential_type}. "
            f"Expected: {expected_value}, Got: {actual_value}",
        )

    # Step 4: Verify updated integration works by creating assistant with tool
    # Only test if toolkit and tool_name are provided (some integrations don't have tools)
    if toolkit and tool_name and prompt and expected_response:
        # Create assistant with the updated integration
        test_assistant = assistant(toolkit, tool_name, settings=updated_integration)

        # Ask the assistant using the provided prompt
        response = assistant_utils.ask_assistant(
            test_assistant, prompt, minimal_response=False
        )

        # Verify the response contains expected content
        similarity_check.check_similarity(response, expected_response)


integration_types = [
    pytest.param(IntegrationType.PROJECT, id="project_integration"),
    pytest.param(IntegrationType.USER, id="user_integration"),
]


@pytest.mark.integration
@pytest.mark.openapi
@pytest.mark.api
@pytest.mark.parametrize(
    "integration_type",
    integration_types,
)
@pytest.mark.skipif(
    EnvironmentResolver.is_azure(),
    reason="Still have an issue with encoding long strings",
)
def test_openapi_integration_update(
    integration_type,
    client,
    general_integration,
    integration_utils,
    assistant_utils,
    assistant,
    similarity_check,
):
    """
    Test that verifies updating OpenAPI integration with valid credentials
    and validates that the updated integration works by testing it with an assistant.

    This test is separate from the main parametrized test because OpenAPI requires
    a valid bearer token from the client.token, which is not available at test
    collection time.

    Steps:
    1. Create an integration with initial (invalid) credentials
    2. Update with valid credentials (using client.token)
    3. Validate all fields are updated correctly
    4. Create an assistant with the updated integration and verify it works

    Args:
        integration_type: Type of integration (PROJECT or USER)
        client: CodeMie client fixture with valid authentication token
        general_integration: Fixture for creating integrations
        integration_utils: Utility methods for integration operations
        assistant_utils: Utility methods for assistant operations
        assistant: Factory fixture for creating assistants
        similarity_check: Utility for checking response similarity
    """

    # Step 1: Create integration with initial (invalid) credentials
    initial_alias = get_random_name()
    initial_credentials = CredentialsManager.open_api_credentials("fake-token-12345")
    general_integration(
        integration_type=integration_type,
        credential_type=CredentialTypes.OPENAPI,
        credential_values=initial_credentials,
        integration_alias=initial_alias,
    )

    created_integration = integration_utils.get_integration_by_alias(
        initial_alias, integration_type
    )

    # Step 2: Update with valid credentials using client.token
    updated_alias = f"{get_random_name()}-updated"
    updated_credentials = CredentialsManager.open_api_credentials(str(client.token))
    update_request = Integration(
        id=created_integration.id,
        project_name=PROJECT,
        credential_type=CredentialTypes.OPENAPI,
        credential_values=updated_credentials,
        alias=updated_alias,
        setting_type=integration_type,
    )

    update_response = integration_utils.update_integration(update_request)

    assert_that(
        update_response["message"],
        equal_to("Specified credentials updated"),
        f"Integration update response message is not as expected for {CredentialTypes.OPENAPI}.",
    )

    # Step 3: Validate all fields are updated correctly
    updated_integration = integration_utils.get_integration_by_alias(
        updated_alias, integration_type
    )

    # Validate alias was updated
    assert_that(
        updated_integration.alias,
        equal_to(updated_alias),
        f"Integration alias was not updated correctly for {CredentialTypes.OPENAPI}",
    )

    # Validate credential fields
    # Note: openapi_api_key is sensitive and will be masked with '******'
    # We can only validate non-sensitive fields like 'url'
    credential_values_dict = {
        cv.key: cv.value for cv in updated_integration.credential_values
    }

    # URL should be AUTO_GENERATED for both initial and updated credentials
    assert_that(
        credential_values_dict.get("url"),
        equal_to(CredentialsManager.AUTO_GENERATED),
        "URL field should be AUTO_GENERATED for OpenAPI integration",
    )

    # Step 4: Verify updated integration works by creating assistant with tool
    # Use test data from open_api_tools_test_data
    test_assistant = assistant(
        Toolkit.OPEN_API,
        open_api_tools_test_data[1][0],  # OpenApiTool.GET_OPEN_API_SPEC
        settings=updated_integration,
    )

    # Ask the assistant using the provided prompt
    response = assistant_utils.ask_assistant(
        test_assistant,
        open_api_tools_test_data[1][1],  # OPEN_API_SPEC_TOOL_TASK
        minimal_response=False,
    )

    # Verify the response contains expected content
    similarity_check.check_similarity(
        response,
        open_api_tools_test_data[1][2],  # RESPONSE_FOR_OPEN_API_SPEC
    )


@pytest.mark.integration
@pytest.mark.mcp
@pytest.mark.api
@pytest.mark.parametrize(
    "integration_type",
    integration_types,
)
def test_mcp_integration_update(
    integration_type,
    general_integration,
    integration_utils,
    assistant_utils,
    assistant,
):
    """
    Test that verifies updating MCP integration with valid credentials
    and validates that the updated integration works by testing it with an assistant.

    This test is separate from the main parametrized test because MCP integration
    requires special handling with MCP server configuration.

    Steps:
    1. Create an integration with initial (invalid) credentials
    2. Update with valid credentials
    3. Validate all fields are updated correctly
    4. Create an assistant with MCP server using the updated integration and verify it works

    Args:
        integration_type: Type of integration (PROJECT or USER)
        general_integration: Fixture for creating integrations
        integration_utils: Utility methods for integration operations
        assistant_utils: Utility methods for assistant operations
        assistant: Factory fixture for creating assistants
    """
    from codemie_sdk.models.assistant import MCPServerDetails, MCPServerConfig
    from codemie_test_harness.tests import autotest_entity_prefix
    from hamcrest import contains_string

    # Step 1: Create integration with initial (invalid) credentials
    initial_alias = get_random_name()
    initial_credentials = [
        CredentialValues(key="ALLOWED_COMMANDS", value="fake-command")
    ]
    general_integration(
        integration_type=integration_type,
        credential_type=CredentialTypes.MCP,
        credential_values=initial_credentials,
        integration_alias=initial_alias,
    )

    created_integration = integration_utils.get_integration_by_alias(
        initial_alias, integration_type
    )

    # Step 2: Update with valid credentials
    updated_alias = f"{get_random_name()}-updated"
    updated_credentials = CredentialsManager.mcp_credentials()
    update_request = Integration(
        id=created_integration.id,
        project_name=PROJECT,
        credential_type=CredentialTypes.MCP,
        credential_values=updated_credentials,
        alias=updated_alias,
        setting_type=integration_type,
    )

    update_response = integration_utils.update_integration(update_request)

    assert_that(
        update_response["message"],
        equal_to("Specified credentials updated"),
        f"Integration update response message is not as expected for {CredentialTypes.MCP}.",
    )

    # Step 3: Validate all fields are updated correctly
    updated_integration = integration_utils.get_integration_by_alias(
        updated_alias, integration_type
    )

    # Validate alias was updated
    assert_that(
        updated_integration.alias,
        equal_to(updated_alias),
        f"Integration alias was not updated correctly for {CredentialTypes.MCP}",
    )

    # Step 4: Verify updated integration works by creating assistant with MCP server
    # Create MCP server configuration using the updated integration
    cli_mcp_server_with_integration = MCPServerDetails(
        name="CLI MCP server",
        description="CLI MCP server for testing",
        enabled=True,
        settings=updated_integration,  # "ALLOWED_COMMANDS": "ls,echo,mkdir",
        config=MCPServerConfig(
            command="uvx",
            # Pin `mcp` below 2.0.0: cli-mcp-server declares an unpinned `mcp>=1.10.1`
            # dependency, and mcp==2.0.0 renamed `Server.list_tools`, breaking it.
            args=["--with", "mcp<2.0.0", "cli-mcp-server"],
            env={
                "ALLOWED_DIR": "/tmp",
                "ALLOWED_FLAGS": "-l,--help",
                "MAX_COMMAND_LENGTH": "48",
            },
        ),
    )

    test_assistant = assistant(mcp_server=cli_mcp_server_with_integration)

    # Test the assistant by creating a directory and listing it
    dir_name = f"{autotest_entity_prefix}{get_random_name()}"
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant,
        f"Execute commands sequentially: 'mkdir {dir_name}' then 'ls'. In the end return output of the second command.",
        minimal_response=False,
    )

    # Verify the response contains the created directory name
    assert_that(
        response,
        contains_string(dir_name),
        f"Expected directory name '{dir_name}' not found in response",
    )
