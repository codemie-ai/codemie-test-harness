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
from hamcrest import assert_that, equal_to, greater_than, not_none

from codemie_test_harness.tests.test_data.budget_test_data import (
    budget_chat_prompt,
    CHROME_EXTENSION_CLIENT_HEADER,
    CLI_PROJECT_HEADER,
)

logger = logging.getLogger(__name__)


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_chrome_extension_request_spends_only_from_platform_budget(
    keycloak_user,
    default_llm,
    user_proxy_utils,
    lite_llm_budget_utils,
    project_with_all_three_budgets,
):
    email, _ = keycloak_user
    (
        project_name,
        _,
        _,
        _,
        platform_alias,
        cli_alias,
        premium_alias,
    ) = project_with_all_three_budgets
    request_headers = {
        **CHROME_EXTENSION_CLIENT_HEADER,
        CLI_PROJECT_HEADER: project_name,
    }

    logger.info(
        "Sending chrome extension request (user=%s, project=%s)", email, project_name
    )
    user_proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=request_headers,
    ).raise_for_status()

    logger.info("Waiting for platform key spending (alias=%s)", platform_alias)
    key_info = lite_llm_budget_utils.wait_for_key_alias_spending(platform_alias)
    assert_that(
        key_info,
        not_none(),
        "Chrome extension request was not charged to the platform budget.",
    )
    assert_that(
        float(key_info["spend"]),
        greater_than(0),
        "Platform key spend should increase after a chrome extension request.",
    )

    assert_that(
        float(lite_llm_budget_utils.get_key_info_by_alias(cli_alias)["spend"]),
        equal_to(0),
        "CLI budget must not be charged for a chrome extension request.",
    )
    assert_that(
        float(lite_llm_budget_utils.get_key_info_by_alias(premium_alias)["spend"]),
        equal_to(0),
        "Premium models budget must not be charged for a chrome extension request.",
    )
