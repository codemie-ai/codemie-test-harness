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

"""Page object for the Applications collections that list hosted application cards."""

from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.pageobject.components.options_menu import (
    OptionsMenu,
)
from codemie_test_harness.tests.ui.pageobject.hosted_apps.hosted_application_details_page import (
    HostedApplicationDetailsPage,
)
from codemie_test_harness.tests.ui.pageobject.hosted_apps.hosted_application_viewer_page import (
    HostedApplicationViewerPage,
)

MY_APPS = "My apps"
SHARED_WITH_ME = "Shared with me"
NO_ACTIVE_VERSION = "No active version yet"
# A card holds its own role=button element plus the More options button.
CARD_BUTTONS_WITHOUT_NEXT_STEP = 2


class HostedApplicationsPage(BasePage):
    """Collections of hosted applications: My apps, Shared with me and the others."""

    @property
    def collection_tabs(self) -> Locator:
        """Navigation bar of the collections."""
        return self.page.get_by_role("navigation", name="Application collections")

    def collection_tab(self, name: str) -> Locator:
        """Tab of one collection."""
        return self.collection_tabs.get_by_role("button", name=name, exact=True)

    def collection_heading(self, name: str) -> Locator:
        """Heading of the open collection."""
        return self.page.get_by_role("heading", level=1, name=name, exact=True)

    def card(self, app_name: str) -> Locator:
        """The article of the card whose title is this application name."""
        return self.page.get_by_role("article").filter(
            has=self.page.get_by_role("heading", level=3, name=app_name, exact=True)
        )

    def card_button(self, app_name: str, openable: bool = True) -> Locator:
        """The card itself, a button named "Open <name>", or just the name when it cannot open."""
        label = f"Open {app_name}" if openable else app_name
        return self.card(app_name).get_by_role("button", name=label, exact=True)

    def more_options_button(self, app_name: str) -> Locator:
        """More options button of a card."""
        return self.card(app_name).get_by_role(
            "button", name=f"More options {app_name}"
        )

    def next_step_button(self, app_name: str, label: str) -> Locator:
        """The manager's next-step button of a card without an active version."""
        return self.card(app_name).get_by_role("button", name=label, exact=True)

    @property
    def options_menu(self) -> OptionsMenu:
        """The card More options menu."""
        return OptionsMenu(self.page)

    @step
    def open_collection(self, name: str):
        """Open the Applications area and switch to a collection."""
        self.go_to_applications_page()
        self.collection_tab(name).click()
        expect(self.collection_heading(name)).to_be_visible()
        return self

    @step
    def open_my_apps(self):
        """Open the My apps collection."""
        return self.open_collection(MY_APPS)

    @step
    def open_shared_with_me(self):
        """Open the Shared with me collection."""
        return self.open_collection(SHARED_WITH_ME)

    @step
    def should_name_card_for_opening(self, app_name: str):
        """Verify the card is a button whose accessible name is "Open <app name>"."""
        expect(self.card_button(app_name)).to_be_visible()
        expect(self.card_button(app_name)).to_have_attribute(
            "aria-label", f"Open {app_name}"
        )
        return self

    @step
    def should_name_card_without_open(self, app_name: str):
        """Verify the card is a button named with the bare application name."""
        expect(self.card_button(app_name, openable=False)).to_have_attribute(
            "aria-label", app_name
        )
        return self

    @step
    def activate_card(self, app_name: str, activation: str, openable: bool = True):
        """Activate the card with a click, or with a key pressed on the focused card."""
        card_button = self.card_button(app_name, openable)
        if activation == "click":
            card_button.click()
        else:
            card_button.press(activation)
        return self

    @step
    def click_card(self, app_name: str, openable: bool = True):
        """Click the card body."""
        return self.activate_card(app_name, "click", openable)

    @step
    def should_show_no_active_version_badge(self, app_name: str):
        """Verify the cover carries the "No active version yet" badge."""
        expect(
            self.card(app_name).get_by_text(NO_ACTIVE_VERSION, exact=True)
        ).to_be_visible()
        return self

    @step
    def should_have_only_card_and_menu_buttons(self, app_name: str):
        """Verify the card has no button besides itself and More options."""
        expect(self.card(app_name).get_by_role("button")).to_have_count(
            CARD_BUTTONS_WITHOUT_NEXT_STEP
        )
        expect(self.more_options_button(app_name)).to_be_visible()
        return self

    @step
    def should_show_next_step_button(self, app_name: str, label: str):
        """Verify the card shows the manager's next-step button with this text."""
        expect(self.next_step_button(app_name, label)).to_be_visible()
        return self

    @step
    def click_next_step_button(self, app_name: str, label: str):
        """Click the manager's next-step button of a card."""
        self.next_step_button(app_name, label).click()
        return HostedApplicationDetailsPage(self.page)

    @step
    def open_card_menu(self, app_name: str):
        """Open the More options menu of a card."""
        self.more_options_button(app_name).click()
        self.options_menu.should_be_open()
        return self.options_menu

    @step
    def open_details_from_card_menu(self, app_name: str):
        """Choose Details in the More options menu of a card."""
        self.open_card_menu(app_name).choose_item("Details")
        return HostedApplicationDetailsPage(self.page)

    @step
    def open_viewer_from_card(self, app_name: str):
        """Click an openable card to go to its viewer."""
        self.click_card(app_name)
        return HostedApplicationViewerPage(self.page)

    @step
    def should_still_list_card(self, app_name: str):
        """Verify the collection still shows the card, so no navigation left the list."""
        expect(self.card(app_name)).to_be_visible()
        return self
