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

"""UI test for the personal default budget rows of the 'Your personal spending' panel.

The test runs as a fresh platform user with the admin role and no project
(``personal_budget_user``, budgets/conftest.py), so the panel lists exactly its three personal
default budgets: platform, cli and premium. The spend is generated the way
tests/budgets/test_personal_budget_spending.py generates it: platform spend comes from chat with
the user's own assistant in its personal project (``personal_budget_assistant``), cli and
premium spend from /v1/messages requests with the CLI client header and no project header. The
page is compared with the same user's GET /v1/analytics/budget_usage response read through the
SDK.
"""

import pytest

from codemie_test_harness.tests.ui.budgets.personal_spending_steps import (
    assert_api_lists_only_the_personal_rows,
    assert_personal_spend_is_recorded_on_every_category,
    assert_platform_spend_has_more_than_two_decimals,
    find_personal_platform_row,
    generate_personal_spend_on_every_category,
    read_rows,
    wait_for_personal_rows_with_own_spend,
)
from codemie_test_harness.tests.ui.pageobject.budgets.personal_spending_page import (
    PersonalSpendingPage,
)
from codemie_test_harness.tests.ui.pageobject.login_page import LoginPage
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager


@pytest.fixture(autouse=True)
def login(page, personal_budget_user):
    """Override budgets/conftest.py login: authenticate as the fresh user with no project.

    The package's login creates a project and a budget group this module does not use.
    """
    frontend_url = CredentialsManager.get_parameter("FRONTEND_URL", "")
    LoginPage(page).login_suppressing_popups(
        personal_budget_user.email,
        personal_budget_user.password,
        personal_budget_user.user_id,
        frontend_url,
    )


# @case spend-values-use-inconsistent-decimal_TC_001
# @case spend-values-use-inconsistent-decimal_TC_003
@pytest.mark.enterprise
@pytest.mark.budget
@pytest.mark.timeout(1800)
@pytest.mark.ui
def test_personal_spending_shows_own_spend_of_every_category_in_cents(
    page,
    personal_budget_user,
    personal_budget_assistant,
    lite_llm_budget_utils,
    default_llm,
):
    user = personal_budget_user
    # Platform through assistant chat, cli and premium through /v1/messages; all settled first.
    spends = generate_personal_spend_on_every_category(
        user, personal_budget_assistant, default_llm, lite_llm_budget_utils
    )
    assert_personal_spend_is_recorded_on_every_category(spends)
    personal_rows = wait_for_personal_rows_with_own_spend(
        user.client, spends, lite_llm_budget_utils
    )
    assert_platform_spend_has_more_than_two_decimals(
        find_personal_platform_row(personal_rows, user.email)
    )

    spending = PersonalSpendingPage(page).open()
    api_rows = read_rows(user.client)

    assert_api_lists_only_the_personal_rows(api_rows, personal_rows)
    spending.should_show_table()
    # 'Your spending' and 'Available' of every row: the API value rounded half up to cents.
    spending.should_match_budget_usage(api_rows)
    # The same format on every category: exactly 2 decimals, never the full sub-cent value.
    spending.should_show_amounts_with_two_decimals(api_rows)
    # Platform: 'Your spending' is the sub-cent API spend rounded half up, e.g. 0.0067 -> $0.01.
    spending.should_show_usage_block(find_personal_platform_row(api_rows, user.email))
