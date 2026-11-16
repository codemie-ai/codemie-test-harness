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
"""

import logging
import secrets
from types import SimpleNamespace

import pytest
from hamcrest import assert_that, equal_to

from codemie_test_harness.tests.test_data.budget_test_data import (
    CLI_CLIENT_HEADER,
    DEFAULT_CLI_BUDGET_ID,
    DEFAULT_PREMIUM_BUDGET_ID,
    budget_chat_prompt,
    budget_skill_description,
)
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.proxy_utils import ProxyUtils
from codemie_test_harness.tests.utils.skill_utils import SkillsUtils
from codemie_test_harness.tests.utils.user_lifecycle_utils import user_email

logger = logging.getLogger(__name__)


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
