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

import os
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from time import sleep
from typing import List, Optional

import pytest
from hamcrest import assert_that, not_none
from codemie_sdk import CodeMieClient
from codemie_sdk.models.assistant import (
    ToolKitDetails,
    ToolDetails,
    Context,
    ContextType,
    ToolPermissionsConfig,
)
from codemie_sdk.models.datasource import DataSource
from codemie_sdk.models.integration import (
    IntegrationType,
    CredentialValues,
    CredentialTypes,
    Integration,
)
from codemie_sdk.models.workflow import WorkflowCreateRequest, WorkflowMode, Workflow
from codemie_test_harness import capability_gate
from codemie_test_harness.tests.utils.categories_utils import CategoriesUtils
from requests import HTTPError

from codemie_test_harness.tests import (
    API_DOMAIN,
    PROJECT,
    TEST_USER,
    VERIFY_SSL,
    autotest_entity_prefix,
)
from codemie_test_harness.tests.test_data.customer_config_test_data import (
    get_web_search_settings_data,
)
from codemie_test_harness.tests.test_data.file_test_data import file_test_data
from codemie_test_harness.tests.test_data.marketplace_thresholds_test_data import (
    MARKETPLACE_THRESHOLDS_COMPONENT_ID,
)
from codemie_test_harness.tests.test_data.fixture_generator import (
    generate_large_text_file,
)
from codemie_test_harness.tests.test_data.google_datasource_test_data import (
    get_google_doc_url,
)
from codemie_test_harness.tests.utils.admin_budget_utils import AdminBudgetUtils
from codemie_test_harness.tests.utils.admin_project_budget_utils import (
    AdminProjectBudgetUtils,
)
from codemie_test_harness.tests.utils.admin_utils import AdminUtils
from codemie_test_harness.tests.utils.assistant_utils import AssistantUtils
from codemie_test_harness.tests.utils.base_utils import get_random_name, wait_for_entity
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.customer_config_utils import CustomerConfigUtils
from codemie_test_harness.tests.utils.marketplace_management_utils import (
    MarketplaceManagementUtils,
)
from codemie_test_harness.tests.utils.constants import (
    FILES_PATH,
)
from codemie_test_harness.tests.utils.ado_seed import AdoSeed, SeedTestPlan
from codemie_test_harness.tests.utils.ado_utils import AdoUtils
from codemie_test_harness.tests.utils.conversation_utils import ConversationUtils
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.datasource_utils import DataSourceUtils
from codemie_test_harness.tests.utils.env_resolver import (
    EnvironmentResolver,
)
from codemie_test_harness.tests.utils import cleanup_utils
from codemie_test_harness.tests.utils.gitbud_utils import GitBudUtils
from codemie_test_harness.tests.utils.gitlab_seed import (
    GITLAB_SEED_FAKE_PNG_UPLOAD,
    GITLAB_SEED_IMAGE_UPLOAD,
    SEED_FAKE_PNG_UPLOAD_NAME,
    SEED_IMAGE_UPLOAD_NAME,
    SeedBranches,
    SeedImageUpload,
    SeedMergeRequest,
    png_bytes_from_image,
)
from codemie_test_harness.tests.utils.github_seed import (
    SeedFile as GitHubSeedFile,
    SeedIssue as GitHubSeedIssue,
)
from codemie_test_harness.tests.utils.github_utils import GitHubUtils
from codemie_test_harness.tests.utils.azure_devops_seed import SeedPullRequest
from codemie_test_harness.tests.utils.azure_devops_utils import AzureDevOpsUtils
from codemie_test_harness.tests.utils.http_utils import RequestHandler
from codemie_test_harness.tests.utils.integration_utils import IntegrationUtils
from codemie_test_harness.tests.utils.jira_seed import (
    SeedIssue,
    resolve_seeded,
    resolve_shared,
)
from codemie_test_harness.tests.utils.jira_utils import JiraUtils
from codemie_test_harness.tests.utils.cloud_seed import (
    SeedAwsBucket,
    SeedAzureResourceGroup,
    SeedGcpBucket,
    SeedKubernetesService,
)
from codemie_test_harness.tests.utils.cloud_utils import (
    AwsUtils,
    AzureUtils,
    GcpUtils,
    KubernetesUtils,
)
from codemie_test_harness.tests.utils.confluence_seed import SeedPage
from codemie_test_harness.tests.utils.confluence_utils import ConfluenceUtils
from codemie_test_harness.tests.utils.servicenow_seed import SeedIncident
from codemie_test_harness.tests.utils.servicenow_utils import ServiceNowUtils
from codemie_test_harness.tests.utils.report_portal_seed import (
    SeedDashboard,
    SeedLaunch,
)
from codemie_test_harness.tests.utils.report_portal_utils import ReportPortalUtils
from codemie_test_harness.tests.utils.xwiki_seed import XWikiSeedPage
from codemie_test_harness.tests.utils.xwiki_utils import XWikiUtils
from codemie_test_harness.tests.utils.influxdb_seed import InfluxDBSeedPoint
from codemie_test_harness.tests.utils.influxdb_utils import InfluxDBUtils
from codemie_test_harness.tests.utils.keycloak_seed import SeedUser as KeycloakSeedUser
from codemie_test_harness.tests.utils.keycloak_utils import KeycloakUtils
from codemie_test_harness.tests.utils.lite_llm_budget_utils import LiteLLMBudgetUtils
from codemie_test_harness.tests.utils.project_budget_groups import ProjectBudgetGroups
from codemie_test_harness.tests.utils.llm_utils import LLMUtils
from codemie_test_harness.tests.utils.local_user_utils import LocalUserUtils
from codemie_test_harness.tests.utils.ordered_users_utils import OrderedUsersBuilder
from codemie_test_harness.tests.utils.logger_util import setup_logger
from codemie_test_harness.tests.utils.notification_utils import (
    GmailUtils,
    AzureEmailUtils,
)
from codemie_test_harness.tests.utils.project_utils import ProjectUtils
from codemie_test_harness.tests.utils.cli_analytics_api_utils import (
    assert_auditor_without_admin_roles,
    assert_principal_is,
    assert_stored_roles,
    wait_until_auditor_effective,
)
from codemie_test_harness.tests.utils.cost_center_budget_projects import (
    CostCenterBudgetProjects,
)
from codemie_test_harness.tests.utils.cost_center_utils import CostCenterUtils
from codemie_test_harness.tests.utils.provider_utils import ProviderUtils
from codemie_test_harness.tests.utils.search_utils import SearchUtils
from codemie_test_harness.tests.utils.similarity_check import SimilarityCheck
from codemie_test_harness.tests.utils.swagger_utils import SwaggerUtils
from codemie_test_harness.tests.utils.user_utils import UserUtils
from codemie_test_harness.tests.utils.webhook_utils import WebhookUtils
from codemie_test_harness.tests.utils.vendor_runtime_utils import VendorRuntimeUtils
from codemie_test_harness.tests.utils.workflow_utils import WorkflowUtils
from codemie_test_harness.tests.utils.yaml_utils import (
    WorkflowYamlModel,
    AssistantModel,
    ToolModel,
    StateModel,
    prepare_yaml_content,
)

logger = setup_logger(__name__)


def pg_collation_sort_key(name: str) -> tuple:
    # Replicates PostgreSQL locale-aware collation: alphanumeric chars as primary key;
    # spaces sort after other separators (hyphens, slashes, underscores) via a high-value sentinel.
    primary = re.sub(r"[^a-z0-9]", "", name)
    secondary = name.replace(" ", "￿")
    return (primary, secondary)


def expected_name_order_with_search(
    names: list, search_term: str, reverse: bool
) -> list:
    """Build the expected name sequence when sort_by=NAME is combined with an active search.

    The backend keeps a priority CASE expression in the ORDER BY when
    sort_by=NAME + search are active together.  This splits results into two groups:
      Group 0 — assistants whose *name* contains the search term (title matches), sorted by name.
      Group 1 — assistants that match only in their *description*, also sorted by name.
    Each group is ordered with PostgreSQL locale-aware collation (pg_collation_sort_key).
    The result is NOT a single globally-sorted list.
    """
    term = search_term.lower()
    title_matches = [n for n in names if term in n]
    desc_only = [n for n in names if term not in n]
    return sorted(title_matches, key=pg_collation_sort_key, reverse=reverse) + sorted(
        desc_only, key=pg_collation_sort_key, reverse=reverse
    )


COMMON_ASSISTANT_SYSTEM_PROMPT = """
            You are a helpful integration test assistant.
            If task requires tools triggering ALWAYS do it. Run tool at least once even when you see it may return error.
            If task requires information that is missing in user prompt take it from integration configuration if any.
            
            Carefully analyze tools descriptions and ensure you do not wrap tool query with redundant query object like
            this: 
            {
                "query": {"query": {TOOL ARGS HERE}}
            }
            
        """


def pytest_addoption(parser):
    """Add custom pytest options for UI test configuration."""
    capability_gate.pytest_addoption(parser)
    parser.addoption(
        "--ui-headless",
        action="store_true",
        default=False,
        help="Run UI tests in headless mode (no browser window)",
    )
    parser.addoption(
        "--ui-headed",
        action="store_true",
        default=False,
        help="Run UI tests in headed mode (visible browser window) - overrides --ui-headless",
    )


def pytest_configure(config):
    """Pytest hook that runs before test collection starts.

    This hook loads environment variables from .env file and optionally
    retrieves additional configuration from AWS Parameter Store.
    """
    import platform
    from codemie_test_harness.cli.runner import resolve_tests_path_and_root
    from codemie_test_harness.tests.utils.aws_parameters_store import SecretStoreError
    from codemie_test_harness.tests.utils.env_utils import EnvManager, load_env_file

    # Set timeout method based on OS
    # Windows requires 'thread' method, Unix-like systems can use 'signal'
    config.option.timeout_method = (
        "thread" if platform.system() == "Windows" else "signal"
    )

    # Resolve the root directory and .env file path
    _, root_dir = resolve_tests_path_and_root()
    env_file_path = Path(root_dir) / ".env"

    # Load initial .env file (don't override existing environment variables from config).
    load_env_file(env_file_path)

    # Debug: Show which API domain is being used
    api_domain = os.getenv("CODEMIE_API_DOMAIN", "NOT SET")
    print(f"\n{'=' * 60}")
    print(f"[pytest_configure] CODEMIE_API_DOMAIN: {api_domain}")
    print(f"{'=' * 60}\n")

    # Opt-in secret store (HARNESS_SECRET_STORE): a misconfigured or unreachable
    # store stops the run here, before collection.
    try:
        if EnvManager.download_from_secret_store():
            print("[OK] AWS Parameter Store configuration loaded successfully")
    except SecretStoreError as e:
        pytest.exit(str(e), returncode=2)

    # Reads GET /v1/config once; exits with code 2 before any test when it fails.
    capability_gate.FETCHER = _fetch_capabilities
    capability_gate.pytest_configure(config)


def _fetch_capabilities() -> dict[str, bool]:
    """Resolve which runtime feature-flag components are enabled via GET /v1/config.

    A component is enabled only if it is present in the response AND its
    settings.enabled is True. A missing component means disabled.
    """
    api = RequestHandler(API_DOMAIN, get_client().token, VERIFY_SSL)
    response = api.get("/v1/config")
    response.raise_for_status()
    components = response.json()
    if not isinstance(components, list):
        raise TypeError(
            f"GET /v1/config returned unexpected response type: {type(components)!r}"
        )
    return {
        component["id"]: component.get("settings", {}).get("enabled") is True
        for component in components
    }


def pytest_collection_modifyitems(config, items):
    """Pytest hook that modifies collected test items before execution.

    When running in parallel mode (pytest-xdist with -n flag), this hook
    automatically deselects tests marked with 'not_for_parallel_run'.

    This ensures that:
    1. Parallel runs (-n X) exclude sequential-only tests automatically
    2. Sequential runs include all tests
    3. Users don't need to manually add marker filters
    """
    # Check if pytest-xdist is active (parallel execution)
    is_xdist_worker = hasattr(config, "workerinput")  # Running as xdist worker
    is_xdist_controller = config.getoption("numprocesses", default=None)  # -n flag used

    # If running in parallel mode (either as controller or worker)
    if is_xdist_controller or is_xdist_worker:
        # Filter out tests marked with 'not_for_parallel_run'
        deselected = []
        remaining = []

        for item in items:
            # Check if test has the 'not_for_parallel_run' marker
            if item.get_closest_marker("not_for_parallel_run"):
                deselected.append(item)
            else:
                remaining.append(item)

        if deselected:
            config.hook.pytest_deselected(items=deselected)
            items[:] = remaining

            # Log the deselection (only on controller, not workers)
            if is_xdist_controller and not is_xdist_worker:
                logger.info(
                    f"Parallel mode detected: Automatically excluded {len(deselected)} "
                    f"tests marked with 'not_for_parallel_run'"
                )


@pytest.fixture(scope="session")
def large_file_fixture(tmp_path_factory):
    """Path to a generated >100MB text file (never committed).

    Under pytest-xdist each worker generates its own copy, so the file is
    removed after the session to keep temp dirs small.
    """
    path = generate_large_text_file(
        tmp_path_factory.mktemp("large-files") / "large_file.txt"
    )
    yield path
    path.unlink(missing_ok=True)


@pytest.fixture(scope="session")
def client():
    return get_client()


@pytest.fixture(scope="session")
def resolver_runtime_capabilities(request):
    """Runtime feature-flag components ({id: enabled}) read once from GET /v1/config."""
    return request.config.pluginmanager.get_plugin("capability-gate").capabilities


@pytest.fixture(scope="session")
def regular_client():
    """CodeMieClient authenticated as the plain (no-role) test user.

    Uses AUTH_USERNAME_DEFAULT / AUTH_PASSWORD_DEFAULT — a user without admin,
    auditor, or maintainer flags — so that write-denial parity checks (TC-014)
    correctly reflect what a fully unprivileged user receives.
    """
    return get_client(
        username=CredentialsManager.get_parameter(
            "AUTH_USERNAME_DEFAULT",
            CredentialsManager.get_parameter("AUTH_USERNAME"),
        ),
        password=CredentialsManager.get_parameter(
            "AUTH_PASSWORD_DEFAULT",
            CredentialsManager.get_parameter("AUTH_PASSWORD"),
        ),
    )


@pytest.fixture(scope="session")
def auditor_client():
    """CodeMieClient authenticated as the auditor test user."""
    return get_client(
        username=CredentialsManager.get_parameter("AUDITOR_USERNAME"),
        password=CredentialsManager.get_parameter("AUDITOR_PASSWORD"),
    )


@pytest.fixture(scope="session")
def default_llm(client):
    models = [row for row in client.llms.list() if row.default]
    return models[0]


@pytest.fixture(scope="session")
def sonnet_46_llm(client):
    models = [row for row in client.llms.list() if "claude-sonnet-4-6" in row.base_name]
    return models[0]


@pytest.fixture(scope="session")
def default_embedding_llm(client):
    embeddings_models = client.llms.list_embeddings()
    return embeddings_models[0]


@pytest.fixture(scope="session")
def first_available_llm_label(client):
    models = [row for row in client.llms.list() if row.enabled]
    model = models[0]
    return model.label or model.deployment_name


@pytest.fixture(scope="session")
def available_embedding_model_labels(client):
    models = client.llms.list_embeddings()
    return [m.label or m.deployment_name for m in models]


@pytest.fixture(scope="session")
def similarity_workflow_yaml(default_llm):
    assistant = AssistantModel(
        id="similarity_analysis",
        model=default_llm.base_name,
        system_prompt="""
            You are a similarity analyzer. Your task is to compare two texts and rank their semantic similarity.
            You will receive two texts from user input: text1 and text2.
            Your output should be a JSON object with a single key "similarity_rank" and an integer value from 0 to 100.
            A similarity rank of 0 indicates entirely different meanings and facts,
            A similarity rank of 100 means they are entirely the same.
            IMPORTANT! Output format MUST be an integer number from 0 to 100.
            Do not describe any your thoughts!
        """,
    )
    state = StateModel(
        id="similarity_analysis",
        assistant_id="similarity_analysis",
        task="""
            Compare two texts from user input: text1 and text2 and rank their semantic similarity from 0 to 100.
            A similarity rank of 0 indicates entirely different meanings and facts,
            A similarity rank of 100 means they are entirely the same.
            IMPORTANT! Output format MUST be an integer number from 0 to 100.
            Do not describe any your thoughts!
        """,
        output_schema="""
              ```json
              {
                "similarity_rank": "..."
              }
            """,
    )

    workflow_yaml = WorkflowYamlModel(
        assistants=[assistant],
        states=[state],
    )

    return prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))


@pytest.fixture(scope="session")
def similarity_check(client, similarity_workflow_yaml, workflow_utils):
    workflow_name = get_random_name()
    create_request = WorkflowCreateRequest(
        name=workflow_name,
        description="Similarity expert",
        project=PROJECT,
        yaml_config=similarity_workflow_yaml,
        mode=WorkflowMode.SEQUENTIAL,
        shared=False,
    )
    client.workflows.create_workflow(create_request)
    similarity_workflow = wait_for_entity(
        lambda: client.workflows.list(per_page=50),
        entity_name=workflow_name,
    )
    yield SimilarityCheck(client, similarity_workflow.id)
    if similarity_workflow:
        workflow_utils.delete_workflow(similarity_workflow)


@pytest.fixture(scope="session")
def integration_utils(client):
    return IntegrationUtils(client)


@pytest.fixture(scope="session")
def datasource_utils(client):
    return DataSourceUtils(client)


@pytest.fixture(scope="session")
def assistant_utils(client):
    return AssistantUtils(client)


@pytest.fixture(scope="session")
def customer_config_utils(client):
    return CustomerConfigUtils(client)


@pytest.fixture(scope="session")
def workflow_utils(client):
    return WorkflowUtils(client)


@pytest.fixture(scope="session")
def providers_utils(client):
    utils = ProviderUtils(client)
    yield utils
    utils.cleanup_test_providers(f"autotest-{autotest_entity_prefix}")


@pytest.fixture(scope="session")
def git_utils():
    """Create GitBudUtils instance"""
    return GitBudUtils(
        url=CredentialsManager.get_parameter("GITLAB_URL"),
        token=CredentialsManager.get_parameter("GITLAB_TOKEN"),
        project_id=CredentialsManager.get_parameter("GITLAB_PROJECT_ID"),
    )


@pytest.fixture(scope="session")
def search_utils(client):
    return SearchUtils(client)


@pytest.fixture(scope="session")
def admin_utils(client):
    """Create AdminUtils instance for managing applications/projects"""
    return AdminUtils(client)


@pytest.fixture(scope="session")
def admin_project_budget_utils(client):
    return AdminProjectBudgetUtils(client)


@pytest.fixture(scope="session")
def admin_budget_utils(client):
    return AdminBudgetUtils(client)


@pytest.fixture(scope="session")
def lite_llm_budget_utils():
    """Session-scoped LiteLLM budget helper for customer teardown."""
    return LiteLLMBudgetUtils()


@pytest.fixture(scope="function")
def project_budget_groups(admin_project_budget_utils, lite_llm_budget_utils):
    """Creates project budget groups; deletes the remaining ones and their LiteLLM objects on teardown."""
    groups = ProjectBudgetGroups(admin_project_budget_utils, lite_llm_budget_utils)
    yield groups
    groups.cleanup()


@pytest.fixture
def raw_skill(skill_utils):
    """Factory: create skills via utils with auto-cleanup.

    Tracks every skill created during the test and deletes all of them on
    teardown. A 404 on deletion (entity already gone) is silently ignored.
    """
    created_ids = []

    def _create(
        enabled_builtin_subagents=None, name=None, content=None, description=None
    ):
        name = (name or get_random_name()).replace("_", "-")
        skill, _ = skill_utils.send_create_skill_request(
            skill_name=name,
            description=description,
            content=content,
            enabled_builtin_subagents=enabled_builtin_subagents,
        )
        created_ids.append(skill.id)
        return skill

    yield _create

    for skill_id in created_ids:
        try:
            skill_utils.delete_skill_by_id(skill_id)
        except Exception as e:
            logger.warning(f"Failed to delete skill {skill_id}: {e}")


@pytest.fixture
def raw_assistant(assistant_utils, skill_utils, default_llm):
    """Factory: create minimal assistants directly via send_create_assistant_request
    (bypassing the wait_for_entity round-trip the `assistant` factory does), with
    auto-cleanup and optional skill attachment.

    Tracks every assistant created during the test and deletes all of them on
    teardown. A 404 on deletion (entity already gone) is silently ignored.
    """
    created_ids = []

    def _create(
        enabled_builtin_subagents=None,
        name=None,
        system_prompt="Test assistant",
        sub_assistant_ids=None,
        description="Integration test assistant",
        skill_id=None,
    ):
        name = (name or get_random_name()).replace("_", "-")
        response, _ = assistant_utils.send_create_assistant_request(
            llm_model_type=default_llm.base_name,
            assistant_name=name,
            slug=name,
            description=description,
            shared=False,
            system_prompt=system_prompt,
            assistant_ids=sub_assistant_ids or [],
            enabled_builtin_subagents=enabled_builtin_subagents or [],
        )
        asst_id = response.assistant_id
        created_ids.append(asst_id)
        assert_that(
            asst_id, not_none(), f"No assistant ID in creation response: {response}"
        )
        if skill_id:
            skill_utils.attach_skill_to_assistant(asst_id, skill_id)
        sleep(1)
        return asst_id

    yield _create

    for asst_id in created_ids:
        try:
            assistant_utils.delete_assistant_by_id(asst_id)
        except Exception as e:
            logger.warning(f"Failed to delete assistant {asst_id}: {e}")


@pytest.fixture
def ado_work_item_ids_to_cleanup():
    """Yield a list for registering work item IDs; deletes all on teardown."""
    ids_to_delete = []
    yield ids_to_delete
    for item_id in ids_to_delete:
        try:
            AdoUtils().delete_work_item(item_id)
        except Exception as e:
            logger.warning(f"Failed to delete ADO work item {item_id}: {e}")


@pytest.fixture
def confluence_page_cleanup():
    """Yield a list for registering distinctive title fragments (e.g. the
    random name baked into a page title by a test); deletes any Confluence
    page (Server or Cloud) whose title contains one of them on teardown.
    Used by tests that create a page via a raw generic-tool call, where no
    page ID is ever returned to the test itself.
    """
    title_fragments = []
    yield title_fragments
    for fragment in title_fragments:
        try:
            cleanup_utils.delete_confluence_pages(title_contains=fragment)
        except Exception as e:
            logger.warning(
                f"Failed to delete Confluence pages matching '{fragment}': {e}"
            )


@pytest.fixture
def cleanup_cloned_assistants(assistant_utils):
    """Collect cloned assistants created during a test and delete them on
    teardown. API-created clones (which return an object) can be appended
    as the assistant object itself; UI-created clones (which don't return
    one) can be appended as just the name string.
    """
    cloned = []
    yield cloned
    for item in cloned:
        try:
            if isinstance(item, str):
                assistant_utils.delete_assistant(
                    assistant_utils.get_assistant_by_name(item)
                )
            else:
                assistant_utils.delete_assistant_by_id(item.id)
        except Exception as e:
            logger.warning(f"Failed to delete cloned assistant {item}: {e}")


_WEB_SEARCH_COMPONENT_ID = "features:webSearch"


@pytest.fixture(scope="function")
def web_search_disabled(customer_config_utils):
    """Force features:webSearch to enabled=False for the duration of the test,
    then reset back to the YAML default in teardown."""
    customer_config_utils.save_setting(
        _WEB_SEARCH_COMPONENT_ID,
        get_web_search_settings_data(enabled=False).as_settings,
    )
    yield
    try:
        customer_config_utils.reset_setting(_WEB_SEARCH_COMPONENT_ID)
    except Exception as e:
        logger.warning(f"Failed to reset {_WEB_SEARCH_COMPONENT_ID} setting: {e}")


@pytest.fixture(scope="function")
def clean_marketplace_thresholds(customer_config_utils):
    """Guarantee no marketplaceThresholds override exists before the test and
    reset it again in teardown (the reset is idempotent)."""
    customer_config_utils.reset_setting(MARKETPLACE_THRESHOLDS_COMPONENT_ID)
    yield
    try:
        customer_config_utils.reset_setting(MARKETPLACE_THRESHOLDS_COMPONENT_ID)
    except Exception as e:
        logger.warning(
            f"Failed to reset {MARKETPLACE_THRESHOLDS_COMPONENT_ID} setting: {e}"
        )


@pytest.fixture(scope="session")
def marketplace_management_utils(client):
    return MarketplaceManagementUtils(client)


@pytest.fixture(scope="session")
def categories_utils(client):
    return CategoriesUtils(client)


@pytest.fixture(scope="session", autouse=True)
def ensure_test_project(admin_utils):
    """Ensure the test project exists before running tests"""
    logger.info(f"Ensuring test project '{PROJECT}' exists...")
    filtered_projects = admin_utils.list_projects(PROJECT)
    if PROJECT not in filtered_projects:
        admin_utils.create_project(PROJECT)
        logger.info(f"Created test project '{PROJECT}'.")
    logger.info(f"Test project '{PROJECT}' is ready.")


@pytest.fixture(scope="session")
def keycloak_utils(client):
    """Session-scoped user-lifecycle helper. Uses LocalUserUtils on localhost, KeycloakUtils elsewhere."""
    if EnvironmentResolver.is_localhost():
        return LocalUserUtils(client)
    return KeycloakUtils()


@pytest.fixture
def disposable_user(keycloak_utils):
    """Function-scoped fresh user; deleted automatically after each test.

    NOTE (localhost only): LocalUserUtils.create_test_user creates users with
    is_admin=True.  On localhost TC-010 may therefore receive HTTP 200 instead
    of 403, giving false assurance for the access-control scenario.
    """
    uid = secrets.token_hex(4)
    email = f"autotest_user_{uid}@email.com"
    password = keycloak_utils.create_test_user(email=email, project_name=email)
    try:
        user_client = get_client(username=email, password=password)
        user_id = user_client.users.about_me().user_id
    except Exception:
        try:
            keycloak_utils.delete_user(email)
        except Exception as e:
            logger.warning(f"Failed to delete user {email} after setup failure: {e}")
        raise
    yield email, user_id, user_client
    try:
        keycloak_utils.delete_user(email)
    except Exception as e:
        logger.warning(f"Failed to delete user {email}: {e}")


@pytest.fixture
def ordered_users(client, user_utils):
    """Factory: create the users of an OrderScenario with a per-run search token.

    Works on local-auth stands (admin API) and identity-provider stands (auth server plus a
    first login). Returns an OrderedUsers: the search token and the created users in their
    expected order. The users are removed after the test.
    """
    builder = OrderedUsersBuilder(client, user_utils)
    yield builder.create
    builder.delete_all()


@pytest.fixture
def promoted_admin_user(keycloak_utils, user_utils):
    uid = secrets.token_hex(4)
    email = f"autotest_admin_{uid}@email.com"
    password = keycloak_utils.create_test_user(email=email, project_name=email)
    user_client = get_client(username=email, password=password)
    user_id = user_client.users.about_me().user_id
    user_utils.update_admin_user(user_id, is_admin=True)
    yield email, user_id, user_client
    keycloak_utils.delete_user(email)


@pytest.fixture
def non_admin_user(keycloak_utils):
    """Function-scoped, genuinely non-privileged secondary user (developer
    role only, no admin/maintainer rights; "applications" attribute is
    exactly their own personal project), deleted after each test.

    Intentionally does NOT reuse `disposable_user`: that fixture is built via
    `keycloak_utils.create_test_user`, which grants the Keycloak "admin"
    realm role (see `KeycloakUtils.create_test_user`), so it is not
    genuinely non-privileged.
    """
    uid = secrets.token_hex(4)
    email = f"autotest_member_{uid}@email.com"
    password = keycloak_utils.create_platform_user(email=email)
    member_client = get_client(username=email, password=password)
    member_id = member_client.users.about_me().user_id
    yield email, member_id, member_client
    keycloak_utils.delete_user(email)


@pytest.fixture(scope="function")
def keycloak_regular_user(keycloak_utils):
    """Create a plain developer-role user with no admin or project-admin permissions."""
    uid = secrets.token_hex(4)
    email = f"autotest_regular_{uid}@email.com"
    password = keycloak_utils.create_platform_user(email=email)
    yield email, password
    keycloak_utils.delete_user(email)


@pytest.fixture(scope="session")
def user_utils(client):
    return UserUtils(client)


@pytest.fixture(scope="session")
def project_utils(client):
    return ProjectUtils(client)


@dataclass
class DefaultProjectMember:
    email: str
    user_id: str
    client: CodeMieClient
    personal_project: str
    project_a: str
    project_b: str


def _delete_projects_with_members(project_utils, project_names):
    for name in project_names:
        try:
            project_utils.delete_project_with_all_members(name)
        except Exception as e:
            logger.warning(f"Failed to delete project {name}: {e}")


@pytest.fixture
def default_project_member(
    request, non_admin_user, admin_utils, project_utils, user_utils
):
    """Plain user (no platform role) who owns a personal project and is a member of two extra projects."""
    email, user_id, member_client = non_admin_user
    project_names = []
    request.addfinalizer(
        lambda: _delete_projects_with_members(project_utils, project_names)
    )
    for _ in range(2):
        name = get_random_name()
        admin_utils.create_project(name)
        project_names.append(name)
        user_utils.assign_user_to_project(user_id, name)
    return DefaultProjectMember(
        email=email,
        user_id=user_id,
        client=member_client,
        personal_project=email,
        project_a=project_names[0],
        project_b=project_names[1],
    )


@pytest.fixture
def admin_client(promoted_admin_user):
    """Client of a user promoted to platform admin, once the role is active on all replicas."""
    client = promoted_admin_user[2]
    UserUtils(client).wait_until_user_management_effective()
    return client


@pytest.fixture
def maintainer_credentials(request, keycloak_utils, user_utils):
    """(email, password) of a user with the maintainer flag only (not a platform admin)."""
    email = f"autotest_maintainer_{secrets.token_hex(4)}@email.com"
    password = keycloak_utils.create_platform_user(email=email)
    request.addfinalizer(lambda: keycloak_utils.delete_user(email))
    client = get_client(username=email, password=password)
    user_utils.update_admin_user(client.users.about_me().user_id, is_maintainer=True)
    UserUtils(client).wait_until_user_management_effective()
    return email, password


@pytest.fixture
def maintainer_client(maintainer_credentials):
    email, password = maintainer_credentials
    return get_client(username=email, password=password)


@pytest.fixture
def project_admin_client(request, keycloak_utils, user_utils, default_project_member):
    """Plain user who is project admin of the member's project, but holds no platform role."""
    email = f"autotest_projadmin_{secrets.token_hex(4)}@email.com"
    password = keycloak_utils.create_platform_user(email=email)
    request.addfinalizer(lambda: keycloak_utils.delete_user(email))
    client = get_client(username=email, password=password)
    user_utils.assign_user_to_project(
        client.users.about_me().user_id,
        default_project_member.project_a,
        is_project_admin=True,
    )
    return client


@pytest.fixture
def unrelated_client(request, keycloak_utils):
    """Fresh plain user with no project membership beyond their own personal project."""
    email = f"autotest_unrelated_{secrets.token_hex(4)}@email.com"
    password = keycloak_utils.create_platform_user(email=email)
    request.addfinalizer(lambda: keycloak_utils.delete_user(email))
    return get_client(username=email, password=password)


def _module_user_client(keycloak_utils, user_utils, label, **role):
    """Generator body of the module-scoped sender fixtures: optional global role, deleted at the end."""
    email = f"autotest_{label}_{secrets.token_hex(4)}@email.com"
    password = keycloak_utils.create_platform_user(email=email)
    try:
        client = get_client(username=email, password=password)
        if role:
            user_utils.update_admin_user(client.users.about_me().user_id, **role)
            UserUtils(client).wait_until_user_management_effective()
        yield client
    finally:
        try:
            keycloak_utils.delete_user(email)
        except Exception as e:
            logger.warning(f"Failed to delete user {email}: {e}")


@pytest.fixture(scope="module")
def gate_admin_client(keycloak_utils, user_utils):
    """Module-scoped global admin (ingest senders must outlive a single test)."""
    yield from _module_user_client(
        keycloak_utils, user_utils, "gateadmin", is_admin=True
    )


@pytest.fixture(scope="module")
def gate_maintainer_client(keycloak_utils, user_utils):
    """Module-scoped user with the maintainer flag only."""
    yield from _module_user_client(
        keycloak_utils, user_utils, "gatemaint", is_maintainer=True
    )


@pytest.fixture(scope="module")
def gate_member_client(keycloak_utils, user_utils):
    """Module-scoped plain user (MB); gate_projects makes it a member of p_on and p_off."""
    yield from _module_user_client(keycloak_utils, user_utils, "gatemember")


@pytest.fixture(scope="module")
def gate_outsider_client(keycloak_utils, user_utils):
    """Module-scoped plain user with no membership in any gate project (NR)."""
    yield from _module_user_client(keycloak_utils, user_utils, "gateoutsider")


@pytest.fixture
def verified_maintainer_client(maintainer_credentials, user_utils):
    """Client of a user provisioned for this test through `create_platform_user` and promoted
    ONLY to maintainer (see `maintainer_credentials`), never a pre-existing manual account.
    Asserts the principal and the stored roles. Only the maintainer flag is set by the test; the
    backend's role normalization (UserManagementService._normalize_role_updates: a maintainer
    update sets is_admin to true, "maintainer implies admin") stores is_admin as true, so that is
    the expected stored state, not a second promotion."""
    email, password = maintainer_credentials
    client = get_client(username=email, password=password)
    assert_principal_is(client, email)
    assert_stored_roles(
        user_utils, client.users.about_me().user_id, is_maintainer=True, is_admin=True
    )
    return client


@pytest.fixture(scope="module")
def cli_auditor_credentials(request, keycloak_utils, user_utils):
    """Create one dedicated auditor per module/worker using the maintainer provisioning flow.

    Unlike function-scoped maintainer_credentials, this read/denial-only role is shared within
    a module to avoid creating one user per parametrized case. Each worker owns its account.
    The administrative harness account creates the user and assigns only the auditor flag.
    Register deletion before login/role setup so a setup failure also cleans up the user.
    Shared AUDITOR_* credentials and the existing shared account are never used or modified.
    """
    email = f"autotest_cliauditor_{secrets.token_hex(4)}@email.com"
    password = keycloak_utils.create_platform_user(email=email)
    request.addfinalizer(lambda: keycloak_utils.delete_user(email))
    client = get_client(username=email, password=password)
    user_utils.update_admin_user(client.users.about_me().user_id, is_auditor=True)
    wait_until_auditor_effective(client)
    return email, password


@pytest.fixture(scope="module")
def verified_auditor_client(cli_auditor_credentials):
    """Verified client of the freshly provisioned auditor, never a shared configured user."""
    username, password = cli_auditor_credentials
    client = get_client(username=username, password=password)
    assert_principal_is(client, username, not_admin=True)
    assert_auditor_without_admin_roles(client)
    return client


@pytest.fixture(scope="session")
def cost_center_utils(client):
    return CostCenterUtils(client)


@pytest.fixture(scope="function")
def cost_center(cost_center_utils):
    """Factory fixture that creates a cost center and yields its id, with auto-cleanup.

    Usage:
        def test_example(cost_center):
            cc_id = cost_center()
            # use cc_id ...

    Note: the id is tracked after create_cost_center() returns. If the HTTP POST
    succeeds server-side but the SDK raises before returning (e.g. unexpected response
    shape), the resource will not be tracked and cleanup will be skipped for that id.
    This is an inherent limitation of the SDK-first pattern; treat leaked cost centers
    as test-environment noise and clean them up manually if they accumulate.
    """
    from codemie_test_harness.tests.utils.cost_center_utils import (
        get_random_cost_center_name,
    )

    created_ids = []

    def _create_cost_center(name=None, description=None):
        if name is None:
            name = get_random_cost_center_name()
        response = cost_center_utils.create_cost_center(
            name=name,
            description=description,
        )
        cc_id = response.id
        created_ids.append(cc_id)
        return cc_id

    yield _create_cost_center

    for cc_id in created_ids:
        try:
            cost_center_utils.delete_cost_center(cc_id)
        except Exception as e:
            # A 404 means the cost center was already deleted (e.g. by a test that
            # explicitly soft-deletes it as part of its setup — such as TC-06).
            # Log at debug level only; a genuine delete failure is re-raised below.
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status == 404:
                logger.debug(
                    f"Cost center {cc_id} was already deleted before teardown (404): {e}"
                )
            else:
                logger.error(f"Failed to delete cost center {cc_id}: {e}")


@pytest.fixture(scope="function")
def cost_center_budget_projects(
    cost_center, project_utils, project_budget_groups, lite_llm_budget_utils
):
    """Creates budgeted projects linked to a cost center; removes them before the cost center.

    Usage:
        def test_example(cost_center, cost_center_budget_projects):
            cc_id = cost_center()
            budget = cost_center_budget_projects.create(cc_id, {"platform": {...}})
    """
    projects = CostCenterBudgetProjects(
        project_utils, project_budget_groups, lite_llm_budget_utils
    )
    yield projects
    projects.cleanup()


@pytest.fixture(scope="session")
def llm_utils(client):
    return LLMUtils(client)


@pytest.fixture(scope="session")
def conversation_utils(client):
    return ConversationUtils(client)


@pytest.fixture(scope="session")
def skill_utils(client):
    """Skill utilities fixture."""
    from codemie_test_harness.tests.utils.skill_utils import SkillsUtils

    return SkillsUtils(client)


@pytest.fixture(scope="session")
def analytics_utils(client):
    """Analytics utility fixture."""
    from codemie_test_harness.tests.utils.analytics_utils import AnalyticsUtils

    return AnalyticsUtils(client)


@pytest.fixture(scope="session")
def webhook_utils(client):
    return WebhookUtils(client)


@pytest.fixture(scope="session")
def swagger_utils(client):
    return SwaggerUtils(client)


@pytest.fixture(scope="session")
def proxy_utils(client):
    from codemie_test_harness.tests.utils.proxy_utils import ProxyUtils

    return ProxyUtils(client)


@pytest.fixture(scope="session")
def gitlab_integration(
    integration_utils, gitlab_seed_merge_request, gitlab_seed_branches
):
    integration = integration_utils.create_integration(
        credential_type=CredentialTypes.GIT,
        credential_values=CredentialsManager.gitlab_credentials(),
    )
    yield integration
    if integration:
        integration_utils.delete_integration(integration)


@pytest.fixture(scope="session")
def invalid_gitlab_integration(integration_utils):
    integration = integration_utils.create_integration(
        credential_type=CredentialTypes.GIT,
        credential_values=CredentialsManager.invalid_gitlab_credentials(),
    )
    yield integration
    if integration:
        integration_utils.delete_integration(integration)


@pytest.fixture(scope="session")
def github_integration(integration_utils, github_seed_issue, github_seed_file):
    integration = integration_utils.create_integration(
        credential_type=CredentialTypes.GIT,
        credential_values=CredentialsManager.github_credentials(),
    )
    yield integration
    if integration:
        integration_utils.delete_integration(integration)


@pytest.fixture(scope="session")
def github_pat_integration(integration_utils, github_seed_file):
    integration = integration_utils.create_integration(
        credential_type=CredentialTypes.GIT,
        credential_values=CredentialsManager.github_pat_credentials(),
    )
    yield integration
    if integration:
        integration_utils.delete_integration(integration)


@pytest.fixture(scope="session")
def github_app_integration(integration_utils, github_seed_file):
    integration = integration_utils.create_integration(
        credential_type=CredentialTypes.GIT,
        credential_values=CredentialsManager.github_app_credentials(),
    )
    yield integration
    if integration:
        integration_utils.delete_integration(integration)


def _seed_lock_dir(tmp_path_factory) -> Optional[Path]:
    """Directory shared by all xdist workers of this run; None without xdist."""
    if os.environ.get("PYTEST_XDIST_WORKER") is None:
        return None
    return tmp_path_factory.getbasetemp().parent


def _jira_seed(tmp_path_factory, is_cloud: bool) -> SeedIssue:
    name = "jira_seed_cloud" if is_cloud else "jira_seed_server"
    data = resolve_shared(
        _seed_lock_dir(tmp_path_factory),
        name,
        lambda: JiraUtils(is_cloud=is_cloud).ensure_seed_issue().to_dict(),
    )
    return SeedIssue.from_dict(data)


@pytest.fixture(scope="session")
def jira_seed_issue(tmp_path_factory) -> SeedIssue:
    return _jira_seed(tmp_path_factory, is_cloud=False)


@pytest.fixture(scope="session")
def jira_cloud_seed_issue(tmp_path_factory) -> SeedIssue:
    return _jira_seed(tmp_path_factory, is_cloud=True)


def _confluence_seed(tmp_path_factory, is_cloud: bool) -> SeedPage:
    name = "confluence_seed_cloud" if is_cloud else "confluence_seed_server"
    data = resolve_shared(
        _seed_lock_dir(tmp_path_factory),
        name,
        lambda: ConfluenceUtils(is_cloud=is_cloud).ensure_seed_page().to_dict(),
    )
    return SeedPage.from_dict(data)


@pytest.fixture(scope="session")
def confluence_seed_page(tmp_path_factory) -> SeedPage:
    return _confluence_seed(tmp_path_factory, is_cloud=False)


@pytest.fixture(scope="session")
def confluence_cloud_seed_page(tmp_path_factory) -> SeedPage:
    return _confluence_seed(tmp_path_factory, is_cloud=True)


def _ado_seed(tmp_path_factory) -> AdoSeed:
    data = resolve_shared(
        _seed_lock_dir(tmp_path_factory),
        "ado_seed",
        lambda: AdoUtils().ensure_seed().to_dict(),
    )
    return AdoSeed.from_dict(data)


@pytest.fixture(scope="session")
def ado_seed(tmp_path_factory) -> AdoSeed:
    """Azure DevOps work items and wiki pages the ADO tests read from."""
    return _ado_seed(tmp_path_factory)


@pytest.fixture(scope="session")
def ado_test_plan_seed(tmp_path_factory) -> SeedTestPlan:
    """Azure DevOps test plan the ADO test plan tests read from."""
    data = resolve_shared(
        _seed_lock_dir(tmp_path_factory),
        "ado_test_plan_seed",
        lambda: AdoUtils().ensure_test_plan().to_dict(),
    )
    return SeedTestPlan.from_dict(data)


def _github_seed(tmp_path_factory) -> GitHubSeedIssue:
    data = resolve_shared(
        _seed_lock_dir(tmp_path_factory),
        "github_seed_issue",
        lambda: GitHubUtils().ensure_seed_issue().to_dict(),
    )
    return GitHubSeedIssue.from_dict(data)


@pytest.fixture(scope="session")
def github_seed_issue(tmp_path_factory) -> GitHubSeedIssue:
    return _github_seed(tmp_path_factory)


def _github_seed_file(tmp_path_factory) -> GitHubSeedFile:
    data = resolve_shared(
        _seed_lock_dir(tmp_path_factory),
        "github_seed_file",
        lambda: GitHubUtils().ensure_seed_file().to_dict(),
    )
    return GitHubSeedFile.from_dict(data)


@pytest.fixture(scope="session")
def github_seed_file(tmp_path_factory) -> GitHubSeedFile:
    """Marker file the harness commits to the GitHub repo's default branch."""
    return _github_seed_file(tmp_path_factory)


def _servicenow_seed(tmp_path_factory) -> SeedIncident:
    data = resolve_shared(
        _seed_lock_dir(tmp_path_factory),
        "servicenow_seed_incident",
        lambda: ServiceNowUtils().ensure_seed_incident().to_dict(),
    )
    return SeedIncident.from_dict(data)


@pytest.fixture(scope="session")
def servicenow_seed_incident(tmp_path_factory) -> SeedIncident:
    """ServiceNow incident the ServiceNow tests read from."""
    return _servicenow_seed(tmp_path_factory)


def _gitlab_seed(tmp_path_factory) -> SeedMergeRequest:
    data = resolve_shared(
        _seed_lock_dir(tmp_path_factory),
        "gitlab_seed_merge_request",
        lambda: GitBudUtils().ensure_seed_merge_request().to_dict(),
    )
    return SeedMergeRequest.from_dict(data)


@pytest.fixture(scope="session")
def gitlab_seed_merge_request(tmp_path_factory) -> SeedMergeRequest:
    return _gitlab_seed(tmp_path_factory)


def _gitlab_seed_branches(tmp_path_factory) -> SeedBranches:
    data = resolve_shared(
        _seed_lock_dir(tmp_path_factory),
        "gitlab_seed_branches",
        lambda: GitBudUtils().ensure_seed_branches().to_dict(),
    )
    return SeedBranches.from_dict(data)


@pytest.fixture(scope="session")
def gitlab_seed_branches(tmp_path_factory) -> SeedBranches:
    """Deterministically-named branches the GitLab branch-listing tests read from."""
    return _gitlab_seed_branches(tmp_path_factory)


def _gitlab_image_upload(
    tmp_path_factory, name: str, filename: str, build_data
) -> SeedImageUpload:
    data = resolve_shared(
        _seed_lock_dir(tmp_path_factory),
        name,
        lambda: GitBudUtils().upload_image(filename, build_data()).to_dict(),
    )
    return SeedImageUpload.from_dict(data)


@pytest.fixture(scope="session")
def gitlab_image_upload(tmp_path_factory) -> SeedImageUpload:
    """A genuine PNG (test.jpg re-encoded) uploaded to the GitLab project."""
    return _gitlab_image_upload(
        tmp_path_factory,
        GITLAB_SEED_IMAGE_UPLOAD,
        SEED_IMAGE_UPLOAD_NAME,
        lambda: png_bytes_from_image((FILES_PATH / "test.jpg").read_bytes()),
    )


@pytest.fixture(scope="session")
def gitlab_fake_png_upload(tmp_path_factory) -> SeedImageUpload:
    """A plain text file served under a .png name, uploaded to the GitLab project."""
    return _gitlab_image_upload(
        tmp_path_factory,
        GITLAB_SEED_FAKE_PNG_UPLOAD,
        SEED_FAKE_PNG_UPLOAD_NAME,
        lambda: (FILES_PATH / "invalid_image.txt").read_bytes(),
    )


def _azure_devops_seed(tmp_path_factory) -> SeedPullRequest:
    data = resolve_shared(
        _seed_lock_dir(tmp_path_factory),
        "azure_devops_seed_pull_request",
        lambda: AzureDevOpsUtils().ensure_seed_pull_request().to_dict(),
    )
    return SeedPullRequest.from_dict(data)


@pytest.fixture(scope="session")
def azure_devops_seed_pull_request(tmp_path_factory) -> SeedPullRequest:
    return _azure_devops_seed(tmp_path_factory)


@pytest.fixture(scope="session")
def report_portal_seed_launch(tmp_path_factory) -> SeedLaunch:
    data = resolve_shared(
        _seed_lock_dir(tmp_path_factory),
        "report_portal_seed_launch",
        lambda: ReportPortalUtils().ensure_seed_launch().to_dict(),
    )
    return SeedLaunch.from_dict(data)


@pytest.fixture(scope="session")
def xwiki_seed_page(tmp_path_factory) -> XWikiSeedPage:
    """xWiki seed page with a known token, written to the configured XWIKI_SPACE."""
    data = resolve_shared(
        _seed_lock_dir(tmp_path_factory),
        "xwiki_seed_page",
        lambda: XWikiUtils().ensure_seed_page().to_dict(),
    )
    return XWikiSeedPage.from_dict(data)


@pytest.fixture(scope="session")
def influxdb_seed_point(tmp_path_factory) -> InfluxDBSeedPoint:
    """InfluxDB point written fresh into codemie_harness_seed on every run."""
    data = resolve_shared(
        _seed_lock_dir(tmp_path_factory),
        "influxdb_seed_point",
        lambda: InfluxDBUtils().ensure_seed().to_dict(),
    )
    return InfluxDBSeedPoint.from_dict(data)


@pytest.fixture(scope="session")
def report_portal_seed_dashboard(tmp_path_factory) -> SeedDashboard:
    data = resolve_shared(
        _seed_lock_dir(tmp_path_factory),
        "report_portal_seed_dashboard",
        lambda: ReportPortalUtils().ensure_seed_dashboard().to_dict(),
    )
    return SeedDashboard.from_dict(data)


@pytest.fixture(scope="session")
def keycloak_seed_user(tmp_path_factory) -> KeycloakSeedUser:
    data = resolve_shared(
        _seed_lock_dir(tmp_path_factory),
        "keycloak_seed_user",
        lambda: KeycloakUtils().ensure_seed().to_dict(),
    )
    return KeycloakSeedUser.from_dict(data)


@pytest.fixture(scope="session")
def aws_seed_bucket(tmp_path_factory) -> SeedAwsBucket:
    """Existing S3 bucket the AWS cloud tool tests assert on (read-only)."""
    data = resolve_shared(
        _seed_lock_dir(tmp_path_factory),
        "aws_seed_bucket",
        lambda: AwsUtils().get_seed_bucket().to_dict(),
    )
    return SeedAwsBucket.from_dict(data)


@pytest.fixture(scope="session")
def gcp_seed_bucket(tmp_path_factory) -> SeedGcpBucket:
    """Existing Cloud Storage bucket the GCP cloud tool tests assert on (read-only)."""
    data = resolve_shared(
        _seed_lock_dir(tmp_path_factory),
        "gcp_seed_bucket",
        lambda: GcpUtils().get_seed_bucket().to_dict(),
    )
    return SeedGcpBucket.from_dict(data)


@pytest.fixture(scope="session")
def kubernetes_seed_service(tmp_path_factory) -> SeedKubernetesService:
    """Existing Kubernetes service the Kubernetes cloud tool tests assert on (read-only)."""
    data = resolve_shared(
        _seed_lock_dir(tmp_path_factory),
        "kubernetes_seed_service",
        lambda: KubernetesUtils().get_seed_service().to_dict(),
    )
    return SeedKubernetesService.from_dict(data)


@pytest.fixture(scope="session")
def azure_seed_resource_group(tmp_path_factory) -> SeedAzureResourceGroup:
    """Existing Azure resource group the Azure cloud tool tests assert on (read-only)."""
    data = resolve_shared(
        _seed_lock_dir(tmp_path_factory),
        "azure_seed_resource_group",
        lambda: AzureUtils().get_seed_resource_group().to_dict(),
    )
    return SeedAzureResourceGroup.from_dict(data)


@pytest.fixture
def seeded(request):
    """Resolve Seeded test data (prompts/responses tied to seeded resources)."""
    """Resolve Seeded test data (prompts/responses tied to a Jira, Confluence, ADO or cloud seed)."""
    return lambda value: resolve_seeded(value, request.getfixturevalue)


@pytest.fixture(scope="function")
def jira_integration(integration_utils, jira_seed_issue):
    integration = integration_utils.create_integration(
        credential_type=CredentialTypes.JIRA,
        credential_values=CredentialsManager.jira_credentials(),
    )
    yield integration
    if integration:
        integration_utils.delete_integration(integration)


@pytest.fixture(scope="function")
def jira_cloud_integration(integration_utils, jira_cloud_seed_issue):
    integration = integration_utils.create_integration(
        credential_type=CredentialTypes.JIRA,
        credential_values=CredentialsManager.jira_cloud_credentials(),
    )
    yield integration
    if integration:
        integration_utils.delete_integration(integration)


@pytest.fixture(scope="function")
def confluence_integration(integration_utils, confluence_seed_page):
    integration = integration_utils.create_integration(
        credential_type=CredentialTypes.CONFLUENCE,
        credential_values=CredentialsManager.confluence_credentials(),
    )
    yield integration
    if integration:
        integration_utils.delete_integration(integration)


@pytest.fixture(scope="function")
def xwiki_integration(integration_utils):
    integration = integration_utils.create_integration(
        credential_type=CredentialTypes.XWIKI,
        credential_values=CredentialsManager.xwiki_basic_credentials(),
    )
    yield integration
    if integration:
        integration_utils.delete_integration(integration)


@pytest.fixture(scope="function")
def xwiki_invalid_url_integration(integration_utils):
    """xWiki integration configured with a mismatched base URL (missing /xwiki
    prefix), for base-URL-mismatch health-check testing (see xwiki_loader.py's
    _BASE_URL_HINT)."""
    integration = integration_utils.create_integration(
        credential_type=CredentialTypes.XWIKI,
        credential_values=CredentialsManager.invalid_xwiki_url_credentials(),
    )
    yield integration
    if integration:
        integration_utils.delete_integration(integration)


@pytest.fixture(scope="function")
def xwiki_basic_integration(integration_utils):
    """xWiki integration configured for Basic Auth (username/password) — the
    alternative credential path to xwiki_integration's Bearer token."""
    integration = integration_utils.create_integration(
        credential_type=CredentialTypes.XWIKI,
        credential_values=CredentialsManager.xwiki_basic_credentials(),
    )
    yield integration
    if integration:
        integration_utils.delete_integration(integration)


@pytest.fixture(scope="function")
def confluence_cloud_integration(integration_utils, confluence_cloud_seed_page):
    integration = integration_utils.create_integration(
        credential_type=CredentialTypes.CONFLUENCE,
        credential_values=CredentialsManager.confluence_cloud_credentials(),
    )
    yield integration
    if integration:
        integration_utils.delete_integration(integration)


@pytest.fixture(scope="function")
def google_integration(integration_utils):
    integration = integration_utils.create_user_integration(
        credential_type=CredentialTypes.GOOGLE_OAUTH,
        credentials=CredentialsManager.google_oauth_credentials(),
    )
    yield integration
    if integration:
        integration_utils.delete_integration(integration)


@pytest.fixture(scope="module")
def filesystem_integration(integration_utils):
    """Create Filesystem integration"""
    integration = integration_utils.create_integration(
        credential_type=CredentialTypes.FILESYSTEM,
        credential_values=CredentialsManager.file_system_credentials(),
    )
    yield integration
    if integration:
        integration_utils.delete_integration(integration)


@pytest.fixture(scope="module")
def open_api_integration(client, integration_utils):
    credential_values = CredentialsManager.open_api_credentials(str(client.token))
    integration = integration_utils.create_integration(
        CredentialTypes.OPENAPI, credential_values
    )
    yield integration
    if integration:
        integration_utils.delete_integration(integration)


@pytest.fixture(scope="module")
def email_integration(integration_utils):
    credential_values = CredentialsManager.gmail_credentials()
    integration = integration_utils.create_integration(
        CredentialTypes.EMAIL, credential_values
    )
    yield integration
    if integration:
        integration_utils.delete_integration(integration)


@pytest.fixture(scope="module")
def azure_email_integration(integration_utils):
    credential_values = CredentialsManager.azure_email_credentials()
    integration = integration_utils.create_integration(
        CredentialTypes.EMAIL, credential_values
    )
    yield integration
    if integration:
        integration_utils.delete_integration(integration)


@pytest.fixture(scope="module")
def telegram_integration(integration_utils):
    credential_values = CredentialsManager.telegram_credentials()
    integration = integration_utils.create_integration(
        CredentialTypes.TELEGRAM, credential_values
    )
    yield integration
    if integration:
        integration_utils.delete_integration(integration)


@pytest.fixture(scope="module")
def service_now_integration(integration_utils):
    credential_values = CredentialsManager.servicenow_credentials()
    integration = integration_utils.create_integration(
        CredentialTypes.SERVICE_NOW, credential_values
    )
    yield integration
    if integration:
        integration_utils.delete_integration(integration)


@pytest.fixture(scope="module")
def keycloak_integration(integration_utils, keycloak_seed_user):
    credential_values = CredentialsManager.keycloak_credentials()
    integration = integration_utils.create_integration(
        CredentialTypes.KEYCLOAK, credential_values
    )
    yield integration
    if integration:
        integration_utils.delete_integration(integration)


@pytest.fixture(scope="module")
def lite_llm_integration(integration_utils):
    """Create LiteLLM integration for proxy endpoint tests."""
    credential_values = CredentialsManager.lite_llm_credentials()
    integration = integration_utils.create_integration(
        CredentialTypes.LITE_LLM, credential_values
    )
    yield integration
    if integration:
        integration_utils.delete_integration(integration)


@pytest.fixture(scope="module")
def report_portal_integration(
    integration_utils, report_portal_seed_launch, report_portal_seed_dashboard
):
    credential_values = CredentialsManager.report_portal_credentials()
    integration = integration_utils.create_integration(
        CredentialTypes.REPORT_PORTAL, credential_values
    )
    yield integration
    if integration:
        integration_utils.delete_integration(integration)


@pytest.fixture(scope="function")
def github_mcp_integration(integration_utils, github_seed_issue):
    """Create GitHub MCP Server integration."""
    credential_values = CredentialsManager.mcp_github_credentials()
    _integration = integration_utils.create_integration(
        CredentialTypes.MCP, credential_values
    )
    yield _integration
    if _integration:
        integration_utils.delete_integration(_integration)


@pytest.fixture(scope="function")
def mcp_postgres_integration(integration_utils):
    """Create PostgreSQL MCP Server integration."""
    credential_values = CredentialsManager.mcp_postgres_credentials()
    _integration = integration_utils.create_integration(
        CredentialTypes.MCP, credential_values
    )
    yield _integration
    if _integration:
        integration_utils.delete_integration(_integration)


@pytest.fixture(scope="module")
def webhook_integration(integration_utils):
    created_integrations = []

    def _create(
        webhook_id,
        resource_type,
        resource_id,
        is_enabled: bool = True,
        project_name: str = None,
        extra_credentials: dict = None,
    ):
        credential_values = [
            CredentialValues(key="url", value=CredentialsManager.AUTO_GENERATED),
            CredentialValues(key="webhook_id", value=webhook_id),
            CredentialValues(key="is_enabled", value=is_enabled),
            CredentialValues(key="resource_type", value=resource_type),
            CredentialValues(key="resource_id", value=resource_id),
        ]
        for key, value in (extra_credentials or {}).items():
            credential_values.append(CredentialValues(key=key, value=value))
        integration = integration_utils.create_integration(
            CredentialTypes.WEBHOOK, credential_values, project_name=project_name
        )
        created_integrations.append(integration)
        return integration

    yield _create

    for integration in created_integrations:
        try:
            integration_utils.delete_integration(integration)
        except HTTPError:
            pass


@pytest.fixture(scope="module")
def scheduler_integration(integration_utils):
    created_integrations = []

    def _create(
        alias,
        resource_type,
        resource_id,
        prompt: str = None,
        schedule: str = None,
        is_enabled: bool = True,
        timezone: str = None,
    ):
        # If schedule is not provided, calculate cron for every hour starting at current time + 1 minute
        if schedule is None:
            next_minute = (datetime.now() + timedelta(minutes=2)).minute
            schedule = f"{next_minute} * * * *"  # every hour at the specified minute

        credential_values = [
            CredentialValues(key="url", value=CredentialsManager.AUTO_GENERATED),
            CredentialValues(key="is_enabled", value=is_enabled),
            CredentialValues(key="schedule", value=schedule),
            CredentialValues(key="resource_type", value=resource_type),
            CredentialValues(key="resource_id", value=resource_id),
            CredentialValues(key="prompt", value=prompt),
        ]
        if timezone is not None:
            credential_values.append(CredentialValues(key="timezone", value=timezone))
        integration = integration_utils.create_integration(
            CredentialTypes.SCHEDULER, credential_values, integration_alias=alias
        )
        created_integrations.append(integration)
        return integration

    yield _create

    for integration in created_integrations:
        try:
            integration_utils.delete_integration(integration)
        except HTTPError:
            pass


@pytest.fixture(scope="function")
def general_integration(integration_utils):
    created_integration: Optional[Integration] = None

    def _create_integration(
        integration_type: IntegrationType,
        credential_type: CredentialTypes,
        credential_values: List[CredentialValues],
        integration_alias: str = None,
        project_name: str = None,
        is_global: bool = False,
    ):
        nonlocal created_integration
        created_integration = integration_utils.create_integration(
            setting_type=integration_type,
            credential_type=credential_type,
            credential_values=credential_values,
            integration_alias=integration_alias,
            project_name=project_name,
            is_global=is_global,
        )
        return created_integration

    yield _create_integration
    if created_integration is None:
        return
    try:
        integration_utils.delete_integration(created_integration)
    except HTTPError:
        pass


@pytest.fixture(scope="session")
def code_datasource(
    datasource_utils, gitlab_integration, github_integration, default_embedding_llm
):
    git_env = CredentialsManager.get_parameter("GIT_ENV", "gitlab")
    datasource = datasource_utils.create_code_datasource(
        link=CredentialsManager.get_parameter("GITLAB_PROJECT")
        if git_env == "gitlab"
        else CredentialsManager.get_parameter("GITHUB_PROJECT"),
        branch="main",
        embeddings_model=default_embedding_llm.base_name,
        setting_id=gitlab_integration.id
        if git_env == "gitlab"
        else github_integration.id,
    )
    yield datasource
    if datasource:
        datasource_utils.delete_datasource(datasource)


@pytest.fixture(scope="session")
def file_datasource(datasource_utils, default_embedding_llm):
    file_name = file_test_data[2][0]

    datasource = datasource_utils.create_file_datasource(
        name=get_random_name(),
        description=f"[Autotest] {file_name} with {default_embedding_llm.base_name} embedding model",
        files=[str(FILES_PATH / file_name)],
        embeddings_model=default_embedding_llm.base_name,
    )
    yield datasource
    if datasource:
        datasource_utils.delete_datasource(datasource)


@pytest.fixture(scope="session")
def gitlab_datasource(datasource_utils, gitlab_integration, default_embedding_llm):
    datasource = datasource_utils.create_gitlab_datasource(
        setting_id=gitlab_integration.id,
        embeddings_model=default_embedding_llm.base_name,
    )
    yield datasource
    if datasource:
        datasource_utils.delete_datasource(datasource)


@pytest.fixture(scope="session")
def invalid_gitlab_datasource(
    datasource_utils, invalid_gitlab_integration, default_embedding_llm, client
):
    datasource_name = get_random_name()
    try:
        datasource = datasource_utils.create_gitlab_datasource(
            name=datasource_name,
            setting_id=invalid_gitlab_integration.id,
            embeddings_model=default_embedding_llm.base_name,
        )
    except Exception as e:
        logger.warning(f"Datasource creation failed as expected: {e}")
        datasource = wait_for_entity(
            lambda: client.datasources.list(per_page=200),
            entity_name=datasource_name,
        )
    yield datasource

    if datasource:
        try:
            datasource_utils.delete_datasource(datasource)
        except Exception as e:
            logger.warning(f"Failed to delete invalid GitLab datasource: {e}")


@pytest.fixture(scope="session")
def github_datasource(datasource_utils, github_integration, default_embedding_llm):
    datasource = datasource_utils.create_github_datasource(
        setting_id=github_integration.id,
        embeddings_model=default_embedding_llm.base_name,
    )
    yield datasource
    if datasource:
        datasource_utils.delete_datasource(datasource)


@pytest.fixture(scope="session")
def code_context():
    """Create code context"""

    def _create_code_context(datasource: DataSource):
        return Context(name=datasource.name, context_type=ContextType.CODE)

    return _create_code_context


@pytest.fixture(scope="session")
def kb_context():
    """Create KB context"""

    def _create_kb_context(datasource: DataSource):
        return Context(name=datasource.name, context_type=ContextType.KNOWLEDGE_BASE)

    return _create_kb_context


@pytest.fixture(scope="session")
def provider_context():
    """Create provider context"""

    def _create_provider_context(datasource: DataSource):
        return Context(name=datasource.name, context_type=ContextType.PROVIDER)

    return _create_provider_context


@pytest.fixture(scope="function")
def assistant(default_llm, assistant_utils):
    """Create assistant"""
    created_assistant = None

    def _create_assistant(
        toolkit: str = None,
        *tool_names: str,
        settings=None,
        context=None,
        mcp_server=None,
        project_name: str = None,
        description: str = None,
        system_prompt=COMMON_ASSISTANT_SYSTEM_PROMPT,
        sub_assistants_ids: List[str] = None,
        categories: List[str] = None,
        conversation_starters: List[str] = None,
        assistant_name: str = None,
        tool_permissions: ToolPermissionsConfig | None = None,
    ):
        nonlocal created_assistant
        # Correctly handle empty `tool_names`
        if tool_names:  # Ensure `tool_names` is not empty
            tool_names = tool_names[0] if isinstance(tool_names, tuple) else tool_names
            toolkits = [
                ToolKitDetails(
                    toolkit=toolkit,
                    tools=[
                        ToolDetails(name=tool, settings=settings) for tool in tool_names
                    ]
                    if isinstance(tool_names, tuple)
                    else [ToolDetails(name=tool_names, settings=settings)],
                    settings=settings,
                )
            ]
        else:
            toolkits = []  # Assign an empty list if no tool_names provided

        created_assistant = assistant_utils.create_assistant(
            llm_model_type=default_llm.base_name,
            toolkits=toolkits,
            context=[context] if context else [],
            mcp_servers=[mcp_server] if mcp_server else [],
            system_prompt=system_prompt,
            project_name=project_name,
            description=description,
            assistant_ids=sub_assistants_ids if sub_assistants_ids else [],
            categories=categories if categories else [],
            conversation_starters=conversation_starters
            if conversation_starters
            else [],
            assistant_name=assistant_name,
            tool_permissions=tool_permissions,
        )
        return created_assistant

    yield _create_assistant
    if created_assistant:
        assistant_utils.delete_assistant(created_assistant)


@pytest.fixture(scope="function")
def assistant_factory(assistant_utils):
    """Create assistants for tests with automatic cleanup.

    This fixture tracks all assistants created during a test and cleans them up
    automatically, including their conversations.

    Usage:
        def test_something(assistant_factory):
            assistant1 = assistant_factory.create(model_type="gpt-4", temperature=0.5)
            assistant2 = assistant_factory.create(model_type="claude-3")
            # Test logic...
            # Cleanup happens automatically after test completes
    """
    created_assistants = []

    class AssistantFactory:
        @staticmethod
        def create(*args, **kwargs):
            """Create an assistant and track it for cleanup."""
            _assistant = assistant_utils.create_assistant(*args, **kwargs)
            created_assistants.append(_assistant)
            return _assistant

    yield AssistantFactory()

    # Cleanup all created assistants (delete_assistant also cleans up their conversations)
    for assistant in created_assistants:
        try:
            assistant_utils.delete_assistant(assistant)
        except Exception as e:
            logger.error(f"Failed to delete assistant {assistant.name}: {e}")


@pytest.fixture(scope="function")
def skill(skill_utils):
    """Factory fixture for creating skills with automatic cleanup.

    All parameters are optional. Defaults are provided by skill_utils.create_skill()
    using constants from test_data.skill_test_data.
    """
    created_skill = None

    def _create_skill(
        skill_name=None,
        description=None,
        content=None,
        visibility=None,
        categories=None,
    ):
        nonlocal created_skill
        from codemie_sdk.models.skill import SkillVisibility

        created_skill = skill_utils.create_skill(
            skill_name=skill_name,
            description=description,
            content=content,
            visibility=visibility or SkillVisibility.PROJECT,
            categories=categories,
        )
        return created_skill

    yield _create_skill

    # Cleanup
    if created_skill:
        try:
            skill_utils.delete_skill(created_skill)
        except Exception as e:
            logger.error(f"Failed to delete skill: {e}")


@pytest.fixture(scope="function")
def project(project_utils):
    """Factory fixture for creating projects with automatic cleanup.

    Usage:
        def test_example(project):
            # Create default project
            my_project = project()

            # Or create with custom parameters
            custom_project = project(name="custom-name", description="custom desc")
    """
    from codemie_test_harness.tests.test_data.projects_test_data import (
        get_project_create_data,
    )

    created_projects = []

    def _create_project(
        name=None, description=None, cost_center_id=None, display_name=None
    ):
        if name is None or description is None:
            project_data = get_project_create_data()
            name = name or project_data["name"]
            description = description or project_data["description"]

        project = project_utils.create_project(
            name=name,
            description=description,
            cost_center_id=cost_center_id,
            display_name=display_name,
        )
        created_projects.append(project)
        return project

    yield _create_project

    # Cleanup all created projects
    for proj in created_projects:
        try:
            project_utils.delete_project_cascade(proj.name)
        except Exception as e:
            logger.error(f"Failed to delete project {proj.name}: {e}")


@pytest.fixture(scope="function")
def ownership_project(project, project_utils):
    """Shared project owned by the admin client, safe to hand over to another user.

    Cascade cleanup of ``project`` only works while the creator is the owner, so the
    teardown gives ownership back before the cascade runs. Request the user fixtures a
    test needs (``non_admin_user`` ...) before this one so those users outlive the
    project teardown and can still be unassigned from it.
    """
    created = project()
    yield created
    try:
        project_utils.transfer_ownership(created.name, created.created_by)
    except Exception as e:
        logger.warning(f"Failed to restore ownership of project {created.name}: {e}")


@pytest.fixture(scope="function")
def workflow(workflow_utils):
    created_workflow: Optional[Workflow] = None

    def _create_workflow(
        workflow_name=None,
        tool_model=None,
        assistant_model=None,
        state_model=None,
        project_name=None,
        description=None,
    ):
        workflow_name = workflow_name if workflow_name else get_random_name()

        workflow_yaml = WorkflowYamlModel(
            tools=[tool_model] if tool_model else [],
            assistants=[assistant_model] if assistant_model else [],
            states=[state_model],
        )

        yaml_content = prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))

        nonlocal created_workflow
        created_workflow = workflow_utils.create_workflow(
            workflow_name=workflow_name,
            workflow_type=WorkflowMode.SEQUENTIAL,
            description=description,
            shared=True,
            workflow_yaml=yaml_content,
            project_name=project_name,
        )
        return created_workflow

    yield _create_workflow
    if created_workflow:
        workflow_utils.delete_workflow(created_workflow)


@pytest.fixture(scope="function")
def workflow_with_virtual_assistant(workflow, default_llm):
    """Create workflow with virtual assistant"""

    def _create_workflow(
        assistant_and_state_name,
        tool_names=None,
        integration=None,
        system_prompt=COMMON_ASSISTANT_SYSTEM_PROMPT,
        task=None,
        mcp_servers=None,
        datasource_ids=None,
        project_name=None,
        skill_ids=None,
    ):
        # Normalize tool_names to a tuple; allow None or single or tuple
        if tool_names is None:
            tool_names_tuple = ()
        elif isinstance(tool_names, tuple):
            tool_names_tuple = tool_names
        else:
            tool_names_tuple = (tool_names,)

        tools_list = [
            ToolModel(
                name=tool_enum.value,
                integration_alias=integration.alias if integration else None,
            )
            for tool_enum in tool_names_tuple
        ]

        assistant = AssistantModel(
            id=assistant_and_state_name,
            model=default_llm.base_name,
            system_prompt=system_prompt,
            datasource_ids=datasource_ids,
            skill_ids=skill_ids,
            tools=tools_list,
            mcp_servers=mcp_servers,
        )

        state = StateModel(
            id=assistant_and_state_name,
            assistant_id=assistant_and_state_name,
            task=task,
        )

        return workflow(
            assistant_model=assistant, state_model=state, project_name=project_name
        )

    return _create_workflow


@pytest.fixture(scope="function")
def workflow_with_assistant(workflow, default_llm):
    """Create workflow with specific assistant id"""

    def _create_workflow(assistant, prompt):
        assistant_model = AssistantModel(
            id=assistant.name,
            model=default_llm.base_name,
            assistant_id=assistant.id,
        )
        state_model = StateModel(
            id=assistant.name,
            assistant_id=assistant.name,
            task=prompt,
        )

        return workflow(assistant_model=assistant_model, state_model=state_model)

    return _create_workflow


@pytest.fixture(scope="function")
def workflow_with_tool(workflow):
    """Create workflow with tool"""

    def _create_workflow(
        tool_and_state_name,
        tool_name,
        tool_args=None,
        integration=None,
        datasource_ids=None,
        project_name=None,
    ):
        state_model = StateModel(id=tool_and_state_name, tool_id=tool_and_state_name)

        tool_model = ToolModel(
            id=tool_and_state_name,
            tool=tool_name.value,
            integration_alias=integration.alias if integration else None,
            tool_args=tool_args,
            datasource_ids=datasource_ids,
        )

        return workflow(
            tool_model=tool_model, state_model=state_model, project_name=project_name
        )

    return _create_workflow


@pytest.fixture(scope="function")
def jira_datasource(datasource_utils, jira_integration, jira_seed_issue):
    datasource = datasource_utils.create_jira_datasource(
        setting_id=jira_integration.id, jql=jira_seed_issue.jql
    )
    yield datasource
    if datasource:
        datasource_utils.delete_datasource(datasource)


@pytest.fixture(scope="function")
def google_doc_datasource(datasource_utils, google_integration):
    datasource = datasource_utils.create_google_doc_datasource(
        google_doc=get_google_doc_url(), setting_id=google_integration.id
    )
    yield datasource
    if datasource:
        datasource_utils.delete_datasource(datasource)


@pytest.fixture(scope="function")
def confluence_datasource(datasource_utils, confluence_integration):
    datasource = datasource_utils.create_confluence_datasource(
        setting_id=confluence_integration.id
    )
    yield datasource
    if datasource:
        datasource_utils.delete_datasource(datasource)


@pytest.fixture(scope="function")
def ado_wiki_datasource(datasource_utils, ado_integration):
    """Create an Azure DevOps Wiki datasource for testing."""
    datasource = datasource_utils.create_azure_devops_wiki_datasource(
        setting_id=ado_integration.id
    )
    yield datasource
    if datasource:
        datasource_utils.delete_datasource(datasource)


@pytest.fixture(scope="function")
def xwiki_datasource(datasource_utils, xwiki_integration, xwiki_seed_page):
    """Create an xWiki datasource indexed against the seeded space."""
    datasource = datasource_utils.create_xwiki_datasource(
        setting_id=xwiki_integration.id,
        space=xwiki_seed_page.space,
    )
    yield datasource
    if datasource:
        datasource_utils.delete_datasource(datasource)


@pytest.fixture(scope="function")
def xwiki_basic_datasource(datasource_utils, xwiki_basic_integration, xwiki_seed_page):
    """Create an xWiki datasource authenticated with Basic Auth (username/password)
    instead of the Bearer token xwiki_datasource uses."""
    datasource = datasource_utils.create_xwiki_datasource(
        setting_id=xwiki_basic_integration.id,
        space=xwiki_seed_page.space,
    )
    yield datasource
    if datasource:
        datasource_utils.delete_datasource(datasource)


@pytest.fixture(scope="function")
def ado_work_items_datasource(datasource_utils, ado_integration, ado_seed):
    """Create an Azure DevOps Work Items datasource for testing."""
    datasource = datasource_utils.create_azure_devops_work_items_datasource(
        setting_id=ado_integration.id
    )
    yield datasource
    if datasource:
        datasource_utils.delete_datasource(datasource)


@pytest.fixture(scope="session")
def gmail_message_operator():
    gmail_utils = GmailUtils()
    yield gmail_utils
    gmail_utils.delete_all_messages()


@pytest.fixture(scope="session")
def azure_message_operator():
    azure_email_utils = AzureEmailUtils()
    yield azure_email_utils
    azure_email_utils.delete_all_messages()


@pytest.fixture(scope="module")
def ado_integration(integration_utils, azure_devops_seed_pull_request):
    """Create Azure DevOps integration"""
    _integration = integration_utils.create_integration(
        CredentialTypes.AZURE_DEVOPS,
        CredentialsManager.azure_devops_credentials(),
    )
    yield _integration
    if _integration:
        integration_utils.delete_integration(_integration)


@pytest.fixture(scope="function")
def integration(integration_utils):
    """Create integration with custom credentials"""

    created_integration: Optional[Integration] = None

    def _integration(
        credential_type: CredentialTypes, credential_values, integration_alias=None
    ):
        nonlocal created_integration

        created_integration = integration_utils.create_integration(
            credential_type,
            credential_values,
            integration_alias=integration_alias,
        )
        return created_integration

    yield _integration
    if created_integration:
        integration_utils.delete_integration(created_integration)


@pytest.fixture(scope="session")
def vendor_assistant_utils():
    """Create VendorUtils instance for managing vendor assistants"""
    from codemie_test_harness.tests.utils.vendor_assistant_utils import (
        VendorAssistantUtils,
    )

    return VendorAssistantUtils()


@pytest.fixture(scope="session")
def vendor_workflow_utils():
    """Create VendorWorkflowUtils instance for managing vendor workflows"""
    from codemie_test_harness.tests.utils.vendor_workflow_utils import (
        VendorWorkflowUtils,
    )

    return VendorWorkflowUtils()


@pytest.fixture(scope="session")
def vendor_knowledge_base_utils():
    """Create VendorKnowledgeBaseUtils instance for managing vendor knowledge bases"""
    from codemie_test_harness.tests.utils.vendor_knowledge_base_utils import (
        VendorKnowledgeBaseUtils,
    )

    return VendorKnowledgeBaseUtils()


@pytest.fixture(scope="session")
def vendor_guardrail_utils():
    """Create VendorGuardrailUtils instance for managing vendor guardrails"""
    from codemie_test_harness.tests.utils.vendor_guardrail_utils import (
        VendorGuardrailUtils,
    )

    return VendorGuardrailUtils()


@pytest.fixture(scope="session")
def vendor_runtime_utils():
    """Create VendorRuntimeUtils instance for managing vendor AgentCore runtimes"""
    return VendorRuntimeUtils()


@pytest.fixture
def cleanup_ado_wiki_pages(request):
    """
    Unified fixture to cleanup ADO wiki pages after test execution.

    Usage:
        # Get registration function by passing deletion callable
        register_page = cleanup_ado_wiki_pages(deleter_function)

        # Register each page immediately after creation
        register_page(page_path)
    """
    pages_to_delete = []
    deleter_function = None

    def register_page(deleter_func):
        """
        Register the deletion function and return a page registration function.
        """
        nonlocal deleter_function
        deleter_function = deleter_func

        def add_page(page_path):
            """Register a single page for cleanup."""
            pages_to_delete.append(page_path)

        return add_page

    def cleanup():
        """Cleanup function that runs after test completes."""
        if deleter_function:
            # Delete pages in reverse order (deepest first)
            for page_path in reversed(pages_to_delete):
                try:
                    deleter_function(page_path)
                except Exception as e:
                    print(f"Warning: Failed to delete page {page_path}: {e}")

    # Register cleanup to run after test
    request.addfinalizer(cleanup)

    return register_page


@pytest.fixture
def cleanup_xwiki_pages(request):
    """
    Unified fixture to cleanup xWiki pages after test execution.

    Usage:
        # Get registration function by passing deletion callable
        register_page = cleanup_xwiki_pages(deleter_function)

        # Register each page immediately after creation
        register_page(page_identifier)
    """
    pages_to_delete = []
    deleter_function = None

    def register_page(deleter_func):
        """
        Register the deletion function and return a page registration function.
        """
        nonlocal deleter_function
        deleter_function = deleter_func

        def add_page(page_identifier):
            """Register a single page for cleanup."""
            pages_to_delete.append(page_identifier)

        return add_page

    def cleanup():
        """Cleanup function that runs after test completes."""
        if deleter_function:
            # Delete pages in reverse order (deepest/child pages first)
            for page_identifier in reversed(pages_to_delete):
                try:
                    deleter_function(page_identifier)
                except Exception as e:
                    print(f"Warning: Failed to delete page {page_identifier}: {e}")

    # Register cleanup to run after test
    request.addfinalizer(cleanup)

    return register_page


@pytest.fixture(scope="session")
def guardrails_assignment_utils(client):
    """Create GuardrailsAssignmentUtils instance for assigning guardrails to entities"""
    from codemie_test_harness.tests.utils.guardrails_assignment_util import (
        GuardrailsAssignmentUtils,
    )

    return GuardrailsAssignmentUtils(client)


def pytest_sessionfinish(session):
    """Run cleanup code after all tests have finished.

    Session-scoped last-resort backstop. Per-fixture teardown
    (ProjectUtils.delete_project_cascade and friends) is the primary
    cleanup mechanism — this only catches whatever a fixture still
    missed. Every call is independently wrapped so one failure doesn't
    block the rest.

    Assistants/datasources/workflows/integrations/projects are all scoped
    to entities whose name contains THIS session's own random prefix
    (autotest_entity_prefix), so they can never touch another
    concurrently-running session's in-progress data — the project sweep
    additionally narrows via search="autotest-" for performance, but the
    predicate still requires the session prefix too, not "autotest-"
    alone. Skills are only scoped by created_by (matches every skill this
    TEST_USER created, across sessions — same as before this refactor,
    not narrowed further here). Providers and cost centers match a
    structural name pattern, also session-agnostic. Jira/Confluence/ADO
    cleanup is intentionally NOT done here — see test_clean_all_entities
    for that.
    """
    if CredentialsManager.get_parameter("CLEANUP_DATA", "true").lower() != "true":
        return

    logger.info("Starting session cleanup...")
    client = get_client()
    prefix = autotest_entity_prefix
    common_filters = {"created_by": TEST_USER}

    try:
        cleanup_utils.delete_integrations(
            client,
            IntegrationType.PROJECT,
            {**common_filters, "search": prefix},
            name_contains=prefix,
        )
    except Exception as e:
        logger.error(f"Failed to clean up project integrations: {e}")

    try:
        cleanup_utils.delete_integrations(
            client,
            IntegrationType.USER,
            {**common_filters, "search": prefix},
            name_contains=prefix,
        )
    except Exception as e:
        logger.error(f"Failed to clean up user integrations: {e}")

    try:
        cleanup_utils.delete_assistants(
            client, {**common_filters, "search": prefix}, name_contains=prefix
        )
    except Exception as e:
        logger.error(f"Failed to clean up assistants: {e}")

    try:
        cleanup_utils.delete_skills(
            client,
            {**common_filters, "search": prefix},
        )
    except Exception as e:
        logger.error(f"Failed to clean up skills: {e}")

    try:
        cleanup_utils.delete_datasources(
            client, {**common_filters, "name": prefix}, name_contains=prefix
        )
    except Exception as e:
        logger.error(f"Failed to clean up datasources: {e}")

    try:
        cleanup_utils.delete_workflows(
            client, {**common_filters, "name": prefix}, name_contains=prefix
        )
    except Exception as e:
        logger.error(f"Failed to clean up workflows: {e}")

    try:
        # search="autotest-" narrows the listing server-side (fast); the
        # predicate still requires THIS session's own prefix, not just
        # "autotest-" alone — matching any "autotest-"-shaped project
        # regardless of which session created it would risk deleting
        # another concurrently-running session's in-progress project on
        # this shared environment.
        ProjectUtils(client).delete_matching_projects(
            lambda n: prefix in n and n.startswith("autotest-"), search="autotest-"
        )
    except Exception as e:
        logger.error(f"Failed to clean up projects: {e}")

    try:
        cleanup_utils.delete_providers(client)
    except Exception as e:
        logger.error(f"Failed to cleanup providers: {e}")

    try:
        cleanup_utils.delete_cost_centers(client)
    except Exception as e:
        logger.error(f"Failed to cleanup cost centers: {e}")

    logger.info("Session cleanup completed.")
