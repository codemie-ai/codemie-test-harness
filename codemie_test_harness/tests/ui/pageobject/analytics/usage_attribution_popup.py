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

"""Page object for the popups of Analytics > Usage Attribution.

The shared project, repository group and person popups share one layout: a dialog titled by its
subject, a grid of metric tiles and titled sections. The dialog is found by its level-4 header. Locators follow the codemie-ui ``Popup``, ``Tile`` and ``Section``
components (``ModalParts.tsx``): tile labels are paragraphs, section titles are level-5 headings.
"""

import re

from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


class UsageAttributionPopup(BasePage):
    """A details popup that opened from a row of a Usage Attribution table."""

    # The popup reads its details on open; a person's recent sessions come from a live query.
    CONTENT_TIMEOUT = 90_000

    def __init__(self, page, header: str):
        super().__init__(page)
        self.header = header

    # ── Locators ─────────────────────────────────────────────────────────────────

    @property
    def root(self) -> Locator:
        """The popup dialog: the one whose level-4 header is the subject's name."""
        return self.page.get_by_role("dialog").filter(
            has=self.page.get_by_role("heading", name=self.header, exact=True, level=4)
        )

    @property
    def close_button(self) -> Locator:
        """Dialog 'Close' button."""
        return self.root.get_by_role("button", name="Close", exact=True)

    def tile(self, label: str) -> Locator:
        """Metric tile of the popup by its exact label (the label is a paragraph)."""
        return self.root.locator("p").filter(
            has_text=re.compile(rf"^{re.escape(label)}$")
        )

    def section_heading(self, title: str) -> Locator:
        """Heading of a popup section by its exact title."""
        return self.root.get_by_role("heading", name=title, exact=True, level=5)

    # ── Actions ──────────────────────────────────────────────────────────────────

    @step
    def close(self):
        """Close the popup with its 'Close' button."""
        self.close_button.click()
        return self

    # ── Assertions ───────────────────────────────────────────────────────────────

    @step
    def should_be_visible(self):
        """Assert the popup is open, titled by the row it was opened from."""
        expect(self.root, f"Popup '{self.header}' should be open").to_be_visible(
            timeout=self.CONTENT_TIMEOUT
        )
        return self

    @step
    def should_have_tiles(self, labels: tuple[str, ...]):
        """Assert each metric tile is shown, once the popup has loaded its details."""
        for label in labels:
            expect(
                self.tile(label), f"Popup tile '{label}' should be visible"
            ).to_be_visible(timeout=self.CONTENT_TIMEOUT)
        return self

    @step
    def should_have_sections(self, titles: tuple[str, ...]):
        """Assert each titled section is shown."""
        for title in titles:
            expect(
                self.section_heading(title),
                f"Popup section '{title}' should be visible",
            ).to_be_visible(timeout=self.CONTENT_TIMEOUT)
        return self

    @step
    def should_be_closed(self):
        """Assert the popup is closed."""
        expect(self.root).to_be_hidden(timeout=15_000)
        return self
