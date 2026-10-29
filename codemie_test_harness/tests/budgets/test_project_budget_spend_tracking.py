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
from time import sleep

import pytest
from hamcrest import assert_that, close_to, has_length

from codemie_test_harness.tests.test_data.budget_test_data import (
    budget_chat_prompt,
    BUDGET_CACHE_DELAY,
    budget_chat_prompt_bigger,
)

logger = logging.getLogger(__name__)


@pytest.fixture(scope="function")
def lifecycle_project_with_platform_budget_enforce_on(
    lifecycle_project,
    user1_project_utils,
    project_budget_groups,
):
    project_name, user2_id = lifecycle_project
    user1_project_utils.set_enforce_member_spend_limits(project_name, True)
    budget = project_budget_groups.create(project_name)
    sleep(BUDGET_CACHE_DELAY)
    yield project_name, user2_id, budget.budget_ids["platform"], budget.alias()
    project_budget_groups.delete(budget, user2_id)


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.api
@pytest.mark.timeout(1000)
def test_two_users_chat_creates_member_and_project_rows(
    lifecycle_project_with_platform_budget,
    user1_assistant,
    user1_assistant_utils,
    user2_assistant,
    user2_assistant_utils,
    lite_llm_budget_utils,
    admin_spend_tracking_utils,
):
    project_name, _user2_id, _budget_id, alias = lifecycle_project_with_platform_budget
    today = datetime.date.today()

    logger.info("User1 creating assistant and chatting (project=%s)", project_name)
    user1_ast = user1_assistant(project_name=project_name)
    user1_assistant_utils.ask_assistant(user1_ast, budget_chat_prompt())

    logger.info("User2 creating assistant and chatting (project=%s)", project_name)
    user2_ast = user2_assistant(project_name=project_name)
    user2_assistant_utils.ask_assistant(user2_ast, budget_chat_prompt())

    logger.info("Waiting for platform key spend (alias=%s)", alias)
    lite_llm_budget_utils.wait_for_key_alias_spending_above(alias, 0)

    logger.info("Triggering async collect (project=%s)", project_name)
    admin_spend_tracking_utils.collect_spends_nowait()

    logger.info("Waiting for member_budget rows (project=%s)", project_name)
    spends_member = admin_spend_tracking_utils.wait_for_project_spends(
        project_name, today, today
    )

    assert_that(
        spends_member["rows"],
        has_length(2),
        "Expected exactly 2 member_budget rows — one per user.",
    )
    assert_that(
        sum(float(r["budget_period_spend"]) for r in spends_member["rows"]),
        close_to(spends_member["total_spend"], 0.0001),
        "Sum of member budget_period_spend must equal total_spend.",
    )
    assert_that(
        sum(float(r["cumulative_spend"]) for r in spends_member["rows"]),
        close_to(spends_member["total_spend"], 0.0001),
        "Sum of member cumulative_spend must equal total_spend.",
    )
    # Bootstrap: first snapshot daily_spend == budget_period_spend (no prior row)
    assert_that(
        float(spends_member["rows"][0]["daily_spend"]),
        close_to(float(spends_member["rows"][0]["budget_period_spend"]), 0.0001),
        "Member bootstrap row: daily_spend must equal budget_period_spend.",
    )
    assert_that(
        float(spends_member["rows"][1]["daily_spend"]),
        close_to(float(spends_member["rows"][1]["budget_period_spend"]), 0.0001),
        "Member bootstrap row: daily_spend must equal budget_period_spend.",
    )
    assert_that(
        sum(float(r["daily_spend"]) for r in spends_member["rows"]),
        close_to(spends_member["total_spend"], 0.0001),
        "Sum of member daily_spend must equal total_spend.",
    )

    logger.info("Verifying project_budget row (project=%s)", project_name)
    spends_project = admin_spend_tracking_utils.wait_for_project_spends(
        project_name, today, today, spend_subject_type="project_budget"
    )
    total_member_spend = spends_member["total_spend"]

    assert_that(
        spends_project["rows"],
        has_length(1),
        "Expected exactly 1 project_budget row.",
    )
    assert_that(
        float(spends_project["rows"][0]["budget_period_spend"]),
        close_to(total_member_spend, 0.0001),
        "project_budget budget_period_spend must equal total member spend.",
    )
    assert_that(
        float(spends_project["rows"][0]["cumulative_spend"]),
        close_to(total_member_spend, 0.0001),
        "project_budget cumulative_spend must equal total member spend.",
    )
    # Project bootstrap: daily_spend == budget_period_spend == cumulative_spend
    assert_that(
        float(spends_project["rows"][0]["daily_spend"]),
        close_to(float(spends_project["rows"][0]["budget_period_spend"]), 0.0001),
        "Project bootstrap row: daily_spend must equal budget_period_spend.",
    )
    # Cross-checks: member aggregates vs project scalar
    assert_that(
        sum(float(r["daily_spend"]) for r in spends_member["rows"]),
        close_to(float(spends_project["rows"][0]["budget_period_spend"]), 0.0001),
        "Sum of member daily_spend must equal project budget_period_spend.",
    )
    assert_that(
        sum(float(r["budget_period_spend"]) for r in spends_member["rows"]),
        close_to(float(spends_project["rows"][0]["budget_period_spend"]), 0.0001),
        "Sum of member budget_period_spend must equal project budget_period_spend.",
    )


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.api
@pytest.mark.timeout(1000)
def test_sequential_user_spend_accumulates_project_rows(
    lifecycle_project_with_platform_budget,
    user1_assistant,
    user1_assistant_utils,
    user2_assistant,
    user2_assistant_utils,
    lite_llm_budget_utils,
    admin_spend_tracking_utils,
):
    project_name, _user2_id, _budget_id, alias = lifecycle_project_with_platform_budget
    today = datetime.date.today()

    # Phase 1 — User1 only
    logger.info("Phase 1: user1 chats only (project=%s)", project_name)
    user1_ast = user1_assistant(project_name=project_name)
    user1_assistant_utils.ask_assistant(user1_ast, budget_chat_prompt())

    logger.info("Waiting for user1 key spend (alias=%s)", alias)
    lite_llm_budget_utils.wait_for_key_alias_spending(alias)

    logger.info("Triggering async collect after user1 spend (project=%s)", project_name)
    admin_spend_tracking_utils.collect_spends_nowait()

    logger.info("Waiting for member_budget row (project=%s)", project_name)
    spends_member_p1 = admin_spend_tracking_utils.wait_for_project_spends(
        project_name, today, today
    )

    assert_that(
        spends_member_p1["rows"],
        has_length(1),
        "Expected 1 member_budget row after user1 spend.",
    )
    user1_spend = float(spends_member_p1["rows"][0]["budget_period_spend"])
    # Bootstrap: daily_spend == budget_period_spend on the first row
    assert_that(
        float(spends_member_p1["rows"][0]["daily_spend"]),
        close_to(user1_spend, 0.0001),
        "Phase1 member bootstrap: daily_spend must equal budget_period_spend.",
    )

    spends_project_p1 = admin_spend_tracking_utils.wait_for_project_spends(
        project_name, today, today, spend_subject_type="project_budget"
    )

    assert_that(
        spends_project_p1["rows"],
        has_length(1),
        "Expected 1 project_budget row after user1 spend.",
    )
    assert_that(
        float(spends_project_p1["rows"][0]["budget_period_spend"]),
        close_to(user1_spend, 0.0001),
        "project_budget budget_period_spend must equal user1_spend.",
    )
    assert_that(
        float(spends_project_p1["rows"][0]["cumulative_spend"]),
        close_to(user1_spend, 0.0001),
        "project_budget cumulative_spend must equal user1_spend.",
    )
    # Project bootstrap: daily_spend == budget_period_spend == cumulative_spend
    assert_that(
        float(spends_project_p1["rows"][0]["daily_spend"]),
        close_to(float(spends_project_p1["rows"][0]["budget_period_spend"]), 0.0001),
        "Project Phase1 bootstrap: daily_spend must equal budget_period_spend.",
    )

    # Phase 2 — User2 added
    logger.info("Phase 2: user2 also chats (project=%s)", project_name)
    user2_ast = user2_assistant(project_name=project_name)
    user2_assistant_utils.ask_assistant(user2_ast, budget_chat_prompt())

    logger.info("Waiting for key spend above user1_spend (alias=%s)", alias)
    lite_llm_budget_utils.wait_for_key_alias_spending_above(alias, user1_spend)

    logger.info("Running blocking collect after user2 spend (project=%s)", project_name)
    admin_spend_tracking_utils.collect_spends()

    spends_member_p2 = admin_spend_tracking_utils.get_project_spends(
        project_name, today, today
    )

    assert_that(
        spends_member_p2["rows"],
        has_length(2),
        "Expected 2 member_budget rows after both users spent.",
    )
    assert_that(
        sum(float(r["budget_period_spend"]) for r in spends_member_p2["rows"]),
        close_to(spends_member_p2["total_spend"], 0.0001),
        "Sum of member budget_period_spend must equal total_spend.",
    )
    assert_that(
        sum(float(r["daily_spend"]) for r in spends_member_p2["rows"]),
        close_to(spends_member_p2["total_spend"], 0.0001),
        "Sum of member daily_spend must equal total_spend.",
    )
    # No-reset invariant: each row's budget_period_spend == cumulative_spend
    assert_that(
        float(spends_member_p2["rows"][0]["budget_period_spend"]),
        close_to(float(spends_member_p2["rows"][0]["cumulative_spend"]), 0.0001),
        "Member row: budget_period_spend must equal cumulative_spend (no reset).",
    )
    assert_that(
        float(spends_member_p2["rows"][1]["budget_period_spend"]),
        close_to(float(spends_member_p2["rows"][1]["cumulative_spend"]), 0.0001),
        "Member row: budget_period_spend must equal cumulative_spend (no reset).",
    )

    spends_project_p2 = admin_spend_tracking_utils.get_project_spends(
        project_name, today, today, spend_subject_type="project_budget"
    )
    total_member_spend = spends_member_p2["total_spend"]

    assert_that(
        spends_project_p2["rows"],
        has_length(2),
        "Expected 2 project_budget rows after both users spent.",
    )
    sorted_project_rows = sorted(
        spends_project_p2["rows"], key=lambda r: float(r["cumulative_spend"])
    )
    latest_row = sorted_project_rows[-1]

    assert_that(
        float(latest_row["budget_period_spend"]),
        close_to(total_member_spend, 0.0001),
        "Latest project_budget budget_period_spend must equal total member spend.",
    )
    assert_that(
        float(latest_row["cumulative_spend"]),
        close_to(total_member_spend, 0.0001),
        "Latest project_budget cumulative_spend must equal total member spend.",
    )
    # No-reset invariant: project last budget_period_spend == cumulative_spend
    assert_that(
        float(latest_row["budget_period_spend"]),
        close_to(float(latest_row["cumulative_spend"]), 0.0001),
        "Project latest row: budget_period_spend must equal cumulative_spend (no reset).",
    )
    # Cross-checks: member aggregates vs project latest scalars
    assert_that(
        sum(float(r["budget_period_spend"]) for r in spends_member_p2["rows"]),
        close_to(float(latest_row["cumulative_spend"]), 0.0001),
        "Sum of member budget_period_spend must equal project latest cumulative_spend.",
    )
    assert_that(
        sum(float(r["daily_spend"]) for r in spends_member_p2["rows"]),
        close_to(float(latest_row["budget_period_spend"]), 0.0001),
        "Sum of member daily_spend must equal project latest budget_period_spend.",
    )
    assert_that(
        sum(float(r["budget_period_spend"]) for r in spends_member_p2["rows"]),
        close_to(float(latest_row["budget_period_spend"]), 0.0001),
        "Sum of member budget_period_spend must equal project latest budget_period_spend.",
    )


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.api
@pytest.mark.timeout(1000)
def test_spend_accumulates_across_collect_cycles_enforce_off(
    lifecycle_project_with_platform_budget,
    user1_assistant,
    user1_assistant_utils,
    user2_assistant,
    user2_assistant_utils,
    lite_llm_budget_utils,
    admin_spend_tracking_utils,
):
    project_name, _user2_id, _, alias = lifecycle_project_with_platform_budget
    today = datetime.date.today()

    # Phase 1 — initial spending
    logger.info("Phase 1: user1 and user2 chat (project=%s)", project_name)
    user1_ast = user1_assistant(project_name=project_name)
    user1_assistant_utils.ask_assistant(user1_ast, budget_chat_prompt())
    user2_ast = user2_assistant(project_name=project_name)
    user2_assistant_utils.ask_assistant(user2_ast, budget_chat_prompt())

    logger.info("Waiting for platform key spend (alias=%s)", alias)
    lite_llm_budget_utils.wait_for_key_alias_spending_above(alias, 0)

    logger.info("Triggering async collect (project=%s)", project_name)
    admin_spend_tracking_utils.collect_spends()

    logger.info("Waiting for member_budget rows (project=%s)", project_name)
    spends_member = admin_spend_tracking_utils.wait_for_project_spends(
        project_name, today, today
    )

    assert_that(
        spends_member["rows"],
        has_length(2),
        "Expected 2 member_budget rows after Phase 1.",
    )
    key_info = lite_llm_budget_utils.get_key_info_by_alias(alias)
    key_spend = float(key_info["spend"])
    assert_that(
        spends_member["total_spend"],
        close_to(key_spend, 0.0001),
        "total_spend must match LiteLLM key spend.",
    )
    assert_that(
        sum(float(r["daily_spend"]) for r in spends_member["rows"]),
        close_to(spends_member["total_spend"], 0.0001),
        "Sum of member daily_spend must equal total_spend.",
    )
    assert_that(
        sum(float(r["cumulative_spend"]) for r in spends_member["rows"]),
        close_to(spends_member["total_spend"], 0.0001),
        "Sum of member cumulative_spend must equal total_spend.",
    )

    spends_project = admin_spend_tracking_utils.wait_for_project_spends(
        project_name, today, today, spend_subject_type="project_budget"
    )

    assert_that(
        spends_project["rows"],
        has_length(1),
        "Expected 1 project_budget row after Phase 1.",
    )
    assert_that(
        float(spends_project["rows"][0]["daily_spend"]),
        close_to(spends_member["total_spend"], 0.0001),
        "project_budget daily_spend must equal total member spend.",
    )
    assert_that(
        float(spends_project["rows"][0]["cumulative_spend"]),
        close_to(spends_member["total_spend"], 0.0001),
        "project_budget cumulative_spend must equal total member spend.",
    )
    # Phase 1 bootstrap invariants
    assert_that(
        float(spends_member["rows"][0]["daily_spend"]),
        close_to(float(spends_member["rows"][0]["budget_period_spend"]), 0.0001),
        "Phase1 member bootstrap: daily_spend must equal budget_period_spend.",
    )
    assert_that(
        float(spends_member["rows"][1]["daily_spend"]),
        close_to(float(spends_member["rows"][1]["budget_period_spend"]), 0.0001),
        "Phase1 member bootstrap: daily_spend must equal budget_period_spend.",
    )
    assert_that(
        sum(float(r["budget_period_spend"]) for r in spends_member["rows"]),
        close_to(spends_member["total_spend"], 0.0001),
        "Sum of member budget_period_spend must equal total_spend.",
    )
    assert_that(
        float(spends_project["rows"][0]["budget_period_spend"]),
        close_to(spends_member["total_spend"], 0.0001),
        "project_budget budget_period_spend must equal total member spend.",
    )
    assert_that(
        sum(float(r["budget_period_spend"]) for r in spends_member["rows"]),
        close_to(float(spends_project["rows"][0]["budget_period_spend"]), 0.0001),
        "Sum of member budget_period_spend must equal project budget_period_spend.",
    )
    assert_that(
        sum(float(r["daily_spend"]) for r in spends_member["rows"]),
        close_to(float(spends_project["rows"][0]["budget_period_spend"]), 0.0001),
        "Sum of member daily_spend must equal project budget_period_spend.",
    )

    # Phase 2 — additional spending (no reset)
    logger.info("Phase 2: user1 and user2 chat again (project=%s)", project_name)
    user1_assistant_utils.ask_assistant(user1_ast, budget_chat_prompt_bigger())
    user2_assistant_utils.ask_assistant(user2_ast, budget_chat_prompt_bigger())

    logger.info("Waiting for platform key spend to exceed Phase 1 (alias=%s)", alias)
    lite_llm_budget_utils.wait_for_key_alias_spending_above(alias, key_spend)

    logger.info("Blocking collect after Phase 2 spend (project=%s)", project_name)
    admin_spend_tracking_utils.collect_spends()

    spends_member_post = admin_spend_tracking_utils.get_project_spends(
        project_name, today, today
    )

    assert_that(
        spends_member_post["rows"],
        has_length(4),
        "Expected 4 member_budget rows (2 Phase 1 + 2 Phase 2).",
    )
    assert_that(
        sum(float(r["daily_spend"]) for r in spends_member_post["rows"]),
        close_to(spends_member_post["total_spend"], 0.0001),
        "Sum of member daily_spend must equal total_spend.",
    )

    spends_project_post = admin_spend_tracking_utils.get_project_spends(
        project_name, today, today, spend_subject_type="project_budget"
    )

    assert_that(
        spends_project_post["rows"],
        has_length(2),
        "Expected 2 project_budget rows (1 Phase 1 + 1 Phase 2).",
    )
    sorted_project_rows = sorted(
        spends_project_post["rows"], key=lambda r: float(r["cumulative_spend"])
    )
    last_row = sorted_project_rows[-1]

    assert_that(
        sum(float(r["daily_spend"]) for r in sorted_project_rows),
        close_to(float(last_row["cumulative_spend"]), 0.0001),
        "Sum of project daily_spend must equal last row cumulative_spend.",
    )
    assert_that(
        spends_member_post["total_spend"],
        close_to(float(last_row["cumulative_spend"]), 0.0001),
        "Total member spend must equal last project row cumulative_spend.",
    )
    # Phase 2 per-cycle invariants
    sorted_dates = sorted(set(r["spend_date"] for r in spends_member_post["rows"]))
    phase2_member_rows = [
        r for r in spends_member_post["rows"] if r["spend_date"] == sorted_dates[-1]
    ]
    assert_that(
        phase2_member_rows,
        has_length(2),
        "Expected 2 member_budget rows in the Phase2 collect cycle.",
    )
    assert_that(
        float(phase2_member_rows[0]["budget_period_spend"]),
        close_to(float(phase2_member_rows[0]["cumulative_spend"]), 0.0001),
        "Phase2 member row: budget_period_spend must equal cumulative_spend (no reset).",
    )
    assert_that(
        float(phase2_member_rows[1]["budget_period_spend"]),
        close_to(float(phase2_member_rows[1]["cumulative_spend"]), 0.0001),
        "Phase2 member row: budget_period_spend must equal cumulative_spend (no reset).",
    )
    assert_that(
        float(last_row["budget_period_spend"]),
        close_to(float(last_row["cumulative_spend"]), 0.0001),
        "Project last row: budget_period_spend must equal cumulative_spend (no reset).",
    )
    assert_that(
        sum(float(r["budget_period_spend"]) for r in phase2_member_rows),
        close_to(float(last_row["cumulative_spend"]), 0.0001),
        "Sum of Phase2 member budget_period_spend must equal project last cumulative_spend.",
    )
    assert_that(
        spends_member_post["total_spend"],
        close_to(float(last_row["budget_period_spend"]), 0.0001),
        "total_spend must equal project last budget_period_spend.",
    )
    assert_that(
        sum(float(r["budget_period_spend"]) for r in phase2_member_rows),
        close_to(float(last_row["budget_period_spend"]), 0.0001),
        "Sum of Phase2 member budget_period_spend must equal project last budget_period_spend.",
    )


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.api
@pytest.mark.timeout(1000)
def test_spend_accumulates_across_collect_cycles_enforce_on(
    lifecycle_project_with_platform_budget_enforce_on,
    user1_assistant,
    user1_assistant_utils,
    user2_assistant,
    user2_assistant_utils,
    lite_llm_budget_utils,
    admin_spend_tracking_utils,
):
    project_name, _user2_id, _, alias = (
        lifecycle_project_with_platform_budget_enforce_on
    )
    today = datetime.date.today()

    # Phase 1 — initial spending
    logger.info("Phase 1: user1 and user2 chat enforce-ON (project=%s)", project_name)
    user1_ast = user1_assistant(project_name=project_name)
    user1_assistant_utils.ask_assistant(user1_ast, budget_chat_prompt())
    user2_ast = user2_assistant(project_name=project_name)
    user2_assistant_utils.ask_assistant(user2_ast, budget_chat_prompt())

    logger.info("Waiting for platform key spend (alias=%s)", alias)
    lite_llm_budget_utils.wait_for_key_alias_spending_above(alias, 0)

    logger.info("Triggering async collect (project=%s)", project_name)
    admin_spend_tracking_utils.collect_spends()

    logger.info("Waiting for member_budget rows (project=%s)", project_name)
    spends_member = admin_spend_tracking_utils.wait_for_project_spends(
        project_name, today, today
    )

    assert_that(
        spends_member["rows"],
        has_length(2),
        "Expected 2 member_budget rows after Phase 1 (enforce-ON).",
    )
    key_info = lite_llm_budget_utils.get_key_info_by_alias(alias)
    key_spend = float(key_info["spend"])
    assert_that(
        spends_member["total_spend"],
        close_to(key_spend, 0.0001),
        "total_spend must match LiteLLM key spend.",
    )
    assert_that(
        sum(float(r["daily_spend"]) for r in spends_member["rows"]),
        close_to(spends_member["total_spend"], 0.0001),
        "Sum of member daily_spend must equal total_spend.",
    )
    assert_that(
        sum(float(r["cumulative_spend"]) for r in spends_member["rows"]),
        close_to(spends_member["total_spend"], 0.0001),
        "Sum of member cumulative_spend must equal total_spend.",
    )

    spends_project = admin_spend_tracking_utils.wait_for_project_spends(
        project_name, today, today, spend_subject_type="project_budget"
    )

    assert_that(
        spends_project["rows"],
        has_length(1),
        "Expected 1 project_budget row after Phase 1 (enforce-ON).",
    )
    assert_that(
        float(spends_project["rows"][0]["daily_spend"]),
        close_to(spends_member["total_spend"], 0.0001),
        "project_budget daily_spend must equal total member spend.",
    )
    assert_that(
        float(spends_project["rows"][0]["cumulative_spend"]),
        close_to(spends_member["total_spend"], 0.0001),
        "project_budget cumulative_spend must equal total member spend.",
    )
    # Phase 1 bootstrap invariants
    assert_that(
        float(spends_member["rows"][0]["daily_spend"]),
        close_to(float(spends_member["rows"][0]["budget_period_spend"]), 0.0001),
        "Phase1 member bootstrap: daily_spend must equal budget_period_spend.",
    )
    assert_that(
        float(spends_member["rows"][1]["daily_spend"]),
        close_to(float(spends_member["rows"][1]["budget_period_spend"]), 0.0001),
        "Phase1 member bootstrap: daily_spend must equal budget_period_spend.",
    )
    assert_that(
        sum(float(r["budget_period_spend"]) for r in spends_member["rows"]),
        close_to(spends_member["total_spend"], 0.0001),
        "Sum of member budget_period_spend must equal total_spend.",
    )
    assert_that(
        float(spends_project["rows"][0]["budget_period_spend"]),
        close_to(spends_member["total_spend"], 0.0001),
        "project_budget budget_period_spend must equal total member spend.",
    )
    assert_that(
        sum(float(r["budget_period_spend"]) for r in spends_member["rows"]),
        close_to(float(spends_project["rows"][0]["budget_period_spend"]), 0.0001),
        "Sum of member budget_period_spend must equal project budget_period_spend.",
    )
    assert_that(
        sum(float(r["daily_spend"]) for r in spends_member["rows"]),
        close_to(float(spends_project["rows"][0]["budget_period_spend"]), 0.0001),
        "Sum of member daily_spend must equal project budget_period_spend.",
    )

    # Phase 2 — additional spending
    logger.info(
        "Phase 2: user1 and user2 chat again enforce-ON (project=%s)", project_name
    )
    user1_assistant_utils.ask_assistant(user1_ast, budget_chat_prompt_bigger())
    user2_assistant_utils.ask_assistant(user2_ast, budget_chat_prompt_bigger())

    logger.info("Waiting for key spend to exceed Phase 1 (alias=%s)", alias)
    lite_llm_budget_utils.wait_for_key_alias_spending_above(alias, key_spend)

    logger.info("Blocking collect after Phase 2 spend (project=%s)", project_name)
    admin_spend_tracking_utils.collect_spends()

    spends_member_post = admin_spend_tracking_utils.get_project_spends(
        project_name, today, today
    )

    assert_that(
        spends_member_post["rows"],
        has_length(4),
        "Expected 4 member_budget rows (2 Phase 1 + 2 Phase 2, enforce-ON).",
    )
    assert_that(
        sum(float(r["daily_spend"]) for r in spends_member_post["rows"]),
        close_to(spends_member_post["total_spend"], 0.0001),
        "Sum of member daily_spend must equal total_spend.",
    )

    spends_project_post = admin_spend_tracking_utils.get_project_spends(
        project_name, today, today, spend_subject_type="project_budget"
    )

    assert_that(
        spends_project_post["rows"],
        has_length(2),
        "Expected 2 project_budget rows (1 Phase 1 + 1 Phase 2, enforce-ON).",
    )
    sorted_project_rows = sorted(
        spends_project_post["rows"], key=lambda r: float(r["cumulative_spend"])
    )
    last_row = sorted_project_rows[-1]

    assert_that(
        sum(float(r["daily_spend"]) for r in sorted_project_rows),
        close_to(float(last_row["cumulative_spend"]), 0.0001),
        "Sum of project daily_spend must equal last row cumulative_spend.",
    )
    assert_that(
        spends_member_post["total_spend"],
        close_to(float(last_row["cumulative_spend"]), 0.0001),
        "Total member spend must equal last project row cumulative_spend.",
    )
    # Phase 2 per-cycle invariants
    sorted_dates = sorted(set(r["spend_date"] for r in spends_member_post["rows"]))
    phase2_member_rows = [
        r for r in spends_member_post["rows"] if r["spend_date"] == sorted_dates[-1]
    ]
    assert_that(
        phase2_member_rows,
        has_length(2),
        "Expected 2 member_budget rows in the Phase2 collect cycle.",
    )
    assert_that(
        float(phase2_member_rows[0]["budget_period_spend"]),
        close_to(float(phase2_member_rows[0]["cumulative_spend"]), 0.0001),
        "Phase2 member row: budget_period_spend must equal cumulative_spend (no reset).",
    )
    assert_that(
        float(phase2_member_rows[1]["budget_period_spend"]),
        close_to(float(phase2_member_rows[1]["cumulative_spend"]), 0.0001),
        "Phase2 member row: budget_period_spend must equal cumulative_spend (no reset).",
    )
    assert_that(
        float(last_row["budget_period_spend"]),
        close_to(float(last_row["cumulative_spend"]), 0.0001),
        "Project last row: budget_period_spend must equal cumulative_spend (no reset).",
    )
    assert_that(
        sum(float(r["budget_period_spend"]) for r in phase2_member_rows),
        close_to(float(last_row["cumulative_spend"]), 0.0001),
        "Sum of Phase2 member budget_period_spend must equal project last cumulative_spend.",
    )
    assert_that(
        spends_member_post["total_spend"],
        close_to(float(last_row["budget_period_spend"]), 0.0001),
        "total_spend must equal project last budget_period_spend.",
    )
    assert_that(
        sum(float(r["budget_period_spend"]) for r in phase2_member_rows),
        close_to(float(last_row["budget_period_spend"]), 0.0001),
        "Sum of Phase2 member budget_period_spend must equal project last budget_period_spend.",
    )
