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
Test data for integration update tests covering all 26 integration types.
Each entry contains:
- credential_type: The integration type
- initial_credentials: Fake/unreal credentials used for creating the integration
- updated_credentials: Real credentials from CredentialsManager for updates
- fields_to_validate: Dictionary of field keys and their expected updated values
- toolkit: The toolkit to use for testing the integration
- tool_name: The specific tool to test
- prompt: The prompt to send to the assistant
- expected_response: The expected response pattern
"""

import json
import os

import pytest
from codemie_sdk.models.integration import CredentialTypes, CredentialValues

from codemie_test_harness.tests.enums.integrations import DataBaseDialect
from codemie_test_harness.tests.enums.tools import (
    Toolkit,
    ProjectManagementTool,
    DataManagementTool,
    NotificationTool,
    ServiceNowTool,
    AccessManagementTool,
)
from codemie_test_harness.tests.test_data.ado_work_item_tools_test_data import (
    ado_work_item_get_test_data,
)

# Import existing test data for prompts and expected responses
from codemie_test_harness.tests.test_data.cloud_tools_test_data import cloud_test_data
from codemie_test_harness.tests.test_data.codebase_tools_test_data import (
    sonar_tools_test_data,
)
from codemie_test_harness.tests.test_data.data_management_tools_test_data import (
    ELASTIC_TOOL_TASK,
    RESPONSE_FOR_ELASTIC,
)
from codemie_test_harness.tests.test_data.keycloak_tool_test_data import (
    KEYCLOAK_TOOL_PROMPT,
    KEYCLOAK_TOOL_RESPONSE,
)
from codemie_test_harness.tests.test_data.notification_tools_test_data import (
    email_tool_prompt,
    email_response,
    TELEGRAM_TOOL_PROMPT,
    TELEGRAM_RESPONSE,
)
from codemie_test_harness.tests.test_data.pm_tools_test_data import (
    JIRA_TOOL_PROMPT,
    RESPONSE_FOR_JIRA_TOOL,
    CONFLUENCE_TOOL_PROMPT,
    RESPONSE_FOR_CONFLUENCE_TOOL,
    JIRA_CLOUD_TOOL_PROMPT,
    RESPONSE_FOR_JIRA_CLOUD_TOOL,
    CONFLUENCE_CLOUD_TOOL_PROMPT,
    RESPONSE_FOR_CONFLUENCE_CLOUD_TOOL,
)
from codemie_test_harness.tests.test_data.report_portal_tools_test_data import (
    rp_test_data,
)
from codemie_test_harness.tests.test_data.servicenow_tools_test_data import (
    PROMPT as SERVICENOW_PROMPT,
    EXPECTED_RESPONSE as SERVICENOW_RESPONSE,
)
from codemie_test_harness.tests.test_data.vcs_tools_test_data import vcs_tools_test_data
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver


# Helper function to create fake initial credentials by modifying real credentials
def get_fake_credentials(
    real_credentials: list[CredentialValues],
) -> list[CredentialValues]:
    """
    Create fake initial credentials based on real credentials structure.

    For most fields, generates fake values (e.g., "fake-url", "fake-token").
    For special fields (booleans, complex objects), uses appropriate fake values.

    Returns:
        List of CredentialValues with fake values
    """
    fake_credentials = []

    for cv in real_credentials:
        key = cv.key
        value = cv.value

        # Skip AUTO_GENERATED fields as they need to remain auto-generated
        if value == CredentialsManager.AUTO_GENERATED:
            fake_credentials.append(cv)
            continue

        # Handle different value types
        if isinstance(value, bool):
            # For boolean fields, use the opposite value or False
            fake_value = False
            fake_credentials.append(CredentialValues(key=key, value=fake_value))
        elif isinstance(value, (dict, list)):
            # For complex objects (like openapi_spec), keep them as-is
            # since structure matters
            fake_credentials.append(cv)
        elif isinstance(value, str):
            # For string fields, generate fake values
            if value == "" or value == "":
                # For empty string fields, keep them empty
                fake_credentials.append(CredentialValues(key=key, value=value))
            else:
                # Generate fake value based on field name
                if any(x in key.lower() for x in ["url", "host", "domain", "server"]):
                    fake_value = "https://fake-server.example.com"
                elif any(
                    x in key.lower() for x in ["token", "key", "secret", "password"]
                ):
                    fake_value = "fake-token-12345"
                elif "email" in key.lower():
                    fake_value = "fake@example.com"
                elif "username" in key.lower() or "user" in key.lower():
                    fake_value = "fake-user"
                elif "project" in key.lower():
                    fake_value = "fake-project"
                elif "path" in key.lower() or "directory" in key.lower():
                    fake_value = "/fake/path"
                elif "database" in key.lower() or "db" in key.lower():
                    fake_value = "fake_database"
                elif "auth_type" in key.lower():
                    fake_value = "pat"
                else:
                    fake_value = f"fake-{key.lower()}"

                fake_credentials.append(CredentialValues(key=key, value=fake_value))
        elif isinstance(value, int):
            # For integer fields (like port), use a fake port number
            fake_value = 9999
            fake_credentials.append(CredentialValues(key=key, value=fake_value))
        else:
            # Default: keep as-is
            fake_credentials.append(cv)

    return fake_credentials


# Helper function to extract fields to validate from real credentials
def get_fields_to_validate(
    real_credentials: list[CredentialValues],
) -> dict:
    """
    Extract fields to validate from real credentials.

    Only includes fields that can be validated (non-sensitive, non-complex).
    Sensitive fields will be masked by the API and cannot be validated.

    Returns:
        Dictionary mapping field keys to expected values
    """
    fields_to_validate = {}

    for cv in real_credentials:
        key = cv.key
        value = cv.value

        # Skip AUTO_GENERATED fields
        if value == CredentialsManager.AUTO_GENERATED:
            continue

        # Skip complex objects (dict, list)
        if isinstance(value, (dict, list)):
            continue

        # Include all other fields (sensitive ones will be skipped during validation)
        fields_to_validate[key] = value

    return fields_to_validate


# AWS Integration
aws_real = CredentialsManager.aws_credentials()
aws_initial = get_fake_credentials(aws_real)
aws_updated = aws_real
aws_fields = get_fields_to_validate(aws_real)

# Azure Integration
azure_real = CredentialsManager.azure_credentials()
azure_initial = get_fake_credentials(azure_real)
azure_updated = azure_real
azure_fields = get_fields_to_validate(azure_real)

# GCP Integration
gcp_real = CredentialsManager.gcp_credentials()
gcp_initial = get_fake_credentials(gcp_real)
gcp_updated = gcp_real
gcp_fields = get_fields_to_validate(gcp_real)

# SONAR Server Integration
sonar_real = CredentialsManager.sonar_credentials()
sonar_initial = get_fake_credentials(sonar_real)
sonar_updated = sonar_real
sonar_fields = get_fields_to_validate(sonar_real)

# SONAR Cloud Integration
sonar_cloud_real = CredentialsManager.sonar_cloud_credentials()
sonar_cloud_initial = get_fake_credentials(sonar_cloud_real)
sonar_cloud_updated = sonar_cloud_real
sonar_cloud_fields = get_fields_to_validate(sonar_cloud_real)

# GitLab Integration
gitlab_real = CredentialsManager.gitlab_credentials()
gitlab_initial = get_fake_credentials(gitlab_real)
gitlab_updated = gitlab_real
gitlab_fields = get_fields_to_validate(gitlab_real)

# GitHub Integration
github_real = CredentialsManager.github_credentials()
github_initial = get_fake_credentials(github_real)
github_updated = github_real
github_fields = get_fields_to_validate(github_real)

# Confluence Server Integration
confluence_real = CredentialsManager.confluence_credentials()
confluence_initial = get_fake_credentials(confluence_real)
confluence_updated = confluence_real
confluence_fields = get_fields_to_validate(confluence_real)

# Confluence Cloud Integration
confluence_cloud_real = CredentialsManager.confluence_cloud_credentials()
confluence_cloud_initial = get_fake_credentials(confluence_cloud_real)
confluence_cloud_updated = confluence_cloud_real
confluence_cloud_fields = get_fields_to_validate(confluence_cloud_real)

# JIRA Server Integration
jira_real = CredentialsManager.jira_credentials()
jira_initial = get_fake_credentials(jira_real)
jira_updated = jira_real
jira_fields = get_fields_to_validate(jira_real)

# JIRA Cloud Integration
jira_cloud_real = CredentialsManager.jira_cloud_credentials()
jira_cloud_initial = get_fake_credentials(jira_cloud_real)
jira_cloud_updated = jira_cloud_real
jira_cloud_fields = get_fields_to_validate(jira_cloud_real)

# SQL - PostgresSQL Integration
postgres_real = CredentialsManager.sql_credentials(DataBaseDialect.POSTGRES)
postgres_initial = get_fake_credentials(postgres_real)
postgres_updated = postgres_real
postgres_fields = get_fields_to_validate(postgres_real)

# SQL - MySQL Integration
mysql_real = CredentialsManager.sql_credentials(DataBaseDialect.MY_SQL)
mysql_initial = get_fake_credentials(mysql_real)
mysql_updated = mysql_real
mysql_fields = get_fields_to_validate(mysql_real)

# Elasticsearch Integration
elastic_real = CredentialsManager.elasticsearch_credentials()
elastic_initial = get_fake_credentials(elastic_real)
elastic_updated = elastic_real
elastic_fields = get_fields_to_validate(elastic_real)

# Azure DevOps Integration
ado_real = CredentialsManager.azure_devops_credentials()
ado_initial = get_fake_credentials(ado_real)
ado_updated = ado_real
ado_fields = get_fields_to_validate(ado_real)

# FileSystem Integration
filesystem_real = CredentialsManager.file_system_credentials()
filesystem_initial = get_fake_credentials(filesystem_real)
filesystem_updated = filesystem_real
filesystem_fields = get_fields_to_validate(filesystem_real)

# Email (Gmail) Integration
email_real = CredentialsManager.gmail_credentials()
email_initial = get_fake_credentials(email_real)
email_updated = email_real
email_fields = get_fields_to_validate(email_real)

# Telegram Integration
telegram_real = CredentialsManager.telegram_credentials()
telegram_initial = get_fake_credentials(telegram_real)
telegram_updated = telegram_real
telegram_fields = get_fields_to_validate(telegram_real)

# ServiceNow Integration
servicenow_real = CredentialsManager.servicenow_credentials()
servicenow_initial = get_fake_credentials(servicenow_real)
servicenow_updated = servicenow_real
servicenow_fields = get_fields_to_validate(servicenow_real)

# Keycloak Integration
keycloak_real = CredentialsManager.keycloak_credentials()
keycloak_initial = get_fake_credentials(keycloak_real)
keycloak_updated = keycloak_real
keycloak_fields = get_fields_to_validate(keycloak_real)

# Kubernetes Integration
kubernetes_real = CredentialsManager.kubernetes_credentials()
kubernetes_initial = get_fake_credentials(kubernetes_real)
kubernetes_updated = kubernetes_real
kubernetes_fields = get_fields_to_validate(kubernetes_real)

# Report Portal Integration
report_portal_real = CredentialsManager.report_portal_credentials()
report_portal_initial = get_fake_credentials(report_portal_real)
report_portal_updated = report_portal_real
report_portal_fields = get_fields_to_validate(report_portal_real)

# LiteLLM Integration
lite_llm_real = CredentialsManager.lite_llm_credentials()
lite_llm_initial = get_fake_credentials(lite_llm_real)
lite_llm_updated = lite_llm_real
lite_llm_fields = get_fields_to_validate(lite_llm_real)

# OpenAPI Integration
# OpenAPI requires special handling due to openapi_spec field
openapi_path = os.path.join(os.path.dirname(__file__), "openapi.json")
with open(openapi_path, "r") as openapi_json_file:
    openapi_spec = json.load(openapi_json_file)

openapi_real = [
    CredentialValues(key="url", value=CredentialsManager.AUTO_GENERATED),
    CredentialValues(key="openapi_api_key", value="Bearer real-token-abc123"),
    CredentialValues(key="openapi_spec", value=openapi_spec),
]
openapi_initial = [
    CredentialValues(key="url", value=CredentialsManager.AUTO_GENERATED),
    CredentialValues(key="openapi_api_key", value="Bearer fake-token-12345"),
    CredentialValues(key="openapi_spec", value=openapi_spec),
]
openapi_updated = openapi_real
openapi_fields = {"openapi_api_key": "Bearer real-token-abc123"}


# Build the parameterized test data
# Parameters: credential_type, initial_credentials, updated_credentials, fields_to_validate,
#             toolkit, tool_name, prompt, expected_response
integration_update_data = [
    pytest.param(
        CredentialTypes.AWS,
        aws_initial,
        aws_updated,
        aws_fields,
        cloud_test_data[0].values[0],  # Toolkit.CLOUD
        cloud_test_data[0].values[1],  # CloudTool.AWS
        cloud_test_data[0].values[4],  # Prompt
        cloud_test_data[0].values[5],  # Expected response
        marks=[pytest.mark.aws, pytest.mark.cloud],
        id=CredentialTypes.AWS,
    ),
    pytest.param(
        CredentialTypes.AZURE,
        azure_initial,
        azure_updated,
        azure_fields,
        cloud_test_data[1].values[0],  # Toolkit.CLOUD
        cloud_test_data[1].values[1],  # CloudTool.AZURE
        cloud_test_data[1].values[4],  # Prompt
        cloud_test_data[1].values[5],  # Expected response
        marks=[pytest.mark.azure, pytest.mark.cloud],
        id=CredentialTypes.AZURE,
    ),
    pytest.param(
        CredentialTypes.GCP,
        gcp_initial,
        gcp_updated,
        gcp_fields,
        cloud_test_data[2].values[0],  # Toolkit.CLOUD
        cloud_test_data[2].values[1],  # CloudTool.GCP
        cloud_test_data[2].values[4],  # Prompt
        cloud_test_data[2].values[5],  # Expected response
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
        sonar_initial,
        sonar_updated,
        sonar_fields,
        sonar_tools_test_data[0].values[0],  # Toolkit.CODEBASE_TOOLS
        sonar_tools_test_data[0].values[1],  # CodeBaseTool.SONAR
        sonar_tools_test_data[0].values[3],  # Prompt
        sonar_tools_test_data[0].values[4],  # Expected response
        marks=pytest.mark.sonar,
        id=f"{CredentialTypes.SONAR.value}_server",
    ),
    pytest.param(
        CredentialTypes.SONAR,
        sonar_cloud_initial,
        sonar_cloud_updated,
        sonar_cloud_fields,
        sonar_tools_test_data[1].values[0],  # Toolkit.CODEBASE_TOOLS
        sonar_tools_test_data[0].values[1],  # CodeBaseTool.SONAR
        sonar_tools_test_data[1].values[3],  # Prompt
        sonar_tools_test_data[1].values[4],  # Expected response
        marks=pytest.mark.sonar,
        id=f"{CredentialTypes.SONAR.value}_cloud",
    ),
    pytest.param(
        CredentialTypes.GIT,
        gitlab_initial,
        gitlab_updated,
        gitlab_fields,
        Toolkit.VCS,  # vcs_tools_test_data doesn't have toolkit in params
        vcs_tools_test_data[1].values[0],  # VcsTool.GITLAB
        vcs_tools_test_data[1].values[1],  # Prompt
        vcs_tools_test_data[1].values[2],  # Expected response
        marks=pytest.mark.gitlab,
        id=f"{CredentialTypes.GIT}_gitlab",
    ),
    pytest.param(
        CredentialTypes.GIT,
        github_initial,
        github_updated,
        github_fields,
        Toolkit.VCS,  # vcs_tools_test_data doesn't have toolkit in params
        vcs_tools_test_data[0].values[0],  # VcsTool.GITHUB
        vcs_tools_test_data[0].values[1],  # Prompt
        vcs_tools_test_data[0].values[2],  # Expected response
        marks=pytest.mark.github,
        id=f"{CredentialTypes.GIT}_github",
    ),
    pytest.param(
        CredentialTypes.CONFLUENCE,
        confluence_initial,
        confluence_updated,
        confluence_fields,
        Toolkit.PROJECT_MANAGEMENT,
        ProjectManagementTool.CONFLUENCE,
        CONFLUENCE_TOOL_PROMPT,
        RESPONSE_FOR_CONFLUENCE_TOOL,
        marks=[pytest.mark.confluence, pytest.mark.project_management],
        id=f"{CredentialTypes.CONFLUENCE.value}_server",
    ),
    pytest.param(
        CredentialTypes.CONFLUENCE,
        confluence_cloud_initial,
        confluence_cloud_updated,
        confluence_cloud_fields,
        Toolkit.PROJECT_MANAGEMENT,
        ProjectManagementTool.CONFLUENCE,
        CONFLUENCE_CLOUD_TOOL_PROMPT,
        RESPONSE_FOR_CONFLUENCE_CLOUD_TOOL,
        marks=[
            pytest.mark.confluence,
            pytest.mark.confluence_cloud,
            pytest.mark.project_management,
        ],
        id=f"{CredentialTypes.CONFLUENCE.value}_cloud",
    ),
    pytest.param(
        CredentialTypes.JIRA,
        jira_initial,
        jira_updated,
        jira_fields,
        Toolkit.PROJECT_MANAGEMENT,
        ProjectManagementTool.JIRA,
        JIRA_TOOL_PROMPT,
        RESPONSE_FOR_JIRA_TOOL,
        marks=[pytest.mark.jira, pytest.mark.project_management],
        id=f"{CredentialTypes.JIRA.value}_server",
    ),
    pytest.param(
        CredentialTypes.JIRA,
        jira_cloud_initial,
        jira_cloud_updated,
        jira_cloud_fields,
        Toolkit.PROJECT_MANAGEMENT,
        ProjectManagementTool.JIRA,
        JIRA_CLOUD_TOOL_PROMPT,
        RESPONSE_FOR_JIRA_CLOUD_TOOL,
        marks=[
            pytest.mark.jira,
            pytest.mark.jira_cloud,
            pytest.mark.project_management,
        ],
        id=f"{CredentialTypes.JIRA.value}_cloud",
    ),
    pytest.param(
        CredentialTypes.SQL,
        postgres_initial,
        postgres_updated,
        postgres_fields,
        Toolkit.DATA_MANAGEMENT,
        DataManagementTool.SQL,
        "Show the DB version",
        "The database version is PostgreSQL 17.5",
        marks=[
            pytest.mark.sql,
            pytest.mark.skipif(
                EnvironmentResolver.is_localhost(),
                reason="Skipping this tests on local environment",
            ),
        ],
        id=DataBaseDialect.POSTGRES,
    ),
    pytest.param(
        CredentialTypes.SQL,
        mysql_initial,
        mysql_updated,
        mysql_fields,
        Toolkit.DATA_MANAGEMENT,
        DataManagementTool.SQL,
        "Show the DB version",
        "The database version is 8.4.3",
        marks=[
            pytest.mark.sql,
            pytest.mark.skipif(
                EnvironmentResolver.is_localhost(),
                reason="Skipping this tests on local environment",
            ),
        ],
        id=DataBaseDialect.MY_SQL,
    ),
    pytest.param(
        CredentialTypes.ELASTIC,
        elastic_initial,
        elastic_updated,
        elastic_fields,
        Toolkit.DATA_MANAGEMENT,
        DataManagementTool.ELASTIC,
        ELASTIC_TOOL_TASK,
        RESPONSE_FOR_ELASTIC,
        marks=[
            pytest.mark.elastic,
            pytest.mark.skipif(
                EnvironmentResolver.is_localhost(),
                reason="Skipping this tests on local environment",
            ),
        ],
        id=CredentialTypes.ELASTIC,
    ),
    pytest.param(
        CredentialTypes.AZURE_DEVOPS,
        ado_initial,
        ado_updated,
        ado_fields,
        ado_work_item_get_test_data[0].values[0],  # Toolkit.AZURE_DEVOPS_WORK_ITEM
        ado_work_item_get_test_data[0].values[
            1
        ],  # AzureDevOpsWorkItemTool.GET_WORK_ITEM
        ado_work_item_get_test_data[0].values[2],  # Prompt
        ado_work_item_get_test_data[0].values[3],  # Expected response
        marks=pytest.mark.ado,
        id=CredentialTypes.AZURE_DEVOPS,
    ),
    pytest.param(
        CredentialTypes.EMAIL,
        email_initial,
        email_updated,
        email_fields,
        Toolkit.NOTIFICATION,
        NotificationTool.EMAIL,
        email_tool_prompt(),
        email_response(CredentialsManager.get_parameter("GMAIL_USER_EMAIL")),
        marks=[
            pytest.mark.notification,
            pytest.mark.email,
            pytest.mark.skipif(
                EnvironmentResolver.is_localhost(),
                reason="Skipping this tests on local environment",
            ),
            pytest.mark.xfail(reason="EPAM blocks gmail smtp now", strict=False),
        ],
        id=CredentialTypes.EMAIL,
    ),
    pytest.param(
        CredentialTypes.TELEGRAM,
        telegram_initial,
        telegram_updated,
        telegram_fields,
        Toolkit.NOTIFICATION,
        NotificationTool.TELEGRAM,
        TELEGRAM_TOOL_PROMPT,
        TELEGRAM_RESPONSE,
        marks=[pytest.mark.notification, pytest.mark.telegram],
        id=CredentialTypes.TELEGRAM,
    ),
    pytest.param(
        CredentialTypes.SERVICE_NOW,
        servicenow_initial,
        servicenow_updated,
        servicenow_fields,
        Toolkit.SERVICENOW,
        ServiceNowTool.SERVICE_NOW,
        SERVICENOW_PROMPT,
        SERVICENOW_RESPONSE,
        marks=[
            pytest.mark.servicenow,
        ],
        id=CredentialTypes.SERVICE_NOW,
    ),
    pytest.param(
        CredentialTypes.KEYCLOAK,
        keycloak_initial,
        keycloak_updated,
        keycloak_fields,
        Toolkit.ACCESS_MANAGEMENT,
        AccessManagementTool.KEYCLOAK,
        KEYCLOAK_TOOL_PROMPT,
        KEYCLOAK_TOOL_RESPONSE,
        marks=pytest.mark.keycloak,
        id=CredentialTypes.KEYCLOAK,
    ),
    pytest.param(
        CredentialTypes.KUBERNETES,
        kubernetes_initial,
        kubernetes_updated,
        kubernetes_fields,
        cloud_test_data[3].values[0],  # Toolkit.CLOUD
        cloud_test_data[3].values[1],  # CloudTool.KUBERNETES
        cloud_test_data[3].values[4],  # Prompt
        cloud_test_data[3].values[5],  # Expected response
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
        report_portal_initial,
        report_portal_updated,
        report_portal_fields,
        rp_test_data[2][0],  # Toolkit.REPORT_PORTAL
        rp_test_data[2][1],  # ReportPortalTool.GET_ALL_LAUNCHES
        rp_test_data[2][2],  # Prompt
        rp_test_data[2][3],  # Expected response
        marks=pytest.mark.report_portal,
        id=CredentialTypes.REPORT_PORTAL,
    ),
    pytest.param(
        CredentialTypes.LITE_LLM,
        lite_llm_initial,
        lite_llm_updated,
        lite_llm_fields,
        None,  # LiteLLM doesn't have direct assistant tools
        None,
        None,
        None,
        marks=[
            pytest.mark.lite_llm,
            pytest.mark.enterprise,
            pytest.mark.skipif(
                EnvironmentResolver.is_localhost(),
                reason="Skipping this tests on local environment",
            ),
        ],
        id=CredentialTypes.LITE_LLM,
    ),
]
