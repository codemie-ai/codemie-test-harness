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

from codemie_test_harness.tests.enums.tools import ProjectManagementTool
from codemie_test_harness.tests.test_data.pm_tools_test_data import (
    get_confluence_tool_create_prompt,
    get_response_for_confluence_tool_create,
    CONFLUENCE_CLOUD_TOOL_PROMPT,
    RESPONSE_FOR_CONFLUENCE_CLOUD_TOOL,
    CONFLUENCE_TOOL_PROMPT,
    RESPONSE_FOR_CONFLUENCE_TOOL,
    get_jira_tool_create_prompt,
    get_response_for_jira_tool_create,
    JIRA_TOOL_PROMPT,
    RESPONSE_FOR_JIRA_TOOL,
    JIRA_CLOUD_TOOL_PROMPT,
    RESPONSE_FOR_JIRA_CLOUD_TOOL,
)
from codemie_test_harness.tests.utils.constants import ProjectManagementIntegrationType

pm_tools_test_data = [
    pytest.param(
        ProjectManagementTool.JIRA,
        ProjectManagementIntegrationType.JIRA,
        JIRA_TOOL_PROMPT,
        RESPONSE_FOR_JIRA_TOOL,
        marks=[pytest.mark.jira, pytest.mark.smoke],
        id=ProjectManagementIntegrationType.JIRA,
    ),
    pytest.param(
        ProjectManagementTool.CONFLUENCE,
        ProjectManagementIntegrationType.CONFLUENCE,
        CONFLUENCE_TOOL_PROMPT,
        RESPONSE_FOR_CONFLUENCE_TOOL,
        marks=pytest.mark.confluence,
        id=ProjectManagementIntegrationType.CONFLUENCE,
    ),
    pytest.param(
        ProjectManagementTool.JIRA,
        ProjectManagementIntegrationType.JIRA_CLOUD,
        JIRA_CLOUD_TOOL_PROMPT,
        RESPONSE_FOR_JIRA_CLOUD_TOOL,
        marks=[pytest.mark.jira, pytest.mark.jira_cloud],
        id=ProjectManagementIntegrationType.JIRA_CLOUD,
    ),
    pytest.param(
        ProjectManagementTool.CONFLUENCE,
        ProjectManagementIntegrationType.CONFLUENCE_CLOUD,
        CONFLUENCE_CLOUD_TOOL_PROMPT,
        RESPONSE_FOR_CONFLUENCE_CLOUD_TOOL,
        marks=[pytest.mark.confluence, pytest.mark.confluence_cloud, pytest.mark.smoke],
        id=ProjectManagementIntegrationType.CONFLUENCE_CLOUD,
    ),
    pytest.param(
        ProjectManagementTool.JIRA,
        ProjectManagementIntegrationType.JIRA,
        get_jira_tool_create_prompt("server"),
        get_response_for_jira_tool_create("server"),
        marks=[pytest.mark.jira],
        id=f"{ProjectManagementIntegrationType.JIRA.value} - create",
    ),
    pytest.param(
        ProjectManagementTool.JIRA,
        ProjectManagementIntegrationType.JIRA_CLOUD,
        get_jira_tool_create_prompt("cloud"),
        get_response_for_jira_tool_create("cloud"),
        marks=[pytest.mark.jira, pytest.mark.jira_cloud, pytest.mark.smoke],
        id=f"{ProjectManagementIntegrationType.JIRA_CLOUD.value} - create",
    ),
    pytest.param(
        ProjectManagementTool.CONFLUENCE,
        ProjectManagementIntegrationType.CONFLUENCE,
        get_confluence_tool_create_prompt("server"),
        get_response_for_confluence_tool_create("server"),
        marks=[pytest.mark.confluence],
        id=f"{ProjectManagementIntegrationType.CONFLUENCE.value} - create",
    ),
    pytest.param(
        ProjectManagementTool.CONFLUENCE,
        ProjectManagementIntegrationType.CONFLUENCE_CLOUD,
        get_confluence_tool_create_prompt("cloud"),
        get_response_for_confluence_tool_create("cloud"),
        marks=[pytest.mark.confluence, pytest.mark.confluence_cloud, pytest.mark.smoke],
        id=f"{ProjectManagementIntegrationType.CONFLUENCE_CLOUD.value} - create",
    ),
]
