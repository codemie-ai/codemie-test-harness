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
Test Data for Assistant UI Tests

This module provides test data generation and management for assistant-related UI tests.
Following best practices by separating test data from test logic and providing
reusable data factories for consistent testing.
"""

from dataclasses import dataclass
from typing import Optional, List
from enum import Enum

import pytest

from codemie_test_harness.tests.utils.base_utils import get_random_name


@dataclass
class AssistantTestData:
    """
    Data class for assistant test data.

    This class encapsulates all the data needed for assistant creation tests,
    providing a clean and type-safe way to manage test data.
    """

    name: str
    description: str
    system_prompt: str
    icon_url: Optional[str] = None
    shared: bool = False


@dataclass
class AssistantMCPConfigTestData:
    """
    Data class for assistant MCP config test data.

    This class encapsulates all the data needed for assistant creation tests,
    providing a clean and type-safe way to manage test data.
    """

    name: str
    description: str
    configuration: str
    token_size_limit: Optional[str] = None
    configuration_type: Optional[bool] = False
    env_var: Optional[str] = None
    mcp_url: Optional[str] = None


class AssistantTestDataFactory:
    """
    Factory class for generating assistant test data.

    This factory provides various methods to create different types of
    assistant test data for different testing scenarios.
    """

    @staticmethod
    def create_minimal_assistant_data() -> AssistantTestData:
        """
        Create minimal assistant data with only required fields.

        This represents the most basic assistant creation scenario
        with minimal required information.

        Returns:
            AssistantTestData: Minimal assistant test data
        """
        return AssistantTestData(
            name=f"QA Test Assistant {get_random_name()}",
            description="Minimal test assistant for QA automation.",
            system_prompt=(
                "You are a test assistant created for QA validation purposes. "
                "Provide helpful and accurate responses to user queries."
            ),
            shared=False,
            icon_url=ICON_URL,
        )

    @staticmethod
    def create_shared_assistant_data() -> AssistantTestData:
        """
        Create shared assistant data for public/shared testing scenarios.

        Returns:
            AssistantTestData: Shared assistant test data
        """
        return AssistantTestData(
            name=f"QA Shared Assistant {get_random_name()}",
            description="Shared QA assistant available to all team members",
            system_prompt=(
                "You are a shared QA assistant available to the entire team. "
                "Provide collaborative testing support, knowledge sharing, and "
                "help maintain consistent quality standards across projects."
            ),
            icon_url=ICON_URL,
            shared=True,
        )

    @staticmethod
    def create_validation_test_data() -> List[AssistantTestData]:
        """
        Create a list of assistant data for validation testing scenarios.

        This includes data for testing various validation scenarios,
        edge cases in form validation, and error handling.

        Returns:
            List[AssistantTestData]: List of validation test data
        """
        return [
            # Empty name scenario
            AssistantTestData(
                name="",
                description="Test description",
                system_prompt="Test prompt",
            ),
            # Long name scenario
            AssistantTestData(
                name="A" * 100,  # Very long name
                description="Test description for long name validation",
                system_prompt="Test prompt for long name scenario",
            ),
            # Empty description scenario
            AssistantTestData(
                name="Test Assistant",
                description="",
                system_prompt="Test prompt",
            ),
            # Empty system prompt scenario
            AssistantTestData(
                name="Test Assistant",
                description="Test description",
                system_prompt="",
            ),
        ]

    @staticmethod
    def create_marketplace_assistant_data() -> AssistantTestData:
        """
        Create marketplace assistant data for testing scenarios.

        Returns:
            AssistantTestData: Marketplace assistant test data
        """
        return AssistantTestData(
            name=f"QA Marketplace Assistant {get_random_name()}",
            description="A lightweight assistant intended for marketplace testing and validation."
            "It supports basic conversational flows, simple task handling, and prompt-following"
            "checks to help evaluate listing quality and assistant behavior in a marketplace environment.",
            system_prompt=(
                """
                    ## Instructions
                    You are a general-purpose assistant intended for marketplace testing. Help users validate basic assistant behaviors such 
                    as instruction-following, clarity, concision, and safe, professional responses.
                
                    ## Steps to Follow
                    1. Identify the user’s testing goal (e.g., conversational flow, response quality, adherence to instructions).
                    2. Provide a direct response that demonstrates clear structure and correct interpretation.
                    3. When asked to “test” or “simulate,” generate short, repeatable test cases (checklists, sample prompts, expected behaviors).
                    4. Keep outputs minimal, readable, and consistent.
                
                    ## Constraints
                    - Use only information provided by the user; do not invent user-specific details.
                    - Avoid unnecessary verbosity and filler.
                    - If a request is ambiguous, choose a reasonable interpretation and proceed without asking follow-ups.
                
                    ## Examples / Use Cases
                    - Create a short QA checklist for evaluating assistant responses.
                    - Simulate a 3–5 turn conversation to test tone and compliance.
                    - Generate sample prompts for marketplace evaluation.
                """
            ),
            icon_url=ICON_URL,
            shared=False,
        )


@dataclass
class SubAssistantMarketplaceTestData:
    """
    Data class for the Publish to Marketplace modal sub-assistants scenario.

    Describes a parent assistant that has one sub-assistant already published
    to Marketplace and one sub-assistant that is still private.
    """

    parent_name: str
    published_sub_assistant_name: str
    unpublished_sub_assistant_name: str


class AssistantMCPTestDataFactory:
    """
    Factory class for generating assistant test data for creating new MCP server..

    This factory provides various methods to create different types of
    assistant test data for different testing scenarios.
    """

    @staticmethod
    def create_minimal_assistant_mcp_data() -> AssistantMCPConfigTestData:
        """
        Create minimal assistant data with only required fields.

        This represents the most basic assistant creation scenario
        with minimal required information.

        Returns:
            AssistantMCPTestDataFactory: Minimal assistant mcp config test data
        """
        return AssistantMCPConfigTestData(
            name="MCP Test",
            description="MCP for test purposes",
            configuration='{"command": "test"}',
        )


class AssistantValidationErrors(Enum):
    """
    Validation rules and constraints for assistant data.

    This class defines the validation rules that should be applied
    to assistant data during testing.
    """

    NAME_REQUIRED = "Name is required"
    ICON_URL_NOT_VALID = "Please enter a valid URL"
    DESCRIPTION_REQUIRED = "Description is required"
    SYSTEM_PROMPT_REQUIRED = "System instructions are required"
    TEMPERATURE_NOT_VALID = "Temperature must be between 0 and 2"
    TEMPERATURE_CLAUDE_NOT_VALID = (
        "Temperature must be between 0 and 1 for Claude models"
    )
    TOP_P_NOT_VALID = "Top P must be at most 1"


class AssistantPopUpMessages(Enum):
    """
    Enumerates expected popup notification and toast messages for assistant actions in UI tests.

    This enum class should include all standardized popup/toast messages
    that are expected to appear as a result of user workflow, such as
    success/error messages after saving or updating an assistant,
    deletion confirmations, or integration test results.

    Using this enum in UI tests ensures message checks are maintainable,
    consistent, and robust against typo errors or message changes.
    """

    ASSISTANT_UPDATED_SUCCESS = "Assistant has been updated successfully!"
    ASSISTANT_CREATED_SUCCESS = "Assistant has been created successfully!"
    ASSISTANT_DELETED_SUCCESS = "Assistant has been deleted successfully!"


# ==================== CONVENIENCE FUNCTIONS ====================


def get_minimal_assistant_data() -> AssistantTestData:
    """Convenience function to get minimal assistant data."""
    return AssistantTestDataFactory.create_minimal_assistant_data()


def get_shared_assistant_data() -> AssistantTestData:
    """Convenience function to get shared assistant data."""
    return AssistantTestDataFactory.create_shared_assistant_data()


def get_validation_test_data() -> List[AssistantTestData]:
    """Convenience function to get validation test data."""
    return AssistantTestDataFactory.create_validation_test_data()


def get_minimal_assistant_mcp_config_data() -> AssistantMCPConfigTestData:
    """Convenience function to get minimal assistant mcp config test data."""
    return AssistantMCPTestDataFactory.create_minimal_assistant_mcp_data()


def get_marketplace_assistant_data() -> AssistantTestData:
    """Convenience function to get marketplace assistant data with categories."""
    return AssistantTestDataFactory.create_marketplace_assistant_data()


def get_sub_assistant_marketplace_data() -> SubAssistantMarketplaceTestData:
    """Convenience function to get parent/published/unpublished sub-assistant names."""
    return SubAssistantMarketplaceTestData(
        parent_name=get_random_name(),
        published_sub_assistant_name=get_random_name(),
        unpublished_sub_assistant_name=get_random_name(),
    )


# ==================== TEST DATA CONSTANTS ====================

# Common test values for reuse
COMMON_TEST_PROMPTS = {
    "qa_assistant": (
        "You are a QA testing assistant. Your primary role is to help with "
        "quality assurance tasks, test automation, and ensuring software quality. "
        "Provide detailed and actionable guidance."
    ),
    "general_assistant": (
        "You are a helpful assistant. Provide clear, accurate, and helpful "
        "responses to user queries. Always be polite and professional."
    ),
    "specialist_assistant": (
        "You are a specialist assistant with deep expertise in your domain. "
        "Provide expert-level guidance and detailed technical solutions."
    ),
}

COMMON_TEST_DESCRIPTIONS = {
    "qa_assistant": "QA testing assistant for automation and quality assurance tasks",
    "general_assistant": "General purpose assistant for various tasks and queries",
    "specialist_assistant": "Specialist assistant with domain-specific expertise",
}

COMMON_ICON_URLS = {
    "qa_icon": "https://example.com/qa-assistant-icon.png",
    "general_icon": "https://example.com/general-assistant-icon.png",
    "specialist_icon": "https://example.com/specialist-assistant-icon.png",
}

ICON_URL = "https://raw.githubusercontent.com/epam-gen-ai-run/ai-run-install/main/docs/assets/ai/AQAUiTestGenerator.png"


# ==================== ASSISTANT TOOLS CONSTANTS ====================
class Section(Enum):
    AVAILABLE_TOOLS = "Available Tools"
    EXTERNAL_TOOLS = "External Tools"
    MCP_SERVERS = "MCP Servers"


class Toolkit(Enum):
    GIT = "Git"
    VCS = "VCS"
    CODEBASE_TOOLS = "Codebase Tools"
    RESEARCH = "Research"
    CLOUD = "Cloud"
    AZURE_DEVOPS_WIKI = "Azure DevOps Wiki"
    AZURE_DEVOPS_WORK_ITEM = "Azure DevOps Work Item"
    AZURE_DEVOPS_TEST_PLAN = "Azure DevOps Test Plan"
    ACCESS_MANAGEMENT = "Access Management"
    PROJECT_MANAGEMENT = "Project Management"
    OPEN_API = "OpenAPI"
    NOTIFICATION = "Notification"
    DATA_MANAGEMENT = "Data Management"
    FILESYSTEM = "FileSystem"
    QUALITY_ASSURANCE = "Quality Assurance"
    REPORT_PORTAL = "Report Portal"
    IT_SERVICE_MANAGEMENT = "IT Service Management"
    PLATFORM_TOOLS = "Platform Tools"


class GitTool(Enum):
    CREATE_BRANCH = "Create Branch"
    SET_ACTIVE_BRANCH = "Set Active Branch"
    LIST_BRANCHES_IN_REPO = "List Branches In Repo"
    CREATE_FILE = "Create File"
    UPDATE_FILE = "Update File"
    UPDATE_FILE_DIFF = "Update File Diff"
    DELETE_FILE = "Delete File"
    CREATE_PULL_REQUEST = "Create Pull/Merge request"
    GET_PR_CHANGES = "Get Pull/Merge Request Changes"
    CREATE_PR_CHANGE_COMMENT = "Create Pull/Merge Request Change Comment"


class VcsTool(Enum):
    GITHUB = "Github"
    GITLAB = "Gitlab"
    AZURE_GIT = "Azure DevOps Git"


class CodebaseTool(Enum):
    GET_REPOSITORY_FILE_TREE_V2 = "Get Repo Tree with filtering (Experimental)"
    SEARCH_CODE_REPO_V2 = "Search Code with filtering (Experimental)"
    READ_FILES_CONTENT = "Read Files Content"
    READ_FILES_CONTENT_SUMMARY = "Read Files Content With Summary For Large"
    SEARCH_CODE_REPO_BY_PATH = "Search Code Repo By Path"
    SONAR = "Sonar"


class ResearchTool(Enum):
    GOOGLE_SEARCH = "Google Search"
    GOOGLE_PLACES = "Google Places"
    GOOGLE_PLACES_FIND_NEAR = "Google Places Find Near"
    WIKIPEDIA = "Wikipedia"
    TAVILY_SEARCH = "Tavily Search"
    WEB_SCRAPPER = "Web Scraper"


class CloudTool(Enum):
    KUBERNETES = "Kubernetes"
    AWS = "AWS"
    GCP = "GCP"
    AZURE = "Azure"


class AzureDevOpsWikiTool(Enum):
    GET_WIKI = "Get Wiki"
    GET_WIKI_PAGE_BY_PATH = "Get Wiki Page By Path"
    GET_WIKI_PAGE_BY_ID = "Get Wiki Page By ID"
    DELETE_PAGE_BY_PATH = "Delete Wiki Page By Path"
    CREATE_WIKI_PAGE = "Create Wiki Page"
    DELETE_PAGE_BY_ID = "Delete Wiki Page By ID"
    MODIFY_WIKI_PAGE = "Modify Wiki Page"
    RENAME_WIKI_PAGE = "Rename Wiki Page"


class AzureDevOpsWorkItemTool(Enum):
    SEARCH_WORK_ITEMS = "Search Work Items"
    CREATE_WORK_ITEM = "Create Work Item"
    UPDATE_WORK_ITEM = "Update Work Item"
    GET_WORK_ITEM = "Get Work Item"
    LINK_WORK_ITEMS = "Link Work Items"
    GET_RELATION_TYPES = "Get Relation Types"
    GET_COMMENTS = "Get Comments"


class AzureDevOpsTestPlanTool(Enum):
    CREATE_TEST_PLAN = "Create Test Plan"
    DELETE_TEST_PLAN = "Delete Test Plan"
    GET_TEST_PLAN = "Get Test Plan"
    CREATE_TEST_SUITE = "Create Test Suite"
    DELETE_TEST_SUITE = "Delete Test Suite"
    GET_TEST_SUITE = "Get Test Suite"
    ADD_TEST_CASE = "Add Test Case"
    GET_TEST_CASE = "Get Test Case"
    GET_TEST_CASES = "Get Test Cases"


class AccessManagementTool(Enum):
    KEYCLOAK = "Keycloak"


class ProjectManagementTool(Enum):
    GENERIC_JIRA = "Generic Jira"
    GENERIC_CONFLUENCE = "Generic Confluence"


class OpenAPITool(Enum):
    INVOKE_EXTERNAL_API = "Invoke external API"
    GET_OPEN_API_SPEC = "Get Open API spec"


class NotificationTool(Enum):
    EMAIL = "Email"
    TELEGRAM = "Telegram"


class DataManagementTool(Enum):
    ELASTIC = "Search Elastic index"
    SQL = "SQL"


class FileSystemTool(Enum):
    GENERATE_IMAGE_TOOL = "Generate image"


class QualityAssuranceTool(Enum):
    ZEPHYR_SCALE = "Zephyr Scale"
    XRAY_GET_TESTS = "Xray Get Tests"
    XRAY_CREATE_TEST = "Xray Create Test"
    XRAY_EXECUTE_GRAPHQL = "Xray Execute GraphQL"


class ITServiceManagementTool(Enum):
    SERVICENOW_TABLE_API = "ServiceNow Table API"


class ReportPortalTool(Enum):
    GET_EXTENDED_LAUNCH_DATA = "Get Extended Launch Data"
    GET_EXTENDED_LAUNCH_RAW_DATA = "Get Extended Launch Data as Raw"
    GET_LAUNCH_DETAILS = "Get Launch Details"
    GET_ALL_LAUNCHES = "Get All Launches"
    GET_USER_INFORMATION = "Get User Information"
    GET_DASHBOARD_DATA = "Get Dashboard Data"
    UPDATE_TEST_ITEM = "Update Test Item"
    FIND_TEST_ITEM_BY_ID = "Find Test Item by ID"


class PlatformTool(Enum):
    GET_ASSISTANTS = "Get Assistants"
    GET_CONVERSATION_METRICS = "Get Conversation Metrics"
    GET_RAW_CONVERSATIONS = "Get Raw Conversations"
    GET_SPENDING_ANALYTICS = "Get Spending Analytics"
    GET_LITELLM_KEY_SPENDING = "Get LiteLLM Key Spending"
    GET_CONVERSATION_ANALYTICS = "Get Conversation Analytics"


class MCPServersAction(Enum):
    BROWSE_CATALOG = "Browse catalog"
    MANUAL_SETUP = "Manual Setup"


TOOLKIT_TOOLS = {
    Section.AVAILABLE_TOOLS: {
        Toolkit.GIT: [
            GitTool.CREATE_BRANCH,
            GitTool.SET_ACTIVE_BRANCH,
            GitTool.LIST_BRANCHES_IN_REPO,
            GitTool.CREATE_FILE,
            GitTool.UPDATE_FILE,
            GitTool.UPDATE_FILE_DIFF,
            GitTool.DELETE_FILE,
            GitTool.CREATE_PULL_REQUEST,
            GitTool.GET_PR_CHANGES,
            GitTool.CREATE_PR_CHANGE_COMMENT,
        ],
        Toolkit.VCS: [
            VcsTool.GITHUB,
            VcsTool.GITLAB,
            VcsTool.AZURE_GIT,
        ],
        Toolkit.CODEBASE_TOOLS: [
            CodebaseTool.GET_REPOSITORY_FILE_TREE_V2,
            CodebaseTool.SEARCH_CODE_REPO_V2,
            CodebaseTool.READ_FILES_CONTENT,
            CodebaseTool.READ_FILES_CONTENT_SUMMARY,
            CodebaseTool.SEARCH_CODE_REPO_BY_PATH,
            CodebaseTool.SONAR,
        ],
        Toolkit.RESEARCH: [
            ResearchTool.GOOGLE_SEARCH,
            ResearchTool.GOOGLE_PLACES,
            ResearchTool.GOOGLE_PLACES_FIND_NEAR,
            ResearchTool.WIKIPEDIA,
            ResearchTool.TAVILY_SEARCH,
            ResearchTool.WEB_SCRAPPER,
        ],
        Toolkit.CLOUD: [
            CloudTool.KUBERNETES,
            CloudTool.AWS,
            CloudTool.GCP,
            CloudTool.AZURE,
        ],
        Toolkit.AZURE_DEVOPS_WIKI: [
            AzureDevOpsWikiTool.GET_WIKI,
            AzureDevOpsWikiTool.GET_WIKI_PAGE_BY_PATH,
            AzureDevOpsWikiTool.GET_WIKI_PAGE_BY_ID,
            AzureDevOpsWikiTool.DELETE_PAGE_BY_PATH,
            AzureDevOpsWikiTool.CREATE_WIKI_PAGE,
            AzureDevOpsWikiTool.DELETE_PAGE_BY_ID,
            AzureDevOpsWikiTool.MODIFY_WIKI_PAGE,
            AzureDevOpsWikiTool.RENAME_WIKI_PAGE,
        ],
        Toolkit.AZURE_DEVOPS_WORK_ITEM: [
            AzureDevOpsWorkItemTool.SEARCH_WORK_ITEMS,
            AzureDevOpsWorkItemTool.CREATE_WORK_ITEM,
            AzureDevOpsWorkItemTool.UPDATE_WORK_ITEM,
            AzureDevOpsWorkItemTool.GET_WORK_ITEM,
            AzureDevOpsWorkItemTool.LINK_WORK_ITEMS,
            AzureDevOpsWorkItemTool.GET_RELATION_TYPES,
            AzureDevOpsWorkItemTool.GET_COMMENTS,
        ],
        Toolkit.AZURE_DEVOPS_TEST_PLAN: [
            AzureDevOpsTestPlanTool.CREATE_TEST_PLAN,
            AzureDevOpsTestPlanTool.DELETE_TEST_PLAN,
            AzureDevOpsTestPlanTool.GET_TEST_PLAN,
            AzureDevOpsTestPlanTool.CREATE_TEST_SUITE,
            AzureDevOpsTestPlanTool.DELETE_TEST_SUITE,
            AzureDevOpsTestPlanTool.GET_TEST_SUITE,
            AzureDevOpsTestPlanTool.ADD_TEST_CASE,
            AzureDevOpsTestPlanTool.GET_TEST_CASE,
            AzureDevOpsTestPlanTool.GET_TEST_CASES,
        ],
        Toolkit.ACCESS_MANAGEMENT: [
            AccessManagementTool.KEYCLOAK,
        ],
        Toolkit.PROJECT_MANAGEMENT: [
            ProjectManagementTool.GENERIC_JIRA,
            ProjectManagementTool.GENERIC_CONFLUENCE,
        ],
        Toolkit.OPEN_API: [
            OpenAPITool.INVOKE_EXTERNAL_API,
            OpenAPITool.GET_OPEN_API_SPEC,
        ],
        Toolkit.NOTIFICATION: [
            NotificationTool.EMAIL,
            NotificationTool.TELEGRAM,
        ],
        Toolkit.DATA_MANAGEMENT: [
            DataManagementTool.ELASTIC,
            DataManagementTool.SQL,
        ],
        Toolkit.FILESYSTEM: [
            FileSystemTool.GENERATE_IMAGE_TOOL,
        ],
        Toolkit.QUALITY_ASSURANCE: [
            QualityAssuranceTool.ZEPHYR_SCALE,
            QualityAssuranceTool.XRAY_GET_TESTS,
            QualityAssuranceTool.XRAY_CREATE_TEST,
            QualityAssuranceTool.XRAY_EXECUTE_GRAPHQL,
        ],
        Toolkit.REPORT_PORTAL: [
            ReportPortalTool.GET_EXTENDED_LAUNCH_DATA,
            ReportPortalTool.GET_EXTENDED_LAUNCH_RAW_DATA,
            ReportPortalTool.GET_LAUNCH_DETAILS,
            ReportPortalTool.GET_ALL_LAUNCHES,
            ReportPortalTool.GET_USER_INFORMATION,
            ReportPortalTool.GET_DASHBOARD_DATA,
            ReportPortalTool.UPDATE_TEST_ITEM,
            ReportPortalTool.FIND_TEST_ITEM_BY_ID,
        ],
        Toolkit.IT_SERVICE_MANAGEMENT: [
            ITServiceManagementTool.SERVICENOW_TABLE_API,
        ],
        Toolkit.PLATFORM_TOOLS: [
            PlatformTool.GET_ASSISTANTS,
            PlatformTool.GET_CONVERSATION_METRICS,
            PlatformTool.GET_RAW_CONVERSATIONS,
            PlatformTool.GET_SPENDING_ANALYTICS,
            PlatformTool.GET_LITELLM_KEY_SPENDING,
            PlatformTool.GET_CONVERSATION_ANALYTICS,
        ],
    },
    Section.EXTERNAL_TOOLS: {},
    Section.MCP_SERVERS: [
        MCPServersAction.BROWSE_CATALOG,
        MCPServersAction.MANUAL_SETUP,
    ],
}

# ---------------------------------------------------------------------------
# Sorting UI constants
# ---------------------------------------------------------------------------

SORT_BY_UI_OPTIONS = ["Usage", "Likes", "Dislikes", "Name"]
SORT_ORDER_UI_OPTIONS = ["Descending", "Ascending"]

# ---------------------------------------------------------------------------
# Favorites card metrics
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FavoritesMetricsScenario:
    """How a published assistant is seeded and which metrics its cards must show.

    ``chats`` is the number of chat requests the test user sends (a user counts once
    toward ``unique_users_count`` however many requests they send), ``clones`` the
    number of API clones made of the published assistant.
    """

    chats: int
    clones: int
    expected_usage: int
    expected_clones: int


FAVORITES_METRICS_SCENARIOS = [
    pytest.param(
        FavoritesMetricsScenario(
            chats=1, clones=1, expected_usage=1, expected_clones=1
        ),
        id="non-zero-metrics",
    ),
    pytest.param(
        FavoritesMetricsScenario(
            chats=0, clones=0, expected_usage=0, expected_clones=0
        ),
        id="real-zero-metrics",
    ),
]


def expected_usage_label(count: int) -> str:
    """Accessible name of the usage label on an assistant card (singular for 1)."""
    return f"{count} {'total use' if count == 1 else 'total uses'}"


def expected_clone_label(assistant_name: str, count: int) -> str:
    """Accessible name of the clone button on an assistant card."""
    return f"Clone {assistant_name}, {count}"
