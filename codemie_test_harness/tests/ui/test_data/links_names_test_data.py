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
Test data for Help Page and Creation Pages Help Links UI tests.

This module contains all URLs, card names, section headers, and other constants
used in help page tests and creation page help panel tests for better maintainability and reusability.
"""

# ============================================================================
# HELP PAGE DATA
# ============================================================================


class AssistantNames:
    """Assistant card titles used on the Help page."""

    AI_RUN_FAQ = "AI/Run FAQ"
    AI_RUN_CHATBOT = "AI/Run Chatbot"
    AI_RUN_FEEDBACK = "AI/Run Feedback"


class InternalUrls:
    """Internal URLs for navigation within the application."""

    CHATS = "/chats"
    RELEASE_NOTES = "/release-notes"


DOCS_BASE = "docs.codemie.ai"


class ExternalUrls:
    """External URLs for help page links.

    The video-portal and learning-courses links come from the platform config
    (GET /v1/config), not from constants.
    """

    DOCUMENTATION = f"https://{DOCS_BASE}/"
    YOUTUBE_CHANNEL = "youtube.com/@EPAMAIRunCodeMie"
    SURVEY = "forms.office.com/Pages/ResponsePage.aspx"


# ============================================================================
# WORKFLOWS
# ============================================================================


class WorkflowDocUrls:
    """Documentation URLs for workflow help resources."""

    CREATE_WORKFLOW = f"{DOCS_BASE}/user-guide/workflows/create-workflow"
    YAML_CONFIGURATION = f"{DOCS_BASE}/user-guide/workflows/configuration"


# ============================================================================
# ASSISTANTS
# ============================================================================


class AssistantDocUrls:
    """Documentation URLs for assistant help resources."""

    CREATE_ASSISTANT = f"{DOCS_BASE}/user-guide/assistants/create-assistant"
    CONNECT_TOOLS = f"{DOCS_BASE}/user-guide/tools_integrations/tools/overview"
    CONNECT_INTEGRATIONS = f"{DOCS_BASE}/user-guide/tools_integrations/integrations"


# ============================================================================
# INTEGRATIONS
# ============================================================================


class IntegrationDocUrls:
    """Documentation URLs for integration help resources."""

    WORK_WITH_INTEGRATIONS = f"{DOCS_BASE}/user-guide/tools_integrations"


# ============================================================================
# DATA SOURCES
# ============================================================================


class DatasourceDocUrls:
    """Documentation URLs for datasource help resources."""

    WORK_WITH_DATASOURCES = f"{DOCS_BASE}/user-guide/data-source"
    CREATE_GIT_DATASOURCE = (
        f"{DOCS_BASE}/user-guide/data-source/datasources-types/add-git-data-sources"
    )


# ============================================================================
# KATAS
# ============================================================================


class KatasDocUrls:
    """Documentation URLs for katas help resources."""

    WORK_WITH_KATAS = f"{DOCS_BASE}/user-guide/ai-katas"
