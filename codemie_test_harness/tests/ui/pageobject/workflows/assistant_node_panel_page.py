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

"""Page object for the AssistantNodePanel on workflow details screens.

The panel opens as a complementary aside element when a workflow node is clicked.
It embeds AssistantDetailsEmbedded which may contain the UserMapping section.

Covers: Per-workflow scope for personal integration settings.
"""

from playwright.sync_api import expect, Locator
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.pageobject.workflows.user_mapping_section_page import (
    UserMappingSectionPage,
)


class AssistantNodePanelPage(BasePage):
    """Composite page object for the full assistant panel on workflow screens.

    The panel opens when a workflow canvas node is clicked. It contains
    the assistant's details including the 'Your Integration Settings' section
    when the assistant has user-selectable integration slots.
    """

    # ==================== PROPERTIES ====================

    @property
    def panel_container(self) -> Locator:
        """The aside element representing the open assistant node panel."""
        return self.page.locator("aside").filter(has_text="Assistant")

    @property
    def user_mapping_section(self) -> UserMappingSectionPage:
        """Composed UserMappingSectionPage component within the panel."""
        return UserMappingSectionPage(self.page)

    # ==================== ASSERTION METHODS ====================

    @step
    def should_be_visible(self):
        """Assert that the assistant node panel is open and visible."""
        expect(self.panel_container).to_be_visible()

    @step
    def should_have_user_mapping_section(self, timeout: int = 15000):
        """Assert that the 'Your Integration Settings' section is present in the panel.

        Expected for assistants with at least one user-selectable integration slot.
        """
        self.user_mapping_section.should_be_visible(timeout=timeout)

    @step
    def should_not_have_user_mapping_section(self):
        """Assert that the 'Your Integration Settings' section is absent.

        Expected for assistants with no user-selectable (all-pinned) integration slots (AC25).
        """
        self.user_mapping_section.should_not_be_visible()

    @step
    def should_have_no_checkbox(self):
        """Assert that no 'Apply to the whole assistant' checkbox is present.

        Used to verify assistant-page behavior where no checkbox is rendered (AC15).
        """
        self.user_mapping_section.should_have_no_checkbox()

    @step
    def should_have_checkbox_pre_ticked(self):
        """Assert that the 'Apply to the whole assistant' checkbox is pre-ticked.

        Expected when user has no existing assistant-scoped selection (AC8).
        """
        self.user_mapping_section.should_checkbox_be_checked()

    @step
    def should_have_checkbox_unticked(self):
        """Assert that the 'Apply to the whole assistant' checkbox is not checked.

        Expected when user already has an assistant-scoped selection (AC9).
        """
        self.user_mapping_section.should_checkbox_be_unchecked()
