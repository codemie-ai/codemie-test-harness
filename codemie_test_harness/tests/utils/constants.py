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

from enum import Enum
from pathlib import Path

from codemie_test_harness.tests.enums.tools import VcsTool, NotificationTool


class ProjectManagementIntegrationType(str, Enum):
    JIRA = "jira"
    CONFLUENCE = "confluence"
    JIRA_CLOUD = "jira_cloud"
    CONFLUENCE_CLOUD = "confluence_cloud"


TESTS_PATH = Path(__file__).parent.parent

FILES_PATH = TESTS_PATH / "test_data" / "files"

ID_PATTERN = r'\{\s*"?ID"?\s*:\s*"?(\d+)"?\s*\}'

WORK_ITEM_ID_PATTERN = r"workItems/(\d+)"

vcs_integrations = {
    VcsTool.GITHUB: "github_integration",
    VcsTool.GITLAB: "gitlab_integration",
    VcsTool.AZURE_DEVOPS_GIT: "ado_integration",
}

project_management_integrations = {
    ProjectManagementIntegrationType.JIRA: "jira_integration",
    ProjectManagementIntegrationType.CONFLUENCE: "confluence_integration",
    ProjectManagementIntegrationType.JIRA_CLOUD: "jira_cloud_integration",
    ProjectManagementIntegrationType.CONFLUENCE_CLOUD: "confluence_cloud_integration",
}

notification_integrations = {
    NotificationTool.EMAIL: "email_integration",
    NotificationTool.TELEGRAM: "telegram_integration",
}

test_project_name = "automation-tests-project"
