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

from playwright.sync_api import expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


class ShareAssistantPopup(BasePage):
    """Page object for the 'Share assistant' dialog (owner-only grant/revoke view)."""

    # ----------------
    # --- LOCATORS ---
    # ----------------

    @property
    def dialog_heading(self):
        """Dialog title: 'Share assistant'."""
        return self.page.get_by_role("heading", name="Share assistant")

    @property
    def dialog(self):
        """The dialog container, scoped by its title."""
        return self.page.get_by_role("dialog").filter(has=self.dialog_heading)

    @property
    def user_search_input(self):
        """Typeahead combobox used to find and add a grantee."""
        return self.dialog.get_by_role("combobox", name="Search users by name or email")

    def user_option(self, name: str):
        """Typeahead option for a matching user, by display name."""
        return self.dialog.get_by_role("option", name=name)

    @property
    def people_with_access_label(self):
        """'People With Access' label above the current grants list."""
        return self.dialog.get_by_text("People With Access")

    def access_list_item(self, name: str):
        """A single 'People With Access' entry, by grantee display name."""
        return self.dialog.get_by_role("listitem").filter(has_text=name)

    def remove_button(self, name: str):
        """'Remove <name>' button on a 'People With Access' entry."""
        return self.dialog.get_by_role("button", name=f"Remove {name}")

    @property
    def save_button(self):
        """Dialog 'Save' button (disabled until a change is made)."""
        return self.dialog.get_by_role("button", name="Save")

    @property
    def cancel_button(self):
        """Dialog 'Cancel' button."""
        return self.dialog.get_by_role("button", name="Cancel")

    @property
    def status_toast(self):
        """Status toast shown after Save: 'Assistant sharing updated.'."""
        return self.page.get_by_text("Assistant sharing updated.")

    # --------------------------
    # --- ACTIONS ---
    # --------------------------

    @step
    def search_user(self, query: str):
        """Type into the user typeahead."""
        self.user_search_input.click()
        self.user_search_input.fill(query)
        return self

    @step
    def select_user(self, name: str):
        """Pick a matching user from the typeahead options."""
        self.user_option(name).click()
        return self

    @step
    def close_listbox(self):
        """Close the open typeahead listbox (it otherwise intercepts the Save click)."""
        self.dialog_heading.click()
        return self

    @step
    def save(self):
        """Close the typeahead listbox if open, then click Save."""
        self.close_listbox()
        self.save_button.click()
        return self

    @step
    def remove_user(self, name: str):
        """Click 'Remove' for a grantee in the 'People With Access' list.

        Removal is applied immediately (optimistic UI update backed by an
        immediate DELETE call), independent of the Save button. Waits for
        that DELETE to resolve so a caller that reloads right after this
        call is guaranteed the revoke was persisted, instead of racing an
        in-flight request that `page.reload()` could cancel.
        """
        with self.page.expect_response(
            lambda response: "/share" in response.url
            and response.request.method == "DELETE"
        ):
            self.remove_button(name).click()
        return self

    # --------------------------
    # --- EXPECT/VERIFY ---
    # --------------------------

    @step
    def should_be_open(self):
        """Verify the dialog is visible."""
        expect(self.dialog_heading).to_be_visible()
        return self

    @step
    def should_list_user(self, name: str):
        """Verify a grantee is listed under 'People With Access'."""
        expect(self.access_list_item(name)).to_be_visible()
        return self

    @step
    def should_not_list_user(self, name: str):
        """Verify a grantee is no longer listed under 'People With Access'."""
        expect(self.access_list_item(name)).to_be_hidden()
        return self

    @step
    def should_show_update_status(self):
        """Verify the 'Assistant sharing updated.' status toast appeared."""
        expect(self.status_toast).to_be_visible()
        return self
