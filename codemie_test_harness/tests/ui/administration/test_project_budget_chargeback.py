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

"""UI tests for configurable chargeback settings in project budget flows.

Feature: features:projectChargeback (must be enabled on the target environment).

Covered ACs:
    TC-01  AC2, AC3, AC4  — Toggle visible when flag on; reveals attribution group with default
    TC-02  AC4, AC5       — Attribution switch enabled/disabled based on cost center link
    TC-03  AC5, AC6       — Attribution switch disabled with hint when no cost center linked
    TC-04  AC1, AC7       — Full e2e: enable + cost_center attribution + save + round-trip verify
    TC-06  AC1, AC3, AC4  — Existing settings load correctly when modal is reopened
    B1    — Chargeback/Routing impact inside Financial summary; Overview
                            Chargeback value follows the switch; Routing impact always shown

Navigation path:
    /settings/administration/projects → click project name
    → Manage Budget button → Edit Budget link → UnifiedProjectBudgetModal

Cleanup strategy: create via API → mutate via UI → clean up via API.

Important: "Manage Budget" only appears when a project has at least one budget.
New projects use project_with_budget fixture which creates both a project and a
platform budget so that the Manage Budget button is present.
"""

import logging
import secrets

import pytest

from codemie_test_harness.tests.test_data.budget_test_data import (
    project_key_alias,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_details_page import (
    ProjectDetailsPage,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name

logger = logging.getLogger(__name__)


@pytest.fixture(scope="function")
def project_with_budget(
    project_utils, admin_project_budget_utils, lite_llm_budget_utils
):
    """Factory fixture: creates a project AND a budget group for it.

    The app requires a budget group (POST /v1/admin/project-budget-groups) to
    exist before the budget modal's Save button succeeds.  A single platform
    category at 100 % is sufficient for chargeback tests.

    Usage::

        def test_example(project_with_budget):
            proj = project_with_budget()                      # no cost center
            proj = project_with_budget(cost_center_id=cc_id) # with CC
    """
    created: list[list] = []  # [[project_name, group_id]]

    def _make(cost_center_id: str | None = None):
        proj = project_utils.create_project(
            name=get_random_name(),
            description="autotest chargeback budget project",
            cost_center_id=cost_center_id,
        )
        created.append([proj.name, None])
        group_response = admin_project_budget_utils.create_budget_group(
            project_name=proj.name,
            name=f"autotest-cb-{secrets.token_hex(4)}",
            categories={"platform": {"max_budget": 2.0, "soft_budget": 1.0}},
        )
        created[-1][1] = group_response["group_id"]
        return proj

    yield _make

    for project_name, group_id in created:
        try:
            lite_llm_budget_utils.delete_key_by_alias(
                project_key_alias(project_name, "platform")
            )
        except Exception as e:
            logger.warning(
                f"Failed to delete LiteLLM key for project {project_name} "
                f"category platform: {e}"
            )
        try:
            if group_id:
                admin_project_budget_utils.delete_budget_group(group_id)
        except Exception:
            pass
        try:
            project_utils.delete_project(project_name)
        except Exception:
            pass


@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_chargeback_toggle_visible_and_reveals_attribution_group(
    page,
    project_with_budget,
):
    """TC-01  AC2/AC3/AC4 — Enable chargeback toggle visible when flag on;
    reveals 'Attribute to a cost center' switch (project default) on enable.
    """
    test_project = project_with_budget()

    details_page = ProjectDetailsPage(page)
    details_page.navigate_to(test_project.name)
    modal = details_page.open_budget_config_modal()

    # Chargeback toggle must be visible
    modal.should_have_chargeback_toggle()

    # Enable chargeback — attribution group should appear
    modal.enable_chargeback_toggle()
    modal.should_have_attribution_group()

    # Default attribution is "project" (toggle unchecked)
    modal.should_have_attribution_selected("project")

    modal.cancel()


@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_attribution_switch_enabled_with_linked_cost_center(
    page,
    cost_center,
    project_with_budget,
):
    """TC-02  AC4/AC5 — Attribution switch is enabled when project has a linked
    cost center; toggling it shows/hides the active hint.
    """
    from playwright.sync_api import expect

    cc_id = cost_center()
    test_project = project_with_budget(cost_center_id=cc_id)

    details_page = ProjectDetailsPage(page)
    details_page.navigate_to(test_project.name)
    modal = details_page.open_budget_config_modal()

    modal.enable_chargeback_toggle()
    modal.should_have_attribution_group()

    # Attribution switch must NOT be disabled — a cost center is linked
    modal.attribution_toggle.wait_for(state="visible", timeout=5000)
    expect(modal.attribution_toggle).not_to_be_disabled(timeout=5000)

    # Toggle ON → cost_center attribution; active hint should appear
    modal.select_attribution("cost_center")
    modal.should_have_attribution_active_hint()

    # Toggle OFF → project attribution; switch returns to unchecked state.
    # Note: the hint text is rendered in a sr-only <div role="status"> that
    # Playwright reports as "visible" regardless of attribution state, so we
    # verify state via the toggle's checked attribute rather than hint absence.
    modal.select_attribution("project")
    modal.should_have_attribution_selected("project")

    modal.cancel()


@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_attribution_switch_disabled_hint_when_no_cost_center(
    page,
    project_with_budget,
):
    """TC-03  AC5/AC6 — Attribution switch is disabled with link-hint when
    project has no linked cost center.  Cancelling leaves the modal intact then
    closed.
    """
    # Project without a cost center
    test_project = project_with_budget()

    details_page = ProjectDetailsPage(page)
    details_page.navigate_to(test_project.name)
    modal = details_page.open_budget_config_modal()

    modal.enable_chargeback_toggle()
    modal.should_have_attribution_group()

    # Attribution switch must be DISABLED (no CC linked)
    modal.should_have_attribution_switch_disabled()

    # Disabled hint must be visible
    modal.should_have_attribution_disabled_hint()

    # Cancel — budget modal closes cleanly
    modal.cancel()


@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_chargeback_settings_round_trip_cost_center_attribution(
    page,
    cost_center,
    project_with_budget,
):
    """TC-04  AC1/AC7 — Enable chargeback + select cost_center attribution + save;
    reopen modal and verify both settings persisted (round-trip).
    """
    cc_id = cost_center()
    test_project = project_with_budget(cost_center_id=cc_id)

    details_page = ProjectDetailsPage(page)
    details_page.navigate_to(test_project.name)

    # First open: configure and save
    modal = details_page.open_budget_config_modal()
    modal.enable_chargeback_toggle()
    modal.select_attribution("cost_center")
    modal.save_budget_config()  # modal closes after successful save
    page.wait_for_load_state("networkidle")

    # Second open: verify round-trip persistence
    modal = details_page.open_budget_config_modal()
    modal.should_have_chargeback_toggle_checked()
    modal.should_have_attribution_selected("cost_center")

    modal.cancel()


@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_chargeback_settings_round_trip_project_attribution(
    page,
    project_with_budget,
):
    """TC-06  AC1/AC3/AC4 — Save budget with chargeback_enabled=true and
    attribution=project; reopen modal and verify both values persisted.
    """
    test_project = project_with_budget()

    details_page = ProjectDetailsPage(page)
    details_page.navigate_to(test_project.name)

    # First open: enable chargeback (leave attribution as default = project) and save
    modal = details_page.open_budget_config_modal()
    modal.enable_chargeback_toggle()
    modal.should_have_attribution_selected("project")  # default
    modal.save_budget_config()
    page.wait_for_load_state("networkidle")

    # Second open: verify persisted state
    modal = details_page.open_budget_config_modal()
    modal.should_have_chargeback_toggle_checked()
    modal.should_have_attribution_selected("project")

    modal.cancel()


@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_chargeback_and_routing_impact_are_inside_financial_summary(
    page,
    project_with_budget,
):
    """B1 — Chargeback and Routing impact sit inside the Financial
    summary card; the Overview's Chargeback value follows the budget modal's
    chargeback switch (Enabled/Disabled), and Routing impact stays visible in
    both chargeback states.
    """
    test_project = project_with_budget()

    details_page = ProjectDetailsPage(page)
    details_page.navigate_to(test_project.name)

    details_page.should_have_chargeback_and_routing_inside_financial_summary()
    details_page.should_show_routing_impact()

    # Enable chargeback → save → Overview should show "Enabled"
    modal = details_page.open_budget_config_modal()
    modal.enable_chargeback_toggle()
    modal.save_budget_config()
    page.wait_for_load_state("networkidle")
    details_page.should_have_chargeback_value("Enabled")
    details_page.should_show_routing_impact()

    # Disable chargeback → save → Overview should show "Disabled"
    modal = details_page.open_budget_config_modal()
    modal.disable_chargeback_toggle()
    modal.save_budget_config()
    page.wait_for_load_state("networkidle")
    details_page.should_have_chargeback_value("Disabled")
    details_page.should_show_routing_impact()
