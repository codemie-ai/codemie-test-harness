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

"""Page object for the hosted application viewer, route /apps/{id}/view."""

import re

from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.pageobject.components.options_menu import (
    OptionsMenu,
)


class HostedApplicationViewerPage(BasePage):
    """Viewer that runs the active version of a hosted application."""

    def title(self, app_name: str) -> Locator:
        """Application name in the page header."""
        return self.page.get_by_role("heading", level=1, name=app_name, exact=True)

    @property
    def actions_button(self) -> Locator:
        """Application actions button that opens the viewer menu."""
        return self.page.get_by_role("button", name="Application actions")

    @property
    def options_menu(self) -> OptionsMenu:
        """The viewer menu."""
        return OptionsMenu(self.page)

    @step
    def should_be_open(self, app_id: str, app_name: str):
        """Verify the viewer route of this application is open."""
        expect(self.page).to_have_url(
            re.compile(rf"/apps/{re.escape(app_id)}/view/?(\?.*)?$")
        )
        expect(self.title(app_name)).to_be_visible()
        return self

    @step
    def open_actions_menu(self):
        """Open the Application actions menu."""
        self.actions_button.click()
        self.options_menu.should_be_open()
        return self.options_menu
