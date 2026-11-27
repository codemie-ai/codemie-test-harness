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

"""E2E budget attribution: which identity names the personal budget.

The personal budget is the LiteLLM customer named after the user's username, on the web
and on the CLI alike. Every other test user logs in with the e-mail as the username, so the
two names cannot be told apart there.

Covers:
    TC-42  A user whose username differs from the e-mail falls back to the personal budget
           from the web and from the CLI: both are charged to the username customers
    user-management-shows-no-default_TC_003
           A mixed-case personal project is charged under its real name, and its own
           identity in another casing still resolves to the personal budget
"""

import logging
import secrets
from types import SimpleNamespace

import pytest
from hamcrest import assert_that, equal_to, greater_than, not_none

from codemie_test_harness.tests.test_data.budget_test_data import (
    CLI_CLIENT_HEADER,
    CLI_PROJECT_HEADER,
    DEFAULT_CLI_BUDGET_ID,
    DEFAULT_PLATFORM_BUDGET_ID,
    DEFAULT_PREMIUM_BUDGET_ID,
    budget_chat_prompt,
    budget_skill_description,
)
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.proxy_utils import ProxyUtils
from codemie_test_harness.tests.utils.skill_utils import SkillsUtils
from codemie_test_harness.tests.utils.user_lifecycle_utils import user_email

logger = logging.getLogger(__name__)

# How long the ledger may take to show a charge made through the proxy.
LEDGER_CHARGE_TIMEOUT = 300


@pytest.fixture(scope="function")
def user_with_own_username(keycloak_utils, lite_llm_budget_utils):
    """Platform admin whose username differs from the e-mail, logged in by the username."""
    email = user_email("budget")
    username = f"autotest_budget_{secrets.token_hex(4)}"
    password = keycloak_utils.create_test_user(
        email=email, project_name=email, username=username
    )
    try:
        yield SimpleNamespace(
            email=email,
            username=username,
            client=get_client(username=username, password=password),
        )
    finally:
        keycloak_utils.delete_user(email)
        for name in (username, email):
            for customer_id in (
                name,
                f"{name}_{DEFAULT_CLI_BUDGET_ID}",
                f"{name}_{DEFAULT_PREMIUM_BUDGET_ID}",
            ):
                lite_llm_budget_utils.delete_customer(customer_id)


# ── TC-42 ──────────────────────────────────────────────────────────────────────


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1200)
def test_web_and_cli_personal_fallback_use_the_username_customers(
    user_with_own_username,
    default_llm,
    lite_llm_budget_utils,
):
    user = user_with_own_username
    customers = {
        "web_username": user.username,
        "web_email": user.email,
        "cli_username": f"{user.username}_{DEFAULT_CLI_BUDGET_ID}",
        "cli_email": f"{user.email}_{DEFAULT_CLI_BUDGET_ID}",
    }

    logger.info("Web request of a user without a default project")
    before = lite_llm_budget_utils.get_spends({}, customers)
    SkillsUtils(user.client).generate_instructions(budget_skill_description())
    assert_that(
        lite_llm_budget_utils.wait_for_charged_sources(before, {}, customers),
        equal_to({"web_username"}),
        "A web request must be charged to the customer named after the username",
    )

    logger.info("CLI request of the same user")
    before = lite_llm_budget_utils.get_spends({}, customers)
    ProxyUtils(user.client).send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=CLI_CLIENT_HEADER,
    ).raise_for_status()
    assert_that(
        lite_llm_budget_utils.wait_for_charged_sources(before, {}, customers),
        equal_to({"cli_username"}),
        "A CLI request must be charged to the CLI customer named after the username",
    )


# ── user-management-shows-no-default_TC_003 ────────────────────────────────


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1500)
def test_mixed_case_personal_project_is_charged_under_its_real_name(
    mixed_case_keycloak_user,
    mixed_case_user_id,
    mixed_case_skills_utils,
    mixed_case_proxy_utils,
    default_llm,
    admin_project_utils,
    lite_llm_budget_utils,
):
    """@case user-management-shows-no-default_TC_003

    A mixed-case personal project must be charged under its real casing, and
    requesting the user's own identity under a different casing must still
    resolve to that same personal budget -- never a fallback destination.

    Each charge is checked twice: on the LiteLLM personal customer, and in the
    ledger by user id.
    """
    email, _ = mixed_case_keycloak_user
    # LiteLLM keys the personal customer by the username, which the identity provider
    # lowercases; the project itself keeps the real mixed-case name.
    customers = {"personal": email.lower()}

    logger.info("Phase 0: the project carries the real mixed-case name and is personal")
    project = admin_project_utils.get_project_detail(email)
    assert_that(project.name, equal_to(email), "The project keeps its real casing")
    assert_that(
        project.project_type,
        equal_to("personal"),
        "A mixed-case email must get a personal project, not a regular one",
    )

    logger.info("Phase 1: unbound flow charges the real mixed-case personal project")
    before = lite_llm_budget_utils.get_spends({}, customers)
    ledger_before = admin_project_utils.get_member_budget_spending(
        DEFAULT_PLATFORM_BUDGET_ID, "platform", mixed_case_user_id
    )
    mixed_case_skills_utils.generate_instructions(budget_skill_description())
    assert_that(
        lite_llm_budget_utils.wait_for_charged_sources(before, {}, customers),
        equal_to({"personal"}),
        "Spend must be charged to the personal budget key under the project's real "
        "mixed-case name",
    )
    charged = admin_project_utils.wait_for_member_budget_spending_above(
        DEFAULT_PLATFORM_BUDGET_ID,
        "platform",
        ledger_before,
        user_id=mixed_case_user_id,
        timeout=LEDGER_CHARGE_TIMEOUT,
    )
    assert_that(charged, not_none(), "No personal platform spend in the ledger")
    assert_that(
        charged.current_spending,
        greater_than(ledger_before),
        "The ledger must show the spend on the personal platform budget",
    )

    logger.info(
        "Phase 2: requesting the user's own identity in another casing is not a fallback"
    )
    cli_customers = {
        **customers,
        "personal_cli": f"{customers['personal']}_{DEFAULT_CLI_BUDGET_ID}",
    }
    before = lite_llm_budget_utils.get_spends({}, cli_customers)
    ledger_before = admin_project_utils.get_member_budget_spending(
        DEFAULT_CLI_BUDGET_ID, "cli", mixed_case_user_id
    )
    mixed_case_proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers={**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: email.upper()},
    ).raise_for_status()
    assert_that(
        lite_llm_budget_utils.wait_for_charged_sources(before, {}, cli_customers),
        equal_to({"personal_cli"}),
        "Requesting the user's own identity in another casing must still charge the "
        "real personal CLI budget, not a fallback destination",
    )
    charged = admin_project_utils.wait_for_member_budget_spending_above(
        DEFAULT_CLI_BUDGET_ID,
        "cli",
        ledger_before,
        user_id=mixed_case_user_id,
        timeout=LEDGER_CHARGE_TIMEOUT,
    )
    assert_that(charged, not_none(), "No personal CLI spend in the ledger")
    assert_that(
        charged.current_spending,
        greater_than(ledger_before),
        "The ledger must show the spend on the personal CLI budget",
    )
