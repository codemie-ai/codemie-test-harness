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

"""Page object component for the ChatDisclaimer element in the Chat page.

Locators derived from live UI inspection on 2026-08-31.
The component renders below the chat message input as a non-dismissible
notice with ``data-testid="chat-disclaimer"``.  URL links in the disclaimer
text are rendered as ``<a>`` elements with ``rel="noopener noreferrer"``.
"""

from playwright.sync_api import expect, Page
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


class ChatDisclaimerComponent(BasePage):
    """Page object component for the chat disclaimer area below the composer."""

    def __init__(self, page: Page):
        super().__init__(page)

    # ── Locators ──────────────────────────────────────────────────────────────

    @property
    def disclaimer_container(self):
        """Root element of the chat disclaimer (``data-testid="chat-disclaimer"``)."""
        return self.page.get_by_test_id("chat-disclaimer")

    @property
    def disclaimer_link(self):
        """First anchor link rendered inside the disclaimer text."""
        return self.disclaimer_container.get_by_role("link").first

    @property
    def dismiss_button(self):
        """Dismiss / close button (must NOT be present — disclaimer is non-dismissible)."""
        return self.disclaimer_container.get_by_role("button")

    # ── Assertions ────────────────────────────────────────────────────────────

    @step
    def should_be_visible(self):
        """Assert the disclaimer element is visible in the chat page."""
        expect(self.disclaimer_container).to_be_visible(timeout=10000)
        return self

    @step
    def should_not_be_visible(self):
        """Assert the disclaimer element is absent from the chat page."""
        expect(self.disclaimer_container).to_have_count(0)
        return self

    @step
    def should_not_have_dismiss_button(self):
        """Assert there is no dismiss/close button on the disclaimer (non-dismissible)."""
        expect(self.dismiss_button).to_have_count(0)
        return self

    @step
    def should_have_link(self):
        """Assert at least one anchor link is rendered inside the disclaimer."""
        expect(self.disclaimer_link).to_be_visible(timeout=10000)
        return self

    @step
    def should_contain_text(self, text: str):
        """Assert the disclaimer container contains the given text.

        Args:
            text: Substring expected to appear in the disclaimer.
        """
        expect(self.disclaimer_container).to_contain_text(text)
        return self
