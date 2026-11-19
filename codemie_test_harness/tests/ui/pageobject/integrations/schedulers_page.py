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

"""Page object for the Schedulers page and the scheduler forms its Create menu opens."""

from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage

PAGE_URL = "/schedulers"


# noinspection PyArgumentList
class SchedulersPage(BasePage):
    """Schedulers list with its Create menu (user and project schedulers)."""

    @property
    def create_menu_button(self) -> Locator:
        """'Create' button that opens the scheduler menu."""
        return self.page.get_by_role("button", name="Create", exact=True)

    def scheduler_menu_item(self, kind: str) -> Locator:
        """Menu item 'Create User Scheduler' or 'Create Project Scheduler'."""
        return self.page.get_by_role("menuitem", name=f"Create {kind} Scheduler")

    def form_heading(self, kind: str) -> Locator:
        """Heading 'New User Scheduler' or 'New Project Scheduler'."""
        return self.page.get_by_role("heading", name=f"New {kind} Scheduler")

    @step
    def navigate_to(self):
        """Open the Schedulers page."""
        self.page.goto(PAGE_URL)
        expect(self.create_menu_button).to_be_visible(timeout=30000)
        return self

    @step
    def open_scheduler_form(self, kind: str):
        """Create a scheduler of the kind, 'User' or 'Project', from the Create menu."""
        self.create_menu_button.click()
        self.scheduler_menu_item(kind).click()
        return self

    @step
    def should_show_form(self, kind: str):
        """The scheduler form of the kind is open."""
        expect(self.form_heading(kind)).to_be_visible()
        return self

    @step
    def should_have_no_scope_field(self):
        """The scheduler form has no Scope field: no label and no User/Project toggle."""
        expect(self.page.get_by_text("Scope", exact=True)).to_have_count(0)
        expect(self.page.get_by_role("button", name="User", exact=True)).to_have_count(
            0
        )
        return self
