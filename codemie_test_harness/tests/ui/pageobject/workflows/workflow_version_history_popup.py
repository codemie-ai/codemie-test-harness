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

"""WorkflowVersionHistoryPopup page-object component.

Covers the popup that opens when a user clicks the 'Version History' button
in the YAML editor header actions (WorkflowYamlHeaderActions.tsx).

Evidence:
  WorkflowVersionHistoryPopup.tsx      — full-width overlay, version combobox
  VersionHistoryDiffView.tsx:11        — Previous Version / Current Version buttons
  VersionHistoryDiffView.tsx:78        — side-by-side diff content
  VersionedFieldHistoryTab.tsx:48      — Restore hidden when canWrite=false
  VersionedFieldHistoryTab.tsx:100     — ConfirmationModal with restore warning text
"""

from hamcrest import assert_that, greater_than_or_equal_to, matches_regexp
from playwright.sync_api import Locator, Page, expect
from reportportal_client import step


class WorkflowVersionHistoryPopup:
    """Component for the workflow version history popup overlay.

    Opened by clicking the 'Version History' button (aria-label='Version History'
    or 'Version History (YAML)') in the YAML editor header actions.
    The popup shows a version combobox for selection and a diff view with
    'Previous Version' / 'Current Version' comparison buttons.
    """

    def __init__(self, page: Page):
        self.page = page

    # ==========================================================================
    # PROPERTIES — UI ELEMENTS
    # ==========================================================================

    @property
    def popup_container(self) -> Locator:
        """WorkflowVersionHistoryPopup overlay container.

        The popup is rendered as a dialog identified by the 'Version History'
        heading inside it.
        """
        return self.page.get_by_role("dialog").filter(
            has=self.page.get_by_role("heading", name="Version History")
        )

    # ------ Version selector ------

    @property
    def version_selector_toggle(self) -> Locator:
        """Dropdown toggle button that opens the version selector combobox."""
        return self.popup_container.get_by_role("button", name="Select a version")

    @property
    def version_entries(self) -> Locator:
        """Version option elements in the open combobox dropdown.

        Only visible when the combobox is open (after clicking version_selector_toggle).
        """
        return self.page.get_by_role("option")

    # ------ Diff comparison buttons ------

    @property
    def previous_version_tab(self) -> Locator:
        """'Previous Version' comparison button.

        Compares the selected version against its immediate predecessor.
        Disabled when the selected version has no predecessor (VersionHistoryDiffView.tsx:11).
        """
        return self.popup_container.get_by_role("button", name="Previous Version")

    @property
    def current_version_tab(self) -> Locator:
        """'Current Version' comparison button.

        Compares the selected version against the current editor state
        (VersionHistoryDiffView.tsx:11).
        """
        return self.popup_container.get_by_role("button", name="Current Version")

    @property
    def restore_button(self) -> Locator:
        """Restore button inside the popup (absent when canWrite=false).

        Hidden entirely — not just disabled — for read-only users
        (VersionedFieldHistoryTab.tsx:48).
        """
        return self.popup_container.get_by_role("button", name="Restore")

    # ------ ConfirmationModal ------

    @property
    def restore_confirmation_dialog(self) -> Locator:
        """ConfirmationModal that appears after clicking Restore.

        Identified by the exact warning text that warns the user that
        unsaved changes will be lost (VersionedFieldHistoryTab.tsx:100).
        """
        return self.page.get_by_role("dialog").filter(
            has=self.page.get_by_text("Restore this version?")
        )

    @property
    def confirm_restore_button(self) -> Locator:
        """Primary action button inside the confirmation modal."""
        return self.restore_confirmation_dialog.get_by_role("button", name="Restore")

    # ==========================================================================
    # METHODS — ACTIONS
    # ==========================================================================

    @step
    def wait_for_visible(self, timeout: int = 10_000):
        """Wait for the popup to become visible."""
        self.popup_container.wait_for(state="visible", timeout=timeout)

    @step
    def select_version_entry(self, index: int = 0):
        """Select a version by zero-based index from the combobox dropdown.

        The popup auto-selects the first (most-recent) entry on open, so
        index=0 is typically a no-op.  For index > 0, opens the dropdown
        and clicks the nth option.

        Args:
            index: 0 = most-recent entry (auto-selected on popup open).
        """
        if index == 0:
            # First entry is auto-selected when popup opens.
            return
        self.version_selector_toggle.click()
        entries = self.version_entries
        entries.first.wait_for(state="visible")
        entries.nth(index).click()

    @step
    def click_current_version_tab(self):
        """Switch the diff view to compare against the current editor state."""
        self.current_version_tab.click()

    @step
    def click_restore(self):
        """Click the Restore button to trigger the confirmation modal."""
        self.restore_button.click()

    @step
    def confirm_restore(self):
        """Click the primary confirm button in the restoration modal."""
        self.confirm_restore_button.click()
        expect(self.restore_confirmation_dialog).not_to_be_visible()

    # ==========================================================================
    # METHODS — ASSERTIONS
    # ==========================================================================

    @step
    def should_be_visible(self):
        """Assert the version history popup is visible."""
        expect(self.popup_container).to_be_visible()

    @step
    def should_not_be_visible(self):
        """Assert the version history popup is not visible."""
        expect(self.popup_container).not_to_be_visible()

    @step
    def should_have_version_entries(self, min_count: int = 1):
        """Assert the version combobox has at least ``min_count`` selectable entries.

        Opens the dropdown to count options, then closes it via the toggle button
        (avoids Escape which might close the whole popup dialog).
        """
        self.version_selector_toggle.click()
        entries = self.version_entries
        expect(entries.first).to_be_visible()
        actual_count = entries.count()
        self.version_selector_toggle.click()
        entries.first.wait_for(state="hidden")
        assert_that(
            actual_count,
            greater_than_or_equal_to(min_count),
            f"Expected at least {min_count} version entries in the combobox, "
            f"found {actual_count}",
        )

    @step
    def should_have_version_entry_format(self):
        """Assert version entries have the [NN] + datetime + author format.

        Opens the dropdown, checks the first option's text, then closes the dropdown
        via the toggle button.
        """
        self.version_selector_toggle.click()
        first_option = self.version_entries.first
        expect(first_option).to_be_visible()
        option_text = first_option.inner_text()
        self.version_selector_toggle.click()
        self.version_entries.first.wait_for(state="hidden")
        assert_that(
            option_text,
            matches_regexp(r"\[\d{2}\]"),
            f"Expected version entry to contain a [NN] zero-padded label, "
            f"but got: {option_text!r}",
        )

    @step
    def should_have_diff_tabs_visible(self):
        """Assert both diff comparison buttons are visible."""
        expect(self.previous_version_tab).to_be_visible()
        expect(self.current_version_tab).to_be_visible()

    @step
    def should_have_diff_view_visible(self):
        """Assert the diff view is visible (version comparison buttons are rendered)."""
        expect(self.current_version_tab).to_be_visible()

    @step
    def should_have_restore_confirmation_visible(self):
        """Assert the confirmation modal is visible."""
        expect(self.restore_confirmation_dialog).to_be_visible()

    @step
    def should_have_restore_confirmation_hidden(self):
        """Assert the confirmation modal is not visible."""
        expect(self.restore_confirmation_dialog).not_to_be_visible()
