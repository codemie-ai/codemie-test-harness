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

"""Page object for the unified Integrations list.

One table lists user and project integrations with a Scope column; the Filters sidebar holds
the Scope, Project, Type, Global and Created by filters. Selectors come from the recon walk of
the stand and the list's accessible names (table "Integrations", Scope radios, "New Integration").
"""

import re
from typing import Optional

from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests import CredentialsManager
from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.pageobject.login_page import LoginPage

PAGE_URL = "/integrations"


def _label_pattern(label: str):
    """Option text that starts with the label as a whole word, before any badge or hint."""
    return re.compile(rf"^\s*{re.escape(label)}(?!\w)")


# noinspection PyArgumentList
class IntegrationsListPage(BasePage):
    """Integrations page: scope-aware table and Filters sidebar."""

    # ====================
    # PROPERTIES
    # ====================

    @property
    def new_integration_button(self) -> Locator:
        """'New Integration' button of the page header; the one entry to the create form."""
        return self.page.get_by_role("button", name="New Integration")

    @property
    def table(self) -> Locator:
        """The integrations table."""
        return self.page.get_by_role("table", name="Integrations")

    @property
    def body_rows(self) -> Locator:
        """Data rows of the table, without the header row."""
        return self.table.locator("tbody").get_by_role("row")

    @property
    def search_input(self) -> Locator:
        """Search box of the Filters sidebar."""
        return self.page.get_by_role("textbox", name="Search")

    @property
    def scope_radios(self) -> Locator:
        """Every radio of the Scope filter; none for a person who cannot use project scope."""
        return self.page.locator("input[name='scope']")

    @property
    def global_radios(self) -> Locator:
        """Every radio of the Global filter."""
        return self.page.locator("input[name='is_global']")

    @property
    def type_filter(self) -> Locator:
        """Type combobox of the Filters sidebar."""
        return self.page.get_by_role("combobox", name="Type")

    @property
    def created_by_filter(self) -> Locator:
        """'Created By' control of the Filters sidebar; offered only at Project scope."""
        return self.page.get_by_role("button", name="Created By")

    @property
    def scope_hint(self) -> Locator:
        """Hint shown at Scope All instead of the Global and Created by filters."""
        return self.page.get_by_text("Pick a scope to filter by Global or Created by.")

    @property
    def type_options(self) -> Locator:
        """Options of the open Type filter."""
        return self.page.get_by_role("option")

    @property
    def toast(self) -> Locator:
        """Status region the save and delete toasts appear in."""
        return self.page.get_by_role("status")

    @property
    def show_all_scopes_button(self) -> Locator:
        """Toast action that clears the Scope and Type filters."""
        return self.page.get_by_role("button", name="Show all scopes and types")

    @property
    def confirm_delete_button(self) -> Locator:
        """'Delete' button of the delete confirmation dialog."""
        return self.page.get_by_role("dialog").get_by_role("button", name="Delete")

    def scope_radio(self, label: str) -> Locator:
        """Scope filter radio 'All', 'User' or 'Project'."""
        return self.page.get_by_role("radio", name=label, exact=True).and_(
            self.scope_radios
        )

    def global_radio(self, label: str) -> Locator:
        """Global filter radio 'All', 'Global' or 'Non Global'."""
        return self.page.get_by_role("radio", name=label, exact=True).and_(
            self.global_radios
        )

    def row(self, alias: str) -> Locator:
        """Table row whose Alias cell holds the alias."""
        return self.body_rows.filter(has_text=alias)

    def type_option(self, label: str) -> Locator:
        """Option of the open Type filter whose text starts with the label."""
        return self.type_options.filter(has_text=_label_pattern(label))

    def disabled_type_option(self, label: str) -> Locator:
        """Disabled marker of the Type option; PrimeReact or the item template carries it."""
        return (
            self.page.locator("[aria-disabled='true']")
            .filter(has_text=_label_pattern(label))
            .first
        )

    def page_button(self, number: int) -> Locator:
        """Pagination button of a page number (1-based)."""
        return self.page.get_by_role("button", name=f"Page {number}", exact=True)

    # ====================
    # NAVIGATION AND ACTIONS
    # ====================

    @step
    def navigate_to(self, query: str = ""):
        """Open the Integrations page, optionally with a query string such as 'scope=user'."""
        self.page.goto(f"{PAGE_URL}?{query}" if query else PAGE_URL)
        expect(self.table).to_be_visible(timeout=30000)
        return self

    @step
    def open_in_new_page(self, url: str, user_id: str):
        """Open an address in a fresh page of the same browser session (same sign-in)."""
        fresh_page = self.page.context.new_page()
        LoginPage(fresh_page).apply_onboarding_overrides(
            user_id, CredentialsManager.get_parameter("FRONTEND_URL", "")
        )
        fresh_page.goto(url)
        return IntegrationsListPage(fresh_page)

    @step
    def select_scope(self, label: str):
        """Select 'All', 'User' or 'Project' in the Scope filter."""
        self.page.keyboard.press("Escape")
        self.page.mouse.move(0, 0)
        self.scope_radio(label).check()
        return self

    @step
    def search_for(self, term: str):
        """Type a term into the search box; the list applies it after a short delay."""
        self.search_input.fill(term)
        return self

    @step
    def click_new_integration(self):
        """Open the New Integration form."""
        self.new_integration_button.click()
        return self

    @step
    def go_back_in_browser(self):
        """Press the browser's Back button."""
        self.page.go_back()
        return self

    @step
    def open_type_filter(self):
        """Open the Type filter's option list."""
        self.type_filter.click()
        return self

    @step
    def pick_type(self, label: str):
        """Tick a type in the open Type filter and close the list."""
        self.type_option(label).click()
        self.page.keyboard.press("Escape")
        return self

    @step
    def close_type_filter(self):
        """Close the Type filter's option list."""
        self.page.keyboard.press("Escape")
        return self

    @step
    def go_to_page(self, number: int):
        """Open a page of the table by its number (1-based)."""
        self.page_button(number).click()
        return self

    @step
    def open_row_menu_item(self, alias: str, item: str):
        """Open the row's 'More options' menu and choose 'Edit' or 'Delete'."""
        self.row(alias).get_by_role("button", name=re.compile("More options")).click()
        self.page.get_by_role("menuitem", name=item).click()
        return self

    @step
    def delete_row(self, alias: str):
        """Delete the row's integration and confirm."""
        self.open_row_menu_item(alias, "Delete")
        self.confirm_delete_button.click()
        return self

    @step
    def click_show_all_scopes_and_types(self):
        """Click the toast action that clears the filters hiding the saved row."""
        self.show_all_scopes_button.click()
        return self

    # ====================
    # VERIFICATION
    # ====================

    @step
    def should_show_row(self, alias: str):
        """The table lists a row with the alias."""
        expect(self.row(alias)).to_have_count(1)
        return self

    @step
    def should_show_rows(self, aliases: list[str]):
        """The table lists a row for each alias."""
        expect(self.body_rows).to_have_count(len(aliases))
        for alias in aliases:
            expect(self.row(alias)).to_have_count(1)
        return self

    @step
    def should_show_rows_in_order(self, aliases: list[str]):
        """The table lists exactly these rows, first to last."""
        expect(self.body_rows).to_have_count(len(aliases))
        for position, alias in enumerate(aliases):
            expect(self.body_rows.nth(position)).to_contain_text(alias)
        return self

    @step
    def should_not_show_row(self, alias: str):
        """The table lists no row with the alias."""
        expect(self.row(alias)).to_have_count(0)
        return self

    @step
    def should_have_row_count(self, count: int):
        """The table lists exactly this many rows on the page."""
        expect(self.body_rows).to_have_count(count)
        return self

    @step
    def should_show_scope_badge(self, alias: str, scope_label: str):
        """The row's Scope cell shows the badge 'User' or 'Project'."""
        expect(self.row(alias).get_by_text(scope_label, exact=True)).to_be_visible()
        return self

    @step
    def should_show_global_badge(self, alias: str):
        """The row carries the 'Global' badge next to its Scope badge."""
        expect(self.row(alias).get_by_text("Global", exact=True)).to_be_visible()
        return self

    @step
    def should_not_show_global_badge(self, alias: str):
        """The row carries no 'Global' badge."""
        expect(self.row(alias).get_by_text("Global", exact=True)).to_have_count(0)
        return self

    @step
    def should_mark_row_as_just_saved(self, alias: str):
        """The row of the integration saved just before is marked 'Just saved'."""
        expect(self.row(alias)).to_contain_text("Just saved")
        return self

    @step
    def should_not_offer_user_project_switch(self):
        """The old User/Project switch buttons are gone from the list page."""
        expect(self.page.get_by_role("button", name="User", exact=True)).to_have_count(
            0
        )
        expect(
            self.page.get_by_role("button", name="Project", exact=True)
        ).to_have_count(0)
        return self

    @step
    def should_offer_scope_filter(self):
        """The Filters sidebar offers the Scope filter with All, User and Project."""
        expect(self.scope_radios).to_have_count(3)
        return self

    @step
    def should_not_offer_scope_filter(self):
        """The Filters sidebar has no Scope filter."""
        expect(self.search_input).to_be_visible()
        expect(self.scope_radios).to_have_count(0)
        return self

    @step
    def should_have_scope_selected(self, label: str):
        """The Scope filter has the option selected."""
        expect(self.scope_radio(label)).to_be_checked()
        return self

    @step
    def should_have_scope_in_url(self, scope: Optional[str]):
        """The address carries 'scope=<scope>', or no scope at all for Scope All (None)."""
        if scope is None:
            expect(self.page).not_to_have_url(re.compile(r"[?&]scope="))
        else:
            expect(self.page).to_have_url(re.compile(rf"[?&]scope={scope}(&|$)"))
        return self

    @step
    def should_have_search_term(self, term: str):
        """The search box holds the term."""
        expect(self.search_input).to_have_value(term)
        return self

    @step
    def should_offer_global_filter(self):
        """The Filters sidebar offers the Global filter."""
        expect(self.global_radios).to_have_count(3)
        return self

    @step
    def should_not_offer_global_filter(self):
        """The Filters sidebar has no Global filter."""
        expect(self.global_radios).to_have_count(0)
        return self

    @step
    def should_offer_created_by_filter(self):
        """The Filters sidebar offers the Created by filter."""
        expect(self.created_by_filter).to_be_visible()
        return self

    @step
    def should_not_offer_created_by_filter(self):
        """The Filters sidebar has no Created by filter."""
        expect(self.created_by_filter).to_have_count(0)
        return self

    @step
    def should_show_scope_hint(self):
        """The Filters sidebar shows the hint about Global and Created by."""
        expect(self.scope_hint).to_be_visible()
        return self

    @step
    def should_not_show_scope_hint(self):
        """The Filters sidebar shows no hint about Global and Created by."""
        expect(self.scope_hint).to_have_count(0)
        return self

    @step
    def should_have_pages(self, count: int):
        """The pagination offers exactly this many pages (1 means no pagination)."""
        expect(self.page_button(count + 1)).to_have_count(0)
        if count > 1:
            expect(self.page_button(count)).to_be_visible()
        return self

    @step
    def should_mark_type(self, label: str, badge: str):
        """The open Type filter marks the type with a scope badge."""
        expect(self.type_option(label)).to_contain_text(badge)
        return self

    @step
    def should_list_each_type_once(self, labels: list[str]):
        """The open Type filter lists every one of the types exactly once."""
        for label in labels:
            expect(self.type_option(label)).to_have_count(1)
        return self

    @step
    def should_disable_type(self, label: str, hint: str):
        """The open Type filter lists the type as disabled, with the hint."""
        expect(self.disabled_type_option(label)).to_contain_text(hint)
        return self

    @step
    def should_not_disable_type(self, label: str):
        """The open Type filter lists the type as selectable."""
        expect(self.type_option(label)).to_have_count(1)
        expect(self.disabled_type_option(label)).to_have_count(0)
        return self

    @step
    def should_show_filter_note(self, text: str):
        """A note under the filters carries the text."""
        expect(self.toast.filter(has_text=text)).to_be_visible()
        return self

    @step
    def should_not_filter_by_type_in_url(self, type_name: str):
        """The address carries no 'type=<type_name>' filter."""
        expect(self.page).not_to_have_url(re.compile(rf"[?&]type={type_name}(&|$)"))
        return self

    @step
    def should_show_toast(self, text: str):
        """A toast shows the text."""
        expect(self.toast.filter(has_text=text).first).to_be_visible()
        return self

    @step
    def should_offer_show_all_scopes_and_types(self):
        """The toast offers the 'Show all scopes and types' action."""
        expect(self.show_all_scopes_button).to_be_visible()
        return self
