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

"""
Page object for the scrollable left navigation menu.
Covers the nav links scroll container, the fixed logo and bottom blocks,
the expand/collapse toggle and the main content area next to the nav.
"""

import re

from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.test_data.navigation_test_data import ScrollInput


class NavigationMenuPage(BasePage):
    """Left navigation menu with its scroll container and fixed blocks."""

    def __init__(self, page):
        super().__init__(page)
        self._logo_height = None
        self._main_scroll_top_before = None

    # ------------------------------------------------------------------
    # Locators
    # ------------------------------------------------------------------
    @property
    def header(self) -> Locator:
        """Navigation header (root of the left menu)."""
        return self.page.locator("header#navigation-menu")

    @property
    def links_wrapper(self) -> Locator:
        """Scrollable wrapper holding the upper, secondary and favorites nav links."""
        # The top/secondary nav elements carry no aria-label in the live DOM, so the
        # wrapper is identified by the role-based Chats link it contains (the logo
        # and bottom blocks are separate direct children without it).
        return self.header.locator(":scope > div").filter(
            has=self.page.get_by_role("link", name="Chats", exact=True)
        )

    @property
    def first_link(self) -> Locator:
        """First link inside the scrollable wrapper."""
        return self.links_wrapper.get_by_role("link").first

    @property
    def last_link(self) -> Locator:
        """Last link inside the scrollable wrapper."""
        return self.links_wrapper.get_by_role("link").last

    @property
    def dividers(self) -> Locator:
        """Divider lines inside the scrollable wrapper."""
        return self.links_wrapper.locator("div.h-px")

    @property
    def toggle_button(self) -> Locator:
        """Expand/collapse button; its name is 'Hide Menu' when expanded, 'Show Menu' when collapsed."""
        return self.header.get_by_role("button", name=re.compile(r"^(Show|Hide) Menu$"))

    @property
    def hide_menu_button(self) -> Locator:
        """Hide Menu button (present while the nav is expanded)."""
        return self.header.get_by_role("button", name="Hide Menu", exact=True)

    @property
    def profile_button(self) -> Locator:
        """Profile button in the bottom block (a button, not a link)."""
        return self.header.get_by_role("button", name="Profile")

    @property
    def analytics_link(self) -> Locator:
        """Analytics nav item (lower item of the secondary section)."""
        return self.links_wrapper.get_by_role("link", name="Analytics", exact=True)

    @property
    def main_scroll_container(self) -> Locator:
        """Scroll container (overflow-y-auto div) inside the main content area."""
        return self.page.locator("main#main-content div.overflow-y-auto").first

    @property
    def main_content(self) -> Locator:
        """Main content area next to the navigation."""
        return self.page_content.first

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    @step
    def set_viewport(self, width: int, height: int):
        """Resize the browser viewport."""
        self.page.set_viewport_size({"width": width, "height": height})
        return self

    @step
    def ensure_expanded(self):
        """Bring the nav to the expanded state (a fresh session starts collapsed)."""
        expect(self.toggle_button).to_be_visible()
        if "w-navbar-expanded" not in (self.header.get_attribute("class") or ""):
            self.toggle_button.click()
        return self.should_be_expanded()

    @step
    def remember_logo_height(self):
        """Record the logo height before the viewport is reduced."""
        expect(self.menu.logo_link).to_be_visible()
        self._logo_height = self.menu.logo_link.bounding_box()["height"]
        return self

    @step
    def scroll_links_wrapper_to_end(self):
        """Scroll the nav links wrapper to its bottom."""
        self.links_wrapper.evaluate("el => { el.scrollTop = el.scrollHeight; }")
        return self

    @step
    def scroll_links_with_input(self, input_method: str):
        """Scroll the nav links using the given input method (mouse wheel or keyboard Tab)."""
        {
            ScrollInput.MOUSE_WHEEL: self._scroll_links_with_mouse_wheel,
            ScrollInput.KEYBOARD_TAB: self._focus_last_link_with_tab,
        }[input_method]()
        return self

    def _scroll_links_with_mouse_wheel(self):
        self.links_wrapper.hover()
        self.page.mouse.wheel(0, 5000)

    def _focus_last_link_with_tab(self):
        self.first_link.focus()
        max_presses = self.links_wrapper.get_by_role("link").count() * 3
        for _ in range(max_presses):
            if self.last_link.evaluate("el => el === document.activeElement"):
                break
            self.page.keyboard.press("Tab")

    @step
    def scroll_analytics_link_into_view(self):
        """Scroll the nav links wrapper until the Analytics item is shown."""
        self.analytics_link.scroll_into_view_if_needed()
        return self

    @step
    def click_analytics_link(self):
        """Click the Analytics nav item."""
        self.analytics_link.click()
        return self

    @step
    def collapse_menu(self):
        """Collapse the expanded nav with Hide Menu."""
        self.hide_menu_button.click()
        return self

    @step
    def expand_menu(self):
        """Expand the collapsed nav with Show Menu."""
        self.toggle_button.click()
        return self

    @step
    def scroll_main_content_with_mouse_wheel(self):
        """Record the main scroll container position, then scroll the main content with the mouse wheel."""
        self._main_scroll_top_before = self.main_scroll_container.evaluate(
            "el => el.scrollTop"
        )
        self.main_content.hover()
        self.page.mouse.wheel(0, 1500)
        return self

    # ------------------------------------------------------------------
    # Verifications
    # ------------------------------------------------------------------
    @step
    def should_have_scrollable_links_wrapper(self):
        """Links wrapper is a vertical scroll container whose content overflows its box."""
        expect(self.links_wrapper).to_have_css("overflow-y", "auto")
        self.page.wait_for_function(
            "el => el.scrollHeight > el.clientHeight",
            arg=self.links_wrapper.element_handle(),
        )
        return self

    @step
    def should_have_desktop_scroll_container(self):
        """Links wrapper keeps overflow-y auto as the desktop scroll container."""
        expect(self.links_wrapper).to_have_css("overflow-y", "auto")
        return self

    @step
    def should_have_links_wrapper_scrolled(self):
        """Links wrapper scroll position has advanced."""
        self.page.wait_for_function(
            "el => el.scrollTop > 0", arg=self.links_wrapper.element_handle()
        )
        return self

    @step
    def should_have_last_link_in_viewport(self):
        """Last nav link is visible inside the nav."""
        expect(self.last_link).to_be_in_viewport()
        return self

    @step
    def should_have_analytics_link_in_viewport(self):
        """Analytics nav item is visible inside the nav."""
        expect(self.analytics_link).to_be_in_viewport()
        return self

    @step
    def should_not_have_analytics_link_in_viewport(self):
        """Analytics nav item is off-screen (clipped by the scroll container)."""
        expect(self.analytics_link).not_to_be_in_viewport()
        return self

    @step
    def should_have_logo_not_squeezed(self):
        """Logo is in the viewport and keeps the height it had before the resize."""
        expect(self.menu.logo_link).to_be_in_viewport()
        assert self._logo_height is not None, "call remember_logo_height() first"
        expect(self.menu.logo_link).to_have_css("height", f"{self._logo_height}px")
        return self

    @step
    def should_have_bottom_nav_reachable(self):
        """Help, Profile and Hide Menu are inside the viewport and clickable."""
        for control in (
            self.menu.help_link,
            self.profile_button,
            self.hide_menu_button,
        ):
            expect(control).to_be_in_viewport()
            expect(control).to_be_enabled()
        return self

    @step
    def should_have_dividers_rendered(self, expected_count: int):
        """Every divider inside the nav links wrapper has a rendered height greater than 0."""
        expect(self.dividers).to_have_count(expected_count)
        for divider in self.dividers.all():
            self.page.wait_for_function(
                "el => el.getBoundingClientRect().height > 0",
                arg=divider.element_handle(),
            )
        return self

    @step
    def should_be_expanded(self):
        """Nav is in its expanded width state."""
        expect(self.header).to_have_class(re.compile(r"w-navbar-expanded"))
        return self

    @step
    def should_be_collapsed(self):
        """Nav is in its collapsed width state."""
        expect(self.header).to_have_class(re.compile(r"(^|\s)w-navbar(\s|$)"))
        expect(self.header).not_to_have_class(re.compile(r"w-navbar-expanded"))
        return self

    @step
    def should_have_main_content_scrolled(self):
        """The main content scroll container advanced past its pre-scroll position."""
        assert self._main_scroll_top_before is not None, (
            "call scroll_main_content_with_mouse_wheel() first"
        )
        self.page.wait_for_function(
            "([el, before]) => el.scrollTop > before",
            arg=[
                self.main_scroll_container.element_handle(),
                self._main_scroll_top_before,
            ],
        )
        return self
