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


"""Page object for the confirmation shown when Save changes the 'Enforce member spend limits' switch.

Rendered by the Edit Project modal on /settings/administration/projects as a second dialog
above it. FE source of truth (codemie-ui):
  src/pages/settings/administration/projectsManagement/components/EnforcementConfirmation.tsx
    (confirm data-testid 'enforce-confirm', disabled while the confirmed save is in flight;
    cancel data-testid 'enforce-cancel')
  src/constants/projectEnforcement.ts (header, explanation and button copy)
The dialog is a PrimeReact Dialog, so its accessible name is its header text.
"""

import re

from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.test_data.project_enforcement_test_data import (
    TURN_OFF_BUTTON,
    TURN_OFF_CLAUSES,
    TURN_OFF_HEADER,
    TURN_ON_BUTTON,
    TURN_ON_CLAUSES,
    TURN_ON_HEADER,
)

CONFIRMATION_HEADER = re.compile(r"Turn (on|off) member spend limit enforcement\?")


class EnforcementConfirmationDialog(BasePage):
    """Confirm / Cancel dialog for switching member spend limit enforcement."""

    @property
    def dialog(self) -> Locator:
        """The enforcement confirmation dialog, told apart from Edit Project by its name."""
        return self.page.get_by_role("dialog", name=CONFIRMATION_HEADER)

    @property
    def confirm_button(self) -> Locator:
        """The 'Turn on enforcement' / 'Turn off enforcement' button."""
        return self.dialog.get_by_test_id("enforce-confirm")

    @property
    def cancel_button(self) -> Locator:
        """The Cancel button of the confirmation."""
        return self.dialog.get_by_test_id("enforce-cancel")

    def _dialog_named(self, header: str) -> Locator:
        return self.page.get_by_role("dialog", name=header, exact=True)

    @step
    def confirm(self):
        """Click the confirm button."""
        self.confirm_button.click()
        return self

    @step
    def cancel(self):
        """Click Cancel."""
        self.cancel_button.click()
        return self

    @step
    def press_escape(self):
        """Press the Escape key, then let the browser render two frames so a dialog that the
        key closes is gone before any "still open" assertion runs."""
        self.page.keyboard.press("Escape")
        self.page.evaluate(
            "() => new Promise(resolve => requestAnimationFrame("
            "() => requestAnimationFrame(resolve)))"
        )
        return self

    @step
    def click_confirm_capturing_save(self, project_name: str):
        """Click the confirm button and wait until the browser has sent the project PATCH."""
        with self.page.expect_request(
            lambda r: r.method == "PATCH" and f"/v1/projects/{project_name}" in r.url,
            timeout=15000,
        ):
            self.confirm_button.click()
        return self

    @step
    def double_click_confirm_capturing_save(self, project_name: str):
        """Double-click the confirm button and wait until the browser has sent the first
        project PATCH. Whether the second click sends another one is for the caller to count."""
        with self.page.expect_request(
            lambda r: r.method == "PATCH" and f"/v1/projects/{project_name}" in r.url,
            timeout=15000,
        ):
            self.confirm_button.dblclick()
        return self

    @step
    def click_cancel_while_pending(self):
        """Click Cancel while the confirmed save is in flight, then let the browser render two
        frames so a dialog the click closes is gone before any "still open" assertion runs."""
        self.cancel_button.click()
        self.page.evaluate(
            "() => new Promise(resolve => requestAnimationFrame("
            "() => requestAnimationFrame(resolve)))"
        )
        return self

    @step
    def should_be_visible(self):
        """Verify the confirmation is open with Confirm and Cancel offered."""
        expect(self.dialog).to_be_visible()
        expect(self.confirm_button).to_be_visible()
        expect(self.cancel_button).to_be_visible()
        return self

    @step
    def should_be_pending(self):
        """Verify the confirmation is still open and its confirm button is disabled, which is
        how the UI shows that the confirmed save is in flight."""
        expect(self.dialog).to_be_visible()
        expect(self.confirm_button).to_be_disabled()
        return self

    @step
    def should_be_closed(self):
        """Verify the confirmation is gone."""
        expect(self.dialog).not_to_be_visible()
        return self

    def _should_explain(self, header: str, clauses: tuple, button: str):
        dialog = self._dialog_named(header)
        expect(dialog).to_be_visible()
        for clause in clauses:
            expect(dialog).to_contain_text(clause)
        expect(self.confirm_button).to_have_text(button)
        return self

    @step
    def should_explain_turning_on(self):
        """Verify the header, every explanation clause and the confirm button of turning
        enforcement ON."""
        return self._should_explain(TURN_ON_HEADER, TURN_ON_CLAUSES, TURN_ON_BUTTON)

    @step
    def should_explain_turning_off(self):
        """Verify the header, every explanation clause and the confirm button of turning
        enforcement OFF."""
        return self._should_explain(TURN_OFF_HEADER, TURN_OFF_CLAUSES, TURN_OFF_BUTTON)

    @step
    def should_explain(self, turning_on: bool):
        """Verify the explanation that matches the direction of the change."""
        if turning_on:
            return self.should_explain_turning_on()
        return self.should_explain_turning_off()
