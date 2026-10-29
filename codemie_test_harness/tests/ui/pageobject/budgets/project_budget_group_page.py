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

"""Page object for the Project Budget Group distribution modal.

URL: /settings/administration/projects/{project_name}

Locators derived from live UI inspection on 2026-09-02.

For a project admin with distribution access:
  - "Manage Budget" button opens the distribution-only modal directly (no dropdown).
  - Modal heading: "Update Budget".
  - Total Budget spinbutton is disabled (read-only).
  - Category hard-limit spinbuttons are editable.
  - Submit button: "Update Budget".

For a maintainer/platform admin:
  - "Manage Budget" opens a dropdown; "Edit Budget" opens the full modal.
  - Full modal exposes Name, Reset Period, Description, Budget Owner fields.
"""

from playwright.sync_api import expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


class ProjectBudgetGroupPage(BasePage):
    """Project details page — budget group distribution section.

    Used by project-admin UI tests.
    """

    PATH_TEMPLATE = "/settings/administration/projects/{project_name}"

    # ── Locators ──────────────────────────────────────────────────────────────

    def path(self, project_name: str) -> str:
        """Return the URL path for a specific project's detail page."""
        return self.PATH_TEMPLATE.format(project_name=project_name)

    @property
    def manage_budget_button(self):
        """'Manage Budget' button.

        For a project admin (distribution-only mode) this opens the modal
        directly.  For maintainers it opens a dropdown.
        """
        return self.page.get_by_role("button", name="Manage Budget")

    @property
    def update_budget_modal(self):
        """The 'Update Budget' dialog element."""
        return self.page.get_by_role("dialog")

    @property
    def modal_heading(self):
        """Heading inside the budget update modal."""
        return self.page.get_by_role("heading", name="Update Budget")

    @property
    def total_budget_input(self):
        """Total Budget spinbutton (disabled in distribution-only mode)."""
        return self.page.get_by_role("spinbutton", name="Total Budget ($)")

    @property
    def total_budget_required_marker(self):
        """Total Budget required asterisk marker (aria-hidden)."""
        return self.page.locator(
            '//label[contains(text(), "Total Budget ($)")]/span[@aria-hidden="true" and text()="*"]'
        )

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
    def submit_button(self):
        """'Update Budget' submit button inside the modal."""
        return self.page.get_by_role("button", name="Update Budget")

    @property
    def cancel_button(self):
        """'Cancel' button inside the modal."""
        return self.page.get_by_role("button", name="Cancel")

    @property
    def close_button(self):
        """Close (×) button in the modal header."""
        return self.page.get_by_role("button", name="Close")

    @property
    def error_toast_header(self):
        """Header text of the error toast notification."""
        return self.error_toast.locator(".codemie-toast-header")

    # ── Actions ───────────────────────────────────────────────────────────────

    @step
    def navigate_to(self, project_name: str):
        """Navigate to the project details page and wait for it to load."""
        self.page.goto(self.path(project_name))
        self.page.wait_for_load_state("domcontentloaded", timeout=30000)
        return self

    @step
    def open_manage_budget_modal(self):
        """Click 'Manage Budget' to open the distribution modal.

        Assumes the caller is logged in as a project admin so the button opens
        the distribution-only modal directly (no intermediate dropdown).
        """
        self.manage_budget_button.click()
        self.page.wait_for_load_state("domcontentloaded", timeout=15000)
        expect(self.modal_heading).to_be_visible(timeout=10000)
        return self

    @step
    def set_platform_hard_limit(self, value: float):
        """Set the Platform category hard-limit value and blur, which commits it."""
        self.platform_hard_limit_input.fill(str(value))
        self.platform_hard_limit_input.blur()
        return self

    @step
    def set_platform_soft_limit(self, value: float):
        """Set the Platform category soft-limit value and blur; it must not exceed the hard limit."""
        self.platform_soft_limit_input.fill(str(value))
        self.platform_soft_limit_input.blur()
        return self

    @step
    def enter_platform_hard_limit(self, text: str):
        """Type text into the Platform hard limit and blur, which commits (or rejects) the value."""
        self.platform_hard_limit_input.fill(text)
        self.platform_hard_limit_input.blur()
        return self

    @step
    def set_cli_hard_limit(self, value: float):
        """Set the CLI category hard-limit value and blur, which commits it."""
        self.cli_hard_limit_input.fill(str(value))
        self.cli_hard_limit_input.blur()
        return self

    @step
    def set_premium_hard_limit(self, value: float):
        """Set the Premium Models category hard-limit value and blur, which commits it."""
        self.premium_hard_limit_input.fill(str(value))
        self.premium_hard_limit_input.blur()
        return self

    @step
    def submit_distribution(self):
        """Click 'Update Budget' and wait for the PUT response to be processed.

        Waits until either the modal closes (success path) or an error toast
        appears (failure path), so callers can safely read post-submission state
        without racing the backend.
        """
        self.submit_button.click()
        # React removes the dialog from the DOM on close; the toast is injected on error.
        self.page.wait_for_function(
            """() => {
                const dialog = document.querySelector('[role="dialog"]');
                const toast = document.querySelector('.codemie-toast-err');
                return !dialog || !!toast;
            }""",
            timeout=15000,
        )
        return self

    @step
    def close_modal(self):
        """Close the modal without saving changes."""
        self.close_button.click()
        return self

    # ── Assertions ────────────────────────────────────────────────────────────

    @step
    def should_show_distribution(self):
        """Assert the budget section with 'Manage Budget' button is visible."""
        expect(self.manage_budget_button).to_be_visible(timeout=15000)
        return self

    @step
    def should_show_modal(self):
        """Assert the Update Budget dialog is open."""
        expect(self.modal_heading).to_be_visible(timeout=10000)
        return self

    @step
    def should_have_total_budget_disabled(self):
        """Assert the Total Budget input is disabled (distribution-only mode)."""
        expect(self.total_budget_input).to_be_disabled()
        expect(self.total_budget_required_marker).to_be_visible()
        return self

    @step
    def should_show_validation_error(self, expected_text: str = None):
        """Assert an error toast is visible after submitting invalid data."""
        expect(self.error_toast).to_be_visible(timeout=10000)
        if expected_text:
            expect(self.error_toast_header).to_contain_text(expected_text)
        return self

    @step
    def should_not_show_validation_error(self):
        """Assert no error toast is present.

        Uses an explicit timeout so a transient backend error toast that appears
        briefly after networkidle is not silently missed.
        """
        expect(self.error_toast).not_to_be_visible(timeout=5000)
        return self

    @step
    def should_have_platform_value(self, value: float):
        """Assert the Platform hard-limit spinbutton has the expected value."""
        expect(self.platform_hard_limit_input).to_have_value(str(value))
        return self

    @step
    def should_have_platform_hard_limit(self, value: str):
        """Assert the Platform hard-limit spinbutton shows exactly value (e.g. '100')."""
        expect(self.platform_hard_limit_input).to_have_value(value, timeout=10000)
        return self
