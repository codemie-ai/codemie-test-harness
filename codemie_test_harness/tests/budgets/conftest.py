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
import secrets
from datetime import datetime, timedelta
from time import sleep

import pytest
from hamcrest import assert_that, is_
from requests.exceptions import HTTPError

from codemie_sdk.models.integration import CredentialTypes, CredentialValues
from codemie_sdk.models.workflow import WorkflowMode

from codemie_test_harness.tests.test_data.budget_member_override_test_data import (
    MEMBER_OVERRIDE_MAX,
    MEMBER_OVERRIDE_SOFT,
)
from codemie_test_harness.tests.test_data.budget_test_data import (
    ALL_BUDGET_CATEGORIES,
    budget_chat_prompt,
    BUDGET_CACHE_DELAY,
    CLI_BUDGET_CATEGORIES,
    CLI_CLIENT_HEADER,
    DEFAULT_CLI_BUDGET_ID,
    DEFAULT_PREMIUM_BUDGET_ID,
    PREMIUM_BUDGET_CATEGORIES,
    PREMIUM_MODEL,
    PROJECT_BUDGET_TRACKING_DELAY,
    project_key_alias,
)
from codemie_test_harness.tests.utils.activity_utils import ActivityUtils
from codemie_test_harness.tests.utils.admin_project_budget_group_utils import (
    AdminProjectBudgetGroupUtils,
)
from codemie_test_harness.tests.utils.admin_project_budget_utils import (
    AdminProjectBudgetUtils,
)
from codemie_test_harness.tests.utils.admin_spend_tracking_utils import (
    AdminSpendTrackingUtils,
)
from codemie_test_harness.tests.utils.assistant_utils import AssistantUtils
from codemie_test_harness.tests.utils.budget_utils import BudgetUtils
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.integration_utils import IntegrationUtils
from codemie_test_harness.tests.utils.project_utils import ProjectUtils
from codemie_test_harness.tests.utils.proxy_utils import ProxyUtils
from codemie_test_harness.tests.utils.skill_utils import SkillsUtils
from codemie_test_harness.tests.utils.workflow_utils import WorkflowUtils
from codemie_test_harness.tests.utils.yaml_utils import (
    AssistantModel,
    StateModel,
    WorkflowYamlModel,
    prepare_yaml_content,
)

logger = logging.getLogger(__name__)


@pytest.fixture(scope="function")
def keycloak_user(keycloak_utils, lite_llm_budget_utils):
    uid = secrets.token_hex(4)
    email = f"autotest_budget_{uid}@email.com"
    password = keycloak_utils.create_test_user(email=email, project_name=email)
    yield email, password
    keycloak_utils.delete_user(email)
    for customer_id in (
        email,
        f"{email}_{DEFAULT_PREMIUM_BUDGET_ID}",
        f"{email}_{DEFAULT_CLI_BUDGET_ID}",
    ):
        lite_llm_budget_utils.delete_customer(customer_id)


@pytest.fixture(scope="function")
def user_client(keycloak_user):
    email, password = keycloak_user
    return get_client(username=email, password=password)


@pytest.fixture(scope="function")
def user_assistant_utils(user_client):
    return AssistantUtils(user_client)


@pytest.fixture(scope="function")
def user_budget_utils(user_client):
    return BudgetUtils(user_client)


@pytest.fixture(scope="function")
def user_proxy_utils(user_client):
    return ProxyUtils(user_client)


@pytest.fixture(scope="function")
def user_integration_utils(user_client):
    return IntegrationUtils(user_client)


@pytest.fixture(scope="function")
def user_litellm_key(lite_llm_budget_utils):
    key = lite_llm_budget_utils.create_key()
    yield key
    lite_llm_budget_utils.delete_key(key)


@pytest.fixture(scope="function")
def user_litellm_integration(user_litellm_key, user_integration_utils, keycloak_user):
    email, _ = keycloak_user
    integration = user_integration_utils.create_user_integration(
        CredentialTypes.LITE_LLM,
        [CredentialValues(key="api_key", value=user_litellm_key)],
        project_name=email,
    )
    yield integration
    if integration:
        user_integration_utils.delete_integration(integration)


@pytest.fixture(scope="function")
def user_id(user_client):
    return user_client.users.about_me().user_id


@pytest.fixture(scope="function")
def assigned_platform_budget(
    admin_budget_utils,
    lite_llm_budget_utils,
    user_id,
    user_proxy_utils,
    default_llm,
    keycloak_user,
):
    email, _ = keycloak_user
    user_proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
    ).raise_for_status()
    initial_customer = lite_llm_budget_utils.wait_for_spending(email)
    initial_spend = float(initial_customer.get("spend", 0)) if initial_customer else 0.0
    uid = secrets.token_hex(4)
    budget_id = f"autotest-platform-{uid}"
    admin_budget_utils.create_budget(budget_id, "platform")
    admin_budget_utils.assign_user_budget(user_id, "platform", budget_id)
    yield budget_id, initial_spend
    admin_budget_utils.unassign_user_budget(user_id, "platform")
    lite_llm_budget_utils.delete_budget(budget_id)
    admin_budget_utils.sync_budgets()


@pytest.fixture(scope="function")
def assigned_cli_budget(
    admin_budget_utils,
    lite_llm_budget_utils,
    user_id,
    user_proxy_utils,
    default_llm,
    keycloak_user,
):
    email, _ = keycloak_user
    user_proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=CLI_CLIENT_HEADER,
    ).raise_for_status()
    initial_customer = lite_llm_budget_utils.wait_for_spending(
        f"{email}_{DEFAULT_CLI_BUDGET_ID}"
    )
    initial_spend = float(initial_customer.get("spend", 0)) if initial_customer else 0.0
    uid = secrets.token_hex(4)
    budget_id = f"autotest-cli-{uid}"
    admin_budget_utils.create_budget(budget_id, "cli")
    admin_budget_utils.assign_user_budget(user_id, "cli", budget_id)
    yield budget_id, initial_spend
    admin_budget_utils.unassign_user_budget(user_id, "cli")
    lite_llm_budget_utils.delete_budget(budget_id)
    admin_budget_utils.sync_budgets()


@pytest.fixture(scope="function")
def assigned_premium_budget(
    admin_budget_utils, lite_llm_budget_utils, user_id, user_proxy_utils, keycloak_user
):
    email, _ = keycloak_user
    user_proxy_utils.send_messages_request(
        model=PREMIUM_MODEL,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
    ).raise_for_status()
    initial_customer = lite_llm_budget_utils.wait_for_spending(
        f"{email}_{DEFAULT_PREMIUM_BUDGET_ID}"
    )
    initial_spend = float(initial_customer.get("spend", 0)) if initial_customer else 0.0
    uid = secrets.token_hex(4)
    budget_id = f"autotest-premium-{uid}"
    admin_budget_utils.create_budget(budget_id, "premium_models")
    admin_budget_utils.assign_user_budget(user_id, "premium_models", budget_id)
    yield budget_id, initial_spend
    admin_budget_utils.unassign_user_budget(user_id, "premium_models")
    lite_llm_budget_utils.delete_budget(budget_id)
    admin_budget_utils.sync_budgets()


@pytest.fixture(scope="function")
def user_assistant(default_llm, user_assistant_utils):
    created_assistant = None

    def _create(project_name: str, shared: bool = False):
        nonlocal created_assistant
        created_assistant = user_assistant_utils.create_assistant(
            llm_model_type=default_llm.base_name,
            project_name=project_name,
            shared=shared,
        )
        return created_assistant

    yield _create

    if created_assistant:
        try:
            user_assistant_utils.delete_assistant(created_assistant)
        except HTTPError as e:
            logger.warning(f"Failed to delete assistant {created_assistant.id}: {e}")


@pytest.fixture(scope="function")
def user1_assistant(default_llm, user1_assistant_utils):
    created_assistant = None

    def _create(project_name: str):
        nonlocal created_assistant
        created_assistant = user1_assistant_utils.create_assistant(
            llm_model_type=default_llm.base_name,
            project_name=project_name,
        )
        return created_assistant

    yield _create

    if created_assistant:
        try:
            user1_assistant_utils.delete_assistant(created_assistant)
        except HTTPError as e:
            logger.warning(f"Failed to delete assistant {created_assistant.id}: {e}")


@pytest.fixture(scope="function")
def user2_assistant(default_llm, user2_assistant_utils):
    created_assistant = None

    def _create(project_name: str, shared: bool = False, llm_model: str = None):
        nonlocal created_assistant
        created_assistant = user2_assistant_utils.create_assistant(
            llm_model_type=llm_model if llm_model else default_llm.base_name,
            project_name=project_name,
            shared=shared,
        )
        return created_assistant

    yield _create

    if created_assistant:
        try:
            user2_assistant_utils.delete_assistant(created_assistant)
        except HTTPError as e:
            logger.warning(f"Failed to delete assistant {created_assistant.id}: {e}")


@pytest.fixture(scope="function")
def user_premium_assistant(user_assistant_utils):
    created_assistant = None

    def _create(project_name: str, shared: bool = False):
        nonlocal created_assistant
        created_assistant = user_assistant_utils.create_assistant(
            llm_model_type=PREMIUM_MODEL,
            project_name=project_name,
            shared=shared,
        )
        return created_assistant

    yield _create

    if created_assistant:
        try:
            user_assistant_utils.delete_assistant(created_assistant)
        except HTTPError as e:
            logger.warning(f"Failed to delete assistant {created_assistant.id}: {e}")


@pytest.fixture(scope="function")
def user2_premium_assistant(user2_assistant_utils):
    created_assistant = None

    def _create(project_name: str, shared: bool = False):
        nonlocal created_assistant
        created_assistant = user2_assistant_utils.create_assistant(
            llm_model_type=PREMIUM_MODEL,
            project_name=project_name,
            shared=shared,
        )
        return created_assistant

    yield _create

    if created_assistant:
        try:
            user2_assistant_utils.delete_assistant(created_assistant)
        except HTTPError as e:
            logger.warning(f"Failed to delete assistant {created_assistant.id}: {e}")


@pytest.fixture(scope="session")
def admin_spend_tracking_utils(client):
    return AdminSpendTrackingUtils(client)


@pytest.fixture(scope="session")
def admin_project_utils(client):
    return ProjectUtils(client)


@pytest.fixture(scope="function")
def project_setup(user_client, admin_project_utils, lite_llm_budget_utils):
    uid = secrets.token_hex(4)
    project_name = f"autotest-project-{uid}"
    user_project_utils = ProjectUtils(user_client)
    user_project_utils.create_project(
        name=project_name, description="Autotest budget project"
    )
    user_project_utils.enable_member_budget_tracking(project_name)
    sleep(30)
    yield project_name
    for category in ("platform", "cli", "premium_models"):
        try:
            alias = project_key_alias(project_name, category)
            lite_llm_budget_utils.delete_key_by_alias(alias)
        except Exception as e:
            logger.warning(f"Failed to delete LiteLLM key for alias {alias}: {e}")
    admin_project_utils.delete_project_cascade(project_name)


@pytest.fixture(scope="function")
def keycloak_user_1(keycloak_utils, lite_llm_budget_utils):
    uid = secrets.token_hex(4)
    email = f"autotest_budget_{uid}@email.com"
    password = keycloak_utils.create_test_user(email=email, project_name=email)
    yield email, password
    keycloak_utils.delete_user(email)
    for customer_id in (
        email,
        f"{email}_{DEFAULT_PREMIUM_BUDGET_ID}",
        f"{email}_{DEFAULT_CLI_BUDGET_ID}",
    ):
        lite_llm_budget_utils.delete_customer(customer_id)


@pytest.fixture(scope="function")
def keycloak_user_2(keycloak_utils, lite_llm_budget_utils):
    uid = secrets.token_hex(4)
    email = f"autotest_budget_{uid}@email.com"
    password = keycloak_utils.create_test_user(email=email, project_name=email)
    yield email, password
    keycloak_utils.delete_user(email)
    for customer_id in (
        email,
        f"{email}_{DEFAULT_PREMIUM_BUDGET_ID}",
        f"{email}_{DEFAULT_CLI_BUDGET_ID}",
    ):
        lite_llm_budget_utils.delete_customer(customer_id)


@pytest.fixture(scope="function")
def user1_client(keycloak_user_1):
    email, password = keycloak_user_1
    return get_client(username=email, password=password)


@pytest.fixture(scope="function")
def user2_client(keycloak_user_2):
    email, password = keycloak_user_2
    return get_client(username=email, password=password)


@pytest.fixture(scope="function")
def user1_project_utils(user1_client):
    return ProjectUtils(user1_client)


@pytest.fixture(scope="function")
def user1_assistant_utils(user1_client):
    return AssistantUtils(user1_client)


@pytest.fixture(scope="function")
def user2_assistant_utils(user2_client):
    return AssistantUtils(user2_client)


@pytest.fixture(scope="function")
def user2_proxy_utils(user2_client):
    return ProxyUtils(user2_client)


@pytest.fixture(scope="function")
def lifecycle_project(
    admin_project_utils, user1_project_utils, user2_client, lite_llm_budget_utils
):
    uid = secrets.token_hex(4)
    project_name = f"autotest-project-{uid}"
    user1_project_utils.create_project(
        name=project_name, description="Autotest lifecycle project"
    )
    admin_project_utils.enable_member_budget_tracking(project_name)
    user2_id = user2_client.users.about_me().user_id
    user1_project_utils.assign_user_to_project(
        project_name, user2_id, is_project_admin=False
    )
    sleep(30)
    yield project_name, user2_id
    for category in ("platform", "cli", "premium_models"):
        try:
            alias = project_key_alias(project_name, category)
            lite_llm_budget_utils.delete_key_by_alias(alias)
        except Exception as e:
            logger.warning(f"Failed to delete LiteLLM key for alias {alias}: {e}")
    try:
        lite_llm_budget_utils.delete_override_customers_for_project(
            project_name, user2_id
        )
    except Exception as e:
        logger.warning(
            f"Failed to delete override customers for project {project_name}: {e}"
        )
    admin_project_utils.delete_project_cascade(project_name)


@pytest.fixture(scope="function")
def user2_integration_utils(user2_client):
    return IntegrationUtils(user2_client)


@pytest.fixture(scope="function")
def user1_id(user1_client):
    return user1_client.users.about_me().user_id


@pytest.fixture(scope="function")
def user2_litellm_key(lite_llm_budget_utils):
    key = lite_llm_budget_utils.create_key()
    yield key
    lite_llm_budget_utils.delete_key(key)


@pytest.fixture(scope="function")
def user2_litellm_integration(
    user2_litellm_key, user2_integration_utils, keycloak_user_2
):
    email, _ = keycloak_user_2
    integration = user2_integration_utils.create_user_integration(
        CredentialTypes.LITE_LLM,
        [CredentialValues(key="api_key", value=user2_litellm_key)],
        project_name=email,
        is_global=True,
    )
    yield integration
    if integration:
        user2_integration_utils.delete_integration(integration)


@pytest.fixture(scope="function")
def project_no_member(user1_client, admin_project_utils, lite_llm_budget_utils):
    uid = secrets.token_hex(4)
    project_name = f"autotest-project-{uid}"
    user1_project_utils = ProjectUtils(user1_client)
    user1_project_utils.create_project(
        name=project_name, description="Autotest budget project"
    )
    user1_project_utils.enable_member_budget_tracking(project_name)
    yield project_name
    for category in ("platform", "cli", "premium_models"):
        try:
            alias = project_key_alias(project_name, category)
            lite_llm_budget_utils.delete_key_by_alias(alias)
        except Exception as e:
            logger.warning(f"Failed to delete LiteLLM key for alias {alias}: {e}")
    admin_project_utils.delete_project_cascade(project_name)


def _wait_for_project_budget(project_budget_groups, project_name, categories=None):
    budget = project_budget_groups.create(project_name, categories)
    sleep(BUDGET_CACHE_DELAY)
    return budget


@pytest.fixture(scope="function")
def project_with_platform_budget(project_setup, project_budget_groups):
    budget = _wait_for_project_budget(project_budget_groups, project_setup)
    return project_setup, budget.budget_ids["platform"], budget.alias("platform")


@pytest.fixture(scope="function")
def project_with_cli_budget(project_setup, project_budget_groups):
    budget = _wait_for_project_budget(
        project_budget_groups, project_setup, CLI_BUDGET_CATEGORIES
    )
    return project_setup, budget.budget_ids["cli"], budget.alias("cli")


@pytest.fixture(scope="function")
def project_with_premium_budget(project_setup, project_budget_groups):
    budget = _wait_for_project_budget(
        project_budget_groups, project_setup, PREMIUM_BUDGET_CATEGORIES
    )
    return (
        project_setup,
        budget.budget_ids["premium_models"],
        budget.alias("premium_models"),
    )


def _all_three_budgets(budget):
    return (
        budget.project_name,
        budget.budget_ids["platform"],
        budget.budget_ids["cli"],
        budget.budget_ids["premium_models"],
        budget.alias("platform"),
        budget.alias("cli"),
        budget.alias("premium_models"),
    )


@pytest.fixture(scope="function")
def project_with_all_three_budgets(project_setup, project_budget_groups):
    return _all_three_budgets(
        _wait_for_project_budget(
            project_budget_groups, project_setup, ALL_BUDGET_CATEGORIES
        )
    )


@pytest.fixture(scope="function")
def project_no_member_with_all_three_budgets(project_no_member, project_budget_groups):
    return _all_three_budgets(
        _wait_for_project_budget(
            project_budget_groups, project_no_member, ALL_BUDGET_CATEGORIES
        )
    )


@pytest.fixture(scope="function")
def lifecycle_project_with_platform_budget(lifecycle_project, project_budget_groups):
    project_name, user2_id = lifecycle_project
    budget = _wait_for_project_budget(project_budget_groups, project_name)
    return project_name, user2_id, budget.budget_ids["platform"], budget.alias()


@pytest.fixture(scope="function")
def lifecycle_project_with_cli_budget(lifecycle_project, project_budget_groups):
    project_name, user2_id = lifecycle_project
    budget = _wait_for_project_budget(
        project_budget_groups, project_name, CLI_BUDGET_CATEGORIES
    )
    return project_name, user2_id, budget.budget_ids["cli"], budget.alias("cli")


@pytest.fixture(scope="function")
def lifecycle_project_with_premium_budget(lifecycle_project, project_budget_groups):
    project_name, user2_id = lifecycle_project
    budget = _wait_for_project_budget(
        project_budget_groups, project_name, PREMIUM_BUDGET_CATEGORIES
    )
    return (
        project_name,
        user2_id,
        budget.budget_ids["premium_models"],
        budget.alias("premium_models"),
    )


@pytest.fixture(scope="function")
def user_workflow_utils(user_client):
    return WorkflowUtils(user_client)


@pytest.fixture(scope="function")
def user_workflow(default_llm, user_workflow_utils):
    created_workflow = None

    def _create(project_name: str, shared: bool = False):
        nonlocal created_workflow
        assistant_model = AssistantModel(
            id="budget_test_state",
            model=default_llm.base_name,
            system_prompt="You are a helpful assistant. Say hello when asked.",
        )
        state_model = StateModel(
            id="budget_test_state",
            assistant_id="budget_test_state",
            task="Say hello",
        )
        workflow_yaml = WorkflowYamlModel(
            assistants=[assistant_model],
            states=[state_model],
        )
        yaml_content = prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))
        created_workflow = user_workflow_utils.create_workflow(
            workflow_type=WorkflowMode.SEQUENTIAL,
            workflow_yaml=yaml_content,
            project_name=project_name,
            shared=shared,
        )
        return created_workflow

    yield _create

    if created_workflow:
        user_workflow_utils.delete_workflow(created_workflow)


@pytest.fixture(scope="function")
def budget_scheduler_integration(integration_utils):
    created_integrations = []

    def _create(
        resource_type: str,
        resource_id: str,
        prompt: str = None,
        schedule: str = None,
    ):
        if schedule is None:
            next_minute = (datetime.now() + timedelta(minutes=2)).minute
            schedule = f"{next_minute} * * * *"
        alias = secrets.token_hex(6)
        credential_values = [
            CredentialValues(key="url", value=CredentialsManager.AUTO_GENERATED),
            CredentialValues(key="is_enabled", value=True),
            CredentialValues(key="schedule", value=schedule),
            CredentialValues(key="resource_type", value=resource_type),
            CredentialValues(key="resource_id", value=resource_id),
            CredentialValues(key="prompt", value=prompt),
        ]
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


# ---------------------------------------------------------------------------
# Spend bucket distribution fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def project_budget_group(admin_project_utils, lite_llm_budget_utils):
    """Create an isolated project + budget group; yield (project_name, group_id).

    Creates the project first, then creates the budget group via
    ``POST /v1/admin/project-budget-groups``.  The returned ``group_id`` is the
    UUID of the budget group entity required by the PUT endpoint.

    Teardown deletes the LiteLLM key for all 3 categories (deleting the budget
    group on the CodeMie side does not cascade to LiteLLM) — not just
    "platform": tests using this fixture can PUT-update the group's category
    distribution mid-test (see test_project_budget_group_distribution.py),
    which creates new category budgets/LiteLLM keys the fixture never
    directly created — then the budget group and the project.
    """
    uid = secrets.token_hex(4)
    project_name = f"autotest-pa-proj-{uid}"
    admin_project_utils.create_project(
        name=project_name, description="Autotest PA budget group project"
    )
    try:
        _admin_client = get_client()
        _group_utils = AdminProjectBudgetGroupUtils(_admin_client)
        group = _group_utils.create_budget_group(
            project_name=project_name,
            total_amount=100.0,
            budget_duration="30d",
            categories={"platform": 100.0},
        )
        group_id = group["group_id"]
    except Exception:
        try:
            admin_project_utils.delete_project(project_name)
        except Exception:
            pass
        raise
    yield project_name, group_id
    for category in ("platform", "cli", "premium_models"):
        try:
            lite_llm_budget_utils.delete_key_by_alias(
                project_key_alias(project_name, category)
            )
        except Exception as e:
            logger.warning(
                f"Failed to delete LiteLLM key for project {project_name} "
                f"category {category}: {e}"
            )
    if group_id is not None:
        try:
            _group_utils.delete_budget_group(group_id)
        except Exception:
            pass
    try:
        admin_project_utils.delete_project(project_name)
    except Exception:
        pass


@pytest.fixture(scope="function")
def project_admin_client(
    keycloak_utils,
    admin_project_utils,
    project_budget_group,
    lite_llm_budget_utils,
):
    """Create a user with project-admin role for the project_budget_group project."""
    project_name, _ = project_budget_group
    uid = secrets.token_hex(4)
    email = f"autotest_pa_{uid}@email.com"
    password = keycloak_utils.create_test_user(email=email, project_name=project_name)
    try:
        user_c = get_client(username=email, password=password)
        user_id = user_c.users.about_me().user_id
        admin_project_utils.assign_user_to_project(
            project_name, user_id, is_project_admin=True
        )
    except Exception:
        try:
            keycloak_utils.delete_user(email)
        except Exception:
            pass
        raise
    yield user_c
    if user_id is not None:
        try:
            admin_project_utils.remove_user_from_project(project_name, user_id)
        except Exception:
            pass
    try:
        keycloak_utils.delete_user(email)
    except Exception:
        pass
    for customer_id in (
        email,
        f"{email}_{DEFAULT_CLI_BUDGET_ID}",
        f"{email}_{DEFAULT_PREMIUM_BUDGET_ID}",
    ):
        try:
            lite_llm_budget_utils.delete_customer(customer_id)
        except Exception:
            pass


@pytest.fixture(scope="function")
def project_admin_budget_group_utils(project_admin_client):
    """Return AdminProjectBudgetGroupUtils authenticated as the project admin."""
    return AdminProjectBudgetGroupUtils(project_admin_client)


# ---------------------------------------------------------------------------
# Platform hard limit must be greater than 0
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def admin_budget_group_utils(client):
    """Return AdminProjectBudgetGroupUtils authenticated as the platform admin."""
    return AdminProjectBudgetGroupUtils(client)


@pytest.fixture(scope="function")
def budget_project(admin_project_utils, lite_llm_budget_utils):
    """Create an isolated project without any budget group; yield its name.

    Tests create the budget group themselves (or assert that none was created).
    Teardown removes the LiteLLM keys of all 3 categories, then cascades the
    project deletion, which also deletes any budget group created in the test.
    """
    project_name = f"autotest-bp-{secrets.token_hex(4)}"
    admin_project_utils.create_project(
        name=project_name, description="Autotest platform hard limit project"
    )
    yield project_name
    for category in ("platform", "cli", "premium_models"):
        try:
            lite_llm_budget_utils.delete_key_by_alias(
                project_key_alias(project_name, category)
            )
        except Exception as e:
            logger.warning(
                f"Failed to delete LiteLLM key for project {project_name} "
                f"category {category}: {e}"
            )
    try:
        admin_project_utils.delete_project_cascade(project_name)
    except Exception as e:
        logger.warning(f"Failed to delete project {project_name}: {e}")


@pytest.fixture(scope="function")
def cross_project_admin_client(
    keycloak_utils,
    admin_project_utils,
    lite_llm_budget_utils,
):
    """Create a user who is project admin of a *different* project (for TC-05)."""
    uid = secrets.token_hex(4)
    other_project = f"autotest-other-proj-{uid}"
    email = f"autotest_cpa_{uid}@email.com"
    admin_project_utils.create_project(
        name=other_project, description="Cross-project for PA distribution tests"
    )
    try:
        password = keycloak_utils.create_platform_user(email=email)
        user_c = get_client(username=email, password=password)
        user_id = user_c.users.about_me().user_id
        admin_project_utils.assign_user_to_project(
            other_project, user_id, is_project_admin=True
        )
    except Exception:
        try:
            keycloak_utils.delete_user(email)
        except Exception:
            pass
        try:
            admin_project_utils.delete_project(other_project)
        except Exception:
            pass
        raise
    yield user_c
    if user_id is not None:
        try:
            admin_project_utils.remove_user_from_project(other_project, user_id)
        except Exception:
            pass
    try:
        keycloak_utils.delete_user(email)
    except Exception:
        pass
    for customer_id in (
        email,
        f"{email}_{DEFAULT_CLI_BUDGET_ID}",
        f"{email}_{DEFAULT_PREMIUM_BUDGET_ID}",
    ):
        try:
            lite_llm_budget_utils.delete_customer(customer_id)
        except Exception:
            pass
    try:
        admin_project_utils.delete_project(other_project)
    except Exception:
        pass


@pytest.fixture(scope="function")
def member_override_project(
    project_budget_group,
    project_admin_client,
    project_admin_budget_group_utils,
    keycloak_regular_user,
    admin_project_utils,
):
    """Project with a budget group, a project admin and a developer-only member.

    Enables member budget tracking and assigns the regular user as a non-admin
    member so the budget exposes per-member allocations.

    Yields:
        tuple: (project_name, budget_id, pa_client, member_id, member_client) where
        ``budget_id`` is the platform category budget of the project's budget group.
    """
    project_name, group_id = project_budget_group
    email, password = keycloak_regular_user
    member_client = get_client(username=email, password=password)
    member_id = member_client.users.about_me().user_id
    admin_project_utils.enable_member_budget_tracking(project_name)
    admin_project_utils.assign_user_to_project(
        project_name, member_id, is_project_admin=False
    )
    group = project_admin_budget_group_utils.get_group(group_id)
    budget_id = AdminProjectBudgetUtils.budget_ids_by_category(group)["platform"]
    yield project_name, budget_id, project_admin_client, member_id, member_client
    try:
        admin_project_utils.remove_user_from_project(project_name, member_id)
    except Exception:
        pass


@pytest.fixture(scope="function")
def project_admin_override_ready(member_override_project):
    """``member_override_project`` once the project admin is consistently permitted to override.

    Absorbs the propagation lag of the new project admin's membership across
    backend instances before the test asserts on the override itself.
    """
    _, budget_id, pa_client, member_id, _ = member_override_project
    permitted = AdminProjectBudgetUtils(pa_client).wait_until_member_override_permitted(
        budget_id, member_id, MEMBER_OVERRIDE_MAX, MEMBER_OVERRIDE_SOFT
    )
    assert_that(
        permitted,
        is_(True),
        "Project admin was not permitted to override a member allocation",
    )
    return member_override_project


@pytest.fixture(scope="function")
def auditor_assigned_to_project(
    member_override_project, auditor_client, admin_project_utils
):
    """Assign the shared auditor account to the project as a non-admin member.

    Yields the auditor client; the assignment is removed on teardown so the
    shared account stays clean.
    """
    project_name = member_override_project[0]
    auditor_id = auditor_client.users.about_me().user_id
    admin_project_utils.assign_user_to_project(
        project_name, auditor_id, is_project_admin=False
    )
    yield auditor_client
    try:
        admin_project_utils.remove_user_from_project(project_name, auditor_id)
    except Exception:
        pass


@pytest.fixture(scope="function")
def regular_member_client(member_override_project):
    """Client of the developer-only project member."""
    return member_override_project[4]


@pytest.fixture(scope="function")
def plain_admin_client(promoted_admin_user):
    """Client of a platform Admin who is neither maintainer nor project admin."""
    return promoted_admin_user[2]


@pytest.fixture(
    params=[
        pytest.param("regular_member_client", id="regular_member"),
        pytest.param("cross_project_admin_client", id="cross_project_admin"),
        pytest.param("plain_admin_client", id="plain_admin"),
        pytest.param("auditor_assigned_to_project", id="auditor"),
    ]
)
def unauthorized_override_actor(request):
    """Client of each actor that must not manage member budgets of the project."""
    return request.getfixturevalue(request.param)


@pytest.fixture(scope="function")
def member_with_maintainer_override(
    member_override_project, admin_project_budget_utils
):
    """Pre-set a fixed allocation for the member as the maintainer.

    Yields:
        tuple: (budget_id, member_id, allocations_before) where
        ``allocations_before`` is the budget's ``member_allocations`` snapshot.
    """
    _, budget_id, _, member_id, _ = member_override_project
    admin_project_budget_utils.override_member(
        budget_id,
        member_id,
        MEMBER_OVERRIDE_MAX,
        MEMBER_OVERRIDE_SOFT,
    )
    allocations = admin_project_budget_utils.get_budget(budget_id)["member_allocations"]
    yield budget_id, member_id, allocations


@pytest.fixture(scope="session")
def budget_group_activity_utils(client):
    """Session-scoped ActivityUtils for budget group audit event assertions."""
    return ActivityUtils(client)


@pytest.fixture(scope="function")
def user2_id(user2_client):
    return user2_client.users.about_me().user_id


@pytest.fixture(scope="function")
def user2_skills_utils(user2_client):
    return SkillsUtils(user2_client)


@pytest.fixture(scope="function")
def budget_project_factory(
    user1_project_utils,
    admin_project_utils,
    project_budget_groups,
    lite_llm_budget_utils,
):
    """Creates projects owned by user 1, optionally with members and a project budget group.

    ``categories`` is the budget group definition (None -> project without any budget).
    """
    created = []

    def _create(categories: dict | None = None, member_ids: tuple = ()):
        project_name = f"autotest-project-{secrets.token_hex(4)}"
        user1_project_utils.create_project(
            name=project_name, description="Autotest default-project attribution"
        )
        admin_project_utils.enable_member_budget_tracking(project_name)
        created.append(project_name)
        for member_id in member_ids:
            user1_project_utils.assign_user_to_project(
                project_name, member_id, is_project_admin=False
            )
        if categories:
            sleep(PROJECT_BUDGET_TRACKING_DELAY)
            project_budget_groups.create(
                project_name, categories, name_prefix="autotest-default-project"
            )
        return project_name

    yield _create

    project_budget_groups.cleanup()
    for project_name in reversed(created):
        for category in ("platform", "cli", "premium_models"):
            alias = project_key_alias(project_name, category)
            try:
                lite_llm_budget_utils.delete_key_by_alias(alias)
            except Exception as e:
                logger.warning(f"Failed to delete LiteLLM key for alias {alias}: {e}")
        try:
            admin_project_utils.delete_project_cascade(project_name)
        except Exception as e:
            logger.warning(f"Failed to delete project {project_name}: {e}")


@pytest.fixture(scope="function")
def user1_published_assistant(user1_assistant, user1_assistant_utils):
    published_assistant = None

    def _create(project_name: str):
        nonlocal published_assistant
        published_assistant = user1_assistant(project_name=project_name)
        user1_assistant_utils.publish_assistant_to_marketplace(
            published_assistant.id,
            categories=["quality-assurance"],
            ignore_recommendations=True,
        )
        return published_assistant

    yield _create

    if published_assistant:
        try:
            user1_assistant_utils.unpublish_assistant_from_marketplace(
                published_assistant.id
            )
        except HTTPError as e:
            logger.warning(
                f"Failed to unpublish assistant {published_assistant.id}: {e}"
            )
