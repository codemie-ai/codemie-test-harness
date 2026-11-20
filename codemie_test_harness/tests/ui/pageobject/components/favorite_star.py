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

"""Favorite star shown on a skill or workflow card."""

from playwright.sync_api import Locator, expect
from reportportal_client import step


class FavoriteStar:
    """The favorite star of one card on a Skills or Workflows list.

    The star is a button whose accessible name flips between "Add to favorites"
    (not a favorite) and "Remove from favorites" (a favorite); that name is the
    filled-state signal. Removing a favorite always goes through a confirmation
    dialog whose default button is "Cancel".
    """

    def __init__(self, page, card_locator: Locator):
        """
        Args:
            page: Playwright page object
            card_locator: Locator for the card that holds the star
        """
        self.page = page
        self.card = card_locator

    @property
    def unfilled_star(self) -> Locator:
        """The star while the item is not a favorite."""
        return self.card.get_by_role("button", name="Add to favorites", exact=True)

    @property
    def filled_star(self) -> Locator:
        """The star while the item is a favorite."""
        return self.card.get_by_role("button", name="Remove from favorites", exact=True)

    @property
    def added_toast_heading(self) -> Locator:
        """Heading of the success toast shown after a favorite is saved."""
        return self.page.get_by_role("heading", name="Added to favorites", level=2)

    @property
    def removal_dialog(self) -> Locator:
        """Confirmation dialog shown when the star of a favorite is clicked."""
        return self.page.get_by_role("dialog")

    @property
    def confirm_removal_button(self) -> Locator:
        """'Remove' button of the confirmation dialog."""
        return self.removal_dialog.get_by_role("button", name="Remove", exact=True)

    @step("Favorite the item and wait for the save toast")
    def favorite(self):
        """Click the unfilled star and wait until the save toast confirms the save."""
        self.unfilled_star.click()
        expect(self.added_toast_heading).to_be_visible()
        return self

    @step("Remove the item from favorites")
    def unfavorite(self):
        """Click the filled star, confirm the removal dialog, wait for the star to unfill."""
        self.filled_star.click()
        self.confirm_removal_button.click()
        expect(self.unfilled_star).to_be_visible()
        return self

    @step("Verify the star is filled")
    def should_be_filled(self):
        """Verify the item is shown as a favorite."""
        expect(self.filled_star).to_be_visible()
        return self

    @step("Verify the star is not filled")
    def should_be_unfilled(self):
        """Verify the item is shown as not a favorite."""
        expect(self.unfilled_star).to_be_visible()
        return self
