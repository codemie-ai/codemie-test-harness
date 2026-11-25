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

"""'Context compression (Headroom)' controls.

The same controls render in the assistant form (Extra configuration), the workflow
config panel (Advanced tab) and the assistant node panel (codemie-ui HeadroomConfig.tsx
and HeadroomPanel): a switch, two checkboxes and a Strategy select.
"""

import re

from playwright.sync_api import Locator, Page, expect
from reportportal_client import step

# The select's root carries this class while compression is off.
DISABLED_SELECT_CLASS = re.compile(r"\bp-disabled\b")


class HeadroomSettings:
    """Headroom controls inside ``scope`` (the page, or the region that holds them)."""

    def __init__(self, page: Page, scope):
        self.page = page
        self.scope = scope

    # ── Locators ─────────────────────────────────────────────────────────────────

    @property
    def enable_switch(self) -> Locator:
        """'Enable context compression' switch (1x1 px input under the visible track)."""
        return self.scope.get_by_role("switch", name="Enable context compression")

    @property
    def compress_user_input_checkbox(self) -> Locator:
        """'Compress user input' checkbox; disabled while compression is off."""
        return self.scope.get_by_role("checkbox", name="Compress user input")

    @property
    def compress_tool_outputs_checkbox(self) -> Locator:
        """'Compress tool outputs' checkbox; disabled while compression is off."""
        return self.scope.get_by_role("checkbox", name="Compress tool outputs")

    @property
    def strategy_select(self) -> Locator:
        """Strategy select - PrimeReact dropdown root, found by its labelled input.

        The root shows the selected option's label (Lossless, Balanced or Aggressive).
        """
        return self.scope.locator("div.p-dropdown").filter(
            has=self.page.get_by_label("Strategy", exact=True)
        )

    @property
    def strategy_options(self) -> Locator:
        """Options of the open Strategy select, scoped to the overlay listbox.

        The dropdown also renders a hidden native select whose options are always in
        the DOM; the overlay listbox holds only the visible ones.
        """
        return self.page.locator('ul[role="listbox"]').get_by_role("option")

    # ── Actions ──────────────────────────────────────────────────────────────────

    def _set_checked(self, control: Locator, checked: bool):
        """Set a switch or checkbox by a DOM click; a pointer click is intercepted."""
        expect(control).to_be_attached()
        if control.is_checked() != checked:
            control.evaluate("element => element.click()")
        expect(control).to_be_checked(checked=checked)

    @step
    def set_enabled(self, enabled: bool):
        """Turn context compression on or off."""
        self._set_checked(self.enable_switch, enabled)
        return self

    @step
    def set_compress_user_input(self, checked: bool):
        """Check or uncheck 'Compress user input' (compression must be on)."""
        self._set_checked(self.compress_user_input_checkbox, checked)
        return self

    @step
    def set_compress_tool_outputs(self, checked: bool):
        """Check or uncheck 'Compress tool outputs' (compression must be on)."""
        self._set_checked(self.compress_tool_outputs_checkbox, checked)
        return self

    @step
    def select_strategy(self, label: str):
        """Open the Strategy select and choose an option by its label."""
        self.strategy_select.click()
        self.strategy_options.get_by_text(label, exact=True).click()
        expect(self.strategy_options).to_have_count(0)
        expect(self.strategy_select).to_contain_text(label)
        return self

    # ── Verifications ────────────────────────────────────────────────────────────

    @step
    def should_be_visible(self):
        """Verify the switch, both checkboxes and the Strategy select are shown."""
        expect(self.enable_switch).to_be_attached()
        expect(self.compress_user_input_checkbox).to_be_visible()
        expect(self.compress_tool_outputs_checkbox).to_be_visible()
        expect(self.strategy_select).to_be_visible()
        return self

    @step
    def should_have_enabled(self, enabled: bool):
        """Verify the 'Enable context compression' switch state."""
        expect(self.enable_switch).to_be_checked(checked=enabled)
        return self

    @step
    def should_have_options_disabled(self):
        """Verify both checkboxes and the Strategy select are disabled."""
        expect(self.compress_user_input_checkbox).to_be_disabled()
        expect(self.compress_tool_outputs_checkbox).to_be_disabled()
        expect(self.strategy_select).to_have_class(DISABLED_SELECT_CLASS)
        return self

    @step
    def should_have_settings(
        self,
        enabled: bool,
        compress_user_input: bool,
        compress_tool_outputs: bool,
        strategy: str,
    ):
        """Verify the switch, both checkboxes and the selected strategy label."""
        expect(self.enable_switch).to_be_checked(checked=enabled)
        expect(self.compress_user_input_checkbox).to_be_checked(
            checked=compress_user_input
        )
        expect(self.compress_tool_outputs_checkbox).to_be_checked(
            checked=compress_tool_outputs
        )
        expect(self.strategy_select).to_contain_text(strategy)
        return self

    @step
    def should_have_strategy(self, strategy: str):
        """Verify the selected strategy label."""
        expect(self.strategy_select).to_contain_text(strategy)
        return self
