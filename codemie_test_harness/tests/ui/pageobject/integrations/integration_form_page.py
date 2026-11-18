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

"""Page object for the New Integration form of the unified Integrations page.

The form opens from the list's 'New Integration' button, from the admin project page's
'Create Integration' button and from the onboarding link. Scope (User or Project) is its first
field. Selectors come from the recon walk of the stand.
"""

import re
from typing import Optional

from hamcrest import assert_that, less_than
from playwright.sync_api import Locator, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


def _label_pattern(label: str):
    """Option text that starts with the label as a whole word, before any badge or hint."""
    return re.compile(rf"^\s*{re.escape(label)}(?!\w)")


# noinspection PyArgumentList
class IntegrationFormPage(BasePage):
    """New Integration form with its Scope field, Project selector and Credential Type."""

    # ====================
    # PROPERTIES
    # ====================

    @property
    def heading(self) -> Locator:
        """Page heading 'New Integration'."""
        return self.page.get_by_role("heading", name="New Integration")

    @property
    def project_combobox(self) -> Locator:
        """Project selector of the form."""
        return self.page.get_by_role("combobox", name="Project", exact=True)

    @property
    def project_selector(self) -> Locator:
        """Container of the Project selector, which shows the selected project."""
        return self.page.locator("#project-selector")

    @property
    def global_switch(self) -> Locator:
        """'Global Integration' switch; offered at User scope only."""
        return self.page.get_by_role("switch", name="Global Integration")

    @property
    def credential_type_combobox(self) -> Locator:
        """Credential Type selector."""
        return self.page.get_by_role("combobox", name="Credential Type")

    @property
    def alias_input(self) -> Locator:
        """Alias field, pre-filled with a generated alias."""
        return self.page.get_by_role("textbox", name="Alias")

    @property
    def save_button(self) -> Locator:
        """'Save' button."""
        return self.page.get_by_role("button", name="Save")

    @property
    def cancel_form_button(self) -> Locator:
        """'Cancel' button."""
        return self.page.get_by_role("button", name="Cancel")

    @property
    def maybe_later_button(self) -> Locator:
        """'Maybe Later' button of the guided tour dialog the first form can open."""
        return self.page.get_by_role("button", name="Maybe Later")

    @property
    def options(self) -> Locator:
        """Options of the open Project or Credential Type list."""
        return self.page.get_by_role("option")

    def scope_button(self, label: str) -> Locator:
        """Scope toggle button 'User' or 'Project'."""
        return self.page.get_by_role("button", name=label, exact=True)

    def selected_scope_button(self, label: str) -> Locator:
        """Scope toggle button that is the pressed (current) one."""
        return self.page.get_by_role("button", name=label, exact=True, pressed=True)

    def note(self, text: str) -> Locator:
        """Status note of the form that carries the text."""
        return self.page.get_by_role("status").filter(has_text=text)

    def option(self, label: str) -> Locator:
        """Option of the open list whose text starts with the label."""
        return self.options.filter(has_text=_label_pattern(label))

    def disabled_option(self, label: str) -> Locator:
        """Disabled marker of the option; PrimeReact or the item template carries it."""
        return (
            self.page.locator("[aria-disabled='true']")
            .filter(has_text=_label_pattern(label))
            .first
        )

    # ====================
    # ACTIONS
    # ====================

    @step
    def navigate_to(self, query: str = ""):
        """Open the form by address, optionally with a query string such as 'scope=user'."""
        self.page.goto(f"/integrations/new?{query}" if query else "/integrations/new")
        expect(self.heading).to_be_visible(timeout=30000)
        self.dismiss_guided_tour()
        return self

    @step
    def dismiss_guided_tour(self):
        """Close the guided tour dialog when it opened over the form."""
        try:
            self.maybe_later_button.click(timeout=3000)
        except PlaywrightTimeoutError:
            pass
        return self

    @step
    def wait_until_open(self):
        """Wait for the form to show and clear the guided tour that can cover it."""
        expect(self.heading).to_be_visible(timeout=30000)
        self.dismiss_guided_tour()
        return self

    @step
    def select_scope(self, label: str):
        """Switch the form's Scope to 'User' or 'Project'."""
        self.scope_button(label).click()
        return self

    @step
    def pick_project(self, name: str):
        """Open the Project selector and choose the project."""
        self.project_combobox.click()
        self.option(name).click()
        return self

    @step
    def open_project_list(self):
        """Open the Project selector's list."""
        self.project_combobox.click()
        return self

    @step
    def open_credential_type_list(self):
        """Open the Credential Type list."""
        self.credential_type_combobox.click()
        return self

    @step
    def pick_credential_type(self, label: str):
        """Open the Credential Type list and choose the type."""
        self.credential_type_combobox.click()
        self.option(label).click()
        return self

    @step
    def switch_global_on(self):
        """Turn the 'Global Integration' switch on."""
        self.global_switch.check()
        return self

    @step
    def fill_alias(self, alias: str):
        """Replace the alias."""
        self.alias_input.fill(alias)
        return self

    @step
    def save(self):
        """Click Save."""
        self.save_button.click()
        return self

    @step
    def cancel(self):
        """Click Cancel."""
        self.cancel_form_button.click()
        return self

    @step
    def go_back(self):
        """Click the header's Back button."""
        self.back_button.click()
        return self

    # ====================
    # VERIFICATION
    # ====================

    @step
    def should_show_heading(self):
        """The form is titled 'New Integration'."""
        expect(self.heading).to_be_visible()
        return self

    @step
    def should_show_edit_heading(self, scope_label: str):
        """The edit page is titled 'Edit Integration' (User) or 'Edit Project Integration' (Project)."""
        title = (
            "Edit Project Integration"
            if scope_label == "Project"
            else "Edit Integration"
        )
        expect(self.page.get_by_role("heading", name=title, exact=True)).to_be_visible(
            timeout=30000
        )
        return self

    @step
    def should_have_scope_first(self):
        """Scope sits above the Project selector, which sits above Credential Type."""
        scope_y = self.scope_button("User").bounding_box()["y"]
        project_y = self.project_selector.bounding_box()["y"]
        type_y = self.credential_type_combobox.bounding_box()["y"]
        assert_that(scope_y, less_than(project_y), "Scope is not above Project")
        assert_that(
            project_y, less_than(type_y), "Project is not above Credential Type"
        )
        return self

    @step
    def should_have_scope_selected(self, label: str):
        """The Scope toggle shows the option as current."""
        expect(self.selected_scope_button(label)).to_be_visible()
        return self

    @step
    def should_have_scope_locked_to(self, label: str):
        """Both Scope buttons are disabled and the option is the current one."""
        expect(self.selected_scope_button(label)).to_be_disabled()
        other = "Project" if label == "User" else "User"
        expect(self.scope_button(other)).to_be_disabled()
        return self

    @step
    def should_have_project_locked_to(self, name: str):
        """The Project selector is disabled and shows the project."""
        expect(self.project_combobox).to_be_disabled()
        expect(self.project_selector).to_contain_text(name)
        return self

    @step
    def should_have_project_scope_disabled(self, reason: str):
        """The Project scope button is disabled and its description is the reason."""
        button = self.scope_button("Project")
        expect(button).to_be_disabled()
        expect(button).to_have_accessible_description(re.compile(re.escape(reason)))
        return self

    @step
    def should_offer_global_switch(self):
        """The 'Global Integration' switch is shown."""
        expect(self.global_switch).to_be_visible()
        return self

    @step
    def should_not_offer_global_switch(self):
        """The 'Global Integration' switch is hidden."""
        expect(self.global_switch).to_have_count(0)
        return self

    @step
    def should_have_global_switch(self, on: bool):
        """The 'Global Integration' switch is on or off."""
        if on:
            expect(self.global_switch).to_be_checked()
        else:
            expect(self.global_switch).not_to_be_checked()
        return self

    @step
    def should_show_note(self, text: str):
        """A note of the form carries the text."""
        expect(self.note(text)).to_be_visible()
        return self

    @step
    def should_have_project_cleared(self, name: str):
        """The Project selector no longer holds the project."""
        expect(self.project_selector).not_to_contain_text(name)
        return self

    @step
    def should_offer_exactly_projects(self, names: list[str]):
        """The open Project list offers these projects and no other."""
        expect(self.options).to_have_count(len(names))
        for name in names:
            expect(self.option(name)).to_have_count(1)
        return self

    @step
    def should_offer_project(self, name: str):
        """The open Project list offers the project."""
        expect(self.option(name)).to_have_count(1)
        return self

    @step
    def should_not_offer_project(self, name: str):
        """The open Project list does not offer the project."""
        expect(self.option(name)).to_have_count(0)
        return self

    @step
    def should_disable_credential_type(self, label: str, hint: Optional[str] = None):
        """The open Credential Type list shows the type as disabled, with the hint."""
        expect(self.disabled_option(label)).to_be_visible()
        if hint:
            expect(self.disabled_option(label)).to_contain_text(hint)
        return self

    @step
    def should_have_no_scope_field(self):
        """The form has no Scope field: no label and no User/Project toggle."""
        expect(self.page.get_by_text("Scope", exact=True)).to_have_count(0)
        expect(self.scope_button("User")).to_have_count(0)
        return self
