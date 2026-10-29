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

import logging

import pytest
from codemie_sdk.models.integration import IntegrationType

from codemie_test_harness.tests import PROJECT, TEST_USER
from codemie_test_harness.tests.utils import cleanup_utils
from codemie_test_harness.tests.utils.constants import test_project_name
from codemie_test_harness.tests.utils.project_utils import ProjectUtils

logger = logging.getLogger(__name__)


def _safe(label: str, fn, default):
    """Run fn(), logging and returning `default` on any failure instead of
    letting it raise. Without this, one bad fetch/delete anywhere would
    abort the whole test — including every entity type ordered after it —
    since a single exception raised while building total_deleted below
    would skip its later dict entries entirely.
    """
    try:
        return fn()
    except Exception as e:
        logger.error(f"Failed to clean up {label}: {e}")
        return default


@pytest.mark.cleanup
@pytest.mark.timeout(1000)
def test_clean_all_entities(client):
    logger.info("=" * 80)
    logger.info("🧹 CLEANUP: Starting entity cleanup process")
    logger.info("=" * 80)
    logger.info("📋 Projects: %s, %s", PROJECT, test_project_name)
    logger.info("👤 User: %s", TEST_USER)

    filters = {"created_by": TEST_USER}

    assistant_count, assistant_conversation_count = _safe(
        "assistants", lambda: cleanup_utils.delete_assistants(client, filters), (0, 0)
    )
    workflow_count, workflow_conversation_count = _safe(
        "workflows", lambda: cleanup_utils.delete_workflows(client, filters), (0, 0)
    )
    # search="autotest-" narrows the listing server-side instead of paging
    # through every project on the environment (tens of thousands on a
    # shared, multi-tenant env) — safe as long as every test-project fixture
    # names its projects with an "autotest-" prefix (guaranteed by
    # get_random_name()). name_predicate re-checks it client-side since
    # search is a substring match, not a full naming-pattern match.
    project_count = _safe(
        "projects",
        lambda: ProjectUtils(client).delete_matching_projects(
            lambda n: n.startswith("autotest-"), search="autotest-"
        ),
        0,
    )

    total_deleted = {
        "project_integrations": _safe(
            "project integrations",
            lambda: cleanup_utils.delete_integrations(
                client, IntegrationType.PROJECT, filters
            ),
            0,
        ),
        "user_integrations": _safe(
            "user integrations",
            lambda: cleanup_utils.delete_integrations(
                client, IntegrationType.USER, filters
            ),
            0,
        ),
        "datasources": _safe(
            "datasources", lambda: cleanup_utils.delete_datasources(client, filters), 0
        ),
        "skills": _safe(
            "skills", lambda: cleanup_utils.delete_skills(client, filters), 0
        ),
        "assistants": assistant_count,
        "assistant_conversations": assistant_conversation_count,
        "workflows": workflow_count,
        "workflow_conversations": workflow_conversation_count,
        "projects": project_count,
        "ado_work_items": _safe(
            "ADO work items", cleanup_utils.delete_ado_work_items, 0
        ),
        "ado_wiki_pages": _safe(
            "ADO wiki pages", cleanup_utils.delete_ado_wiki_pages, 0
        ),
        "confluence_pages": _safe(
            "Confluence pages",
            lambda: cleanup_utils.delete_confluence_pages(
                title_contains="Test Page Created by Automation"
            ),
            0,
        ),
        "jira_issues": _safe(
            "Jira issues",
            lambda: cleanup_utils.delete_jira_issues(summary_contains="Autotest"),
            0,
        ),
        "providers": _safe(
            "providers", lambda: cleanup_utils.delete_providers(client), 0
        ),
        "cost_centers": _safe(
            "cost centers", lambda: cleanup_utils.delete_cost_centers(client), 0
        ),
    }

    logger.info("=" * 80)
    logger.info("📊 CLEANUP SUMMARY")
    logger.info("=" * 80)
    logger.info(
        "  Project Integrations:      %d", total_deleted["project_integrations"]
    )
    logger.info("  User Integrations:         %d", total_deleted["user_integrations"])
    logger.info("  Datasources:               %d", total_deleted["datasources"])
    logger.info("  Skills:                    %d", total_deleted["skills"])
    logger.info("  Assistants:                %d", total_deleted["assistants"])
    if cleanup_utils.DELETE_CONVERSATIONS:
        logger.info(
            "  Assistant Conversations:   %d", total_deleted["assistant_conversations"]
        )
    else:
        logger.info(
            "  Assistant Conversations:   %d (cascade-deleted)",
            total_deleted["assistant_conversations"],
        )
    logger.info("  Workflows:                 %d", total_deleted["workflows"])
    if cleanup_utils.DELETE_CONVERSATIONS:
        logger.info(
            "  Workflow Conversations:    %d", total_deleted["workflow_conversations"]
        )
    else:
        logger.info(
            "  Workflow Conversations:    %d (cascade-deleted)",
            total_deleted["workflow_conversations"],
        )
    logger.info("  Projects:                  %d", total_deleted["projects"])
    logger.info("  ADO Work Items:            %d", total_deleted["ado_work_items"])
    logger.info("  ADO Wiki Pages:            %d", total_deleted["ado_wiki_pages"])
    logger.info("  Confluence Pages:          %d", total_deleted["confluence_pages"])
    logger.info("  Jira Issues:               %d", total_deleted["jira_issues"])
    logger.info("  Providers:                 %d", total_deleted["providers"])
    logger.info("  Cost Centers:              %d", total_deleted["cost_centers"])
    logger.info("-" * 80)
    total_count = sum(total_deleted.values())
    logger.info("  TOTAL ENTITIES:            %d", total_count)
    logger.info("=" * 80)
    logger.info("✅ Cleanup completed successfully!")
