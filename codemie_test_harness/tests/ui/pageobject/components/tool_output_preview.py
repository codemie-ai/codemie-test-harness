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
Plain-text tool output in a chat tool card (TextBlock.tsx, collapsible mode).

A result of 60 or more non-empty lines is shown as its first 20 and last 20 lines
with a "Show N hidden lines" button between them (N = total - 40). The button
expands the block to every line, with a "Collapse" button and a
"Full tool output · N lines" header; "Collapse" returns to the preview.
A shorter result is shown in full with no button.

Every output line in the tests is the text ``line <n>``; each rendered line is its
own element, so the visible lines are read as one ordered list.
"""

import re

from playwright.sync_api import expect, Locator
from reportportal_client import step

from codemie_test_harness.tests.ui.test_data.tool_output_preview_test_data import (
    MINIMUM_PREVIEW_LINES,
    PREVIEW_EDGE_LINES,
)

_HIDDEN_LINES_BUTTON_NAME = re.compile(r"^Show \d+ hidden lines$")


def _line_texts(first: int, last: int) -> list:
    return [f"line {number}" for number in range(first, last + 1)]


class ToolOutputPreview:
    """Component for the plain-text output of one tool call in the chat history."""

    def __init__(self, page, scope: Locator):
        """
        Args:
            page: Playwright page object
            scope: Locator of the chat history the tool output is rendered in
        """
        self.page = page
        self.scope = scope

    # Elements

    @property
    def lines(self) -> Locator:
        """Rendered output lines (each is its own element whose whole text is ``line <n>``)."""
        return self.scope.get_by_text(re.compile(r"^line \d+$"))

    @property
    def hidden_lines_button(self) -> Locator:
        """Any 'Show N hidden lines' button (collapsed preview)."""
        return self.scope.get_by_role("button", name=_HIDDEN_LINES_BUTTON_NAME)

    @property
    def collapse_button(self) -> Locator:
        """'Collapse' button (aria-label) shown above the fully expanded output."""
        return self.scope.get_by_role("button", name="Collapse", exact=True)

    def full_output_header(self, total_lines: int) -> Locator:
        """Header 'Full tool output · N lines' shown next to the Collapse button."""
        return self.scope.get_by_text(f"Full tool output · {total_lines} lines")

    # Actions

    @step
    def expand(self, total_lines: int):
        """Click 'Show N hidden lines' (N = total_lines - 40)."""
        hidden = total_lines - 2 * PREVIEW_EDGE_LINES
        self.scope.get_by_role(
            "button", name=f"Show {hidden} hidden lines", exact=True
        ).click()
        return self

    @step
    def collapse(self):
        """Click 'Collapse'."""
        self.collapse_button.click()
        return self

    # Verifications

    @step
    def should_show_preview(self, total_lines: int):
        """Only the first 20 and last 20 lines are rendered, with a collapsed
        'Show N hidden lines' button; the lines in between are not in the DOM."""
        first_edge = _line_texts(1, PREVIEW_EDGE_LINES)
        last_edge = _line_texts(total_lines - PREVIEW_EDGE_LINES + 1, total_lines)
        expect(self.lines).to_have_text(first_edge + last_edge)
        hidden = total_lines - 2 * PREVIEW_EDGE_LINES
        button = self.scope.get_by_role(
            "button", name=f"Show {hidden} hidden lines", exact=True
        )
        expect(button).to_have_count(1)
        expect(button).to_have_attribute("aria-expanded", "false")
        expect(self.collapse_button).to_have_count(0)
        return self

    @step
    def should_show_all_lines_expanded(self, total_lines: int):
        """Every line is rendered, with the 'Collapse' button (aria-expanded=true), the
        'Full tool output · N lines' header and no hidden-lines button."""
        expect(self.lines).to_have_text(_line_texts(1, total_lines))
        expect(self.collapse_button).to_have_count(1)
        expect(self.collapse_button).to_have_attribute("aria-expanded", "true")
        expect(self.full_output_header(total_lines)).to_be_visible()
        expect(self.hidden_lines_button).to_have_count(0)
        return self

    @step
    def should_show_all_lines_without_toggle(self, total_lines: int):
        """A result below the 60-line threshold: every line is rendered and there is
        neither a hidden-lines button nor a Collapse button."""
        assert total_lines < MINIMUM_PREVIEW_LINES
        expect(self.lines).to_have_text(_line_texts(1, total_lines))
        expect(self.hidden_lines_button).to_have_count(0)
        expect(self.collapse_button).to_have_count(0)
        return self
