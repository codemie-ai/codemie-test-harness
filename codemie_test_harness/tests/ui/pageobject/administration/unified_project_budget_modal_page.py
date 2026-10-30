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

"""Page object for the UnifiedProjectBudgetModal dialog.

The modal is opened from ProjectDetailsPage via Manage Budget → Edit Budget.
It exposes budget configuration including the ChargebackSettings section
(rendered when features:projectChargeback is enabled).

Confirmed locators captured with playwright-cli on 2026-09-02 against a
preview environment:

  Enable chargeback switch  → role=switch, name="Enable chargeback"  (id=chargeback_enabled)
  Attribution switch        → role=switch, name="Attribute to a cost center" (id=chargeback_use_cost_center)
  Submit button             → role=button, name="Update Budget"
  Cancel button             → role=button, name="Cancel"
  Disabled-CC hint          → "Link a cost center to this project on the project edit form to enable this."
  Enabled-CC hint           → "Charge this project's spend to its linked cost center instead of the project's own code."
"""

import re

from playwright.sync_api import expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


class InlineCostCenterPopupPage:
    """Nested helper for the inline cost center creation popup.

    NOTE: This popup path (Create Cost Center from within the budget modal) is
    only reachable when the backend serves the inline-creation variant of the
    ChargebackSettings UI.  As of 2026-09-02 the preview environment does not
    expose this path — the 'Attribute to a cost center' toggle is disabled when
    no cost center is linked and there is no inline creation button.  Methods
    here serve as extension points for future test coverage.
    """

    def __init__(self, page):
        self.page = page

    @property
    def popup_container(self):
        return self.page.locator('[role="dialog"]').filter(
            has_text="Create Cost Center"
        )

    @step
    def should_be_open(self):
        expect(self.popup_container).to_be_visible(timeout=5000)
        return self

    @step
    def fill_name(self, name: str):
        self.popup_container.get_by_label("Name").fill(name)
        return self

    @step
    def submit(self):
        self.popup_container.get_by_role("button", name="Create").click()
        expect(self.popup_container).not_to_be_visible(timeout=10000)
        return self

    @step
    def cancel(self):
        self.popup_container.get_by_role("button", name="Cancel").click()
        expect(self.popup_container).not_to_be_visible(timeout=5000)
        return self


class UnifiedProjectBudgetModalPage(BasePage):
    """Page object for the 'Update Budget' dialog in the project administration flow."""

    # ── Locators ──────────────────────────────────────────────────────────────

    @property
    def dialog(self):
        """The top-level 'Update Budget' dialog element.

        Scoped to the dialog containing 'Update Budget' to avoid a Playwright
        strict-mode violation when a second dialog (e.g. the inline CC creation
        popup) is open at the same time.
        """
        return self.page.get_by_role("dialog").filter(has_text="Update Budget")

    @property
    def chargeback_toggle(self):
        """'Enable chargeback' switch (id=chargeback_enabled)."""
        return self.page.get_by_role("switch", name="Enable chargeback")

    @property
    def attribution_toggle(self):
        """'Attribute to a cost center' switch (id=chargeback_use_cost_center).

        Only rendered when chargeback is enabled AND features:costCenters is on.
        Disabled when no cost center is linked to the project.
        """
        return self.page.get_by_role("switch", name="Attribute to a cost center")

    @property
    def submit_button(self):
        """'Update Budget' submit button."""
        return self.page.get_by_role("button", name="Update Budget")

    @property
    def cancel_button(self):
        """'Cancel' button — closes the modal without saving."""
        return self.page.get_by_role("button", name="Cancel")

    @property
    def budget_name_field(self):
        """'Name *' text input in the budget form."""
        return self.page.get_by_placeholder("Budget name")

    @property
    def attribution_disabled_hint(self):
        """Hint shown when attribution toggle is disabled (no CC linked)."""
        return self.page.get_by_text(
            "Link a cost center to this project on the project edit form to enable this."
        )

    @property
    def attribution_active_hint(self):
        """Hint shown when attribution is set to cost_center and CC is linked."""
        return self.page.get_by_text(
            "Charge this project's spend to its linked cost center"
            " instead of the project's own code."
        )

    @property
    def total_budget_input(self):
        """Total Budget spinbutton (editable in the full Edit Budget modal)."""
        return self.page.get_by_role("spinbutton", name="Total Budget ($)")

    @property
    def platform_hard_limit_input(self):
        """Platform category hard-limit spinbutton."""
        return self.page.get_by_role("spinbutton", name="Platform hard limit")

    @property
    def cli_hard_limit_input(self):
        """CLI category hard-limit spinbutton."""
        return self.page.get_by_role("spinbutton", name="CLI hard limit")

    @property
    def premium_hard_limit_input(self):
        """Premium Models category hard-limit spinbutton."""
        return self.page.get_by_role("spinbutton", name="Premium Models hard limit")

    @property
    def platform_soft_limit_input(self):
        """Platform category soft-limit spinbutton."""
        return self.page.get_by_role("spinbutton", name="Platform soft limit")

    @property
    def cli_soft_limit_input(self):
        """CLI category soft-limit spinbutton."""
        return self.page.get_by_role("spinbutton", name="CLI soft limit")

    @property
    def premium_soft_limit_input(self):
        """Premium Models category soft-limit spinbutton."""
        return self.page.get_by_role("spinbutton", name="Premium Models soft limit")

    @property
    def allocation_slider(self):
        """DISTRIBUTION bar (role=slider) with the Platform / CLI / Premium Models handles."""
        return self.page.get_by_role("slider", name="Budget allocation slider")

    @property
    def reset_to_default_button(self):
        """'Reset to Default' button of the DISTRIBUTION section."""
        return self.page.get_by_role("button", name="Reset to Default")

    @property
    def cc_popup(self) -> InlineCostCenterPopupPage:
        """Nested helper for the inline cost center creation popup."""
        return InlineCostCenterPopupPage(self.page)

    # ── Actions ───────────────────────────────────────────────────────────────

    @step
    def enable_chargeback_toggle(self):
        """Click the 'Enable chargeback' switch to turn it ON.

        The underlying <input> is sr-only; force=True is required to bypass the
        decorative <span> that intercepts pointer events in the custom switch UI.
        """
        expect(self.chargeback_toggle).to_be_visible(timeout=5000)
        expect(self.chargeback_toggle).not_to_be_disabled(timeout=5000)
        if not self.chargeback_toggle.is_checked():
            self.chargeback_toggle.click(force=True)
        return self

    @step
    def disable_chargeback_toggle(self):
        """Click the 'Enable chargeback' switch to turn it OFF."""
        expect(self.chargeback_toggle).to_be_visible(timeout=5000)
        expect(self.chargeback_toggle).not_to_be_disabled(timeout=5000)
        if self.chargeback_toggle.is_checked():
            self.chargeback_toggle.click(force=True)
        return self

    @step
    def select_attribution(self, value: str):
        """Set attribution target: 'cost_center' turns the switch ON; 'project' turns it OFF.

        Precondition: chargeback must already be enabled and the toggle must not be disabled.
        """
        if value not in ("cost_center", "project"):
            raise ValueError(
                f"Unknown attribution value: {value!r}; expected 'cost_center' or 'project'"
            )
        expect(self.attribution_toggle).to_be_visible(timeout=5000)
        expect(self.attribution_toggle).not_to_be_disabled(timeout=5000)
        if value == "cost_center":
            if not self.attribution_toggle.is_checked():
                self.attribution_toggle.click(force=True)
        else:
            if self.attribution_toggle.is_checked():
                self.attribution_toggle.click(force=True)
        return self

    @step
    def enter_platform_hard_limit(self, text: str):
        """Type text into 'Platform hard limit' and blur, which commits (or rejects) the value."""
        self._enter_and_blur(self.platform_hard_limit_input, text)
        return self

    @step
    def enter_total_budget(self, text: str):
        """Type text into 'Total Budget ($)' and blur."""
        self._enter_and_blur(self.total_budget_input, text)
        return self

    @step
    def set_limits_to_zero(self, *limits: str):
        """Set the named non-Platform-hard limits to 0 and blur each.

        Names: cli_hard, premium_hard, platform_soft, cli_soft, premium_soft.
        A typed value recalculates no other field, so zeroing a limit leaves the category
        total off 100% until the test types a compensating value (see enter_limits).
        """
        for limit in limits:
            self._enter_and_blur(self._limit_input(limit), "0")
        return self

    @step
    def enter_limits(self, *entries: tuple):
        """Type each (limit name, text) pair into its input and blur (names as in set_limits_to_zero)."""
        for limit, text in entries:
            self._enter_and_blur(self._limit_input(limit), text)
        return self

    @step
    def drag_platform_handle_fully_left(self):
        """Drag the Platform handle (first handle) of the allocation slider past the left edge.

        The handle sits at the Platform share of the bar (30% by default); the pointer is
        released beyond the left edge so the bar clamps to its minimum.
        """
        self.allocation_slider.scroll_into_view_if_needed()
        box = self.allocation_slider.bounding_box()
        y = box["y"] + box["height"] / 2
        self.page.mouse.move(box["x"] + box["width"] * 0.3, y)
        self.page.mouse.down()
        self.page.mouse.move(box["x"] - 100, y, steps=15)
        self.page.mouse.up()
        return self

    @step
    def reset_to_default_distribution(self):
        """Click 'Reset to Default' to restore the default Platform / CLI / Premium split."""
        self.reset_to_default_button.click()
        return self

    def _limit_input(self, limit: str):
        inputs = {
            "cli_hard": self.cli_hard_limit_input,
            "premium_hard": self.premium_hard_limit_input,
            "platform_soft": self.platform_soft_limit_input,
            "cli_soft": self.cli_soft_limit_input,
            "premium_soft": self.premium_soft_limit_input,
        }
        if limit not in inputs:
            raise ValueError(
                f"Unknown limit {limit!r}; expected one of {sorted(inputs)}"
            )
        return inputs[limit]

    def _enter_and_blur(self, field, text: str):
        field.fill(text)
        field.blur()

    @step
    def save_budget_config(self, budget_name: str = "Autotest Budget"):
        """Click 'Update Budget' to persist the configuration."""
        expect(self.submit_button).to_be_enabled(timeout=5000)
        with self.page.expect_response(
            lambda r: r.request.method == "GET"
            and re.search(r"/v1/projects/[^/?]+(\?|$)", r.url),
            timeout=15000,
        ) as project_refresh_info:
            with self.page.expect_response(
                lambda r: r.request.method == "PUT"
                and re.search(r"/admin/project-budget-groups/[^/]+/?$", r.url),
                timeout=15000,
            ) as put_info:
                self.submit_button.click()
            assert put_info.value.ok, (
                f"Budget save request failed with HTTP {put_info.value.status}"
            )
        assert project_refresh_info.value.ok, (
            "Project chargeback-state refresh failed with HTTP "
            f"{project_refresh_info.value.status}"
        )
        # Modal should close after a successful save
        expect(self.dialog).not_to_be_visible(timeout=15000)
        return self

    @step
    def cancel(self):
        """Click 'Cancel' to close the modal without saving."""
        self.cancel_button.click()
        expect(self.dialog).not_to_be_visible(timeout=5000)
        return self

    @step
    def click_create_cost_center(self):
        """Click the inline 'Create Cost Center' action.

        NOTE: Only available in the inline-CC-creation variant of the UI
        (currently not deployed on preview as of 2026-09-02).
        """
        btn = self.page.get_by_role("button", name="Create Cost Center")
        expect(btn).to_be_visible(timeout=5000)
        btn.click()
        return self.cc_popup

    # ── Assertions ────────────────────────────────────────────────────────────

    @step
    def should_be_visible(self):
        """Verify the 'Update Budget' dialog is open."""
        expect(self.dialog).to_be_visible(timeout=15000)
        return self

    @step
    def should_have_chargeback_toggle(self):
        """Verify the 'Enable chargeback' toggle is rendered in the modal."""
        expect(self.chargeback_toggle).to_be_visible(timeout=10000)
        return self

    @step
    def should_not_have_chargeback_section(self):
        """Verify the chargeback toggle is absent (features:projectChargeback disabled)."""
        expect(self.chargeback_toggle).not_to_be_visible(timeout=5000)
        return self

    @step
    def should_have_chargeback_toggle_checked(self):
        """Verify 'Enable chargeback' switch is ON."""
        expect(self.chargeback_toggle).to_be_checked(timeout=5000)
        return self

    @step
    def should_have_chargeback_toggle_unchecked(self):
        """Verify 'Enable chargeback' switch is OFF."""
        expect(self.chargeback_toggle).not_to_be_checked(timeout=5000)
        return self

    @step
    def should_have_attribution_group(self):
        """Verify the 'Attribute to a cost center' toggle is rendered."""
        expect(self.attribution_toggle).to_be_visible(timeout=5000)
        return self

    @step
    def should_have_attribution_selected(self, value: str):
        """Assert attribution toggle state: 'cost_center' → checked; 'project' → unchecked."""
        if value not in ("cost_center", "project"):
            raise ValueError(
                f"Unknown attribution value: {value!r}; expected 'cost_center' or 'project'"
            )
        if value == "cost_center":
            expect(self.attribution_toggle).to_be_checked(timeout=5000)
        else:
            expect(self.attribution_toggle).not_to_be_checked(timeout=5000)
        return self

    @step
    def should_have_attribution_switch_disabled(self):
        """Verify attribution toggle is rendered but disabled (no CC linked)."""
        expect(self.attribution_toggle).to_be_visible(timeout=5000)
        expect(self.attribution_toggle).to_be_disabled(timeout=5000)
        return self

    @step
    def should_have_attribution_disabled_hint(self):
        """Verify the 'Link a cost center...' hint is visible for a project without a CC."""
        expect(self.attribution_disabled_hint).to_be_visible(timeout=5000)
        return self

    @step
    def should_have_attribution_active_hint(self):
        """Verify the 'Charge this project's spend...' hint for cost_center attribution."""
        expect(self.attribution_active_hint).to_be_visible(timeout=5000)
        return self

    @step
    def should_have_chargeback_readonly(self):
        """Verify chargeback toggle is disabled (non-editor view)."""
        expect(self.chargeback_toggle).to_be_visible(timeout=10000)
        expect(self.chargeback_toggle).to_be_disabled(timeout=5000)
        return self

    @step
    def should_have_create_cost_center_button(self):
        """Verify the inline 'Create Cost Center' button is present.

        NOTE: Only available in the inline-CC variant of the UI.
        """
        btn = self.page.get_by_role("button", name="Create Cost Center")
        expect(btn).to_be_visible(timeout=5000)
        return self

    @step
    def should_have_platform_hard_limit(self, value: str):
        """Assert the 'Platform hard limit' input shows exactly value (e.g. '300', '0.10')."""
        expect(self.platform_hard_limit_input).to_have_value(value, timeout=10000)
        return self

    @step
    def should_not_have_platform_hard_limit(self, value: str):
        """Assert the 'Platform hard limit' input no longer shows value."""
        expect(self.platform_hard_limit_input).not_to_have_value(value, timeout=5000)
        return self

    @step
    def should_have_platform_hard_limit_above_zero(self):
        """Assert the 'Platform hard limit' input shows a number greater than 0."""
        expect(self.platform_hard_limit_input).to_have_value(
            re.compile(r"^(?:[1-9]\d*(?:\.\d+)?|0\.\d*[1-9]\d*)$"), timeout=10000
        )
        return self

    @step
    def should_have_zero_limits(self, *limits: str):
        """Assert the named limits (see set_limits_to_zero) show 0."""
        for limit in limits:
            expect(self._limit_input(limit)).to_have_value("0", timeout=10000)
        return self

    @step
    def should_have_hard_limits(self, platform: str, cli: str, premium: str):
        """Assert the three hard limit inputs show exactly the given texts (e.g. '300', '0', '100')."""
        expect(self.platform_hard_limit_input).to_have_value(platform, timeout=10000)
        expect(self.cli_hard_limit_input).to_have_value(cli, timeout=10000)
        expect(self.premium_hard_limit_input).to_have_value(premium, timeout=10000)
        return self

    @step
    def get_linked_cost_center_name(self) -> str:
        """Return the cost center name shown in the budget modal when one is linked."""
        cc_label = self.page.locator('[data-testid="linked-cost-center-name"]')
        expect(cc_label).to_be_visible(timeout=5000)
        return cc_label.inner_text()
