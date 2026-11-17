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

"""Page object for the embedded viewer of a hosted application."""

import re

from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage

PROBE_RESULT_ID = "probe-result"
CONTENT_WAIT_MS = 60000
NEW_TAB_NAME = re.compile("new tab", re.IGNORECASE)


class HostedApplicationViewerPage(BasePage):
    """The viewer: the CodeMie header around a frame that holds the application's own frame."""

    @property
    def new_tab_controls(self) -> Locator:
        """Any button of the viewer that talks about a new tab."""
        return self.page.get_by_role("button", name=NEW_TAB_NAME)

    @property
    def application_actions_button(self) -> Locator:
        """Button that opens the overflow menu of the viewer."""
        return self.page.get_by_role("button", name="Application actions")

    @property
    def new_tab_menu_items(self) -> Locator:
        """Any entry of the open overflow menu that talks about a new tab."""
        return self.page.get_by_role("menuitem", name=NEW_TAB_NAME)

    def content(self, app_name: str):
        """The frame of the application itself, inside the viewer's container frame."""
        return self.page.frame_locator(f'iframe[title="{app_name}"]').frame_locator(
            "iframe"
        )

    def content_heading(self, app_name: str, marker: str) -> Locator:
        """The heading of the application's page that carries its marker."""
        return self.content(app_name).get_by_role("heading", name=marker)

    def probe_report(self, app_name: str) -> Locator:
        """The text a probe page writes about what it could reach."""
        return self.content(app_name).locator(f"#{PROBE_RESULT_ID}")

    @step
    def open(self, app_id: str):
        """Open the viewer of an application at its address."""
        self.page.goto(f"/apps/{app_id}/view")
        return self

    @step
    def should_be_on_view_route(self, app_id: str):
        """The viewer address is open."""
        expect(self.page).to_have_url(re.compile(rf"/apps/{app_id}/view/?$"))
        return self

    @step
    def should_show_content(self, app_name: str, marker: str):
        """The application's own page is shown in the viewer."""
        expect(self.content_heading(app_name, marker)).to_be_visible(
            timeout=CONTENT_WAIT_MS
        )
        return self

    @step
    def should_show_text(self, app_name: str, text: str):
        """The application's page shows this text."""
        expect(self.content(app_name).get_by_text(text)).to_be_visible(
            timeout=CONTENT_WAIT_MS
        )
        return self

    @step
    def should_report(self, app_name: str, report: str):
        """A probe page wrote exactly this report about what it reached (whitespace is normalised)."""
        expect(self.probe_report(app_name)).to_have_text(
            report, timeout=CONTENT_WAIT_MS
        )
        return self

    @step
    def should_not_offer_open_in_new_tab(self):
        """Neither the header nor the overflow menu has a control for a new tab."""
        expect(self.application_actions_button).to_be_visible()
        expect(self.new_tab_controls).to_have_count(0)
        self.application_actions_button.click()
        expect(self.new_tab_menu_items).to_have_count(0)
        return self
