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

"""Page object for the Applications area: the collection tabs, the cards of hosted applications
and the keyboard route through them."""

import re

from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.components.options_menu import (
    OptionsMenu,
)
from codemie_test_harness.tests.ui.pageobject.hosted_applications.hosted_page_base import (
    NEW_TAB_NAME,
    HostedPageBase,
)

APPS_ROUTE = "/apps"
LEGACY_ROUTE = "/applications"
SHARED_WITH_ME = "Shared with me"
NO_ACTIVE_VERSION = "No active version yet"
# A card holds its own role=button element plus the More options button.
CARD_BUTTONS_WITHOUT_NEXT_STEP = 2


class HostedApplicationsPage(HostedPageBase):
    """Applications collections (My apps, Platform apps) and their application cards."""

    # ------------------------------------------------------------------
    # Locators
    # ------------------------------------------------------------------
    @property
    def collections_navigation(self) -> Locator:
        """Navigation of the application collections."""
        return self.page.get_by_role("navigation", name="Application collections")

    @property
    def platform_apps_tab(self) -> Locator:
        """Platform apps collection button."""
        return self.collections_navigation.get_by_role("button", name="Platform apps")

    @property
    def platform_apps_heading(self) -> Locator:
        """Heading of the Platform apps collection."""
        return self.page.get_by_role("heading", name="Platform apps", level=1)

    @property
    def my_apps_heading(self) -> Locator:
        """Heading of the My apps collection."""
        return self.page.get_by_role("heading", name="My apps", level=1)

    def card(self, name: str) -> Locator:
        """The card of the application with this name."""
        return self.page.get_by_role("article", name=name, exact=True)

    def open_card_button(self, name: str) -> Locator:
        """The card itself as one control: it is named 'Open <name>' while the application can run.

        The match is exact: the card also holds an overflow menu and, for a manager, a next-step
        button, whose names are different.
        """
        return self.card(name).get_by_role("button", name=f"Open {name}", exact=True)

    def unopenable_card_button(self, name: str) -> Locator:
        """The card itself as one control named just '<name>': the application cannot run."""
        return self.card(name).get_by_role("button", name=name, exact=True)

    def more_options_button(self, name: str) -> Locator:
        """More options button of a card."""
        return self.card(name).get_by_role("button", name=f"More options {name}")

    @property
    def options_menu(self) -> OptionsMenu:
        """The More options menu of a card."""
        return OptionsMenu(self.page)

    def next_step_button(self, name: str, label: str) -> Locator:
        """The next-step button of a card whose application has nothing live, by its exact label."""
        return self.card(name).get_by_role("button", name=label, exact=True)

    def activate_version_button(self, name: str) -> Locator:
        """Activate version button of a card whose application has nothing live."""
        return self.next_step_button(name, "Activate version")

    def new_tab_controls(self, name: str) -> Locator:
        """Any control of the card that talks about a new tab."""
        return self.card(name).get_by_role("button", name=NEW_TAB_NAME)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    @step
    def open_my_apps(self):
        """Open the My apps collection."""
        self.page.goto(APPS_ROUTE)
        expect(self.my_apps_heading).to_be_visible()
        return self

    @step
    def open_shared_with_me(self):
        """Open the Shared with me collection."""
        self.page.goto(APPS_ROUTE)
        self.collections_navigation.get_by_role(
            "button", name=SHARED_WITH_ME, exact=True
        ).click()
        expect(
            self.page.get_by_role("heading", name=SHARED_WITH_ME, level=1)
        ).to_be_visible()
        return self

    @step
    def open_legacy_applications_route(self):
        """Open the address the Applications page had before the collections."""
        self.page.goto(LEGACY_ROUTE)
        return self

    @step
    def open_platform_apps_tab(self):
        """Switch to the Platform apps collection."""
        self.platform_apps_tab.click()
        return self

    @step
    def click_card(self, name: str):
        """Click the card of an application that can run; it opens in the viewer."""
        self.open_card_button(name).click()
        return self

    @step
    def click_card_without_live_version(self, name: str):
        """Click the card of an application that cannot run; it opens the details page."""
        self.unopenable_card_button(name).click()
        return self

    @step
    def click_next_step_button(self, name: str, label: str):
        """Press the next-step button of a card by its label."""
        self.next_step_button(name, label).click()
        return self

    @step
    def open_card_menu(self, name: str):
        """Open the More options menu of a card."""
        self.more_options_button(name).click()
        self.options_menu.should_be_open()
        return self.options_menu

    @step
    def click_activate_version(self, name: str):
        """Press Activate version on a card."""
        self.activate_version_button(name).click()
        return self

    # ------------------------------------------------------------------
    # Keyboard
    # ------------------------------------------------------------------
    @step
    def focus_card_by_keyboard(self, name: str):
        """Tab to the card of an application that can run."""
        return self.focus_by_keyboard(self.open_card_button(name))

    # ------------------------------------------------------------------
    # Assertions
    # ------------------------------------------------------------------
    @step
    def should_be_on_applications_route(self):
        """The address is the Applications area."""
        expect(self.page).to_have_url(re.compile(r"/apps/?$"))
        return self

    @step
    def should_show_platform_apps(self):
        """The Platform apps collection is shown at its own address."""
        expect(self.page).to_have_url(re.compile(r"/apps/platform/?$"))
        expect(self.platform_apps_heading).to_be_visible()
        return self

    @step
    def should_have_focus_on_card(self, name: str):
        """The focus is on the one control named 'Open <name>'."""
        expect(self.open_card_button(name)).to_have_count(1)
        expect(self.open_card_button(name)).to_be_focused()
        return self

    @step
    def should_name_card_for_opening(self, name: str):
        """The card is one control whose accessible name is 'Open <name>'."""
        expect(self.open_card_button(name)).to_be_visible()
        return self

    @step
    def should_name_card_without_open(self, name: str):
        """The card is one control named just '<name>', with no 'Open' in it."""
        expect(self.unopenable_card_button(name)).to_have_attribute("aria-label", name)
        expect(self.open_card_button(name)).to_have_count(0)
        return self

    @step
    def should_show_no_active_version_badge(self, name: str):
        """The cover carries the 'No active version yet' badge."""
        expect(
            self.card(name).get_by_text(NO_ACTIVE_VERSION, exact=True)
        ).to_be_visible()
        return self

    @step
    def should_have_only_card_and_menu_buttons(self, name: str):
        """The card has no button besides itself and More options."""
        expect(self.card(name).get_by_role("button")).to_have_count(
            CARD_BUTTONS_WITHOUT_NEXT_STEP
        )
        expect(
            self.open_card_button(name).or_(self.unopenable_card_button(name))
        ).to_have_count(1)
        expect(self.more_options_button(name)).to_be_visible()
        return self

    @step
    def should_show_next_step_button(self, name: str, label: str):
        """The card shows the next-step button with this label."""
        expect(self.next_step_button(name, label)).to_be_visible()
        return self

    @step
    def should_show_card_without_live_version(self, name: str):
        """The card says the application is not shared and has no live version, and offers Activate version."""
        card = self.card(name)
        expect(card.get_by_text("Not shared with project", exact=True)).to_be_visible()
        expect(card.get_by_text("No active version yet", exact=True)).to_be_visible()
        expect(self.activate_version_button(name)).to_be_visible()
        return self

    @step
    def should_not_offer_open_in_new_tab(self, name: str):
        """The card has no control for opening the application in a new tab."""
        expect(self.open_card_button(name)).to_be_visible()
        expect(self.new_tab_controls(name)).to_have_count(0)
        return self
