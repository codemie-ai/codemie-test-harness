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

"""Page object for the Issues panel of the workflow editor and its toolbar button.

The panel lists contract findings of a save, a Check or a restore in severity groups
(Errors, Warnings, Unverified), with an outcome note, the input-contract coverage and a
"Go to Issue" button per card.

Evidence (frontend): IssueGroups.tsx (group headers with ``aria-expanded``, cards
``data-testid="issue-card-<id>"``, ``issues-context-note``, coverage, truncation line,
strict tag), IssuesPanel.tsx (notes, workflow strict line), EditorActions.tsx (Issues
button ``data-severity``), issueSeverity.ts (card border classes).
"""

import re

from playwright.sync_api import Locator, Page, expect
from reportportal_client import step

# The restore dry-run has its own 30 s limit (CHECK_TIMEOUT_MS); its outcome may take that long.
RESULT_TIMEOUT_MS = 35_000

# Card border per severity (issueSeverity.ts borderClass).
CARD_BORDER_CLASS = {
    "Error": "border-border-error/50",
    "Warning": "border-aborted-secondary",
    "Unverified": "border-border-quaternary",
}


class WorkflowIssuesPanel:
    """Issues side panel and the Issues toolbar button of the workflow editor."""

    def __init__(self, page: Page):
        self.page = page

    # ==============================================
    # PROPERTIES - UI ELEMENTS
    # ==============================================

    @property
    def panel(self) -> Locator:
        """The side panel whose header is 'Issues'."""
        return self.page.get_by_role("complementary").filter(
            has=self.page.get_by_role("heading", name="Issues", exact=True)
        )

    @property
    def issues_button(self) -> Locator:
        """Issues toolbar button; the only editor button carrying ``data-severity``."""
        return self.page.locator("button[data-severity]")

    @property
    def cards(self) -> Locator:
        """Every issue card rendered in an expanded group."""
        return self.panel.locator('[data-testid^="issue-card-"]')

    @property
    def context_note(self) -> Locator:
        """Outcome note: 'Saved with warnings', 'Workflow created with warnings', 'Changes not saved yet'."""
        return self.panel.get_by_test_id("issues-context-note")

    @property
    def coverage_line(self) -> Locator:
        """'Input contract coverage: X of Y states' line of the coverage block."""
        return self.panel.get_by_text(
            re.compile(r"^Input contract coverage: \d+ of \d+ states$")
        )

    @property
    def strict_tags(self) -> Locator:
        """'node save validation (strict)' tags on cards."""
        return self.panel.get_by_text("node save validation (strict)", exact=True)

    def group_header(self, label: str) -> Locator:
        """Header button of a severity group, named '<label> (<count>)'."""
        return self.panel.get_by_role(
            "button", name=re.compile(rf"^{re.escape(label)}\s*\(\d+\)$")
        )

    def card(self, text: str) -> Locator:
        """Issue card whose text contains ``text``."""
        return self.cards.filter(has_text=text)

    def panel_text(self, text: str) -> Locator:
        """A line of the panel whose whole text is ``text``."""
        return self.panel.get_by_text(text, exact=True)

    # ==============================================
    # METHODS - ACTIONS
    # ==============================================

    @step
    def open(self):
        """Open the panel from the Issues toolbar button."""
        self.issues_button.click()
        expect(self.panel).to_be_visible()
        return self

    @step
    def toggle_group(self, label: str):
        """Expand or collapse a severity group."""
        self.group_header(label).click()
        return self

    @step
    def click_go_to_issue(self, card_text: str):
        """Click 'Go to Issue' on the card whose text contains ``card_text``."""
        self.card(card_text).get_by_role("button", name="Go to Issue").click()
        return self

    # ==============================================
    # METHODS - VERIFICATION & ASSERTIONS
    # ==============================================

    @step
    def should_be_visible(self, timeout: int = RESULT_TIMEOUT_MS):
        """The Issues panel is open."""
        expect(self.panel).to_be_visible(timeout=timeout)
        return self

    @step
    def should_not_be_visible(self):
        """The Issues panel is not open."""
        expect(self.panel).to_have_count(0)
        return self

    @step
    def should_have_group(self, label: str, count: int, expanded: bool):
        """The severity group '<label> (<count>)' is shown, expanded or collapsed."""
        header = self.panel.get_by_role(
            "button", name=re.compile(rf"^{re.escape(label)}\s*\({count}\)$")
        )
        expect(header).to_be_visible(timeout=RESULT_TIMEOUT_MS)
        expect(header).to_have_attribute(
            "aria-expanded", "true" if expanded else "false"
        )
        return self

    @step
    def should_not_have_group(self, label: str):
        """No severity group with this label is shown."""
        expect(self.group_header(label)).to_have_count(0)
        return self

    @step
    def should_have_cards_with_test_ids(self):
        """Every rendered card carries ``data-testid="issue-card-<id>"`` with a non-empty id."""
        expect(self.cards.first).to_be_visible()
        expect(self.cards.first).to_have_attribute(
            "data-testid", re.compile(r"^issue-card-.+")
        )
        return self

    @step
    def should_have_card(self, text: str, badge: str):
        """A card containing ``text`` shows the severity badge and its severity border."""
        card = self.card(text).first
        expect(card).to_be_visible(timeout=RESULT_TIMEOUT_MS)
        expect(card.get_by_role("status", name=badge)).to_be_visible()
        expect(card).to_have_class(re.compile(re.escape(CARD_BORDER_CLASS[badge])))
        expect(card.get_by_role("button", name="Go to Issue")).to_be_visible()
        return self

    @step
    def should_have_resolved_card(self, text: str):
        """The card containing ``text`` shows the 'Resolved' badge instead of its severity."""
        card = self.card(text).first
        expect(card).to_be_visible()
        expect(card.get_by_text("Resolved", exact=True)).to_be_visible()
        return self

    @step
    def should_have_context_note(self, note: str):
        """The outcome note shows ``note``."""
        expect(self.context_note).to_have_text(note, timeout=RESULT_TIMEOUT_MS)
        return self

    @step
    def should_not_have_context_note(self):
        """No outcome note is shown (a rejected save has none)."""
        expect(self.context_note).to_have_count(0)
        return self

    @step
    def should_show_coverage(self):
        """The coverage block shows 'Input contract coverage: X of Y states'."""
        expect(self.coverage_line).to_be_visible()
        return self

    @step
    def should_show_line(self, text: str):
        """The panel shows a line whose whole text is ``text``."""
        expect(self.panel_text(text)).to_be_visible(timeout=RESULT_TIMEOUT_MS)
        return self

    @step
    def should_have_line_visibility(self, text: str, visible: bool):
        """The line ``text`` is shown (visible=True) or absent (visible=False)."""
        expect(self.panel_text(text)).to_have_count(1 if visible else 0)
        return self

    @step
    def should_have_strict_tag_visibility(self, visible: bool):
        """A card shows the state-level strict tag (visible=True), or no card does."""
        if visible:
            expect(self.strict_tags.first).to_be_visible()
        else:
            expect(self.strict_tags).to_have_count(0)
        return self

    @step
    def should_have_issues_button(self, severity: str, count: int):
        """The Issues button shows ``severity`` colour and the unresolved ``count``."""
        expect(self.issues_button).to_have_attribute(
            "data-severity", severity, timeout=RESULT_TIMEOUT_MS
        )
        expect(self.issues_button).to_have_text(
            re.compile(rf"^\s*Issues\s*{count}\s*$")
        )
        return self

    @step
    def should_not_have_issues_button(self):
        """No Issues button: the editor holds no findings."""
        expect(self.issues_button).to_have_count(0)
        return self
