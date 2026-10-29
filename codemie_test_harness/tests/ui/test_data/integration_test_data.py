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
Helper utilities for integration UI tests.
Contains reusable functions and data generators for integration testing.
"""

from dataclasses import dataclass
from typing import Dict, Any

from codemie_sdk.models.integration import CredentialTypes

from codemie_test_harness.tests import PROJECT
from codemie_test_harness.tests.utils.base_utils import get_random_name


@dataclass
class SchedulerTimezoneTestData:
    """Data class for Scheduler integration timezone form fields."""

    alias: str
    schedule: str
    timezone: str
    resource_type: str = "assistant"


@dataclass
class IntegrationTestData:
    """Data class for integration form fields."""

    project: str
    alias: str
    description: str
    credential_type: CredentialTypes
    is_global: bool = False
    fields: Dict[str, Any] = None

    def __post_init__(self):
        if self.fields is None:
            self.fields = {}


class IntegrationTestDataFactory:
    @staticmethod
    def jira_integration() -> IntegrationTestData:
        return IntegrationTestData(
            project=PROJECT,
            alias=f"JIRA Server Integration {get_random_name()}",
            description="JIRA Server integration for project management",
            credential_type=CredentialTypes.JIRA,
            fields={
                "url": "https://jira.company.com",
                "username": "test.user@company.com",
                "token": "secure_password",
            },
        )

    @staticmethod
    def jira_cloud_integration() -> IntegrationTestData:
        return IntegrationTestData(
            project=PROJECT,
            alias=f"JIRA Cloud Integration {get_random_name()}",
            description="JIRA Cloud integration with API token",
            credential_type=CredentialTypes.JIRA,
            fields={
                "url": "https://example.invalid",
                "username": "test.user@company.com",
                "token": "ATATT3xFfGF0...",
                "is_cloud": True,
            },
        )

    @staticmethod
    def git_integration() -> IntegrationTestData:
        return IntegrationTestData(
            project=PROJECT,
            alias=f"GitLab Integration {get_random_name()}",
            description="GitLab integration for code repository access",
            credential_type=CredentialTypes.GIT,
            fields={
                "url": "https://gitlab.company.com",
                "token": "glpat-aaaaaaaaaaaaaaaaaa",
            },
        )

    @staticmethod
    def confluence_integration() -> IntegrationTestData:
        return IntegrationTestData(
            project=PROJECT,
            alias=f"Confluence Integration {get_random_name()}",
            description="Confluence integration for project management",
            credential_type=CredentialTypes.CONFLUENCE,
            fields={
                "url": "https://example.invalid",
                "username": "test.user@company.com",
                "token": "secure_password",
                "is_cloud": False,
            },
        )

    @staticmethod
    def confluence_cloud_integration() -> IntegrationTestData:
        return IntegrationTestData(
            project=PROJECT,
            alias=f"Confluence Cloud Integration {get_random_name()}",
            description="Confluence Cloud integration for project management",
            credential_type=CredentialTypes.CONFLUENCE,
            fields={
                "url": "https://company.atlassian.net",
                "username": "test.user@company.com",
                "token": "ATATT3xFfGF0...",
                "is_cloud": True,
            },
        )

    @staticmethod
    def webhook_integration() -> IntegrationTestData:
        """Plain Webhook integration — no pre-filled webhook_id, gitlab token, or resource.

        Used for structural tests (URL field, accordions, alias sync).
        The empty `fields` dict leaves the form in its reactive default state so that
        alias → webhook_id auto-fill and accordion collapsed-by-default behaviour can
        be asserted without interference from pre-set values.
        """
        return IntegrationTestData(
            project=PROJECT,
            alias=f"Webhook {get_random_name()}",
            description="Plain webhook for structural UI tests",
            credential_type=CredentialTypes.WEBHOOK,
            fields={},
        )

    @staticmethod
    def webhook_gitlab_integration() -> IntegrationTestData:
        return IntegrationTestData(
            project=PROJECT,
            alias=f"GitLab MR Webhook {get_random_name()}",
            description="Webhook integration with a GitLab MR event filter",
            credential_type=CredentialTypes.WEBHOOK,
            fields={
                "webhook_id": get_random_name().replace("_", "-"),
                "gitlab_webhook_token": f"tok_{get_random_name()}",
            },
        )

    @staticmethod
    def scheduler_timezone_integration(
        timezone: str = "Europe/Warsaw",
    ) -> "SchedulerTimezoneTestData":
        """Create test data for a Scheduler integration with timezone.

        Args:
            timezone: IANA timezone name (default: 'Europe/Warsaw')
        """
        return SchedulerTimezoneTestData(
            alias=f"Scheduler TZ {get_random_name()}",
            schedule="0 * * * *",
            timezone=timezone,
        )

    # Expected validation messages
    validation_messages = {
        "invalid_email": "Please enter a valid email address",
        "invalid_url": "Please enter a valid URL",
        "duplicate_name": "An integration with this name already exists",
        "connection_failed": "Connection test failed",
        "connection_timeout": "Connection timeout",
        "cannot_create_setting": "Cannot create specified setting",
        "alias_required": "Alias is required",
    }

    # Success messages
    success_messages = {
        "integration_created": "Integration created successfully",
        "integration_updated": "Integration updated successfully",
        "connection_test_passed": "Connection test passed",
        "integration_deleted": "Integration deleted successfully",
    }
