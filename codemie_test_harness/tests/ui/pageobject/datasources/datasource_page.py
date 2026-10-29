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

import re

from hamcrest import has_length, assert_that, greater_than_or_equal_to
from playwright.sync_api import Error as PlaywrightError, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.pageobject.datasources.datasource_sidebar import (
    DataSourceSidebar,
)
from codemie_test_harness.tests.ui.test_data.datasource_test_data import (
    DATAS_SOURCE_COLUMN_LIST,
)


class DataSourcePage(BasePage):
    """Data Sources page object with property-based element locators."""

    page_url = "/data-sources"

    def __init__(self, page):
        super().__init__(page)
        self.sidebar = DataSourceSidebar(page)

    # -----------------
    # Page Elements
    # -----------------

    @property
    def create_datasource_button(self):
        """'Create Datasource' button."""
        return self.page.locator('button:has-text("Create Datasource")')

    @property
    def table(self):
        """Datasource table."""
        return self.page.locator("table")

    @property
    def table_rows(self):
        """Table data rows."""
        return self.table.locator("tbody tr")

    def table_columns_names(self, column: str):
        """Table data column names."""
        return self.table.locator(".text-left:not(.text-gray-50)").filter(
            has_text=re.compile(f"^{re.escape(column)}$")
        )

    @property
    def row_menu_view_details_button(self):
        return self.page.locator("span.text-left.grow").filter(has_text="View Details")

    @property
    def row_menu_edit_button(self):
        return self.page.locator("span.text-left.grow").filter(has_text="Edit")

    @property
    def row_menu_copy_id_button(self):
        return self.page.locator("span.text-left.grow").filter(has_text="Copy ID")

    @property
    def row_menu_clone_button(self):
        """'Clone' item of the open row actions menu."""
        return self.page.locator("span.text-left.grow").filter(
            has_text=re.compile(r"^\s*Clone\s*$")
        )

    @property
    def row_menu_export_button(self):
        return self.page.locator("span.text-left.grow").filter(has_text="Export")

    @property
    def row_menu_delete_button(self):
        return self.page.locator("span.text-left.grow").filter(has_text="Delete")

    @property
    def row_menu_full_reindex_button(self):
        return self.page.locator("span.text-left.grow").filter(has_text="Full Reindex")

    @property
    def row_menu_incremental_index_button(self):
        return self.page.locator("span.text-left.grow").filter(
            has_text="Incremental Index"
        )

    @property
    def pop_up_message(self):
        return self.page.locator(".codemie-toast-header")

    @property
    def search_input(self):
        """Search input in the sidebar filters."""
        return self.page.locator('input[placeholder="Search"]')

    # -------------------------------
    # Navigation methods
    # -------------------------------
    @step
    def navigate_to(self):
        """
        Navigate to the DataSource page.

        Uses domcontentloaded instead of networkidle to avoid blocking
        during active datasource reindexing (constant status-polling requests).

        Returns:
            self: Returns the page object for method chaining
        """
        self.page.goto(self.page_url)
        self.page.wait_for_load_state("domcontentloaded", timeout=30000)
        # Wait for the table to be rendered before returning
        expect(self.table).to_be_visible(timeout=15000)
        return self

    @step
    def search_for(self, name: str):
        """
        Type a name into the sidebar search field to filter the table.

        After searching, the table shows only rows matching the given name,
        so the row is always on page 1 regardless of the total dataset size.

        Returns:
            self: Returns the page object for method chaining
        """
        search = self.search_input
        expect(search).to_be_visible(timeout=15000)
        search.clear()
        search.fill(name)
        # Wait briefly for the filter to apply
        self.page.wait_for_timeout(500)
        return self

    # -----------------
    # Table Methods
    # -----------------
    @step
    def get_table_row_by_name(self, name: str):
        """Get the row as locator by datasource name."""
        return self.page.locator(
            "tbody tr:has(td:nth-child(1) button.font-bold)"
        ).filter(has_text=name)

    def get_cell_in_row(self, row_locator, col_idx):
        return row_locator.locator(f"td:nth-child({col_idx})")

    def get_status_in_row(self, row_locator):
        return self.get_cell_in_row(row_locator, 8).locator("div.inline-flex")

    def get_project_in_row(self, row_locator):
        return self.get_cell_in_row(row_locator, 2)

    def get_type_in_row(self, row_locator):
        return self.get_cell_in_row(row_locator, 3)

    def get_created_by_in_row(self, row_locator):
        return self.get_cell_in_row(row_locator, 4).locator("span")

    @step
    def click_datasource_row_by_name(self, name: str):
        self.get_table_row_by_name(name).locator("button.font-bold").click()
        return self

    def get_row_action_menu_button(self, datasource_name: str):
        """
        Returns the 3-dot menu button locator for a row by datasource name.
        """
        # Find the row with the given datasource name,
        # then get 3-dot menu button in the last column.
        row = self.get_table_row_by_name(datasource_name)
        return row.locator("td:last-child button")

    @step
    def open_row_action_menu(self, datasource_name: str):
        """
        Opens the 3-dot actions menu for a row by datasource name.

        Uses the search filter to ensure the target row is always visible
        on page 1 regardless of how many datasources exist or the current
        sort order.  Also waits for any blocking overlay to clear and waits
        for the action menu to be visible before returning.
        """
        # Ensure any dialog mask from previous operations is gone
        modal_mask = self.page.locator(".p-dialog-mask")
        if modal_mask.is_visible():
            try:
                modal_mask.wait_for(state="hidden", timeout=5000)
            except Exception:
                pass
        # Search for the datasource to guarantee it is visible on page 1
        self.search_for(datasource_name)
        btn = self.get_row_action_menu_button(datasource_name)
        expect(btn).to_be_visible()
        btn.click()
        # Wait for the action menu to be rendered before returning so that
        # callers can immediately assert on menu items without timing issues.
        action_menu = self.page.locator('[role="menu"]')
        try:
            action_menu.first.wait_for(state="visible", timeout=5000)
        except Exception:
            pass
        return self

    @step
    def click_row_action(self, action_text: str):
        """
        Clicks a menu item in the currently open 3-dot menu by the visible text.

        Scopes the click to the open [role="menu"] container so the sticky page
        header cannot intercept pointer events on near-top items.
        """
        menu = self.page.locator('[role="menu"]').first
        menu.locator("button").filter(has_text=action_text).click(force=True)
        return self

    @step
    def open_and_select_row_action(self, datasource_name: str, action_text: str):
        """
        Opens the 3-dot menu in the specified row and selects a menu action.
        """
        self.open_row_action_menu(datasource_name)
        self.click_row_action(action_text)
        return self

    @step
    def open_delete_dialog(self, datasource_name: str, attempts: int = 3):
        """
        Opens the row menu, clicks Delete and waits for the confirmation dialog.

        A table refresh (status polling, search results) can close the menu between
        opening it and clicking the item, so the whole sequence is retried.
        """
        heading = self.page.get_by_role("heading", name="Delete Data Source?")
        for attempt in range(1, attempts + 1):
            try:
                self.open_row_action_menu(datasource_name)
                self.click_row_action("Delete")
                expect(heading).to_be_visible(timeout=3000)
                return self
            except (PlaywrightError, AssertionError):
                if attempt == attempts:
                    raise
                self.page.keyboard.press("Escape")
        return self

    @step
    def open_datasource_details(self, name: str):
        """
        Opens the details page of a datasource by name.

        Filters the table by name first so the row is on page 1 regardless of
        how many datasources exist.
        """
        self.search_for(name)
        self.click_datasource_row_by_name(name)
        return self

    # -----------------
    # Verification Methods
    # -----------------

    @step
    def should_see_create_datasource_button(self):
        expect(self.create_datasource_button).to_be_visible()
        return self

    @step
    def should_see_table_rows(self, minimum_count: int = 1):
        expect(self.table_rows.first).to_be_visible()
        # Wait until the minimum_count-th row is visible before calling .all(),
        # which captures a DOM snapshot — calling it too early yields fewer rows
        # than expected because the API response may still be rendering.
        expect(self.table_rows.nth(minimum_count - 1)).to_be_visible(timeout=15000)
        assert_that(
            self.table_rows.all(), has_length(greater_than_or_equal_to(minimum_count))
        )
        return self

    @step
    def should_see_table_column_names(self):
        for column in DATAS_SOURCE_COLUMN_LIST:
            column_name = self.table_columns_names(column)
            expect(column_name).to_be_visible()

    @step
    def should_see_datasource_with_name(self, name: str):
        expect(self.get_table_row_by_name(name)).to_be_visible()
        return self

    @step
    def should_see_pagination(self, page: int = 1):
        expect(self.pagination_block).to_be_visible()
        expect(self.pagination_page_button(page)).to_be_visible()
        expect(self.show_per_page_dropdown).to_be_visible()
        expect(self.show_per_page_label).to_be_visible()
        return self

    @step
    def should_see_table_row_with_values(
        self, name, status, project=None, type_=None, created_by=None, timeout=180000
    ):
        """
        Verifies that a table row exists for the given parameters, and has the expected status.
        Optionally checks project, type, created_by columns.
        Polls with page reload because the UI does not auto-update datasource status.

        Filters the table by name so the target row is always on page 1 regardless
        of how many datasources exist or the current sort order. Without this, the
        default `date desc` / `per_page 10` listing pushes a freshly created row off
        page 1 once >10 datasources accumulate (e.g. mid-suite), and the poll can
        never see it. The filter is persisted to the URL + localStorage and re-applied
        by the list on mount, so it survives `page.reload()` — one call up front is
        enough. Mirrors the `search_for` hardening in `open_row_action_menu`.
        """
        import time

        self.search_for(name)
        row = self.get_table_row_by_name(name)
        expect(row).to_be_visible(timeout=15000)

        if project is not None:
            expect(self.get_project_in_row(row)).to_have_text(project)
        if type_ is not None:
            expect(self.get_type_in_row(row)).to_have_text(type_)
        if created_by is not None:
            expect(self.get_created_by_in_row(row)).to_have_text(created_by)

        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            try:
                expect(
                    self.get_status_in_row(self.get_table_row_by_name(name))
                ).to_have_text(status, timeout=3000)
                return self
            except AssertionError:
                pass
            self.page.reload()
            self.page.wait_for_load_state("networkidle", timeout=30000)

        expect(self.get_status_in_row(self.get_table_row_by_name(name))).to_have_text(
            status, timeout=15000
        )
        return self

    @step
    def should_see_edit_dropdown_values(self):
        expect(self.row_menu_view_details_button).to_be_visible()
        expect(self.row_menu_edit_button).to_be_visible()
        expect(self.row_menu_copy_id_button).to_be_visible()
        expect(self.row_menu_export_button).to_be_visible()
        expect(self.row_menu_delete_button).to_be_visible()
        return self

    @step
    def should_see_edit_dropdown_index_values(self):
        expect(self.row_menu_incremental_index_button).to_be_visible()
        expect(self.row_menu_full_reindex_button).to_be_visible()
        return self

    @step
    def should_see_edit_dropdown_full_reindex_value(self):
        expect(self.row_menu_full_reindex_button).to_be_visible()
        return self

    @step
    def should_see_clone_menu_item(self):
        expect(self.row_menu_clone_button).to_be_visible()
        return self

    @step
    def should_see_pop_up_message(self, message):
        expect(self.pop_up_message).to_be_visible()
        expect(self.pop_up_message).to_have_text(message)
        return self

    # -----------------
    # Delete Dialog Methods
    # -----------------

    @step
    def should_see_delete_dialog(self):
        """Verify delete confirmation dialog is visible."""
        delete_dialog_heading = self.page.get_by_role(
            "heading", name="Delete Data Source?"
        )
        expect(delete_dialog_heading).to_be_visible()
        confirmation_text = self.page.locator(
            'text="Are you sure you want to delete this data source?"'
        )
        expect(confirmation_text).to_be_visible()
        return self

    @property
    def delete_dialog_used_in_assistants_text(self):
        """Intro text above the list of assistants affected by the deletion."""
        return self.page.get_by_text("Given data source used in assistants:")

    def delete_dialog_assistant_item(self, assistant_name: str):
        """List item for an affected assistant in the delete dialog."""
        return self.page.locator("ul.list-disc > li").filter(has_text=assistant_name)

    @step
    def should_see_delete_dialog_affected_assistant(
        self, assistant_name: str, created_by: str
    ):
        """Verify the delete dialog lists the assistant with its creator."""
        item = self.delete_dialog_assistant_item(assistant_name)
        expect(item).to_have_count(1)
        expect(item).to_contain_text(f"Name: {assistant_name}")
        expect(item).to_contain_text(f"Created by: {created_by}")
        return self

    @step
    def should_see_delete_dialog_used_in_assistants_list(self):
        """Verify the delete dialog warns that the data source is used in assistants."""
        expect(self.delete_dialog_used_in_assistants_text).to_be_visible()
        return self

    @step
    def should_not_see_delete_dialog(self):
        """Verify delete dialog is not visible."""
        delete_dialog_heading = self.page.get_by_role(
            "heading", name="Delete Data Source?"
        )
        expect(delete_dialog_heading).not_to_be_visible()
        return self

    @step
    def confirm_delete(self):
        """Click the Delete button in the confirmation dialog."""
        delete_button = self.page.get_by_role("button", name="Delete").filter(
            has_text=re.compile("^Delete$")
        )
        expect(delete_button).to_be_visible()
        delete_button.click()
        return self

    @step
    def cancel_delete(self):
        """Click the Cancel button in the delete dialog."""
        cancel_button = self.page.get_by_role("button", name="Cancel")
        expect(cancel_button).to_be_visible()
        cancel_button.click()
        return self

    @step
    def should_not_see_row(self, name: str, timeout: int = 5000):
        """Verify datasource row is not visible."""
        row = self.get_table_row_by_name(name)
        expect(row).not_to_be_visible(timeout=timeout)
        return self

    # -----------------
    # Reindex Methods
    # -----------------

    @step
    def should_see_full_reindex_menu_item(self):
        """Verify Full Reindex menu item is visible."""
        full_reindex_button = self.page.get_by_role("menuitem", name="Full Reindex")
        expect(full_reindex_button).to_be_visible(timeout=10000)
        return self

    @step
    def click_full_reindex(self):
        """Click the Full Reindex menu item and confirm in the dialog."""
        full_reindex_button = self.page.get_by_role("menuitem", name="Full Reindex")
        expect(full_reindex_button).to_be_visible()
        full_reindex_button.click(force=True)
        # Wait for confirmation dialog to appear before clicking Confirm
        confirmation_dialog = self.page.locator(
            'dialog:has-text("Reindex Data Source?")'
        ).or_(
            self.page.locator('div[role="dialog"]').filter(
                has_text="Reindex Data Source?"
            )
        )
        confirmation_dialog.wait_for(state="visible", timeout=5000)
        confirmation_button = self.page.get_by_role("button", name="Confirm")
        expect(confirmation_button).to_be_visible()
        confirmation_button.click()
        # Wait for dialog to be dismissed before returning
        confirmation_dialog.wait_for(state="hidden", timeout=5000)
        return self

    @step
    def get_status_text(self, name: str) -> str:
        """Get the status text for a datasource."""
        row = self.get_table_row_by_name(name)
        status_cell = self.get_status_in_row(row)
        return status_cell.inner_text()

    @step
    def should_have_status_matching(self, name: str, pattern: str):
        """Verify datasource status matches the given regex pattern."""
        row = self.get_table_row_by_name(name)
        status_cell = self.get_status_in_row(row)
        expect(status_cell).to_have_text(re.compile(pattern))
        return self

    @step
    def intercept_reindex_with_error(self):
        """Set up route interception to simulate reindex failure."""

        def handle_reindex_error(route):
            route.fulfill(
                status=500,
                json={
                    "message": "Simulated indexing failure",
                    "error": "Internal Server Error",
                },
            )

        self.page.route("**/api/v1/datasources/*/reindex", handle_reindex_error)
        return self

    @step
    def close_modal_if_visible(self):
        """Close any visible modal dialog and wait for it to disappear."""
        modal_mask = self.page.locator(".p-dialog-mask")
        if modal_mask.is_visible():
            self.page.keyboard.press("Escape")
            # Wait for the overlay to fully disappear before proceeding
            try:
                modal_mask.wait_for(state="hidden", timeout=3000)
            except Exception:
                pass
        return self

    @step
    def should_not_see_error_dialog(self):
        """Verify no error dialog is visible."""
        error_dialog = self.page.locator('dialog:has-text("Error")')
        expect(error_dialog).not_to_be_visible()
        return self

    # -----------------
    # Status Badge Methods
    # -----------------

    @step
    def get_status_badge_class(self, name: str) -> str:
        """Get the CSS class attribute of the status badge."""
        row = self.get_table_row_by_name(name)
        status_badge = self.get_status_in_row(row)
        expect(status_badge).to_be_visible()
        return status_badge.get_attribute("class")

    @step
    def should_see_status_badge(self, name: str, status: str):
        """Verify status badge is visible with expected text."""
        row = self.get_table_row_by_name(name)
        status_badge = self.get_status_in_row(row)
        expect(status_badge).to_be_visible()
        expect(status_badge).to_have_text(status)
        return self

    @step
    def hover_over_status_badge(self, name: str):
        """Hover over the status badge for a datasource."""
        row = self.get_table_row_by_name(name)
        status_badge = self.get_status_in_row(row)
        status_badge.hover()
        self.page.wait_for_timeout(800)
        return self

    @step
    def is_tooltip_visible(self) -> bool:
        """Check if tooltip is visible."""
        tooltip = self.page.locator('[role="tooltip"]')
        return tooltip.count() > 0 and tooltip.first.is_visible()

    @step
    def get_tooltip_text(self) -> str:
        """Get the tooltip text if visible."""
        tooltip = self.page.locator('[role="tooltip"]')
        if tooltip.count() > 0 and tooltip.first.is_visible():
            return tooltip.first.inner_text()
        return ""

    @step
    def get_status_badge_title_attribute(self, name: str) -> str:
        """Get the title attribute of the status badge."""
        row = self.get_table_row_by_name(name)
        status_badge = self.get_status_in_row(row)
        return status_badge.get_attribute("title") or ""

    @step
    def get_status_badge_aria_label(self, name: str) -> str:
        """Get the aria-label of the status badge."""
        row = self.get_table_row_by_name(name)
        status_badge = self.get_status_in_row(row)
        return status_badge.get_attribute("aria-label") or ""

    @step
    def should_show_project_display_name_in_table_row(
        self, name: str, display_name: str
    ):
        """Search for datasource and verify the project column shows display_name as hover tooltip."""
        self.search_for(name)
        row = self.get_table_row_by_name(name)
        self.get_project_in_row(row).hover()
        self.page.wait_for_timeout(300)
        expect(self.page.locator('[role="tooltip"]')).to_contain_text(display_name)
        return self
