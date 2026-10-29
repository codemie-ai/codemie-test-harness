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

"""Tests for integration validation with multiple integrations."""

import pytest
from codemie_sdk.models.assistant import ToolDetails, ToolKitDetails
from codemie_sdk.models.integration import IntegrationType, CredentialTypes
from hamcrest import assert_that, not_none

from codemie_test_harness.tests.enums.tools import Toolkit, GitTool
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.constants import test_project_name
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager


@pytest.mark.assistant
@pytest.mark.gitlab
@pytest.mark.integration
@pytest.mark.not_for_parallel_run
@pytest.mark.api
def test_assistant_creation_with_valid_integration_among_multiple_git_integrations(
    integration_utils, assistant_utils
):
    """
    Test that assistant can be created with a valid Git integration
    when user has both valid and invalid Git integrations.

    This test verifies the fix where integration validation
    failed during Assistant creation when user had multiple Git integrations
    (some valid, some invalid). The fix ensures validation only checks the
    selected integration, not all user integrations.

    Steps:
    1. Delete all existing Git integrations for the test project
    2. Create a valid Git integration
    3. Create an invalid Git integration (empty token)
    4. Create an Assistant with Git tool and valid integration attached
    5. Verify assistant is created without errors
    """
    # Step 1: Delete all existing Git integrations for the test project
    for integration_type in IntegrationType:
        integration_utils.delete_integrations_by_type(
            integration_type, CredentialTypes.GIT, test_project_name
        )

    # Step 2: Create a valid Git integration
    valid_git_integration = integration_utils.create_integration(
        setting_type=IntegrationType.USER,
        credential_type=CredentialTypes.GIT,
        credential_values=CredentialsManager.gitlab_credentials(),
        project_name=test_project_name,
    )

    # Step 3: Create an invalid Git integration (wrong token)
    _invalid_git_integration = integration_utils.create_integration(
        setting_type=IntegrationType.USER,
        credential_type=CredentialTypes.GIT,
        credential_values=CredentialsManager.invalid_gitlab_credentials(),
        project_name=test_project_name,
    )

    _assistant = None
    try:
        # Step 4: Create an Assistant with Git tool and valid integration attached
        assistant_name = get_random_name()
        _assistant = assistant_utils.create_assistant(
            assistant_name=assistant_name,
            toolkits=[
                ToolKitDetails(
                    toolkit=Toolkit.GIT,
                    tools=[
                        ToolDetails(
                            name=GitTool.LIST_BRANCHES_IN_REPO,
                            settings=valid_git_integration,
                        ),
                    ],
                )
            ],
            project_name=test_project_name,
        )

        # Step 5: Verify assistant is created without errors
        git_assistant = assistant_utils.get_assistant_by_name(assistant_name)
        assert_that(git_assistant, not_none())
    finally:
        if _assistant:
            assistant_utils.delete_assistant(_assistant)
        integration_utils.delete_integration(valid_git_integration)
        integration_utils.delete_integration(_invalid_git_integration)
