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
UI tests for the scrollable left navigation menu.

At limited viewport heights the nav links scroll inside the nav while the logo
and the bottom block (Help, Profile, Hide Menu) stay reachable.
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.analytics.analytics_page import (
    AnalyticsPage,
)
from codemie_test_harness.tests.ui.pageobject.assistants.assistants_page import (
    AssistantsPage,
)
from codemie_test_harness.tests.ui.pageobject.navigation.navigation_menu_page import (
    NavigationMenuPage,
)
from codemie_test_harness.tests.ui.test_data.navigation_test_data import (
    DESKTOP_VIEWPORT,
    LIMITED_VIEWPORT_IDS,
    LIMITED_VIEWPORTS,
    SMALL_VIEWPORT,
    ScrollInput,
)


@pytest.mark.parametrize("viewport", LIMITED_VIEWPORTS, ids=LIMITED_VIEWPORT_IDS)
@pytest.mark.ui
def test_nav_links_scroll_and_bottom_block_stays_reachable(page, viewport):
    nav = NavigationMenuPage(page)
    nav.ensure_expanded()
    nav.remember_logo_height()

    nav.set_viewport(viewport.width, viewport.height)
    nav.should_have_scrollable_links_wrapper()
    nav.should_have_logo_not_squeezed()

    nav.scroll_links_wrapper_to_end()
    nav.should_have_links_wrapper_scrolled()
    nav.should_have_last_link_in_viewport()

    nav.should_have_bottom_nav_reachable()


@pytest.mark.parametrize(
    "input_method",
    [ScrollInput.MOUSE_WHEEL, ScrollInput.KEYBOARD_TAB],
    ids=["mouse_wheel", "keyboard_tab"],
)
@pytest.mark.ui
def test_nav_scrolls_by_wheel_and_keyboard(page, input_method):
    nav = NavigationMenuPage(page)
    nav.ensure_expanded()
    nav.set_viewport(SMALL_VIEWPORT.width, SMALL_VIEWPORT.height)
    nav.should_have_scrollable_links_wrapper()

    nav.scroll_links_with_input(input_method)

    nav.should_have_links_wrapper_scrolled()
    nav.should_have_last_link_in_viewport()


@pytest.mark.ui
def test_nav_item_selectable_after_scrolling_nav(page):
    nav = NavigationMenuPage(page)
    nav.ensure_expanded()
    nav.set_viewport(SMALL_VIEWPORT.width, SMALL_VIEWPORT.height)
    nav.should_have_scrollable_links_wrapper()

    nav.should_not_have_analytics_link_in_viewport()

    nav.scroll_analytics_link_into_view()
    nav.should_have_links_wrapper_scrolled()
    nav.should_have_analytics_link_in_viewport()

    nav.click_analytics_link()
    AnalyticsPage(page).should_be_on_analytics_page()


@pytest.mark.ui
def test_nav_collapse_resize_and_main_scroll_not_regressed(page):
    AssistantsPage(page).should_be_on_assistants_page()
    nav = NavigationMenuPage(page)
    nav.ensure_expanded()
    nav.set_viewport(SMALL_VIEWPORT.width, SMALL_VIEWPORT.height)
    nav.should_have_scrollable_links_wrapper()

    nav.collapse_menu()
    nav.should_be_collapsed()
    nav.expand_menu()
    nav.should_be_expanded()
    nav.should_have_scrollable_links_wrapper()

    nav.scroll_main_content_with_mouse_wheel()
    nav.should_have_main_content_scrolled()

    nav.set_viewport(DESKTOP_VIEWPORT.width, DESKTOP_VIEWPORT.height)
    nav.should_have_desktop_scroll_container()


@pytest.mark.ui
def test_nav_dividers_keep_height_at_limited_viewport(page):
    nav = NavigationMenuPage(page)
    nav.ensure_expanded()
    nav.set_viewport(SMALL_VIEWPORT.width, SMALL_VIEWPORT.height)
    nav.should_have_scrollable_links_wrapper()

    nav.should_have_dividers_rendered(expected_count=2)
