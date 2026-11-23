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

"""Page object for the form that creates a hosted application and the form that edits one."""

import re

from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.components.category_picker import (
    CategoryPicker,
)
from codemie_test_harness.tests.ui.pageobject.hosted_applications.hosted_page_base import (
    HostedPageBase,
)

CREATE_ROUTE = "/apps/new"


class HostedApplicationFormPage(HostedPageBase):
    """The create and edit application form, with its Categories field."""

    @property
    def name_input(self) -> Locator:
        """Application name field."""
        return self.page.get_by_role("textbox", name="Application name")

    @property
    def description_input(self) -> Locator:
        """Description field."""
        return self.page.get_by_role("textbox", name=re.compile("Description"))

    @property
    def categories(self) -> CategoryPicker:
        """The Categories field."""
        return CategoryPicker(self.page, self.page.locator("form"))

    @property
    def categories_label(self) -> Locator:
        """Label of the Categories field."""
        return self.page.locator("label").filter(has_text="Categories")

    @property
    def categories_error(self) -> Locator:
        """Error line under the Categories field."""
        return self.page.get_by_role("alert").filter(has_text="categor").first

    @property
    def submit_button(self) -> Locator:
        """Create (new application) or Save (edit) button of the page header."""
        return self.page.get_by_role("button", name=re.compile("^(Create|Save)$"))

    @step
    def open_create(self):
        """Open the create form."""
        self.page.goto(CREATE_ROUTE)
        expect(self.name_input).to_be_visible()
        return self

    @step
    def open_edit(self, app_id: str):
        """Open the edit form of an application."""
        self.page.goto(f"/apps/{app_id}/edit")
        expect(self.name_input).to_be_visible()
        return self

    @step
    def fill_in(self, name: str, description: str):
        """Fill in the name and description."""
        self.name_input.fill(name)
        self.description_input.fill(description)
        return self

    @step
    def submit(self):
        """Press Create or Save."""
        self.submit_button.click()
        return self

    @step
    def should_have_created_application(self):
        """The form was left for the details page of the new application."""
        expect(self.page).to_have_url(re.compile(r"/apps/[0-9a-f-]{36}/?$"))
        return self

    @step
    def should_be_saved(self, app_id: str):
        """The edit form was left for the details page of the application."""
        expect(self.page).to_have_url(re.compile(rf"/apps/{app_id}/?$"))
        return self

    @step
    def should_still_be_on_edit_form(self, app_id: str):
        """The form was not left."""
        expect(self.page).to_have_url(re.compile(rf"/apps/{app_id}/edit/?$"))
        return self

    @step
    def should_mark_categories_required(self):
        """The Categories label carries the required asterisk."""
        expect(self.categories_label).to_have_text(re.compile(r"^Categories\s*\*"))
        return self

    @step
    def should_not_mark_categories_required(self):
        """The Categories label carries no asterisk."""
        expect(self.categories_label).to_have_text(re.compile(r"^Categories$"))
        return self

    @step
    def should_show_categories_error(self, text: str):
        """The Categories field shows this refusal."""
        expect(self.categories_error).to_have_text(text)
        return self

    @step
    def should_refuse_a_fourth_category(self):
        """The Categories field says no more than three can be picked."""
        expect(self.categories_error).to_have_text(
            "You can select maximum 3 categories"
        )
        return self
