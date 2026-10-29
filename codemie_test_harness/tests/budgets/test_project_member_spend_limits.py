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

"""Tests for enforce_member_spend_limits project setting.

Behavioural changes covered:
- API field renamed: project_member_budget_tracking_enabled → enforce_member_spend_limits
- Member allocations are ALWAYS synced to LiteLLM regardless of the flag value
- effective_max_budget varies:
    enforce=True  → allocation.allocated_max_budget (individual share, e.g. 50.0 for 2-member equal split)
    enforce=False → budget.max_budget (project total, e.g. 100.0)
- Toggling the flag immediately re-syncs all already-synced member allocations in LiteLLM
"""

import datetime
import logging
import secrets

import pytest
from hamcrest import assert_that, close_to, equal_to, not_none

from codemie_test_harness.tests.test_data.budget_test_data import (
    budget_chat_prompt,
    CLI_CLIENT_HEADER,
    CLI_PROJECT_HEADER,
    MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE,
    project_key_alias,
)
from codemie_test_harness.tests.utils.project_utils import ProjectUtils

logger = logging.getLogger(__name__)

# These must match PLATFORM_BUDGET_CATEGORIES (max_budget=100.0, 2 members).
_PROJECT_BUDGET_MAX = 100.0
_MEMBER_INDIVIDUAL_MAX = 50.0  # equal 2-member split of _PROJECT_BUDGET_MAX


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def project_no_enforce_with_user2(
    user1_project_utils, user2_client, lite_llm_budget_utils
):
    """Project without enforce_member_spend_limits (default False), user2 assigned."""
    uid = secrets.token_hex(4)
    project_name = f"autotest-project-{uid}"
    user2_id = user2_client.users.about_me().user_id
    user1_project_utils.create_project(
        name=project_name, description="Autotest enforce=False project"
    )
    user1_project_utils.assign_user_to_project(
        project_name, user2_id, is_project_admin=False
    )
    user1_project_utils.wait_for_project_member(project_name, user2_id)
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
    user1_project_utils.delete_project_cascade(project_name)


@pytest.fixture(scope="function")
def project_enforce_enabled_with_user2(
    user1_project_utils, user2_client, lite_llm_budget_utils
):
    """Project with enforce_member_spend_limits=True, user2 assigned."""
    uid = secrets.token_hex(4)
    project_name = f"autotest-project-{uid}"
    user2_id = user2_client.users.about_me().user_id
    user1_project_utils.create_project(
        name=project_name, description="Autotest enforce=True project"
    )
    user1_project_utils.set_enforce_member_spend_limits(project_name, True)
    user1_project_utils.assign_user_to_project(
        project_name, user2_id, is_project_admin=False
    )
    user1_project_utils.wait_for_project_member(project_name, user2_id)
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
    user1_project_utils.delete_project_cascade(project_name)


@pytest.fixture(scope="function")
def spend_limits_flag_project(user_client):
    """Bare project (no budget) used to verify the enforce_member_spend_limits flag."""
    uid = secrets.token_hex(4)
    project_name = f"autotest-project-{uid}"
    project_utils = ProjectUtils(user_client)
    create_response = project_utils.create_project(
        name=project_name, description="Autotest spend limits flag project"
    )
    yield project_name, project_utils, create_response
    project_utils.delete_project_cascade(project_name)


@pytest.fixture(scope="function")
def project_no_enforce_with_platform_budget(
    project_no_enforce_with_user2,
    project_budget_groups,
):
    """project_no_enforce_with_user2 with a platform budget created and ready."""
    project_name, user2_id = project_no_enforce_with_user2
    budget = project_budget_groups.create(project_name, name_prefix="autotest")
    yield project_name, user2_id
    project_budget_groups.delete(budget, user2_id)


@pytest.fixture(scope="function")
def project_enforce_enabled_with_platform_budget(
    project_enforce_enabled_with_user2,
    project_budget_groups,
):
    """project_enforce_enabled_with_user2 with a platform budget created and ready."""
    project_name, user2_id = project_enforce_enabled_with_user2
    budget = project_budget_groups.create(project_name, name_prefix="autotest")
    yield project_name, user2_id
    project_budget_groups.delete(budget, user2_id)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_enforce_member_spend_limits_flag_reflected_in_project_update_response(
    spend_limits_flag_project,
):
    """enforce_member_spend_limits is False by default and toggles correctly via PATCH."""
    project_name, project_utils, create_response = spend_limits_flag_project

    assert_that(create_response.enforce_member_spend_limits, equal_to(False))

    logger.info("Enabling enforce_member_spend_limits on project '%s'", project_name)
    enable_response = project_utils.set_enforce_member_spend_limits(project_name, True)
    assert_that(enable_response.enforce_member_spend_limits, equal_to(True))

    logger.info("Disabling enforce_member_spend_limits on project '%s'", project_name)
    disable_response = project_utils.set_enforce_member_spend_limits(
        project_name, False
    )
    assert_that(disable_response.enforce_member_spend_limits, equal_to(False))


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_member_customer_created_in_litellm_when_enforce_limits_disabled(
    user2_proxy_utils,
    lite_llm_budget_utils,
    default_llm,
    project_no_enforce_with_platform_budget,
    admin_spend_tracking_utils,
):
    """Member customer IS created in LiteLLM even when enforce_member_spend_limits=False.

    Previously, member sync was skipped when budget tracking was disabled.  With the new
    behaviour, the sync always runs but uses budget.max_budget as the effective cap.
    """
    project_name, user2_id = project_no_enforce_with_platform_budget
    override_customer_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category="platform", user_id=user2_id
    )
    request_headers = {**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project_name}

    logger.info("Sending platform request as user2 (enforce_member_spend_limits=False)")
    user2_proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=request_headers,
    ).raise_for_status()
    lite_llm_budget_utils.wait_for_key_alias(override_customer_id)

    logger.info(
        "Verifying per-member customer IS created (customer=%s)", override_customer_id
    )
    customer = lite_llm_budget_utils.wait_for_customer(override_customer_id)
    assert_that(customer, not_none())

    logger.info(
        "Verifying member max_budget=%.1f (project total, not individual limit)",
        _PROJECT_BUDGET_MAX,
    )
    customer = lite_llm_budget_utils.wait_for_customer_max_budget(
        override_customer_id, _PROJECT_BUDGET_MAX
    )
    assert_that(customer, not_none())
    assert_that(
        customer.get("litellm_budget_table", {}).get("max_budget"),
        equal_to(_PROJECT_BUDGET_MAX),
    )

    logger.info("Triggering spend collection")
    admin_spend_tracking_utils.collect_spends_nowait()
    logger.info(
        "Waiting for platform spend in project_spend_tracking (project=%s)",
        project_name,
    )
    today = datetime.date.today()
    spends = admin_spend_tracking_utils.wait_for_project_spends(
        project_name, today, today, "platform"
    )
    assert_that(
        spends["total_spend"],
        close_to(float(customer.get("spend", 0)), 0.0001),
        "project_spend_tracking total_spend should match project platform spend.",
    )


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_enabling_enforce_limits_resyncs_member_max_budget_to_individual(
    user2_proxy_utils,
    user1_project_utils,
    lite_llm_budget_utils,
    default_llm,
    project_no_enforce_with_platform_budget,
    admin_spend_tracking_utils,
):
    """Enabling enforce_member_spend_limits immediately re-syncs member max_budget.

    Before toggle:  member customer max_budget = budget.max_budget (100.0)
    After toggle:   member customer max_budget = allocation.allocated_max_budget (50.0)
    """
    project_name, user2_id = project_no_enforce_with_platform_budget
    override_customer_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category="platform", user_id=user2_id
    )
    request_headers = {**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project_name}

    # Phase 1 — enforce=False: member gets project total as max_budget
    logger.info("Phase 1: sending request (enforce_member_spend_limits=False)")
    user2_proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=request_headers,
    ).raise_for_status()
    lite_llm_budget_utils.wait_for_spending(override_customer_id)
    logger.info(
        "Waiting for member customer max_budget=%.1f (customer=%s)",
        _PROJECT_BUDGET_MAX,
        override_customer_id,
    )
    customer = lite_llm_budget_utils.wait_for_customer_max_budget(
        override_customer_id, _PROJECT_BUDGET_MAX
    )
    assert_that(customer, not_none())
    assert_that(
        customer.get("litellm_budget_table", {}).get("max_budget"),
        equal_to(_PROJECT_BUDGET_MAX),
    )
    phase1_spend = float(customer.get("spend", 0))

    # Phase 2 — enable enforcement: max_budget should drop to individual allocation
    logger.info(
        "Phase 2: enabling enforce_member_spend_limits on project '%s'", project_name
    )
    user1_project_utils.set_enforce_member_spend_limits(project_name, True)
    logger.info(
        "Waiting for member customer max_budget to drop to %.1f (customer=%s)",
        _MEMBER_INDIVIDUAL_MAX,
        override_customer_id,
    )
    customer = lite_llm_budget_utils.wait_for_customer_max_budget(
        override_customer_id, _MEMBER_INDIVIDUAL_MAX
    )
    assert_that(customer, not_none())
    assert_that(
        customer.get("litellm_budget_table", {}).get("max_budget"),
        equal_to(_MEMBER_INDIVIDUAL_MAX),
    )
    logger.info(
        "Verifying LiteLLM customer spend=%.4f is preserved after enabling enforcement",
        phase1_spend,
    )
    assert_that(
        float(customer.get("spend", 0)),
        close_to(phase1_spend, 0.0001),
        "LiteLLM customer spend must not be reset after enabling enforce_member_spend_limits.",
    )

    logger.info("Triggering spend collection")
    admin_spend_tracking_utils.collect_spends_nowait()
    logger.info(
        "Waiting for platform spend in project_spend_tracking (project=%s)",
        project_name,
    )
    today = datetime.date.today()
    spends = admin_spend_tracking_utils.wait_for_project_spends(
        project_name, today, today, "platform"
    )
    assert_that(
        spends["total_spend"],
        close_to(phase1_spend, 0.0001),
        "project_spend_tracking total_spend should match project platform spend.",
    )


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_disabling_enforce_limits_resyncs_member_max_budget_to_project_total(
    user2_proxy_utils,
    user1_project_utils,
    lite_llm_budget_utils,
    default_llm,
    project_enforce_enabled_with_platform_budget,
    admin_spend_tracking_utils,
):
    """Disabling enforce_member_spend_limits immediately re-syncs member max_budget.

    Before toggle:  member customer max_budget = allocation.allocated_max_budget (50.0)
    After toggle:   member customer max_budget = budget.max_budget (100.0)
    """
    project_name, user2_id = project_enforce_enabled_with_platform_budget
    override_customer_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category="platform", user_id=user2_id
    )
    request_headers = {**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project_name}

    # Phase 1 — enforce=True: member gets individual allocation as max_budget
    logger.info("Phase 1: sending request (enforce_member_spend_limits=True)")
    user2_proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=request_headers,
    ).raise_for_status()
    logger.info(
        "Waiting for customer spend to be recorded (customer=%s)", override_customer_id
    )
    lite_llm_budget_utils.wait_for_spending(override_customer_id)
    logger.info(
        "Waiting for member customer max_budget=%.1f (customer=%s)",
        _MEMBER_INDIVIDUAL_MAX,
        override_customer_id,
    )
    customer = lite_llm_budget_utils.wait_for_customer_max_budget(
        override_customer_id, _MEMBER_INDIVIDUAL_MAX
    )
    assert_that(customer, not_none())
    assert_that(
        customer.get("litellm_budget_table", {}).get("max_budget"),
        equal_to(_MEMBER_INDIVIDUAL_MAX),
    )
    phase1_spend = float(customer.get("spend", 0))

    # Phase 2 — disable enforcement: max_budget should rise to project total
    logger.info(
        "Phase 2: disabling enforce_member_spend_limits on project '%s'", project_name
    )
    user1_project_utils.set_enforce_member_spend_limits(project_name, False)
    logger.info(
        "Waiting for member customer max_budget to rise to %.1f (customer=%s)",
        _PROJECT_BUDGET_MAX,
        override_customer_id,
    )
    customer = lite_llm_budget_utils.wait_for_customer_max_budget(
        override_customer_id, _PROJECT_BUDGET_MAX
    )
    assert_that(customer, not_none())
    assert_that(
        customer.get("litellm_budget_table", {}).get("max_budget"),
        equal_to(_PROJECT_BUDGET_MAX),
    )
    logger.info(
        "Verifying LiteLLM customer spend=%.4f is preserved after disabling enforcement",
        phase1_spend,
    )
    assert_that(
        float(customer.get("spend", 0)),
        close_to(phase1_spend, 0.0001),
        "LiteLLM customer spend must not be reset after disabling enforce_member_spend_limits.",
    )

    logger.info("Triggering spend collection")
    admin_spend_tracking_utils.collect_spends()
    logger.info(
        "Waiting for platform spend in project_spend_tracking (project=%s)",
        project_name,
    )
    today = datetime.date.today()
    spends = admin_spend_tracking_utils.wait_for_project_spends(
        project_name, today, today, "platform"
    )
    assert_that(
        spends["total_spend"],
        close_to(phase1_spend, 0.0001),
        "project_spend_tracking total_spend should match project platform spend.",
    )
