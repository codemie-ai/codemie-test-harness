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

"""Page object for the share dialog of a hosted application: people by name and the share link.

Adding a person takes effect on Save; removing one takes effect on the click. The share link is
created by the first copy when the application has none.
"""

import re

from hamcrest import assert_that, contains_string
from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.test_data.hosted_application_ui_test_data import (
    LINK_COPIED_TOAST,
    LINK_REVOKED_TOAST,
    REVOKE_LINK_CONFIRMATION,
    SEARCH_EMPTY_TEXT,
    SHARING_UPDATED_TOAST,
    USER_REMOVED_TOAST,
)


class HostedShareDialog(BasePage):
    """The 'Share "<application name>"' dialog."""

    def __init__(self, page, app_name: str):
        super().__init__(page)
        self.app_name = app_name

    # ------------------------------------------------------------------
    # Locators
    # ------------------------------------------------------------------
    @property
    def heading(self) -> Locator:
        """Dialog title: 'Share "<application name>"'."""
        return self.page.get_by_role("heading", name=f'Share "{self.app_name}"')

    @property
    def dialog(self) -> Locator:
        """The dialog, scoped by its title."""
        return self.page.get_by_role("dialog").filter(has=self.heading)

    @property
    def search_input(self) -> Locator:
        """People search of the dialog: a multiselect whose own input is read-only and hidden.

        It takes no click; its visible label container opens the search panel.
        """
        return self.dialog.get_by_role("combobox", name="Search users by name or email")

    @property
    def search_trigger(self) -> Locator:
        """Visible label of the people search, beside its hidden input; a click opens or closes the panel.

        The dialog holds one multiselect, the people search.
        """
        return self.dialog.locator('[data-pc-section="labelcontainer"]')

    @property
    def search_panel(self) -> Locator:
        """Panel of the people search; rendered at the end of the page, outside the dialog."""
        return self.page.locator('[data-pc-section="panel"]').filter(
            has=self.page.get_by_role("listbox")
        )

    @property
    def search_box(self) -> Locator:
        """Text box of the search panel that takes the query."""
        return self.search_panel.get_by_role("searchbox")

    @property
    def options(self) -> Locator:
        """Every person the search offers."""
        return self.search_panel.get_by_role("option")

    def option(self, name: str) -> Locator:
        """The person the search offers under this display name."""
        return self.search_panel.get_by_role("option", name=name)

    @property
    def search_empty_text(self) -> Locator:
        """Text the search shows when it offers nobody."""
        return self.search_panel.get_by_text(SEARCH_EMPTY_TEXT)

    def access_entry(self, email: str) -> Locator:
        """The 'People With Access' entry of the person with this e-mail."""
        return self.dialog.get_by_role("listitem").filter(has_text=email)

    def remove_button(self, name: str) -> Locator:
        """'Remove <name>' button of a 'People With Access' entry.

        Scoped to the list: a person picked in the search but not saved yet carries a chip with
        the same label.
        """
        return self.dialog.get_by_role("listitem").get_by_role(
            "button", name=f"Remove {name}", exact=True
        )

    @property
    def save_button(self) -> Locator:
        """Save; disabled until a person is picked."""
        return self.dialog.get_by_role("button", name="Save")

    @property
    def copy_link_button(self) -> Locator:
        """Copy share link; creates the link first when the application has none."""
        return self.dialog.get_by_role("button", name="Copy share link")

    @property
    def revoke_link_button(self) -> Locator:
        """Revoke link; present only while the application has a live link."""
        return self.dialog.get_by_role("button", name="Revoke link", exact=True)

    @property
    def revoke_confirmation(self) -> Locator:
        """Confirmation asked before the link is revoked: its own dialog, named by its title.

        Title from frontend src/components/sharing/ShareLinkSection.tsx:39.
        """
        return self.page.get_by_role(
            "dialog", name=REVOKE_LINK_CONFIRMATION, exact=True
        )

    @property
    def confirm_revoke_button(self) -> Locator:
        """'Revoke link' button of the confirmation.

        Label from frontend src/components/sharing/ShareLinkSection.tsx:150.
        """
        return self.revoke_confirmation.get_by_role(
            "button", name="Revoke link", exact=True
        )

    def error_text(self, message: str) -> Locator:
        """The refusal message the dialog shows under the list after a failed Save.

        Only the paragraph: while the dialog is open it also holds the screen-reader copy of every
        notification, with the same text. The paragraph holds the server's message (frontend
        src/components/sharing/SharePopup.tsx:213 and :296).
        """
        return self.dialog.locator("p").filter(
            has_text=re.compile(rf"^{re.escape(message)}$")
        )

    def toast(self, text: str) -> Locator:
        """The visible notification with this text, in the notification area.

        The screen-reader copy of the same text lives elsewhere (in the open dialog, or at the
        end of the page) and is left out.
        """
        return self.page.locator("#toast-container").get_by_text(text, exact=True)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    @step
    def open_search(self):
        """Open the search panel; a panel already open stays open."""
        if not self.search_box.is_visible():
            self.search_trigger.click()
        expect(self.search_box).to_be_visible()
        return self

    @step
    def search(self, query: str):
        """Type a search into the panel and wait until the platform has answered it."""
        self.open_search()
        with self.page.expect_response(
            lambda response: "/sharable-users" in response.url
        ):
            self.search_box.fill(query)
        return self

    @step
    def pick(self, name: str):
        """Pick a person the search offers."""
        self.option(name).click()
        return self

    @step
    def save(self):
        """Close the search list, press Save and wait for the platform's answer."""
        # The open search list covers Save.
        self.heading.click()
        with self.page.expect_response(
            lambda response: response.url.endswith("/share")
            and response.request.method == "POST"
        ):
            self.save_button.click()
        return self

    @step
    def add(self, query: str, name: str):
        """Search a person, pick them and press Save."""
        return self.search(query).pick(name).save()

    @step
    def remove(self, name: str):
        """Remove a person from 'People With Access'; it takes effect on the click."""
        with self.page.expect_response(
            lambda response: response.url.endswith("/share")
            and response.request.method == "DELETE"
        ):
            self.remove_button(name).click()
        return self

    @step
    def copy_link(self):
        """Press Copy share link and wait for the copy to be confirmed."""
        self.copy_link_button.click()
        expect(self.toast(LINK_COPIED_TOAST)).to_be_visible()
        return self

    @step
    def revoke_link(self):
        """Press Revoke link, confirm, and wait for the platform's answer."""
        self.revoke_link_button.click()
        with self.page.expect_response(
            lambda response: response.url.endswith("/share-link")
            and response.request.method == "DELETE"
        ):
            self.confirm_revoke_button.click()
        return self

    def clipboard_text(self) -> str:
        """What the browser's clipboard holds; the context needs the clipboard permissions."""
        return self.page.evaluate("() => navigator.clipboard.readText()")

    # ------------------------------------------------------------------
    # Assertions
    # ------------------------------------------------------------------
    @step
    def should_be_open(self):
        expect(self.heading).to_be_visible()
        return self

    @step
    def should_offer(self, name: str):
        """The search offers the person with this display name."""
        expect(self.option(name)).to_be_visible()
        return self

    @step
    def should_offer_nobody_instead_of(self, previous: str):
        """The latest search offers no person.

        The panel keeps the options of the search before until the new answer replaces them, and
        shows the empty-search text before any search too. Waiting for ``previous``, a person the
        search before offered, to go first makes sure the checks read the latest answer.
        """
        expect(self.option(previous)).to_have_count(0)
        expect(self.options).to_have_count(0)
        expect(self.search_empty_text).to_be_visible()
        return self

    @step
    def should_list(self, email: str):
        """'People With Access' lists the person."""
        expect(self.access_entry(email)).to_be_visible()
        return self

    @step
    def should_not_list(self, email: str):
        """'People With Access' does not list the person."""
        expect(self.access_entry(email)).to_have_count(0)
        return self

    @step
    def should_be_closed_after_sharing(self):
        """Save closed the dialog and said the sharing was updated."""
        expect(self.toast(SHARING_UPDATED_TOAST)).to_be_visible()
        expect(self.heading).to_be_hidden()
        return self

    @step
    def should_confirm_removal(self):
        expect(self.toast(USER_REMOVED_TOAST)).to_be_visible()
        return self

    @step
    def should_have_link(self):
        """The application has a live link: the dialog offers to revoke it."""
        expect(self.revoke_link_button).to_be_visible()
        return self

    @step
    def should_have_no_link(self):
        """The link is revoked: the dialog says so and no longer offers to revoke it."""
        expect(self.toast(LINK_REVOKED_TOAST)).to_be_visible()
        expect(self.revoke_link_button).to_have_count(0)
        return self

    @step
    def should_have_copied(self, text: str):
        """The clipboard holds a link containing ``text``."""
        assert_that(
            self.clipboard_text(),
            contains_string(text),
            "the copied share link is in the clipboard",
        )
        return self

    @step
    def should_show_error(self, message: str):
        """The dialog stays open and shows the refusal message, also as a notification."""
        expect(self.heading).to_be_visible()
        expect(self.error_text(message)).to_be_visible()
        expect(self.toast(message)).to_be_visible()
        return self
