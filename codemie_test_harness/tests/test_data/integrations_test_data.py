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

from codemie_sdk.models.integration import CredentialTypes, CredentialValues
from codemie_test_harness.tests.enums.integrations import DataBaseDialect
from codemie_test_harness.tests.enums.tools import (
    Toolkit,
    VcsTool,
    NotificationTool,
    ProjectManagementTool,
    ServiceNowTool,
    OpenApiTool,
    CloudTool,
    DataManagementTool,
    AccessManagementTool,
)
from codemie_test_harness.tests.test_data.ado_test_plan_tools_test_data import (
    ado_test_plan_get_test_data,
)
from codemie_test_harness.tests.test_data.ado_wiki_tools_test_data import (
    ado_wiki_get_test_data,
)
from codemie_test_harness.tests.test_data.ado_work_item_tools_test_data import (
    ado_work_item_get_test_data,
)
from codemie_test_harness.tests.test_data.cloud_tools_test_data import cloud_test_data
from codemie_test_harness.tests.test_data.data_management_tools_test_data import (
    ELASTIC_TOOL_TASK,
)
from codemie_test_harness.tests.test_data.keycloak_tool_test_data import (
    KEYCLOAK_TOOL_PROMPT,
)
from codemie_test_harness.tests.test_data.notification_tools_test_data import (
    TELEGRAM_TOOL_PROMPT,
)
from codemie_test_harness.tests.test_data.open_api_tools_test_data import (
    OPEN_API_SPEC_TOOL_TASK,
)
from codemie_test_harness.tests.test_data.pm_tools_test_data import (
    CONFLUENCE_TOOL_PROMPT,
)
from codemie_test_harness.tests.test_data.report_portal_tools_test_data import (
    rp_test_data,
)
from codemie_test_harness.tests.test_data.servicenow_tools_test_data import PROMPT
from codemie_test_harness.tests.utils.ado_names import ado_text
from codemie_test_harness.tests.utils.cloud_seed import AZURE_SEED
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver
from codemie_test_harness.tests.utils.jira_seed import Seeded

valid_integrations = [
    pytest.param(
        CredentialTypes.AWS,
        CredentialsManager.aws_credentials(),
        marks=[
            pytest.mark.aws,
            pytest.mark.cloud,
        ],
        id=CredentialTypes.AWS,
    ),
    pytest.param(
        CredentialTypes.AZURE,
        CredentialsManager.azure_credentials(),
        marks=[
            pytest.mark.azure,
            pytest.mark.cloud,
        ],
        id=CredentialTypes.AZURE,
    ),
    pytest.param(
        CredentialTypes.GCP,
        CredentialsManager.gcp_credentials(),
        marks=[
            pytest.mark.gcp,
            pytest.mark.cloud,
            pytest.mark.skipif(
                EnvironmentResolver.is_azure(),
                reason="Still have an issue with encoding long strings",
            ),
        ],
        id=CredentialTypes.GCP,
    ),
    pytest.param(
        CredentialTypes.SONAR,
        CredentialsManager.sonar_credentials(),
        marks=pytest.mark.sonar,
        id=f"{CredentialTypes.SONAR}_server",
    ),
    pytest.param(
        CredentialTypes.SONAR,
        CredentialsManager.sonar_cloud_credentials(),
        marks=pytest.mark.sonar,
        id=f"{CredentialTypes.SONAR}_cloud",
    ),
    pytest.param(
        CredentialTypes.GIT,
        CredentialsManager.gitlab_credentials(),
        marks=pytest.mark.gitlab,
        id=f"{CredentialTypes.GIT}_gitlab",
    ),
    pytest.param(
        CredentialTypes.GIT,
        CredentialsManager.github_credentials(),
        marks=pytest.mark.github,
        id=f"{CredentialTypes.GIT}_github",
    ),
    pytest.param(
        CredentialTypes.CONFLUENCE,
        CredentialsManager.confluence_credentials(),
        marks=[
            pytest.mark.confluence,
            pytest.mark.project_management,
        ],
        id=f"{CredentialTypes.CONFLUENCE}_server",
    ),
    pytest.param(
        CredentialTypes.CONFLUENCE,
        CredentialsManager.confluence_cloud_credentials(),
        marks=[
            pytest.mark.confluence,
            pytest.mark.confluence_cloud,
            pytest.mark.project_management,
        ],
        id=f"{CredentialTypes.CONFLUENCE}_cloud",
    ),
    pytest.param(
        CredentialTypes.JIRA,
        CredentialsManager.jira_credentials(),
        marks=[
            pytest.mark.jira,
            pytest.mark.project_management,
        ],
        id=f"{CredentialTypes.JIRA}_server",
    ),
    pytest.param(
        CredentialTypes.JIRA,
        CredentialsManager.jira_cloud_credentials(),
        marks=[
            pytest.mark.jira,
            pytest.mark.jira_cloud,
            pytest.mark.project_management,
        ],
        id=f"{CredentialTypes.JIRA}_cloud",
    ),
    pytest.param(
        CredentialTypes.SQL,
        CredentialsManager.sql_credentials(DataBaseDialect.POSTGRES),
        marks=pytest.mark.sql,
        id=DataBaseDialect.POSTGRES,
    ),
    pytest.param(
        CredentialTypes.SQL,
        CredentialsManager.sql_credentials(DataBaseDialect.MY_SQL),
        marks=pytest.mark.sql,
        id=DataBaseDialect.MY_SQL,
    ),
    pytest.param(
        CredentialTypes.ELASTIC,
        CredentialsManager.elasticsearch_credentials(),
        marks=pytest.mark.elastic,
        id=CredentialTypes.ELASTIC,
    ),
    pytest.param(
        CredentialTypes.MCP,
        CredentialsManager.mcp_credentials(),
        marks=pytest.mark.mcp,
        id=CredentialTypes.MCP,
    ),
    pytest.param(
        CredentialTypes.AZURE_DEVOPS,
        CredentialsManager.azure_devops_credentials(),
        marks=pytest.mark.ado,
        id=CredentialTypes.AZURE_DEVOPS,
    ),
    pytest.param(
        CredentialTypes.FILESYSTEM,
        CredentialsManager.file_system_credentials(),
        marks=pytest.mark.file_system,
        id=CredentialTypes.FILESYSTEM,
    ),
    pytest.param(
        CredentialTypes.EMAIL,
        CredentialsManager.gmail_credentials(),
        marks=[
            pytest.mark.notification,
            pytest.mark.email,
        ],
        id=CredentialTypes.EMAIL,
    ),
    pytest.param(
        CredentialTypes.TELEGRAM,
        CredentialsManager.telegram_credentials(),
        marks=[
            pytest.mark.notification,
            pytest.mark.telegram,
        ],
        id=CredentialTypes.TELEGRAM,
    ),
    pytest.param(
        CredentialTypes.SERVICE_NOW,
        CredentialsManager.servicenow_credentials(),
        marks=[
            pytest.mark.servicenow,
        ],
        id=CredentialTypes.SERVICE_NOW,
    ),
    pytest.param(
        CredentialTypes.KEYCLOAK,
        CredentialsManager.keycloak_credentials(),
        marks=pytest.mark.keycloak,
        id=CredentialTypes.KEYCLOAK,
    ),
    pytest.param(
        CredentialTypes.KUBERNETES,
        CredentialsManager.kubernetes_credentials(),
        marks=[
            pytest.mark.kubernetes,
            pytest.mark.cloud,
            pytest.mark.skipif(
                EnvironmentResolver.is_azure(),
                reason="Still have an issue with encoding long strings",
            ),
        ],
        id=CredentialTypes.KUBERNETES,
    ),
    pytest.param(
        CredentialTypes.REPORT_PORTAL,
        CredentialsManager.report_portal_credentials(),
        marks=pytest.mark.report_portal,
        id=CredentialTypes.REPORT_PORTAL,
    ),
]

testable_integrations = [
    pytest.param(
        CredentialTypes.AWS,
        CredentialsManager.aws_credentials(),
        marks=[
            pytest.mark.aws,
            pytest.mark.cloud,
        ],
        id=CredentialTypes.AWS,
    ),
    pytest.param(
        CredentialTypes.AZURE,
        CredentialsManager.azure_credentials(),
        marks=[
            pytest.mark.azure,
            pytest.mark.cloud,
        ],
        id=CredentialTypes.AZURE,
    ),
    pytest.param(
        CredentialTypes.GCP,
        CredentialsManager.gcp_credentials(),
        marks=[
            pytest.mark.gcp,
            pytest.mark.cloud,
            pytest.mark.skipif(
                EnvironmentResolver.is_azure(),
                reason="Still have an issue with encoding long strings",
            ),
        ],
        id=CredentialTypes.GCP,
    ),
    pytest.param(
        CredentialTypes.SONAR,
        CredentialsManager.sonar_credentials(),
        marks=pytest.mark.sonar,
        id=f"{CredentialTypes.SONAR}_server",
    ),
    pytest.param(
        CredentialTypes.SONAR,
        CredentialsManager.sonar_cloud_credentials(),
        marks=pytest.mark.sonar,
        id=f"{CredentialTypes.SONAR}_cloud",
    ),
    pytest.param(
        CredentialTypes.CONFLUENCE,
        CredentialsManager.confluence_credentials(),
        marks=[
            pytest.mark.confluence,
            pytest.mark.project_management,
        ],
        id=f"{CredentialTypes.CONFLUENCE}_server",
    ),
    pytest.param(
        CredentialTypes.CONFLUENCE,
        CredentialsManager.confluence_cloud_credentials(),
        marks=[
            pytest.mark.confluence,
            pytest.mark.confluence_cloud,
            pytest.mark.project_management,
        ],
        id=f"{CredentialTypes.CONFLUENCE}_cloud",
    ),
    pytest.param(
        CredentialTypes.JIRA,
        CredentialsManager.jira_credentials(),
        marks=[
            pytest.mark.jira,
            pytest.mark.project_management,
        ],
        id=f"{CredentialTypes.JIRA}_server",
    ),
    pytest.param(
        CredentialTypes.JIRA,
        CredentialsManager.jira_cloud_credentials(),
        marks=[
            pytest.mark.jira,
            pytest.mark.jira_cloud,
            pytest.mark.project_management,
        ],
        id=f"{CredentialTypes.JIRA}_cloud",
    ),
    pytest.param(
        CredentialTypes.EMAIL,
        CredentialsManager.gmail_credentials(),
        marks=[
            pytest.mark.email,
            pytest.mark.notification,
            pytest.mark.skipif(
                EnvironmentResolver.is_localhost(),
                reason="Skipping this test on local environment",
            ),
            pytest.mark.xfail(reason="EPAM blocks gmail smtp now", strict=False),
        ],
        id=CredentialTypes.EMAIL,
    ),
    pytest.param(
        CredentialTypes.SERVICE_NOW,
        CredentialsManager.servicenow_credentials(),
        marks=[
            pytest.mark.servicenow,
        ],
        id=CredentialTypes.SERVICE_NOW,
    ),
    pytest.param(
        CredentialTypes.KUBERNETES,
        CredentialsManager.kubernetes_credentials(),
        marks=[
            pytest.mark.kubernetes,
            pytest.mark.cloud,
            pytest.mark.skipif(
                EnvironmentResolver.is_azure(),
                reason="Still have an issue with encoding long strings",
            ),
        ],
        id=CredentialTypes.KUBERNETES,
    ),
    pytest.param(
        CredentialTypes.REPORT_PORTAL,
        CredentialsManager.report_portal_credentials(),
        marks=pytest.mark.report_portal,
        id=CredentialTypes.REPORT_PORTAL,
    ),
]

invalid_integrations = [
    pytest.param(
        CredentialTypes.AWS,
        CredentialsManager.invalid_aws_credentials(),
        "An error occurred (SignatureDoesNotMatch) when calling the GetCallerIdentity operation: The request signature we calculated does not match the signature you provided. Check your AWS Secret Access Key and signing method. Consult the service documentation for details.",
        marks=[
            pytest.mark.aws,
            pytest.mark.cloud,
        ],
        id=CredentialTypes.AWS,
    ),
    pytest.param(
        CredentialTypes.AZURE,
        CredentialsManager.invalid_azure_credentials(),
        "Invalid client secret provided. Ensure the secret being sent in the request is the client secret value, not the client secret ID, for a secret added to app",
        marks=[
            pytest.mark.azure,
            pytest.mark.cloud,
        ],
        id=CredentialTypes.AZURE,
    ),
    pytest.param(
        CredentialTypes.GCP,
        CredentialsManager.invalid_gcp_credentials(),
        "Failed to create GCP credentials: Unknown key type: ",
        marks=[
            pytest.mark.gcp,
            pytest.mark.cloud,
            pytest.mark.skipif(
                EnvironmentResolver.is_azure(),
                reason="Still have an issue with encoding long strings",
            ),
        ],
        id=CredentialTypes.GCP,
    ),
    pytest.param(
        CredentialTypes.SONAR,
        CredentialsManager.invalid_sonar_credentials(),
        "Invalid token",
        marks=pytest.mark.sonar,
        id=f"{CredentialTypes.SONAR}_server",
    ),
    pytest.param(
        CredentialTypes.SONAR,
        CredentialsManager.invalid_sonar_cloud_credentials(),
        "Invalid token",
        marks=pytest.mark.sonar,
        id=f"{CredentialTypes.SONAR}_cloud",
    ),
    pytest.param(
        CredentialTypes.EMAIL,
        CredentialsManager.invalid_gmail_credentials(),
        "SMTP Code: 535, Message: 5.7.8 Username and Password not accepted.",
        marks=[
            pytest.mark.email,
            pytest.mark.notification,
            pytest.mark.skipif(
                EnvironmentResolver.is_localhost(),
                reason="Skipping this test on local environment",
            ),
            pytest.mark.xfail(reason="EPAM blocks gmail smtp now", strict=False),
        ],
        id=CredentialTypes.EMAIL,
    ),
    pytest.param(
        CredentialTypes.JIRA,
        CredentialsManager.invalid_jira_credentials(),
        "Access denied",
        marks=pytest.mark.jira,
        id=CredentialTypes.JIRA,
    ),
    pytest.param(
        CredentialTypes.CONFLUENCE,
        CredentialsManager.invalid_confluence_credentials(),
        "Access denied",
        marks=pytest.mark.confluence,
        id=CredentialTypes.CONFLUENCE,
    ),
    pytest.param(
        CredentialTypes.SERVICE_NOW,
        CredentialsManager.invalid_servicenow_credentials(),
        'ServiceNow tool exception. Status: 401. Response: {"error":{"message":"User is not authenticated","detail":"Required to provide Auth information"},"status":"failure"}',
        marks=[
            pytest.mark.servicenow,
        ],
        id=CredentialTypes.SERVICE_NOW,
    ),
    pytest.param(
        CredentialTypes.KUBERNETES,
        CredentialsManager.invalid_kubernetes_credentials(),
        "Kubernetes API call failed: (401)\nReason: Unauthorized",
        marks=[
            pytest.mark.kubernetes,
            pytest.mark.cloud,
        ],
        id=CredentialTypes.KUBERNETES,
    ),
    pytest.param(
        CredentialTypes.REPORT_PORTAL,
        CredentialsManager.invalid_report_portal_credentials(),
        'HTTP 401: {\n  "error_description" : "Invalid access token",\n  "error" : "invalid_token"\n}',
        marks=pytest.mark.report_portal,
        id=CredentialTypes.REPORT_PORTAL,
    ),
]

empty_credentials_integrations = [
    # pytest.param(
    #     [
    #         CredentialValues(key="url", value="https://gitlab.com"),
    #     ],
    #     CredentialTypes.GIT,
    #     Toolkit.VCS,
    #     VcsTool.GITLAB,
    #     f"Using gitlab tool get info about MR №7014 for repo with id '{CredentialsManager.get_parameter('GITLAB_PROJECT_ID')}'",
    #     """
    #         It seems there is an issue with the GitLab configuration, as it hasn't been set up properly for this tool.
    #         This requires setting up authentication and configuration to connect to a GitLab instance.
    #
    #         Could you please check your GitLab tool configuration and provide the necessary access details so that I can assist you further?
    #     """,
    #     marks=[pytest.mark.gitlab],
    #     id=f"{CredentialTypes.GIT}_gitlab_empty",
    # ),
    # pytest.param(
    #     [
    #         CredentialValues(key="url", value="https://github.com"),
    #     ],
    #     CredentialTypes.GIT,
    #     Toolkit.VCS,
    #     VcsTool.GITHUB,
    #     f"Using github tool get info about issue №5 for the repo {CredentialsManager.get_parameter('GITHUB_PROJECT')}.",
    #     """
    #         It seems there is an issue with accessing the GitHub API due to a missing configuration.
    #         Unfortunately, I can't fetch the information directly at the moment.
    #         However, you can access information about an issue using the following steps on your own:
    #
    #         1. Navigate to the Issues tab of the repository [wild47/final_task](https://github.com/wild47/final_task).
    #         2. Look for issue number 5 or directly visit `https://github.com/wild47/final_task/issues/5`,
    #         and it should display all the details regarding that specific issue.
    #
    #         If there's anything else you'd like assistance with, please let me know!
    #     """,
    #     marks=[pytest.mark.github],
    #     id=f"{CredentialTypes.GIT}_github_empty",
    # ),
    # pytest.param(
    #     [
    #         CredentialValues(key="url", value=CredentialsManager.AUTO_GENERATED),
    #     ],
    #     CredentialTypes.EMAIL,
    #     Toolkit.NOTIFICATION,
    #     NotificationTool.EMAIL,
    #     email_tool_prompt(),
    #     """
    #         It looks like there's an issue with the SMTP configuration; it's missing a valid SMTP URL to send the email.
    #         Please ensure that the SMTP settings are properly configured in the system.
    #         If you have access to the SMTP details, such as the server URL, username, and password, you could input them into the system to resolve this issue.
    #     """,
    #     marks=[pytest.mark.email, pytest.mark.notification],
    #     id=f"{CredentialTypes.EMAIL}_empty",
    # ),
    pytest.param(
        [
            CredentialValues(key="url", value=CredentialsManager.AUTO_GENERATED),
        ],
        CredentialTypes.TELEGRAM,
        Toolkit.NOTIFICATION,
        NotificationTool.TELEGRAM,
        TELEGRAM_TOOL_PROMPT,
        """
            It seems I don't have access to the necessary Telegram bot token to send a message.

            You should verify that the bot token is set up correctly or send the message directly through your Telegram bot using your bot's token.

            If you have your bot token and need help with the API request, let me know!
        """,
        marks=[pytest.mark.telegram, pytest.mark.notification],
        id=f"{CredentialTypes.TELEGRAM}_empty",
    ),
    pytest.param(
        [
            CredentialValues(
                key="url", value=CredentialsManager.get_parameter("JIRA_URL")
            )
        ],
        CredentialTypes.JIRA,
        Toolkit.PROJECT_MANAGEMENT,
        ProjectManagementTool.JIRA,
        "Get a title for TEST-1 ticket.",
        """
            It seems that there's an authorization issue when trying to access the JIRA ticket.
            The error indicates that the request is unauthorized.
            You may need to ensure that the correct credentials are being used, or check if you have the necessary permissions to access the ticket.

            If there's anything else you'd like to try or if you have further details, let me know!
        """,
        marks=[pytest.mark.jira, pytest.mark.project_management],
        id=f"{CredentialTypes.JIRA}_empty",
    ),
    pytest.param(
        [],
        CredentialTypes.CONFLUENCE,
        Toolkit.PROJECT_MANAGEMENT,
        ProjectManagementTool.CONFLUENCE,
        CONFLUENCE_TOOL_PROMPT,
        """
            It looks like I don't have the required Confluence URL and credentials set up to perform the requested action.
            If you have access to Confluence, please provide these details or try to access the page directly through your Confluence account.
        """,
        marks=[
            pytest.mark.confluence,
            pytest.mark.project_management,
            pytest.mark.xfail(
                reason="assistant response is an empty string",
                strict=False,
            ),
        ],
        id=f"{CredentialTypes.CONFLUENCE}_empty",
    ),
    pytest.param(
        [
            CredentialValues(key="url", value=""),
        ],
        CredentialTypes.SERVICE_NOW,
        Toolkit.SERVICENOW,
        ServiceNowTool.SERVICE_NOW,
        PROMPT,
        """
            It appears that the ServiceNow configuration is not set, which prevents me from executing the request.
            Please ensure that the ServiceNow configuration, including necessary authentication details,
            is properly set up before using the ServiceNow tool. If you have access to configure these details, please do so and try again.
        """,
        marks=[
            pytest.mark.servicenow,
        ],
        id=f"{CredentialTypes.SERVICE_NOW}_empty",
    ),
    pytest.param(
        [
            CredentialValues(key="url", value=CredentialsManager.AUTO_GENERATED),
        ],
        CredentialTypes.OPENAPI,
        Toolkit.OPEN_API,
        OpenApiTool.GET_OPEN_API_SPEC,
        OPEN_API_SPEC_TOOL_TASK,
        """
            It seems that I don't have access to the OpenAPI specification for the `/v1/assistants` endpoint right now.
            To help you better, could you please provide more details about what you'd like to know regarding this endpoint?
            Are you looking for information on request parameters, expected responses, authentication, or something else?
        """,
        marks=[pytest.mark.openapi],
        id=f"{CredentialTypes.OPENAPI}_empty",
    ),
    pytest.param(
        [
            CredentialValues(key="url", value=CredentialsManager.AUTO_GENERATED),
        ],
        CredentialTypes.AWS,
        Toolkit.CLOUD,
        CloudTool.AWS,
        cloud_test_data[0].values[4],
        """
            It looks like there's an issue with the AWS configuration, which needs to be set up before running AWS service operations.
            Without the proper configuration, I'm unable to access the AWS resources.

            Would you like guidance on how to set up the AWS configuration to list the S3 buckets, or is there anything else I can assist you with?
        """,
        marks=[pytest.mark.aws],
        id=f"{CredentialTypes.AWS}_empty",
    ),
    pytest.param(
        [
            CredentialValues(key="url", value=CredentialsManager.AUTO_GENERATED),
        ],
        CredentialTypes.AZURE,
        Toolkit.CLOUD,
        CloudTool.AZURE,
        cloud_test_data[1].values[4],
        Seeded(
            AZURE_SEED,
            lambda seed: f"""
            It seems there's an issue with the configuration required to access Azure.
            I would need additional details such as your Azure subscription ID to proceed.
            Could you please provide the subscription ID associated with the `{seed.name}` resource group?
        """,
        ),
        marks=[pytest.mark.azure],
        id=f"{CredentialTypes.AZURE}_empty",
    ),
    # pytest.param(
    #     [
    #         CredentialValues(key="url", value=CredentialsManager.AUTO_GENERATED),
    #     ],
    #     CredentialTypes.GCP,
    #     Toolkit.CLOUD,
    #     CloudTool.GCP,
    #     cloud_test_data[2].values[4],
    #     """
    #         It seems that the Google Cloud Platform configuration is not set up,
    #         and I couldn't fetch the information for the bucket with the name `009fb622-4e29-42aa-bafd-584c61f5e1e1`.
    #
    #         If you can provide the necessary Google Cloud Platform authentication credentials,
    #         I can attempt to retrieve this information for you.
    #         Alternatively, you might want to run the request using a setup that has the required GCP configuration and access permissions.
    #     """,
    #     marks=[pytest.mark.gcp],
    #     id=f"{CredentialTypes.GCP}_empty",
    # ),
    # pytest.param(
    #     [],
    #     CredentialTypes.KUBERNETES,
    #     Toolkit.CLOUD,
    #     CloudTool.KUBERNETES,
    #     cloud_test_data[3].values[4],
    #     """
    #         It seems there is an issue with the Kubernetes configuration.
    #         Unfortunately, I can't access the Kubernetes API without proper configuration.
    #         If you can provide the necessary access or configuration, I'll be able to assist you further.
    #         Alternatively, you can try running the following command directly in your environment if you have access to kubectl:
    #
    #         ```bash
    #         kubectl get services -n argocd -o jsonpath='{.items[*].metadata.name}'
    #         ```
    #
    #         This command will list all service names in the `argocd` namespace.
    #     """,
    #     marks=[pytest.mark.kubernetes],
    #     id=f"{CredentialTypes.KUBERNETES}_empty",
    # ),
    pytest.param(
        [],
        CredentialTypes.ELASTIC,
        Toolkit.DATA_MANAGEMENT,
        DataManagementTool.ELASTIC,
        ELASTIC_TOOL_TASK,
        """
            It seems that the Elasticsearch configuration is not set, so I'm unable to send the query at the moment.
            Please ensure that the URL and API key for the Elasticsearch setup are correctly configured so that
            I can execute queries for you.
        """,
        marks=[
            pytest.mark.elastic,
            pytest.mark.skipif(
                EnvironmentResolver.is_localhost(),
                reason="Test cannot be run on localhost",
            ),
        ],
        id=f"{CredentialTypes.ELASTIC}_empty",
    ),
    pytest.param(
        [],
        CredentialTypes.KEYCLOAK,
        Toolkit.ACCESS_MANAGEMENT,
        AccessManagementTool.KEYCLOAK,
        KEYCLOAK_TOOL_PROMPT,
        """
            It seems we need to configure the Keycloak connection by setting the `base_url`, `realm`, `client_id`,
            and `client_secret` before we can retrieve user information. Please provide these details so I can assist you further.
        """,
        marks=[pytest.mark.keycloak],
        id=f"{CredentialTypes.KEYCLOAK}_empty",
    ),
    pytest.param(
        [],
        CredentialTypes.AZURE_DEVOPS,
        Toolkit.AZURE_DEVOPS_TEST_PLAN,
        ado_test_plan_get_test_data[0].values[1],
        ado_test_plan_get_test_data[0].values[2],
        """
            It seems that the configuration for Azure DevOps is not set, including the necessary project or
            authentication token. Please provide the project details and authentication token before
            I can proceed with fetching the test plan details.
        """,
        marks=[pytest.mark.ado],
        id=f"{CredentialTypes.AZURE_DEVOPS}_{ado_test_plan_get_test_data[0].values[1]}_empty",
    ),
    pytest.param(
        [],
        CredentialTypes.AZURE_DEVOPS,
        Toolkit.AZURE_DEVOPS_TEST_PLAN,
        ado_test_plan_get_test_data[1][1],
        ado_test_plan_get_test_data[1][2],
        """
            It seems that the configuration for Azure DevOps is not set, including the necessary project or
            authentication token. Please provide the project details and authentication token before
            I can proceed with fetching the test plan details.
        """,
        marks=[pytest.mark.ado],
        id=f"{CredentialTypes.AZURE_DEVOPS}_{ado_test_plan_get_test_data[1][1]}_empty",
    ),
    pytest.param(
        [],
        CredentialTypes.AZURE_DEVOPS,
        Toolkit.AZURE_DEVOPS_TEST_PLAN,
        ado_test_plan_get_test_data[2][1],
        ado_test_plan_get_test_data[2][2],
        """
            It seems that the configuration for Azure DevOps is not set, including the necessary project or
            authentication token. Please provide the project details and authentication token before
            I can proceed with fetching the test plan details.
        """,
        marks=[pytest.mark.ado],
        id=f"{CredentialTypes.AZURE_DEVOPS}_{ado_test_plan_get_test_data[2][1]}_empty",
    ),
    pytest.param(
        [],
        CredentialTypes.AZURE_DEVOPS,
        Toolkit.AZURE_DEVOPS_TEST_PLAN,
        ado_test_plan_get_test_data[3][1],
        ado_test_plan_get_test_data[3][2],
        """
            It seems that the configuration for Azure DevOps is not set, including the necessary project or
            authentication token. Please provide the project details and authentication token before
            I can proceed with fetching the test plan details.
        """,
        marks=[pytest.mark.ado],
        id=f"{CredentialTypes.AZURE_DEVOPS}_{ado_test_plan_get_test_data[3][1]}_empty",
    ),
    pytest.param(
        [],
        CredentialTypes.AZURE_DEVOPS,
        Toolkit.AZURE_DEVOPS_WIKI,
        ado_wiki_get_test_data[0].values[1],
        ado_wiki_get_test_data[0].values[2],
        """
            It seems there's an issue with accessing the Azure DevOps configuration necessary to retrieve the
            Wiki page content. Please ensure that you have provided the correct project and authentication token
            settings in your Azure DevOps environment to use this functionality.

            If you are unsure about how to set this up, please check your Azure DevOps documentation or contact your
            system administrator for assistance.
        """,
        marks=[pytest.mark.ado],
        id=f"{CredentialTypes.AZURE_DEVOPS}_{ado_wiki_get_test_data[0].values[1]}_empty",
    ),
    pytest.param(
        [],
        CredentialTypes.AZURE_DEVOPS,
        Toolkit.AZURE_DEVOPS_WIKI,
        ado_wiki_get_test_data[1][1],
        ado_wiki_get_test_data[1][2],
        """
            It seems there's an issue with accessing the Azure DevOps configuration necessary to retrieve the
            Wiki page content. Please ensure that you have provided the correct project and authentication token
            settings in your Azure DevOps environment to use this functionality.

            If you are unsure about how to set this up, please check your Azure DevOps documentation or contact your
            system administrator for assistance.
        """,
        marks=[pytest.mark.ado],
        id=f"{CredentialTypes.AZURE_DEVOPS}_{ado_wiki_get_test_data[1][1]}_empty",
    ),
    pytest.param(
        [],
        CredentialTypes.AZURE_DEVOPS,
        Toolkit.AZURE_DEVOPS_WIKI,
        ado_wiki_get_test_data[2][1],
        ado_wiki_get_test_data[2][2],
        """
            It seems there's an issue with accessing the Azure DevOps configuration necessary to retrieve the
            Wiki page content. Please ensure that you have provided the correct project and authentication token
            settings in your Azure DevOps environment to use this functionality.

            If you are unsure about how to set this up, please check your Azure DevOps documentation or contact your
            system administrator for assistance.
        """,
        marks=[pytest.mark.ado],
        id=f"{CredentialTypes.AZURE_DEVOPS}_{ado_wiki_get_test_data[2][1]}_empty",
    ),
    pytest.param(
        [],
        CredentialTypes.AZURE_DEVOPS,
        Toolkit.AZURE_DEVOPS_WORK_ITEM,
        ado_work_item_get_test_data[0].values[1],
        ado_work_item_get_test_data[0].values[2],
        """
            I couldn't retrieve the comments for the work item.
            Please ensure that the necessary configurations such as project and token are set.
        """,
        marks=[pytest.mark.ado],
        id=f"{CredentialTypes.AZURE_DEVOPS}_{ado_work_item_get_test_data[0].values[1]}_empty",
    ),
    pytest.param(
        [],
        CredentialTypes.AZURE_DEVOPS,
        Toolkit.AZURE_DEVOPS_WORK_ITEM,
        ado_work_item_get_test_data[1][1],
        ado_work_item_get_test_data[1][2],
        """
            I couldn't retrieve the comments for the work item.
            Please ensure that the necessary configurations such as project and token are set.
        """,
        marks=[pytest.mark.ado],
        id=f"{CredentialTypes.AZURE_DEVOPS}_{ado_work_item_get_test_data[1][1]}_empty",
    ),
    pytest.param(
        [],
        CredentialTypes.AZURE_DEVOPS,
        Toolkit.AZURE_DEVOPS_WORK_ITEM,
        ado_work_item_get_test_data[2][1],
        ado_work_item_get_test_data[2][2],
        """
            Tool config is not set. Please provide organization url, project, and token before using the tool
        """,
        marks=[pytest.mark.ado],
        id=f"{CredentialTypes.AZURE_DEVOPS}_{ado_work_item_get_test_data[2][1]}_empty",
    ),
    pytest.param(
        [],
        CredentialTypes.AZURE_DEVOPS,
        Toolkit.AZURE_DEVOPS_WORK_ITEM,
        ado_work_item_get_test_data[3][1],
        ado_work_item_get_test_data[3][2],
        """
            Sorry, I couldn't perform the search because the tool configuration is missing the required organization 
            URL, project name, and access token. Please provide these details to enable work item search.
        """,
        marks=[pytest.mark.ado],
        id=f"{CredentialTypes.AZURE_DEVOPS}_{ado_work_item_get_test_data[3][1]}_empty",
    ),
    pytest.param(
        [],
        CredentialTypes.REPORT_PORTAL,
        Toolkit.REPORT_PORTAL,
        rp_test_data[0][1],
        rp_test_data[0][2],
        """
            It seems there is a configuration issue with accessing the launch data, specifically missing configurations
            such as URL, API key, or project settings. Unfortunately, without those configurations,
            I'm unable to retrieve the launch details for you.
            If you have access to these configurations, please provide them to set up the access, or check with
            your system administrator for further assistance.
        """,
        marks=pytest.mark.report_portal,
        id=f"{CredentialTypes.SONAR}_{rp_test_data[0][1]}_empty",
    ),
    pytest.param(
        [],
        CredentialTypes.REPORT_PORTAL,
        Toolkit.REPORT_PORTAL,
        rp_test_data[1][1],
        rp_test_data[1][2],
        """
            It seems that there is a configuration issue with accessing the launch details.
            The necessary configuration (URL, API key, project) is not set for accessing the Report Portal.
            Could you provide the required configuration details, or do you need assistance with setting them up?
        """,
        marks=pytest.mark.report_portal,
        id=f"{CredentialTypes.SONAR}_{rp_test_data[1][1]}_empty",
    ),
    pytest.param(
        [],
        CredentialTypes.REPORT_PORTAL,
        Toolkit.REPORT_PORTAL,
        rp_test_data[2][1],
        rp_test_data[2][2],
        """
            It seems like there is an issue with the configuration for accessing the launch data.
            The required configuration settings such as the URL, API key, and project details are missing.
            To proceed, these need to be set correctly. Could you please check the configuration settings or provide them if possible?
        """,
        marks=pytest.mark.report_portal,
        id=f"{CredentialTypes.SONAR}_{rp_test_data[2][1]}_empty",
    ),
    pytest.param(
        [],
        CredentialTypes.REPORT_PORTAL,
        Toolkit.REPORT_PORTAL,
        rp_test_data[3][1],
        rp_test_data[3][2],
        """
            It seems there is an issue with the configuration required to access the testing data.
            The necessary details such as the URL, API key, and project name are not set for connecting to the
            report portal. Please ensure these configurations are provided before making such requests.
            If these details are set up correctly, I can assist you in fetching the test item data.
        """,
        marks=pytest.mark.report_portal,
        id=f"{CredentialTypes.SONAR}_{rp_test_data[3][1]}_empty",
    ),
    pytest.param(
        [],
        CredentialTypes.REPORT_PORTAL,
        Toolkit.REPORT_PORTAL,
        rp_test_data[4][1],
        rp_test_data[4][2],
        """
            It seems that there is a configuration issue with the report portal connection.
            The system requires a URL, API key, and project to be set up before I can retrieve the test items
            for the specified launch ID. Please ensure that the system has been appropriately configured with these
            details. If you have access to these credentials, you may set them up, or you may need to contact your system administrator for assistance.
        """,
        marks=pytest.mark.report_portal,
        id=f"{CredentialTypes.SONAR}_{rp_test_data[4][1]}_empty",
    ),
    pytest.param(
        [],
        CredentialTypes.REPORT_PORTAL,
        Toolkit.REPORT_PORTAL,
        rp_test_data[5][1],
        rp_test_data[5][2],
        """
            It seems that there is a configuration issue with the Report Portal setup.
            To resolve this, please ensure that the following details are provided:

            1. **URL**: The base URL for the Report Portal instance.
            2. **API Key**: An API key that allows access to the Report Portal API.
            3. **Project**: The project name within Report Portal in which the test item is located.

            Once these configurations are in place, I will be able to retrieve the logs for you.
        """,
        marks=pytest.mark.report_portal,
        id=f"{CredentialTypes.SONAR}_{rp_test_data[5][1]}_empty",
    ),
    pytest.param(
        [],
        CredentialTypes.REPORT_PORTAL,
        Toolkit.REPORT_PORTAL,
        rp_test_data[6][1],
        rp_test_data[6][2],
        """
            It seems there is an issue with the configuration of the report portal settings, such as the URL,
            API key, or project details. To proceed with fetching user information, please ensure that these
            settings are correctly configured. If you have access to these details, you could provide them,
            or you might need to contact an administrator to resolve this issue.
        """,
        marks=pytest.mark.report_portal,
        id=f"{CredentialTypes.SONAR}_{rp_test_data[6][1]}_empty",
    ),
    pytest.param(
        [],
        CredentialTypes.AZURE_DEVOPS,
        Toolkit.VCS,
        VcsTool.AZURE_DEVOPS_GIT,
        ado_text("List branches in <ADO_PROJECT> project"),
        ado_text("""
            It seems I don't have the necessary configuration to access the Azure DevOps Git API. You might want to ensure you've set the required URL, organization, and token for your Azure DevOps account in your environment.
            
            Alternatively, I can guide you on how to retrieve this information directly using Azure DevOps.
            
            To list branches in a repository within the "<ADO_PROJECT>" project, you would typically follow these steps:
            
            1. **Identify the Repository ID**: First, list all repositories in the "<ADO_PROJECT>" project to find the repository you're interested in.
            
                ```bash
                curl -u username:password <ADO_URL>/yourorganization/<ADO_PROJECT>/_apis/git/repositories?api-version=7.1-preview.1
                ```
            
            2. **List Branches**: Once you have the repository ID, list its branches.
            
                ```bash
                curl -u username:password <ADO_URL>/yourorganization/<ADO_PROJECT>/_apis/git/repositories/{repositoryId}/refs?filter=heads/&api-version=7.1-preview.1
                ```
            
            Replace `username`, `password`, `yourorganization`, and `{repositoryId}` with your actual Azure DevOps username, password, organization name, and repository ID, respectively.
            
            If you need further assistance on setting up or troubleshooting, feel free to ask!
        """),
        marks=[pytest.mark.ado],
        id=f"{CredentialTypes.AZURE_DEVOPS}_{VcsTool.AZURE_DEVOPS_GIT}_empty",
    ),
]
