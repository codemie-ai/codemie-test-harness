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

"""Page object for the Projects Management administration page.

URL: /settings/administration/projects
"""

from playwright.sync_api import expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


class ProjectManagementPage(BasePage):
    """Administration > Projects Management table page."""

    PATH = "/settings/administration/projects"

    # ── Locators ──────────────────────────────────────────────────────────────

    @property
    def page_heading(self):
        """'Projects management' page heading."""
        return self.page.get_by_role("heading", name="Projects management")

    @property
    def create_project_button(self):
        """'Create' button that opens the project creation modal (top-right)."""
        return self.page.get_by_role("button", name="Create", exact=True)

    @property
    def search_input(self):
        """Search input to filter the projects table."""
        return self.page.get_by_placeholder("Search")

    @property
    def project_table(self):
        """The projects data table."""
        return self.page.locator("table").first

    @property
    def project_rows(self):
        """All data rows inside the projects table."""
        return self.page.locator("tbody tr")

    def _project_row_by_name(self, project_name: str):
        """A specific project row identified by its technical name (visible in Name column)."""
        return self.page.locator("tbody tr").filter(has_text=project_name)

    def _project_name_button(self, project_name: str):
        """The name button in the first column of a project row.

        When the project has a display_name, the button renders it as the primary
        label with the technical name as a muted subtitle (see `_project_name_subtitle`).
        """
        return (
            self._project_row_by_name(project_name)
            .locator("td")
            .first.locator("button")
        )

    def _project_name_subtitle(self, project_name: str):
        """The muted subtitle span (technical name) nested inside the name button."""
        return self._project_name_button(project_name).locator(
            "span.text-text-quaternary"
        )

    def _row_action_menu_button(self, project_name: str):
        """Three-dot (⋮) action menu button in the last column of a project row."""
        return self._project_row_by_name(project_name).locator("td:last-child button")

    @property
    def _action_menu(self):
        """The currently open 3-dot action dropdown menu."""
        return self.page.locator('[role="menu"]').first

    @property
    def _change_ownership_item(self):
        """The 'Change ownership' item of the currently open 3-dot action menu."""
        return self._action_menu.locator("button").filter(has_text="Change ownership")

    def _info_toast(self, text: str):
        """An info toast (codemie-toast-info) containing the given text."""
        return self.page.locator(".codemie-toast-info").filter(has_text=text)

    # ── Actions ───────────────────────────────────────────────────────────────

    @step
    def navigate_to(self):
        """Navigate directly to the Projects Management page and wait for content."""
        self.page.goto(self.PATH)
        self.page.wait_for_load_state("networkidle", timeout=30000)
        # Wait for the page heading to confirm the page has fully rendered
        expect(self.page_heading).to_be_visible(timeout=15000)
        return self

    @step
    def search_for(self, project_name: str):
        """Type a name into the search box to filter the projects table."""
        search = self.search_input
        expect(search).to_be_visible(timeout=5000)
        search.clear()
        search.fill(project_name)
        self.page.wait_for_timeout(800)
        return self

    @step
    def click_create_project(self):
        """Open the create-project modal by clicking the Create button."""
        expect(self.create_project_button).to_be_visible(timeout=10000)
        self.create_project_button.click()
        self.page.wait_for_timeout(500)
        return self

    @step
    def open_row_action_menu(self, project_name: str):
        """Search for a project then open its 3-dot action menu."""
        btn = self._row_action_menu_button(project_name)
        expect(btn).to_be_visible(timeout=5000)
        btn.click()
        # Wait for the dropdown menu to appear — let TimeoutError propagate so
        # failures here produce a clear "menu never opened" diagnostic rather than
        # a confusing downstream locator error.
        self._action_menu.wait_for(state="visible", timeout=5000)
        return self

    @step
    def click_row_action(self, action_text: str):
        """Click an action item in the currently open 3-dot menu."""
        self._action_menu.locator("button").filter(has_text=action_text).click(
            force=True
        )
        self.page.wait_for_timeout(500)
        return self

    @step
    def click_change_ownership(self, project_name: str):
        """Open the project's 3-dot action menu and click 'Change ownership'."""
        self.open_row_action_menu(project_name)
        self.click_row_action("Change ownership")
        return self

    @step
    def open_project(self, project_name: str):
        """Open a project's details page by clicking its name in the projects table."""
        button = self._project_name_button(project_name)
        expect(button).to_be_visible(timeout=15000)
        button.click()
        return self

    @step
    def click_edit_project(self, project_name: str):
        """Search for a project, open its action menu, and click Edit."""
        self.open_row_action_menu(project_name)
        self.click_row_action("Edit")
        return self

    # ── Assertions ────────────────────────────────────────────────────────────

    @step
    def should_see_create_button(self):
        """Verify the Create button is visible."""
        expect(self.create_project_button).to_be_visible()
        return self

    @step
    def should_see_project_table(self):
        """Verify the projects table is present on the page."""
        expect(self.project_table).to_be_visible()
        return self

    @step
    def should_see_project_display_name(self, project_name: str, display_name: str):
        """Search for project and verify display_name is the primary label, with the
        technical name shown as a muted subtitle inside the same button."""
        self.search_for(display_name)
        button = self._project_name_button(project_name)
        expect(button).to_contain_text(display_name, timeout=15000)
        expect(self._project_name_subtitle(project_name)).to_have_text(
            project_name, timeout=15000
        )
        return self

    # ── Row actions of a project ────────
    # FE: src/pages/settings/administration/projectsManagement/ProjectsManagementFull.tsx:518-575
    # The row menu always has 'View' (when user management is on); 'Edit' is added only when
    # canManageProject(item) = isAdmin || project admin of that row (:246-257).

    @step
    def should_list_project(self, project_name: str):
        """Search for the project and verify its row is shown."""
        self.search_for(project_name)
        expect(self._project_row_by_name(project_name)).to_be_visible(timeout=15000)
        return self

    @step
    def should_not_list_project(self, project_name: str):
        """Search for the project and verify no row matches.

        The absence is only meaningful next to a positive control for the same user (a row of
        theirs that IS listed), because an empty result also looks like an unfinished load.
        """
        self.search_for(project_name)
        self.page.wait_for_load_state("networkidle", timeout=15000)
        self.page.wait_for_timeout(1000)
        expect(self._project_row_by_name(project_name)).to_have_count(0)
        return self

    @step
    def should_offer_edit_action(self, project_name: str):
        """Open the row menu and verify it offers 'Edit', then dismiss it."""
        self.open_row_action_menu(project_name)
        expect(
            self._action_menu.locator("button").filter(has_text="Edit")
        ).to_be_visible(timeout=5000)
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(300)
        return self

    @step
    def should_not_offer_edit_action(self, project_name: str):
        """Open the row menu and verify it has 'View' but no 'Edit' (same locator as
        should_offer_edit_action, so a regression of the locator shows up in the positive case)."""
        self.open_row_action_menu(project_name)
        expect(
            self._action_menu.locator("button").filter(has_text="View")
        ).to_be_visible(timeout=5000)
        expect(
            self._action_menu.locator("button").filter(has_text="Edit")
        ).to_have_count(0)
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(300)
        return self

    @step
    def should_see_project_technical_name_only(self, project_name: str):
        """Search for project and verify its technical name appears in the row."""
        self.search_for(project_name)
        row = self._project_row_by_name(project_name)
        expect(row).to_be_visible(timeout=15000)
        expect(row).to_contain_text(project_name)
        return self

    @step
    def should_not_see_write_controls(self, project_name: str):
        """Assert no project write controls are exposed for the auditor role.

        Opens the 3-dot action menu for *project_name* and verifies that only a
        read-only 'View' item is present — no Edit, Delete, or Manage members items.

        Args:
            project_name: Technical name of a project whose action menu to inspect.
        """
        self.open_row_action_menu(project_name)
        menu = self._action_menu
        # Write actions must be absent
        expect(menu.locator("button").filter(has_text="Edit")).to_have_count(0)
        expect(menu.locator("button").filter(has_text="Delete")).to_have_count(0)
        expect(menu.locator("button").filter(has_text="Manage members")).to_have_count(
            0
        )
        # At minimum the read-only View option is present
        expect(menu.locator("button").filter(has_text="View")).to_be_visible(
            timeout=5000
        )
        # Dismiss the menu
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(300)
        return self

    @step
    def should_offer_change_ownership(self, visible: bool):
        """Verify the open 3-dot menu does (visible=True) or does not (visible=False)
        contain the 'Change ownership' item, then dismiss the menu."""
        expect(self._change_ownership_item).to_have_count(1 if visible else 0)
        self.page.keyboard.press("Escape")
        return self

    @step
    def should_see_ownership_transferred_toast(self, new_owner_name: str):
        """Verify the 'Ownership transferred to <name>' toast is shown."""
        expect(
            self._info_toast(f"Ownership transferred to {new_owner_name}")
        ).to_be_visible(timeout=10000)
        return self

    # ── Users badge ───────────────────────────────────────────────────────────
    # FE: src/pages/settings/administration/projectsManagement/ProjectsManagementFull.tsx:161,195,521
    #     src/pages/settings/administration/projectsManagement/ResourceCounterBadge.tsx:35,42
    # The 'Users' column stays; its cell holds a badge (aria-label 'Users', svg icon, count).
    # The badge is a link to User Management only for admin / maintainer / auditor.

    @property
    def users_column_header(self):
        """'Users' column header of the projects table."""
        return self.page.get_by_role("columnheader", name="Users", exact=True)

    def _users_badge(self, project_name: str):
        """The Users badge (aria-label 'Users') of a project row, link or plain."""
        return self._project_row_by_name(project_name).get_by_label("Users", exact=True)

    def _users_badge_links(self, project_name: str):
        """The Users badge of a project row when it is rendered as a link."""
        return self._project_row_by_name(project_name).get_by_role(
            "link", name="Users", exact=True
        )

    def _users_column_index(self) -> int:
        """Zero-based position of the 'Users' column, read from the table header."""
        index = self.project_table.locator("thead th").evaluate_all(
            "els => els.findIndex(e => e.textContent.trim() === 'Users')"
        )
        assert index >= 0, "The projects table has no 'Users' column header"
        return index

    def _users_cell(self, project_name: str):
        """The cell of the 'Users' column in a project row."""
        return (
            self._project_row_by_name(project_name)
            .locator("td")
            .nth(self._users_column_index())
        )

    @step
    def click_users_badge(self, project_name: str):
        """Click the Users badge of a project row (navigates to User Management)."""
        badge = self._users_badge_links(project_name)
        expect(badge).to_be_visible(timeout=15000)
        badge.click()
        return self

    @step
    def should_see_users_badge(
        self, project_name: str, count: int, as_link: bool = True
    ):
        """Verify the row's Users cell holds a badge (svg icon + count) and not plain text,
        that the 'Users' column header remains, and that the badge is a link or not."""
        expect(self.users_column_header).to_be_visible(timeout=15000)
        badge = self._users_badge(project_name)
        expect(badge).to_have_count(1, timeout=15000)
        expect(
            self._users_cell(project_name).get_by_label("Users", exact=True)
        ).to_have_count(1)
        expect(badge.locator("svg")).to_be_visible()
        expect(badge).to_have_text(str(count), timeout=15000)
        expect(self._users_badge_links(project_name)).to_have_count(1 if as_link else 0)
        return self
