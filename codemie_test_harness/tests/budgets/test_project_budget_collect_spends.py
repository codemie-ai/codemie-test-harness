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

import datetime
import logging

import pytest
from hamcrest import assert_that, close_to, equal_to, greater_than, has_length

from codemie_test_harness.tests.test_data.budget_test_data import budget_chat_prompt

logger = logging.getLogger(__name__)


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_collect_spends_creates_single_row_per_subject_type(
    user_assistant,
    user_assistant_utils,
    lite_llm_budget_utils,
    project_with_platform_budget,
    admin_spend_tracking_utils,
):
    project_name, budget_id, platform_alias = project_with_platform_budget
    created_assistant = user_assistant(project_name=project_name)

    logger.info(
        "Sending chat request to accumulate spending (project=%s)", project_name
    )
    user_assistant_utils.ask_assistant(created_assistant, budget_chat_prompt())

    logger.info(
        "Waiting for LiteLLM to record platform key spend (alias=%s)", platform_alias
    )
    lite_llm_budget_utils.wait_for_key_alias_spending(platform_alias)

    today = datetime.date.today()

    # Fire async collect and wait for the member_budget row to appear
    logger.info("Triggering async spend collection (project=%s)", project_name)
    admin_spend_tracking_utils.collect_spends_nowait()

    logger.info(
        "Waiting for member_budget row after nowait collect (project=%s)", project_name
    )
    spends_after_nowait = admin_spend_tracking_utils.wait_for_project_spends(
        project_name, today, today
    )
    assert_that(
        len(spends_after_nowait["rows"]),
        equal_to(1),
        "Expected exactly 1 member_budget row after async collect.",
    )

    # Run blocking collect and verify no duplicate rows were created
    logger.info("Running blocking spend collection (project=%s)", project_name)
    admin_spend_tracking_utils.collect_spends()

    logger.info(
        "Verifying row count is unchanged after blocking collect (project=%s)",
        project_name,
    )
    spends_after_blocking = admin_spend_tracking_utils.wait_for_project_spends(
        project_name, today, today
    )
    assert_that(
        len(spends_after_blocking["rows"]),
        equal_to(1),
        "Blocking collect must not create duplicate member_budget rows.",
    )
    assert_that(
        spends_after_blocking["total_spend"],
        close_to(spends_after_nowait["total_spend"], 0.0001),
        "Total spend must not change after second collect.",
    )

    # Verify project_budget row also exists with matching spend
    logger.info("Verifying project_budget row exists (project=%s)", project_name)
    spends_project_budget = admin_spend_tracking_utils.wait_for_project_spends(
        project_name, today, today, spend_subject_type="project_budget"
    )
    assert_that(
        len(spends_project_budget["rows"]),
        equal_to(1),
        "Expected exactly 1 project_budget row.",
    )
    assert_that(
        spends_project_budget["total_spend"],
        close_to(spends_after_blocking["total_spend"], 0.0001),
        "project_budget total_spend must match member_budget total_spend.",
    )

    # Verify no personal budget or legacy key rows were created for this project
    logger.info("Verifying no budget or key rows exist (project=%s)", project_name)
    spends_budget = admin_spend_tracking_utils.get_project_spends(
        project_name, today, today, spend_subject_type="budget"
    )
    assert_that(
        len(spends_budget["rows"]),
        equal_to(0),
        "No personal budget rows expected for project budget scenario.",
    )
    spends_key = admin_spend_tracking_utils.get_project_spends(
        project_name, today, today, spend_subject_type="key"
    )
    assert_that(
        len(spends_key["rows"]),
        equal_to(0),
        "No legacy key rows expected.",
    )


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_collect_spends_creates_single_budget_row_for_personal_spending(
    keycloak_user,
    user_assistant,
    user_assistant_utils,
    lite_llm_budget_utils,
    admin_spend_tracking_utils,
):
    email, _ = keycloak_user
    created_assistant = user_assistant(project_name=email)

    logger.info("Sending chat request to accumulate personal spending (user=%s)", email)
    user_assistant_utils.ask_assistant(created_assistant, budget_chat_prompt())

    logger.info("Waiting for personal LiteLLM customer spend (user=%s)", email)
    customer = lite_llm_budget_utils.wait_for_spending(email)
    assert_that(float(customer["spend"]), greater_than(0))

    today = datetime.date.today()

    # Fire async collect and wait for the budget row to appear
    logger.info("Triggering async spend collection (project=%s)", email)
    admin_spend_tracking_utils.collect_spends_nowait()

    logger.info("Waiting for budget row after nowait collect (project=%s)", email)
    spends_after_nowait = admin_spend_tracking_utils.wait_for_project_spends(
        email, today, today
    )
    assert_that(
        len(spends_after_nowait["rows"]),
        equal_to(1),
        "Expected exactly 1 budget row after async collect.",
    )

    # Run blocking collect and verify no duplicate rows were created
    logger.info("Running blocking spend collection (project=%s)", email)
    admin_spend_tracking_utils.collect_spends()

    logger.info(
        "Verifying row count is unchanged after blocking collect (project=%s)", email
    )
    spends_after_blocking = admin_spend_tracking_utils.wait_for_project_spends(
        email, today, today
    )
    assert_that(
        len(spends_after_blocking["rows"]),
        equal_to(1),
        "Blocking collect must not create duplicate budget rows.",
    )
    assert_that(
        spends_after_blocking["total_spend"],
        close_to(spends_after_nowait["total_spend"], 0.0001),
        "Total spend must not change after second collect.",
    )

    # Confirm the row is explicitly typed as budget (budget type is returned by default,
    # so this call returns the same result as the default — confirming the type)
    logger.info("Verifying explicit budget-type row (project=%s)", email)
    spends_budget_explicit = admin_spend_tracking_utils.wait_for_project_spends(
        email, today, today, spend_subject_type="budget"
    )
    assert_that(
        len(spends_budget_explicit["rows"]),
        equal_to(1),
        "Expected exactly 1 budget-type row.",
    )
    assert_that(
        spends_budget_explicit["total_spend"],
        close_to(spends_after_blocking["total_spend"], 0.0001),
        "budget-type total_spend must match default total_spend.",
    )

    # Verify no project budget or legacy key rows were created
    logger.info(
        "Verifying no member_budget, project_budget, or key rows (project=%s)", email
    )
    spends_member_budget = admin_spend_tracking_utils.get_project_spends(
        email, today, today, spend_subject_type="member_budget"
    )
    assert_that(
        len(spends_member_budget["rows"]),
        equal_to(0),
        "No member_budget rows expected for personal spending.",
    )
    spends_project_budget = admin_spend_tracking_utils.get_project_spends(
        email, today, today, spend_subject_type="project_budget"
    )
    assert_that(
        len(spends_project_budget["rows"]),
        equal_to(0),
        "No project_budget rows expected for personal spending.",
    )
    spends_key = admin_spend_tracking_utils.get_project_spends(
        email, today, today, spend_subject_type="key"
    )
    assert_that(
        len(spends_key["rows"]),
        equal_to(0),
        "No legacy key rows expected.",
    )


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_collect_spends_creates_one_member_row_per_user(
    lifecycle_project_with_platform_budget,
    user1_assistant,
    user1_assistant_utils,
    user2_assistant,
    user2_assistant_utils,
    lite_llm_budget_utils,
    admin_spend_tracking_utils,
):
    project_name, _user2_id, _budget_id, platform_alias = (
        lifecycle_project_with_platform_budget
    )

    logger.info("User1 creating assistant and chatting (project=%s)", project_name)
    created_user1_assistant = user1_assistant(project_name=project_name)
    user1_assistant_utils.ask_assistant(created_user1_assistant, budget_chat_prompt())

    logger.info("User2 creating assistant and chatting (project=%s)", project_name)
    created_user2_assistant = user2_assistant(project_name=project_name)
    user2_assistant_utils.ask_assistant(created_user2_assistant, budget_chat_prompt())

    logger.info(
        "Waiting for LiteLLM to record platform key spend (alias=%s)", platform_alias
    )
    lite_llm_budget_utils.wait_for_key_alias_spending(platform_alias)

    today = datetime.date.today()

    # First collect — both users' spends should be written in a single batch
    logger.info("Triggering spend collection (project=%s)", project_name)
    admin_spend_tracking_utils.collect_spends()

    logger.info(
        "Waiting for member_budget rows after async collect (project=%s)", project_name
    )
    spends_member = admin_spend_tracking_utils.wait_for_project_spends(
        project_name, today, today
    )
    assert_that(
        spends_member["rows"],
        has_length(2),
        "Expected exactly 2 member_budget rows — one per user.",
    )

    logger.info(
        "Verifying project_budget row matches member_budget total (project=%s)",
        project_name,
    )
    spends_project = admin_spend_tracking_utils.wait_for_project_spends(
        project_name, today, today, spend_subject_type="project_budget"
    )
    assert_that(
        spends_project["rows"],
        has_length(1),
        "Expected exactly 1 project_budget row.",
    )
    assert_that(
        spends_project["total_spend"],
        close_to(spends_member["total_spend"], 0.0001),
        "project_budget total_spend must equal the sum of member_budget rows.",
    )

    # Second collect — must be idempotent: no new rows, no spend change
    logger.info(
        "Running second (blocking) spend collection to verify idempotency (project=%s)",
        project_name,
    )
    admin_spend_tracking_utils.collect_spends()

    logger.info(
        "Verifying row counts and totals are unchanged after second collect (project=%s)",
        project_name,
    )
    spends_member_after = admin_spend_tracking_utils.get_project_spends(
        project_name, today, today
    )
    assert_that(
        spends_member_after["rows"],
        has_length(2),
        "Second collect must not create duplicate member_budget rows.",
    )
    assert_that(
        spends_member_after["total_spend"],
        close_to(spends_member["total_spend"], 0.0001),
        "member_budget total_spend must not change after second collect.",
    )

    spends_project_after = admin_spend_tracking_utils.get_project_spends(
        project_name, today, today, spend_subject_type="project_budget"
    )
    assert_that(
        spends_project_after["rows"],
        has_length(1),
        "Second collect must not create duplicate project_budget rows.",
    )
    assert_that(
        spends_project_after["total_spend"],
        close_to(spends_project["total_spend"], 0.0001),
        "project_budget total_spend must not change after second collect.",
    )
