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

"""Page object for the hosted application details page, route /apps/{id}."""

import re

from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.pageobject.components.options_menu import (
    OptionsMenu,
)
from codemie_test_harness.tests.ui.pageobject.hosted_apps.hosted_application_viewer_page import (
    HostedApplicationViewerPage,
)


class HostedApplicationDetailsPage(BasePage):
    """Details of a hosted application: overview, versions and actions."""

    @property
    def page_heading(self) -> Locator:
        """Page title, "Application details"."""
        return self.page.get_by_role("heading", level=1, name="Application details")

    @property
    def launch_button(self) -> Locator:
        """Open button in the page header."""
        return self.page.get_by_role("button", name="Open", exact=True)

    def more_options_button(self, app_name: str) -> Locator:
        """More options button of the page header."""
        return self.page.get_by_role("button", name=f"More options {app_name}")

    @property
    def options_menu(self) -> OptionsMenu:
        """The More options menu."""
        return OptionsMenu(self.page)

    @step
    def should_be_open(self, app_id: str):
        """Verify the details route of this application is open."""
        expect(self.page).to_have_url(
            re.compile(rf"/apps/{re.escape(app_id)}/?(\?.*)?$")
        )
        expect(self.page_heading).to_be_visible()
        return self

    @step
    def should_have_launch_button(self, enabled: bool):
        """Verify the header has an Open button, enabled or disabled as given."""
        expect(self.launch_button).to_have_text("Open")
        expect(self.launch_button).to_be_enabled(enabled=enabled)
        return self

    @step
    def open_more_options_menu(self, app_name: str):
        """Open the More options menu of the page header."""
        self.more_options_button(app_name).click()
        self.options_menu.should_be_open()
        return self.options_menu

    @step
    def click_launch_button(self):
        """Click Open to run the active version."""
        self.launch_button.click()
        return HostedApplicationViewerPage(self.page)
