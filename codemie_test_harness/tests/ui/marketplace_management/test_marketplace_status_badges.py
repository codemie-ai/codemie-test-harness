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

"""UI tests for the marketplace review badges (REVIEW, REJECTED, VERIFIED) of assistants.

States are set up through API calls: a plain user submits, the admin decides.
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.assistants.assistant_view_page import (
    AssistantViewPage,
)
from codemie_test_harness.tests.ui.pageobject.assistants.assistants_marketplace_page import (
    AssistantsMarketplacePage,
)
from codemie_test_harness.tests.ui.pageobject.assistants.assistants_page import (
    AssistantsPage,
)
from codemie_test_harness.tests.ui.test_data.marketplace_management_test_data import (
    BADGE_STATE_PARAMS,
)


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.prod_regression
@pytest.mark.parametrize("acting_credentials", ["submitter"], indirect=True)
@pytest.mark.parametrize("state, expected_status, expected_label", BADGE_STATE_PARAMS)
def test_submitter_sees_badge_for_each_review_state(
    page, assistant_in_marketplace_state, state, expected_status, expected_label
):
    # @case marketplace-admin-approval-gate_TC_014
    created = assistant_in_marketplace_state(state)
    assistants_page = AssistantsPage(page)
    assistants_page.navigate_to()
    assistants_page.should_be_on_assistants_page()

    assistants_page.search_assistants(created.name)

    assistants_page.should_see_status_badge(
        created.name, expected_status, expected_label
    )


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.parametrize("acting_credentials", ["submitter"], indirect=True)
def test_submitter_sees_verified_badge_on_own_published_assistant(
    page, approved_assistant
):
    # @case marketplace-admin-approval-gate_TC_014
    # An approved assistant is global, so it is listed under the Marketplace tab,
    # not under Project Assistants.
    approved = approved_assistant()
    marketplace_page = AssistantsMarketplacePage(page).navigate_to()

    marketplace_page.search_until_listed(approved.name)

    marketplace_page.should_see_verified_badge_on_card(approved.name)


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.prod_regression
@pytest.mark.parametrize("acting_credentials", ["submitter"], indirect=True)
def test_rejected_badge_carries_the_rejection_reason(page, rejected_assistant):
    # @case marketplace-admin-approval-gate_TC_014
    rejected = rejected_assistant()
    assistants_page = AssistantsPage(page)
    assistants_page.navigate_to()
    assistants_page.should_be_on_assistants_page()

    assistants_page.search_assistants(rejected.name)

    assistants_page.should_see_rejection_reason_on_badge(
        rejected.name, rejected.decision_reason
    )


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.ui
def test_verified_badge_shows_on_marketplace_card(page, approved_assistant):
    # @case marketplace-admin-approval-gate_TC_015
    approved = approved_assistant()
    marketplace_page = AssistantsMarketplacePage(page).navigate_to()

    marketplace_page.search_until_listed(approved.name)

    marketplace_page.should_see_verified_badge_on_card(approved.name)


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.ui
def test_verified_badge_shows_in_assistant_detail_header(page, approved_assistant):
    # @case marketplace-admin-approval-gate_TC_015
    approved = approved_assistant()
    marketplace_page = AssistantsMarketplacePage(page).navigate_to()
    marketplace_page.search_until_listed(approved.name)
    marketplace_page.click_assistant_card(approved.name)

    AssistantViewPage(page).should_see_verified_badge_in_header()
