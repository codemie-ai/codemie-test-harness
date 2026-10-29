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

"""Shared entity-deletion helpers used by both the standalone
`test_clean_all_entities` sweep (cleanup.py) and the automatic
`pytest_sessionfinish` backstop (conftest.py). Callers decide how wide a
net to cast by choosing their own `filters`/name-matching arguments —
nothing in this module hardcodes a scope.
"""

import base64
import copy
import logging
import time
from typing import Any, Callable

import requests
from codemie_sdk.models.integration import IntegrationType

from codemie_test_harness.tests.utils.confluence_utils import ConfluenceUtils
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver
from codemie_test_harness.tests.utils.jira_utils import JiraUtils
from codemie_test_harness.tests.utils.provider_utils import (
    ProviderUtils,
    TEST_PROVIDER_NAME_RE,
)

logger = logging.getLogger(__name__)

DELETION_DELAY = 1 if EnvironmentResolver.is_production() else 0
DELETE_CONVERSATIONS = True
BATCH_SIZE = 200

# ADO static test fixtures that must never be deleted
_ADO_PROTECTED_WORK_ITEM_IDS = frozenset(
    {
        30,  # "Autotest Task TnKIcP" — anchor for SEARCH_WORK_ITEMS expected result (oldest task)
    }
)
_ADO_PROTECTED_WIKI_PAGES = frozenset()


def delete_entities(
    entity_name: str,
    fetch_fn: Callable[[], list[Any]],
    delete_fn: Callable[[Any], None],
    get_entity_name: Callable[[Any], str],
    get_entity_id: Callable[[Any], str],
    post_delete_fn: Callable[[Any], int] | None = None,
) -> tuple[int, int]:
    """
    Generic entity deletion function with batch processing.

    Args:
        entity_name: Display name for the entity type (e.g., "datasource", "workflow")
        fetch_fn: Function to fetch entities (should return a list)
        delete_fn: Function to delete a single entity
        get_entity_name: Function to extract entity name for logging
        get_entity_id: Function to extract entity ID for logging
        post_delete_fn: Optional callback after deleting each entity (returns additional count)

    Returns:
        Tuple of (primary_count, secondary_count) where secondary_count is from post_delete_fn.
        Per-item failures are logged and skipped so one bad delete doesn't abort the rest
        of the batch (or the caller's whole cleanup run).
    """
    logger.info("🔍 Fetching %ss...", entity_name)

    total_count = 0
    secondary_count = 0
    batch_number = 1

    while True:
        entities = fetch_fn()
        batch_count = len(entities)

        if batch_count == 0:
            if total_count == 0:
                logger.info("✓ No %ss found", entity_name)
            else:
                logger.info("✓ No more %ss found", entity_name)
            break

        logger.info(
            "🗑️  Batch %d: Deleting %d %s(s)...", batch_number, batch_count, entity_name
        )

        deleted_in_batch = 0
        for entity in entities:
            name = get_entity_name(entity)
            entity_id = get_entity_id(entity)
            logger.info("   - Deleting %s: %s (ID: %s)", entity_name, name, entity_id)
            try:
                delete_fn(entity)
                time.sleep(DELETION_DELAY)
                if post_delete_fn:
                    secondary_count += post_delete_fn(entity)
                deleted_in_batch += 1
            except Exception as e:
                logger.warning(
                    "   ⚠️  Could not delete %s %s (ID: %s) (skipped): %s",
                    entity_name,
                    name,
                    entity_id,
                    e,
                )

        total_count += deleted_in_batch
        batch_number += 1

        if batch_count < BATCH_SIZE:
            break

    if total_count > 0:
        logger.info(
            "✓ Successfully deleted %d %s(s) in %d batch(es)",
            total_count,
            entity_name,
            batch_number - 1,
        )

    return total_count, secondary_count


def delete_integrations(
    client,
    integration_type: IntegrationType,
    filters: dict,
    name_contains: str | None = None,
) -> int:
    type_name = integration_type.value

    def fetch():
        integrations_filter = copy.deepcopy(filters)
        if integration_type == IntegrationType.USER:
            integrations_filter.pop("created_by", None)
        integrations = client.integrations.list(
            setting_type=integration_type,
            filters=integrations_filter,
            per_page=BATCH_SIZE,
        )
        if name_contains is None:
            return integrations
        return [i for i in integrations if name_contains in i.alias]

    def delete(integration):
        client.integrations.delete(
            setting_id=integration.id, setting_type=integration_type
        )

    count, _ = delete_entities(
        entity_name=f"{type_name} integration",
        fetch_fn=fetch,
        delete_fn=delete,
        get_entity_name=lambda e: e.alias,
        get_entity_id=lambda e: e.id,
    )
    return count


def delete_datasources(client, filters: dict, name_contains: str | None = None) -> int:
    def fetch():
        datasources = client.datasources.list(filters=filters, per_page=BATCH_SIZE)
        if name_contains is None:
            return datasources
        return [d for d in datasources if name_contains in d.name]

    count, _ = delete_entities(
        entity_name="datasource",
        fetch_fn=fetch,
        delete_fn=lambda ds: client.datasources.delete(datasource_id=ds.id),
        get_entity_name=lambda e: e.name,
        get_entity_id=lambda e: e.id,
    )
    return count


def delete_assistants(
    client, filters: dict, name_contains: str | None = None
) -> tuple[int, int]:
    def fetch():
        assistants = client.assistants.list(filters=filters, per_page=BATCH_SIZE)
        if name_contains is None:
            return assistants
        return [a for a in assistants if name_contains in a.name]

    def post_delete(assistant):
        """Delete conversations for the assistant and return count."""
        if not DELETE_CONVERSATIONS:
            return 0

        conversations = client.conversations.list_by_assistant_id(assistant.id)
        if not conversations:
            return 0

        logger.info(
            "     └─ Deleting %d conversation(s) for assistant %s",
            len(conversations),
            assistant.id,
        )
        for conversation in conversations:
            logger.debug("        - Conversation ID: %s", conversation.id)
            client.conversations.delete(conversation.id)
            time.sleep(DELETION_DELAY)

        return len(conversations)

    assistant_count, conversation_count = delete_entities(
        entity_name="assistant",
        fetch_fn=fetch,
        delete_fn=lambda a: client.assistants.delete(assistant_id=a.id),
        get_entity_name=lambda e: e.name,
        get_entity_id=lambda e: e.id,
        post_delete_fn=post_delete,
    )

    if assistant_count > 0:
        if DELETE_CONVERSATIONS:
            logger.info(
                "✓ Total: %d assistant(s) and %d conversation(s) deleted",
                assistant_count,
                conversation_count,
            )
        else:
            logger.info(
                "✓ Total: %d assistant(s) deleted (conversations cascade-deleted)",
                assistant_count,
            )

    return assistant_count, conversation_count


def delete_workflows(
    client, filters: dict, name_contains: str | None = None
) -> tuple[int, int]:
    """Delete workflows and their conversations for chat mode.

    Deletion order:
    1. Delete workflow conversations (if any)
    2. Delete workflow (executions cascade-delete)
    """

    def fetch():
        workflows = client.workflows.list(filters=filters, per_page=BATCH_SIZE)
        if name_contains is None:
            return workflows
        return [w for w in workflows if name_contains in w.name]

    total_workflow_count = 0
    total_conversation_count = 0
    batch_number = 1

    logger.info("Fetching workflows...")

    while True:
        workflows = fetch()
        batch_count = len(workflows)

        if batch_count == 0:
            if total_workflow_count == 0:
                logger.info("No workflows found")
            else:
                logger.info("No more workflows found")
            break

        logger.info(
            "🗑️  Batch %d: Deleting %d workflow(s)...", batch_number, batch_count
        )

        deleted_in_batch = 0
        for workflow in workflows:
            logger.info(
                "   - Deleting workflow: %s (ID: %s)", workflow.name, workflow.id
            )
            try:
                # Step 1: Delete workflow conversations BEFORE deleting workflow
                if DELETE_CONVERSATIONS:
                    try:
                        all_conversations = client.conversations.list()
                        workflow_conversations = [
                            conv
                            for conv in all_conversations
                            if conv.initial_assistant_id == workflow.id
                        ]

                        if workflow_conversations:
                            logger.info(
                                "     └─ Deleting %d conversation(s) for workflow %s",
                                len(workflow_conversations),
                                workflow.id,
                            )
                            for conversation in workflow_conversations:
                                logger.debug(
                                    "        - Conversation ID: %s", conversation.id
                                )
                                client.conversations.delete(conversation.id)
                                time.sleep(DELETION_DELAY)
                            total_conversation_count += len(workflow_conversations)
                    except Exception as e:
                        logger.warning(
                            "     └─ Failed to delete conversations for workflow %s: %s",
                            workflow.id,
                            e,
                        )

                # Step 2: Delete the workflow (executions cascade-delete)
                client.workflows.delete(workflow_id=workflow.id)
                time.sleep(DELETION_DELAY)
                deleted_in_batch += 1
            except Exception as e:
                logger.warning(
                    "   ⚠️  Could not delete workflow %s (ID: %s) (skipped): %s",
                    workflow.name,
                    workflow.id,
                    e,
                )

        total_workflow_count += deleted_in_batch
        batch_number += 1

        if batch_count < BATCH_SIZE:
            break

    if total_workflow_count > 0:
        logger.info(
            "✓ Successfully deleted %d workflow(s) in %d batch(es)",
            total_workflow_count,
            batch_number - 1,
        )
        if DELETE_CONVERSATIONS:
            logger.info(
                "✓ Total: %d workflow(s) and %d conversation(s) deleted",
                total_workflow_count,
                total_conversation_count,
            )
        else:
            logger.info(
                "✓ Total: %d workflow(s) deleted (conversations cascade-deleted)",
                total_workflow_count,
            )

    return total_workflow_count, total_conversation_count


def delete_skills(client, filters: dict) -> int:
    def fetch():
        return client.skills.list(filters=filters, per_page=100).skills

    count, _ = delete_entities(
        entity_name="skill",
        fetch_fn=fetch,
        delete_fn=lambda s: client.skills.delete(s.id),
        get_entity_name=lambda e: e.name,
        get_entity_id=lambda e: e.id,
    )
    return count


def delete_providers(client) -> int:
    """Delete test providers whose names match the test naming pattern.

    Targets providers with names of the form 'autotest-[a-z]{3}_[a-z]{15}' — the
    format produced by get_random_name() (e.g. 'autotest-qdn_inqddvhfehottus').
    Treats 404 responses as already-deleted (idempotent).
    Returns the number of providers deleted.
    """

    provider_utils = ProviderUtils(client)

    def fetch():
        response = provider_utils.list_providers()
        all_providers = response.json()
        return [p for p in all_providers if TEST_PROVIDER_NAME_RE.match(p["name"])]

    def delete(provider):
        response = provider_utils.send_delete_provider_request(provider["id"])
        if response.status_code not in (204, 404):
            logger.warning(
                "   ⚠️  Unexpected status %d deleting provider %s: %s",
                response.status_code,
                provider["id"],
                response.text,
            )

    count, _ = delete_entities(
        entity_name="provider",
        fetch_fn=fetch,
        delete_fn=delete,
        get_entity_name=lambda e: e["name"],
        get_entity_id=lambda e: e["id"],
    )
    return count


def delete_cost_centers(client) -> int:
    """Delete test cost centers whose names match the test naming pattern.

    Targets cost centers with names of the form '[a-z]{3}-[a-z]{10}' — the
    format produced by get_random_cost_center_name() (e.g. 'xju-nxherepeao').
    No created_by-based filtering is possible here (list_cost_centers'
    created_by is a user id, not comparable to TEST_USER's display name),
    so this relies entirely on the distinctive name pattern, same as
    delete_providers above. A cost center still assigned to a project 409s
    on delete; that failure is logged and skipped, not raised.
    """
    from codemie_test_harness.tests.utils.cost_center_utils import (
        CostCenterUtils,
        TEST_COST_CENTER_NAME_RE,
    )

    cost_center_utils = CostCenterUtils(client)

    def fetch():
        all_cost_centers = cost_center_utils.list_cost_centers()
        return [c for c in all_cost_centers if TEST_COST_CENTER_NAME_RE.match(c.name)]

    def delete(cost_center):
        cost_center_utils.delete_cost_center(cost_center.id)

    count, _ = delete_entities(
        entity_name="cost center",
        fetch_fn=fetch,
        delete_fn=delete,
        get_entity_name=lambda e: e.name,
        get_entity_id=lambda e: e.id,
    )
    return count


def delete_ado_work_items() -> int:
    """Delete orphaned ADO work items created by tests.

    Targets work items of type Task or Epic whose title contains 'Autotest'
    in the configured project. IDs listed in _ADO_PROTECTED_WORK_ITEM_IDS
    are always skipped to preserve static test fixtures.
    Items are permanently destroyed (not sent to recycle bin).
    """
    token = CredentialsManager.get_parameter("AZURE_DEVOPS_TOKEN")
    org = CredentialsManager.get_parameter("AZURE_DEVOPS_ORGANIZATION_NAME")
    project = CredentialsManager.get_parameter("AZURE_DEVOPS_PROJECT_NAME")

    if not all([token, org, project]):
        logger.info("⚠️  ADO credentials not configured, skipping work item cleanup")
        return 0

    api_base = f"{CredentialsManager.get_parameter('AZURE_DEVOPS_URL')}/{org}"
    auth = base64.b64encode(f":{token}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

    wiql = {
        "query": (
            f"SELECT [System.Id], [System.Title] FROM WorkItems "
            f"WHERE [System.TeamProject] = '{project}' "
            f"AND [System.WorkItemType] IN ('Task', 'Epic') "
            f"AND [System.Title] CONTAINS 'Autotest' "
            f"ORDER BY [System.CreatedDate] DESC"
        )
    }

    logger.info("🔍 Fetching orphaned ADO work items...")
    response = requests.post(
        f"{api_base}/{project}/_apis/wit/wiql?api-version=7.1",
        headers=headers,
        json=wiql,
        timeout=30,
    )
    response.raise_for_status()

    item_refs = [
        ref
        for ref in response.json().get("workItems", [])
        if ref["id"] not in _ADO_PROTECTED_WORK_ITEM_IDS
    ]

    if not item_refs:
        logger.info("✓ No orphaned ADO work items found")
        return 0

    logger.info("🗑️  Deleting %d orphaned ADO work item(s)...", len(item_refs))
    count = 0
    for ref in item_refs:
        item_id = ref["id"]
        logger.info("   - Deleting work item ID: %d", item_id)
        del_resp = requests.delete(
            f"{api_base}/_apis/wit/workitems/{item_id}?api-version=7.1&destroy=true",
            headers=headers,
            timeout=30,
        )
        if del_resp.status_code == 204:
            count += 1
        else:
            logger.warning(
                "     ⚠️  Failed to delete work item %d: %s", item_id, del_resp.text
            )
        time.sleep(DELETION_DELAY)

    logger.info("✓ Successfully deleted %d ADO work item(s)", count)
    return count


def delete_ado_wiki_pages() -> int:
    """Delete orphaned ADO wiki pages created by tests.

    Targets root-level pages in the configured wiki whose name starts with
    'Autotest-'. Names listed in _ADO_PROTECTED_WIKI_PAGES are always skipped
    to preserve static test fixtures. Deleting a parent page cascades to its
    children, so only root-level matches need to be targeted.
    """
    token = CredentialsManager.get_parameter("AZURE_DEVOPS_TOKEN")
    org = CredentialsManager.get_parameter("AZURE_DEVOPS_ORGANIZATION_NAME")
    project = CredentialsManager.get_parameter("AZURE_DEVOPS_PROJECT_NAME")
    wiki = CredentialsManager.get_parameter("AZURE_DEVOPS_WIKI_NAME")

    if not all([token, org, project, wiki]):
        logger.info("⚠️  ADO credentials not configured, skipping wiki page cleanup")
        return 0

    api_base = (
        f"{CredentialsManager.get_parameter('AZURE_DEVOPS_URL')}/{org}/{project}"
        f"/_apis/wiki/wikis/{wiki}"
    )
    auth = base64.b64encode(f":{token}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

    logger.info("🔍 Fetching orphaned ADO wiki pages...")
    response = requests.get(
        f"{api_base}/pages?path=/&recursionLevel=oneLevel&includeContent=false&api-version=7.1",
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()

    sub_pages = response.json().get("subPages", [])
    autotest_pages = [
        page
        for page in sub_pages
        if page.get("path", "").lstrip("/").startswith("Autotest-")
        and page.get("path", "").lstrip("/") not in _ADO_PROTECTED_WIKI_PAGES
    ]

    if not autotest_pages:
        logger.info("✓ No orphaned ADO wiki pages found")
        return 0

    logger.info("🗑️  Deleting %d orphaned ADO wiki page(s)...", len(autotest_pages))
    count = 0
    for page in autotest_pages:
        page_path = page["path"]
        logger.info("   - Deleting wiki page: %s", page_path)
        del_resp = requests.delete(
            f"{api_base}/pages?path={page_path}&api-version=7.1",
            headers={**headers, "If-Match": "*"},
            timeout=30,
        )
        if del_resp.status_code == 200:
            count += 1
        else:
            logger.warning(
                "     ⚠️  Failed to delete wiki page %s: %s", page_path, del_resp.text
            )
        time.sleep(DELETION_DELAY)

    logger.info("✓ Successfully deleted %d ADO wiki page(s)", count)
    return count


def delete_confluence_pages(
    title_prefix: str | None = None, title_contains: str | None = None
) -> int:
    """Delete orphaned Confluence pages (Server + Cloud) matching the given
    title filter. Pass exactly one of title_prefix (session-scoped) or
    title_contains (session-agnostic) — forwarded as-is to
    ConfluenceUtils.cleanup_confluence_space, which already supports both.
    """
    total = 0

    server_url = CredentialsManager.get_parameter("CONFLUENCE_URL")
    server_token = CredentialsManager.get_parameter("CONFLUENCE_TOKEN")
    if server_url and server_token:
        try:
            total += ConfluenceUtils(is_cloud=False).cleanup_confluence_space(
                title_prefix=title_prefix, title_contains=title_contains
            )
        except Exception as e:
            logger.warning("⚠️  Failed to cleanup Confluence Server pages: %s", e)
    else:
        logger.info("⚠️  Confluence Server credentials not configured, skipping")

    cloud_url = CredentialsManager.get_parameter("CONFLUENCE_CLOUD_URL")
    cloud_token = CredentialsManager.get_parameter("CONFLUENCE_CLOUD_TOKEN")
    if cloud_url and cloud_token:
        try:
            total += ConfluenceUtils(is_cloud=True).cleanup_confluence_space(
                title_prefix=title_prefix, title_contains=title_contains
            )
        except Exception as e:
            logger.warning("⚠️  Failed to cleanup Confluence Cloud pages: %s", e)
    else:
        logger.info("⚠️  Confluence Cloud credentials not configured, skipping")

    return total


def delete_jira_issues(
    summary_prefix: str | None = None, summary_contains: str | None = None
) -> int:
    """Delete orphaned Jira issues (Server + Cloud) matching the given
    summary filter. Mirrors delete_confluence_pages's dual-mode shape.
    """
    total = 0
    for is_cloud in (False, True):
        flavor = "Cloud" if is_cloud else "Server"
        try:
            total += JiraUtils(is_cloud=is_cloud).cleanup_jira_project(
                summary_prefix=summary_prefix, summary_contains=summary_contains
            )
        except Exception as e:
            logger.warning("⚠️  Failed to cleanup Jira %s issues: %s", flavor, e)
    return total
