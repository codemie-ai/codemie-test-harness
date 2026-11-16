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
from codemie_test_harness.tests.ui.pageobject.hosted_applications.hosted_standalone_page import (
    HostedStandalonePage,
)

PROBE_RESULT_ID = "probe-result"
CONTENT_WAIT_MS = 60000


class HostedApplicationViewerPage(BasePage):
    """The viewer: the CodeMie header around a frame that holds the application's own frame."""

    @property
    def open_in_new_tab_button(self) -> Locator:
        """Open in new tab button of the viewer header."""
        return self.page.get_by_role("button", name="Open in new tab")

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
    def open_preview(self, app_id: str, version_id: str):
        """Open the preview of one version of an application at its address."""
        self.page.goto(f"/apps/{app_id}/preview/{version_id}")
        return self

    @step
    def open_in_new_tab(self) -> HostedStandalonePage:
        """Press Open in new tab and return the tab it opens."""
        with self.page.context.expect_page() as opened:
            self.open_in_new_tab_button.click()
        return HostedStandalonePage(opened.value)

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
