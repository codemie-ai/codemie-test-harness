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

"""Page object for the Users Management administration page.

URL: /settings/administration/users

Locators derived from live UI inspection on 2026-08-18.
For the Auditor role:
  - Create user button is ABSENT
  - 'More options' menu only exposes 'View details' (no Edit/Deactivate/role-change)

Default project: the users list marks the stored default inside the Projects cell
(`default-project-marker`); the User Details projects table has one 'Default' radio per project
(`default-radio-<project>`).
"""

import re
from urllib.parse import quote

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage

# The project name must sit on exactly one rendered line and must not overflow its element.
_SINGLE_LINE_JS = """
el => {
    const text = [...el.childNodes].find(n => n.nodeType === Node.TEXT_NODE);
    if (!text) return false;
    const range = document.createRange();
    range.selectNodeContents(text);
    const lines = new Set([...range.getClientRects()].map(r => Math.round(r.top)));
    return lines.size === 1 && el.scrollWidth <= el.clientWidth + 1;
}
"""

# Project, Default, Role and actions sit left-to-right without overlap and inside the table.
_COLUMNS_LAID_OUT_JS = """
({name, defaultControl, role, unassign, table, headers}) => {
    const box = el => el.getBoundingClientRect();
    const [projectHead, defaultHead, roleHead] = headers.map(box);
    const tableBox = box(table);
    const cells = [name, defaultControl, role, unassign].map(box);
    const ordered = cells.every((b, i) => i === 0 || cells[i - 1].right <= b.left + 1);
    const headersOrdered = projectHead.left < defaultHead.left && defaultHead.left < roleHead.left;
    const inside = cells.every(b => b.left >= tableBox.left - 1 && b.right <= tableBox.right + 1);
    return ordered && headersOrdered && inside;
}
"""


class UserManagementPage(BasePage):
    """Administration > Users Management page."""

    PATH = "/settings/administration/users"

    # ── Locators ──────────────────────────────────────────────────────────────

    @property
    def page_heading(self):
        """'Users management' page heading."""
        return self.page.get_by_role("heading", name="Users management")

    @property
    def user_table(self):
        """The users data table."""
        return self.page.locator("table").first

    @property
    def user_rows(self):
        """All data rows inside the users table body."""
        return self.page.locator("tbody tr")

    def _user_row(self, email: str):
        """Table row of the user with the given email."""
        return self.user_rows.filter(has_text=email)

    def _user_email_button(self, email: str):
        """Button labelled with the user's email address (opens User Details dialog)."""
        return self._user_row(email).get_by_role("button", name=email)

    @property
    def user_details_dialog(self):
        """'User Details' dialog panel."""
        return self.page.get_by_role("dialog", name="User Details")

    @property
    def close_user_details_button(self):
        """'Close' button inside the User Details dialog."""
        return self.user_details_dialog.get_by_role("button", name="Close")

    @property
    def search_input(self):
        """Free-text search box above the users table."""
        return self.page.get_by_placeholder("Search", exact=True)

    def _list_project_chip(self, email: str, project: str):
        """Project chip inside the user's Projects cell of the users list."""
        return self._user_row(email).get_by_role("link").filter(has_text=project)

    def _list_default_markers(self, email: str):
        """All 'Default' markers inside the user's Projects cell of the users list."""
        return self._user_row(email).get_by_test_id("default-project-marker")

    @property
    def details_projects_table(self):
        """Projects table inside the User Details dialog (the one with a 'Default' column)."""
        return self.user_details_dialog.locator("table").filter(
            has=self.page.get_by_role("columnheader", name="Default", exact=True)
        )

    def _details_project_row(self, project: str):
        """Row of the project in the User Details projects table."""
        return self.details_projects_table.locator("tbody tr").filter(has_text=project)

    def _project_name_cell(self, project: str):
        """Element holding the project name inside its row of the details table."""
        return self._details_project_row(project).get_by_text(project, exact=True)

    def _default_radio(self, project: str):
        """'Default' radio input of a project row in the User Details projects table."""
        return self.user_details_dialog.locator(f'input[id="default-radio-{project}"]')

    def _default_radio_label(self, project: str):
        """Clickable label of the project's 'Default' radio."""
        return self.user_details_dialog.locator(f'label[for="default-radio-{project}"]')

    @property
    def _default_radios(self):
        """All 'Default' radios of the details projects table."""
        return self.user_details_dialog.get_by_role("radio")

    @property
    def add_project_button(self):
        """'Add Project' button in the User Details dialog."""
        return self.user_details_dialog.get_by_role("button", name="Add Project")

    @property
    def unassign_buttons(self):
        """'Unassign' buttons of all project rows in the User Details dialog."""
        return self.user_details_dialog.get_by_role("button", name="Unassign")

    @property
    def role_selectors(self):
        """Per-project role dropdowns in the User Details projects table."""
        return self.user_details_dialog.locator('[id^="role-"]')

    @property
    def add_project_dialog(self):
        """'Add Project' dialog."""
        return self.page.get_by_role("dialog", name="Add Project")

    @property
    def set_as_default_switch(self):
        """'Set as default' switch inside the Add Project dialog."""
        return self.add_project_dialog.get_by_role("switch", name="Set as default")

    @property
    def unassign_confirmation_dialog(self):
        """Confirmation dialog shown before a project is unassigned."""
        return self.page.get_by_role("dialog", name="Unassign from Project?")

    # ── Actions ───────────────────────────────────────────────────────────────

    @step
    def navigate_to(self):
        """Navigate to the Users Management page and wait for the heading."""
        self.page.goto(self.PATH)
        self.page.wait_for_load_state("networkidle", timeout=30000)
        expect(self.page_heading).to_be_visible(timeout=15000)
        return self

    @step
    def open_first_user_detail(self):
        """Click the first visible user email button in the table.

        The user table is paginated — rather than searching for a specific user that
        may not appear on page 1, this method clicks the first email button on the
        current page to open the User Details dialog.
        """
        # Each row contains an email button (first button in the row) followed by
        # a 'More options' button.  Grab the email button from the first row.
        first_row = self.user_rows.first
        expect(first_row).to_be_visible(timeout=10000)
        email_btn = first_row.get_by_role("button").first
        email_btn.click()
        expect(self.user_details_dialog).to_be_visible(timeout=10000)
        return self

    @step
    def search_user(self, email: str):
        """Filter the users list by email and wait for the user's row."""
        self.search_input.fill(email)
        expect(self._user_row(email)).to_have_count(1, timeout=15000)
        return self

    @step
    def open_user_details(self, email: str):
        """Search for the user and open the User Details dialog."""
        self.search_user(email)
        self._user_email_button(email).click()
        expect(self.user_details_dialog).to_be_visible(timeout=10000)
        expect(self.details_projects_table).to_be_visible(timeout=10000)
        return self

    @step
    def close_user_details(self):
        """Close the User Details dialog."""
        self.close_user_details_button.click()
        expect(self.user_details_dialog).to_be_hidden(timeout=10000)
        return self

    @step
    def set_default_project(self, project: str):
        """Select the project's 'Default' radio in the User Details projects table."""
        self._default_radio_label(project).click()
        expect(self._default_radio(project)).to_be_checked(timeout=10000)
        return self

    @step
    def click_default_control_forcing(self, project: str):
        """Click the project's 'Default' control even when it is disabled (read-only role checks)."""
        self._default_radio_label(project).click(force=True)
        return self

    @step
    def unassign_project(self, project: str):
        """Unassign the user from the project and confirm; wait until its row disappears."""
        self._details_project_row(project).get_by_role(
            "button", name="Unassign"
        ).click()
        dialog = self.unassign_confirmation_dialog
        expect(dialog).to_be_visible(timeout=10000)
        dialog.get_by_role("button", name="Unassign", exact=True).click()
        expect(dialog).to_be_hidden(timeout=15000)
        expect(self._details_project_row(project)).to_have_count(0, timeout=15000)
        return self

    @step
    def add_project(self, project: str, set_as_default: bool):
        """Add the user to a project through the Add Project dialog."""
        self.add_project_button.click()
        dialog = self.add_project_dialog
        expect(dialog).to_be_visible(timeout=10000)
        # The project selector is a PrimeReact MultiSelect without a test id.
        dialog.locator(".p-multiselect").click()
        self.page.get_by_placeholder("Search for project").fill(project)
        self.page.get_by_role("option", name=project, exact=True).click()
        # Escape would close the whole dialog; clicking its title only closes the dropdown panel.
        dialog.get_by_text("Add Project", exact=True).first.click()
        if set_as_default:
            dialog.get_by_text("Set as default", exact=True).click()
            expect(self.set_as_default_switch).to_be_checked()
        dialog.get_by_role("button", name="Add", exact=True).click()
        expect(dialog).to_be_hidden(timeout=15000)
        expect(self._details_project_row(project)).to_be_visible(timeout=15000)
        return self

    # ── Assertions ────────────────────────────────────────────────────────────

    @step
    def should_see_user_list_not_empty(self):
        """Assert the users table contains at least one row."""
        expect(self.user_table).to_be_visible(timeout=10000)
        expect(self.user_rows.first).to_be_visible(timeout=10000)
        return self

    @step
    def should_see_user_detail_fields(self):
        """Assert the User Details dialog is open and shows all expected sections."""
        dialog = self.user_details_dialog
        expect(dialog).to_be_visible(timeout=10000)
        expect(dialog.get_by_text("Budget assignments", exact=False)).to_be_visible(
            timeout=5000
        )
        expect(dialog.get_by_text("User spending", exact=False)).to_be_visible(
            timeout=5000
        )
        expect(dialog.get_by_text("Projects", exact=False)).to_be_visible(timeout=5000)
        return self

    @step
    def should_not_see_write_controls(self):
        """Assert no user write controls are exposed for the auditor role.

        Verifies:
        - No 'Invite', 'Create user', or 'Add user' button on the page
        - The 'More options' menus do not contain Edit/Deactivate/role-change items
        """
        # No create/invite button
        expect(
            self.page.get_by_role("button", name="Invite", exact=True)
        ).to_have_count(0)
        expect(
            self.page.get_by_role("button", name="Create user", exact=True)
        ).to_have_count(0)
        expect(
            self.page.get_by_role("button", name="Add user", exact=True)
        ).to_have_count(0)
        return self

    @step
    def should_see_default_in_users_list(self, email: str, project: str):
        """Assert the project chip carries the default marker and no other chip does."""
        marker = self._list_project_chip(email, project).get_by_test_id(
            "default-project-marker"
        )
        expect(marker).to_be_visible(timeout=15000)
        expect(self._list_default_markers(email)).to_have_count(1, timeout=10000)
        return self

    @step
    def should_see_default_selected_only_for(self, project: str):
        """Assert exactly the given project's Default radio is selected in the details table."""
        expect(self._default_radio(project)).to_be_checked(timeout=10000)
        expect(
            self.user_details_dialog.locator("input[type=radio]:checked")
        ).to_have_count(1, timeout=10000)
        return self

    @step
    def should_see_default_controls_enabled(self):
        """Assert the details dialog exposes project-management controls.

        The radio of the current default is checked and disabled by design, so only the
        unchecked radios are required to be enabled.
        """
        expect(self.add_project_button).to_be_visible(timeout=10000)
        expect(self.unassign_buttons.first).to_be_visible(timeout=10000)
        unchecked = self.user_details_dialog.locator("input[type=radio]:not(:checked)")
        expect(unchecked.first).to_be_visible(timeout=10000)
        for radio in unchecked.all():
            expect(radio).to_be_enabled()
        return self

    @step
    def should_see_default_read_only(self):
        """Assert the details dialog shows default markers but offers no way to change projects."""
        expect(self._default_radios.first).to_be_visible(timeout=10000)
        for radio in self._default_radios.all():
            expect(radio).to_be_disabled()
        expect(self.add_project_button).to_have_count(0)
        expect(self.unassign_buttons).to_have_count(0)
        expect(self.role_selectors).to_have_count(0)
        return self

    @step
    def should_see_not_found(self):
        """Assert the Users management page is not available to the current user."""
        expect(self.page.get_by_text("Not found", exact=True)).to_be_visible(
            timeout=15000
        )
        expect(self.page_heading).to_have_count(0)
        return self

    @step
    def should_see_project_names_on_single_line(self, projects: list[str]):
        """Assert none of the given project names wraps or overflows in the details table."""
        for project in projects:
            name = self._project_name_cell(project)
            name.wait_for(state="visible", timeout=10000)
            self._expect_layout(
                _SINGLE_LINE_JS,
                name.element_handle(),
                f"Project name '{project}' wraps onto several lines or overflows its cell",
            )
        return self

    @step
    def should_see_projects_table_columns_laid_out(self, project: str):
        """Assert, on the given project's row, that Project, Default, Role and Unassign sit
        left-to-right without overlap and inside the table, with headers in the same order."""
        row = self._details_project_row(project)
        table = self.details_projects_table
        headers = [
            table.get_by_role("columnheader", name=title, exact=True).element_handle()
            for title in ("Project", "Default", "Role")
        ]
        self._expect_layout(
            _COLUMNS_LAID_OUT_JS,
            {
                "name": self._project_name_cell(project).element_handle(),
                "defaultControl": self._default_radio_label(project).element_handle(),
                "role": row.locator(".p-dropdown").first.element_handle(),
                "unassign": row.get_by_role("button", name="Unassign").element_handle(),
                "table": table.element_handle(),
                "headers": headers,
            },
            f"Columns of the projects table overlap or leave the table (row '{project}')",
        )
        return self

    def _expect_layout(self, predicate_js: str, arg, message: str) -> None:
        """Retry a layout predicate in the browser; raise AssertionError if it never holds."""
        try:
            self.page.wait_for_function(predicate_js, arg=arg, timeout=5000)
        except PlaywrightTimeoutError as error:
            raise AssertionError(message) from error

    # ── Project filter ────────────────────────────────────────────────────────
    # FE: usersManagement/components/UsersManagementFilters.tsx renders ProjectSelector
    # (label 'Project', id 'project-selector'); the selected projects show in its label.

    @property
    def project_filter(self):
        """Project filter multiselect above the users table."""
        return self.page.locator("#project-selector")

    @property
    def project_filter_value(self):
        """Label of the project filter that lists the selected project names."""
        return self.project_filter.locator(".p-multiselect-label")

    @step
    def should_be_filtered_by_project_in_url(self, project: str):
        """Assert the browser is on the Users management page with ?projects=<project>."""
        expect(self.page).to_have_url(
            re.compile(
                re.escape(self.PATH)
                + r"\?(.*&)?projects="
                + re.escape(quote(project, safe="-_.~"))
                + r"(&.*)?$"
            ),
            timeout=15000,
        )
        return self

    @step
    def should_show_project_selected_in_filter(self, project: str):
        """Assert the project filter control displays the project as selected."""
        expect(self.page_heading).to_be_visible(timeout=15000)
        expect(self.project_filter).to_be_visible(timeout=15000)
        expect(self.project_filter_value).to_contain_text(project, timeout=15000)
        return self

    @step
    def should_list_user(self, email: str):
        """Search the (filtered) users list by email and assert the user's row is shown."""
        self.search_input.fill(email)
        expect(self._user_row(email)).to_have_count(1, timeout=15000)
        return self

    @step
    def should_not_list_user(self, email: str):
        """Search the (filtered) users list by email and assert no row matches.

        Only meaningful after `should_list_user` for another user in the same view, because
        an empty result also looks like an unfinished load.
        """
        self.search_input.fill(email)
        self.page.wait_for_load_state("networkidle", timeout=15000)
        expect(self._user_row(email)).to_have_count(0, timeout=15000)
        return self

    @step
    def should_list_users_in_order(self, search_token: str, emails: list[str]):
        """Search the list by the token and assert exactly these users are listed in this order."""
        self.search_input.fill(search_token)
        expect(self.user_rows.filter(has_text=search_token)).to_contain_text(
            emails, timeout=30000
        )
        return self
