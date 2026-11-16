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

"""Page object for an application opened in its own browser tab."""

from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage

# Words of the error page a hosting gateway answers with when it cannot reach the application.
ERROR_PAGE_TEXT = "Service Unavailable"


class HostedStandalonePage(BasePage):
    """The application alone in a tab, without the CodeMie layout."""

    @property
    def content_frame(self) -> Locator:
        """The frame holding the application itself."""
        return self.page.frame_locator('iframe[title="Application content"]')

    def content_heading(self, marker: str) -> Locator:
        """The heading of the application's page that carries its marker."""
        return self.content_frame.get_by_role("heading", name=marker)

    @step
    def should_show_content(self, marker: str):
        """The tab shows the application's own page."""
        expect(self.content_heading(marker)).to_be_visible(timeout=60000)
        return self

    @step
    def should_not_show_error_page(self):
        """The tab is not a gateway error page."""
        expect(self.page.get_by_text(ERROR_PAGE_TEXT)).to_have_count(0)
        return self
