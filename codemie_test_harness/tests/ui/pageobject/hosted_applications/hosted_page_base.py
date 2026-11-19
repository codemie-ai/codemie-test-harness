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

"""Base of the hosted-application page objects: what they share, kept in one place."""

import re

from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage

# Names of controls that talk about opening an application in a new tab.
NEW_TAB_NAME = re.compile("new tab", re.IGNORECASE)
# Enough Tab presses to cross the navigation, the header and a page of cards.
MAX_TAB_PRESSES = 120


class HostedPageBase(BasePage):
    """Keyboard route shared by the hosted-application pages."""

    @step
    def focus_by_keyboard(self, target: Locator):
        """Press Tab until ``target`` has the focus; it fails when the control is not reachable."""
        for _ in range(MAX_TAB_PRESSES):
            if target.evaluate("element => element === document.activeElement"):
                return self
            self.page.keyboard.press("Tab")
        expect(target).to_be_focused()
        return self

    @step
    def press_key(self, key: str):
        """Press a key on the focused control."""
        self.page.keyboard.press(key)
        return self

    @step
    def press_enter(self):
        """Press Enter on the focused control."""
        return self.press_key("Enter")
