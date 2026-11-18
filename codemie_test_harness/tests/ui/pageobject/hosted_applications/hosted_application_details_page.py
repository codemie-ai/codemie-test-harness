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

"""Page object for the details page of one hosted application."""

import re

from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.hosted_applications.hosted_page_base import (
    NEW_TAB_NAME,
    HostedPageBase,
)


class HostedApplicationDetailsPage(HostedPageBase):
    """Details page: actions, versions and the upload dialog."""

    @property
    def open_button(self) -> Locator:
        """Open button; disabled until a version is live."""
        return self.page.get_by_role("button", name="Open", exact=True)

    @property
    def new_tab_controls(self) -> Locator:
        """Any button of the page that talks about a new tab."""
        return self.page.get_by_role("button", name=NEW_TAB_NAME)

    @property
    def upload_version_button(self) -> Locator:
        """Upload version button of the versions section."""
        return self.page.get_by_role("button", name="Upload version", exact=True)

    @property
    def upload_dialog(self) -> Locator:
        """The upload dialog."""
        return self.page.get_by_role("dialog")

    @property
    def upload_dialog_heading(self) -> Locator:
        """Heading of the upload dialog."""
        return self.upload_dialog.get_by_text("Upload a new version")

    @property
    def upload_dialog_file_button(self) -> Locator:
        """Control of the dialog that picks the application file."""
        return self.upload_dialog.get_by_role(
            "button", name="Upload or drop files: Application file"
        )

    @property
    def upload_dialog_navigation_select(self) -> Locator:
        """Focusable input of the Navigation select of the upload dialog.

        The shared Select renders ``<label for="<id>-input">Navigation</label>`` and gives the
        Dropdown the same ``inputId``, so the label names the read-only input that takes the Tab
        focus. Its trigger (role button) and value text carry no name.
        """
        return self.upload_dialog.get_by_label("Navigation", exact=True)

    @property
    def upload_dialog_cancel_button(self) -> Locator:
        """Cancel button of the upload dialog."""
        return self.upload_dialog.get_by_role("button", name="Cancel")

    def overflow_button(self, app_name: str) -> Locator:
        """Overflow button of the page, named 'More options <name>'; disabled when it has no entry."""
        return self.page.get_by_role(
            "button", name=f"More options {app_name}", exact=True
        )

    @property
    def shared_with_heading(self) -> Locator:
        """Heading of the 'Shared with' section, shown to the people who may share."""
        return self.page.get_by_role("heading", name="Shared with", exact=True)

    @property
    def access_link_heading(self) -> Locator:
        """Heading of the 'ACCESS LINK' section."""
        return self.page.get_by_role("heading", name="ACCESS LINK", exact=True)

    @property
    def shared_with_section(self) -> Locator:
        """The 'Shared with' section: the one block holding its heading and not the next section."""
        return (
            self.page.locator("div")
            .filter(has=self.shared_with_heading)
            .filter(has_not=self.access_link_heading)
        )

    def access_hint(self, text: str) -> Locator:
        """The hint under the application link that says who can open it."""
        return self.page.get_by_text(text, exact=True)

    @step
    def open(self, app_id: str):
        """Open the details page of an application."""
        self.page.goto(f"/apps/{app_id}")
        expect(self.open_button).to_be_visible()
        return self

    @step
    def open_overflow_menu(self, app_name: str):
        """Open the overflow menu of the page."""
        self.overflow_button(app_name).click()
        return self

    @step
    def click_open(self):
        """Press Open."""
        self.open_button.click()
        return self

    @step
    def should_offer_open(self):
        """Open is available, and no control opens the application in a new tab."""
        expect(self.open_button).to_be_enabled()
        expect(self.new_tab_controls).to_have_count(0)
        return self

    @step
    def should_be_on_details_route(self, app_id: str):
        """The details page of the application is open."""
        expect(self.page).to_have_url(re.compile(rf"/apps/{app_id}/?$"))
        return self

    @step
    def should_show_upload_dialog(self):
        """The upload dialog is open."""
        expect(self.upload_dialog_heading).to_be_visible()
        return self

    @step
    def should_reach_upload_dialog_controls_by_keyboard(self):
        """The file control, the Navigation select and Cancel take the focus from Tab, each under its name."""
        expect(self.upload_dialog_navigation_select).to_have_accessible_name(
            "Navigation"
        )
        self.focus_by_keyboard(self.upload_dialog_file_button)
        expect(self.upload_dialog_file_button).to_be_focused()
        self.focus_by_keyboard(self.upload_dialog_navigation_select)
        expect(self.upload_dialog_navigation_select).to_be_focused()
        self.focus_by_keyboard(self.upload_dialog_cancel_button)
        expect(self.upload_dialog_cancel_button).to_be_focused()
        return self

    @step
    def should_list_shared_with(self, email: str):
        """The 'Shared with' section lists the person with this e-mail."""
        expect(self.shared_with_section.get_by_text(email, exact=True)).to_be_visible()
        return self

    @step
    def should_offer_no_actions(self, app_name: str):
        """The overflow menu has no entry at all, so nothing such as Share is offered."""
        expect(self.overflow_button(app_name)).to_be_disabled()
        return self

    @step
    def should_not_show_shared_with(self):
        """The page has loaded its sections and has no 'Shared with' section."""
        expect(self.access_link_heading).to_be_visible()
        expect(self.shared_with_heading).to_have_count(0)
        return self

    @step
    def should_show_access_hint(self, text: str):
        """The hint under the application link reads exactly this."""
        expect(self.access_link_heading).to_be_visible()
        expect(self.access_hint(text)).to_be_visible()
        return self
