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

"""Page object for the Publish to Marketplace dialog of a hosted application."""

from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.components.category_picker import (
    CategoryPicker,
)
from codemie_test_harness.tests.ui.pageobject.hosted_applications.hosted_page_base import (
    HostedPageBase,
)

HEADING = "Publish to Marketplace?"
MENU_ITEM = "Publish to Marketplace"


class HostedPublishDialog(HostedPageBase):
    """The dialog that asks for one to three categories before an application is published."""

    @property
    def dialog(self) -> Locator:
        """The dialog."""
        return self.page.get_by_role("dialog").filter(
            has=self.page.get_by_role("heading", name=HEADING)
        )

    @property
    def categories(self) -> CategoryPicker:
        """The category picker of the dialog."""
        return CategoryPicker(self.page, self.dialog)

    @property
    def publish_button(self) -> Locator:
        """Publish button."""
        return self.dialog.get_by_role("button", name="Publish", exact=True)

    @property
    def cancel_button(self) -> Locator:
        """Cancel button."""
        return self.dialog.get_by_role("button", name="Cancel", exact=True)

    @property
    def alerts(self) -> Locator:
        """Every refusal or error the dialog shows."""
        return self.dialog.get_by_role("alert")

    @step
    def should_be_open(self):
        """The dialog is shown."""
        expect(self.dialog).to_be_visible()
        return self

    @step
    def should_be_closed(self):
        """The dialog is gone."""
        expect(self.dialog).to_be_hidden()
        return self

    @step
    def publish(self):
        """Press Publish."""
        self.publish_button.click()
        return self

    @step
    def cancel(self):
        """Press Cancel."""
        self.cancel_button.click()
        return self

    @step
    def should_show_alert(self, text: str):
        """The dialog shows a message with this text."""
        expect(self.alerts.filter(has_text=text)).to_be_visible()
        return self

    @step
    def should_show_no_alert(self):
        """The dialog shows no refusal or error."""
        expect(self.alerts).to_have_count(0)
        return self
