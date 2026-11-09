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
Agent workspace browser popup (chat header "Browse files" button).

File list on the left, file preview on the right with Expand and Download controls.
The preview renders Markdown (with a front matter block), pretty-printed JSON and
plain text as a code block, and a hint when a file has no preview.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from hamcrest import assert_that, equal_to, none
from playwright.sync_api import Locator, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.test_data.agent_workspace_preview_test_data import (
    COLLAPSE_LABEL,
    DOWNLOAD_BUTTON_LABEL,
    EXPAND_LABEL,
    NO_PREVIEW_HINT_PATTERN,
    PreviewKind,
    WorkspaceFile,
)

POPUP_TITLE = "Agent workspace"
# The PrimeReact dialog that holds the workspace file panel (no testid on the dialog itself).
POPUP_SELECTOR = '.p-dialog:has([data-testid="workspace-file-panel"])'
GUIDED_TOUR_TIMEOUT_MS = 5000


@dataclass
class WorkspaceDownload:
    """A file downloaded through the popup: where it was saved and its suggested name."""

    path: Path
    filename: str


def _exact_text(text: str) -> re.Pattern:
    """Pattern matching ``text`` exactly (an optional trailing line break aside).

    A regular expression is used because ``to_have_text`` with a string collapses
    whitespace, which would hide a wrong indent in pretty-printed JSON.
    """
    body = r"\n".join(re.escape(line) for line in text.split("\n"))
    return re.compile(f"^{body}\\n?$")


class AgentWorkspaceBrowser(BasePage):
    """Agent workspace browser popup of the chat page."""

    # ==================== LOCATORS ====================

    @property
    def guided_tour_dismiss_button(self) -> Locator:
        """ "Maybe Later" button of the first-visit "Guided Tour Available" dialog."""
        return self.page.get_by_role("button", name="Maybe Later")

    @property
    def browse_files_button(self) -> Locator:
        """Chat header button that opens the popup."""
        return self.page.get_by_role("button", name="Browse files")

    @property
    def popup(self) -> Locator:
        """Popup root."""
        return self.page.locator(POPUP_SELECTOR)

    @property
    def file_panel(self) -> Locator:
        """Left column with the file list."""
        return self.page.locator('[data-testid="workspace-file-panel"]')

    @property
    def file_list(self) -> Locator:
        return self.page.locator('[data-testid="workspace-file-list"]')

    def file_row(self, path: str) -> Locator:
        """File list button whose text is exactly ``path``."""
        return self.file_list.locator("button").filter(
            has_text=re.compile(rf"^\s*{re.escape(path)}\s*$")
        )

    @property
    def preview(self) -> Locator:
        """Container wrapping every kind of preview."""
        return self.page.locator('[data-testid="workspace-preview"]')

    @property
    def preview_text(self) -> Locator:
        """Code block of a text or JSON preview."""
        return self.preview.locator("pre")

    @property
    def markdown(self) -> Locator:
        return self.page.locator('[data-testid="workspace-preview-markdown"]')

    @property
    def front_matter(self) -> Locator:
        return self.page.locator('[data-testid="workspace-preview-frontmatter"]')

    @property
    def no_preview_hint(self) -> Locator:
        """Hint shown for files that have no preview (no testid, located by text)."""
        return self.popup.get_by_text(re.compile(NO_PREVIEW_HINT_PATTERN, re.I | re.S))

    @property
    def markdown_expand_button(self) -> Locator:
        """Expand control of a Markdown preview (the only preview kind with a testid on it)."""
        return self.page.locator('[data-testid="workspace-preview-expand"]')

    @property
    def text_expand_button(self) -> Locator:
        """Expand control of a text preview: the "Expand" button of the code block header
        (next to "Copy"), scoped to the workspace popup."""
        return self.popup.get_by_role("button", name=EXPAND_LABEL, exact=True)

    def expand_control(self, file: WorkspaceFile) -> Locator:
        """Expand control that belongs to the preview kind of ``file``."""
        if file.kind is PreviewKind.MARKDOWN:
            return self.markdown_expand_button
        return self.text_expand_button

    @property
    def expanded_dialog(self) -> Locator:
        """Full-screen dialog opened by Expand: the dialog that has a "Collapse" button.

        Located by role and name only; ``.last`` picks the expanded dialog should it be
        rendered inside the workspace popup.
        """
        return (
            self.page.get_by_role("dialog")
            .filter(
                has=self.page.get_by_role("button", name=COLLAPSE_LABEL, exact=True)
            )
            .last
        )

    @property
    def collapse_button(self) -> Locator:
        return self.expanded_dialog.get_by_role(
            "button", name=COLLAPSE_LABEL, exact=True
        )

    @property
    def download_button(self) -> Locator:
        return self.popup.locator(f'button[aria-label="{DOWNLOAD_BUTTON_LABEL}"]')

    @property
    def alerts(self) -> Locator:
        return self.popup.get_by_role("alert")

    # ==================== ACTIONS ====================

    @step
    def dismiss_guided_tour(self):
        """Dismiss the first-visit guided tour dialog when it shows up; its mask blocks all clicks."""
        try:
            self.guided_tour_dismiss_button.wait_for(
                state="visible", timeout=GUIDED_TOUR_TIMEOUT_MS
            )
        except PlaywrightTimeoutError:
            return self
        self.guided_tour_dismiss_button.click()
        expect(self.guided_tour_dismiss_button).to_be_hidden()
        return self

    @step
    def open(self):
        """Open the popup from the chat header."""
        expect(self.browse_files_button).to_be_visible(timeout=30000)
        self.browse_files_button.click()
        return self.should_be_open()

    @step
    def select_file(self, path: str):
        """Select a file in the list."""
        self.file_row(path).click()
        return self

    @step
    def expand_preview(self, file: WorkspaceFile):
        """Click Expand in the popup (opens the expanded dialog above it)."""
        self.expand_control(file).click()
        return self

    @step
    def collapse_preview(self):
        """Click Collapse in the expanded dialog."""
        self.collapse_button.click()
        return self

    @step
    def download_selected_file(self, target_dir: Path) -> WorkspaceDownload:
        """Click Download and save the resulting file into ``target_dir``."""
        with self.page.expect_download() as download_info:
            self.download_button.click()
        download = download_info.value
        path = target_dir / download.suggested_filename
        download.save_as(path)
        return WorkspaceDownload(path=path, filename=download.suggested_filename)

    # ==================== ASSERTIONS ====================

    @step
    def should_be_open(self):
        expect(self.popup).to_be_visible()
        expect(self.popup.get_by_text(POPUP_TITLE, exact=True)).to_be_visible()
        return self

    @step
    def should_show_formatted_markdown(
        self, heading, list_items, table_cell, code_line, source_markers
    ):
        """Heading, list, table and code block are rendered elements, not Markdown source."""
        expect(self.markdown).to_be_visible()
        expect(self.markdown.get_by_role("heading", name=heading)).to_be_visible()
        for item in list_items:
            expect(
                self.markdown.get_by_role("listitem").filter(has_text=item)
            ).to_be_visible()
        expect(self.markdown.get_by_role("table")).to_be_visible()
        expect(self.markdown.get_by_role("cell", name=table_cell)).to_be_visible()
        expect(self.markdown.locator("pre").filter(has_text=code_line)).to_be_visible()
        for marker in source_markers:
            expect(self.markdown).not_to_contain_text(marker)
        return self

    @step
    def should_show_front_matter(self, block_text: str):
        """Front matter block is present with exactly ``block_text`` (empty block included)."""
        expect(self.front_matter).to_be_attached()
        expect(self.front_matter).to_have_text(_exact_text(block_text))
        return self

    @step
    def should_show_front_matter_above_body(self):
        """The front matter block precedes the Markdown body in the document."""
        is_before = self.page.evaluate(
            """() => {
                const fm = document.querySelector('[data-testid="workspace-preview-frontmatter"]');
                const md = document.querySelector('[data-testid="workspace-preview-markdown"]');
                return !!fm && !!md
                    && !!(fm.compareDocumentPosition(md) & Node.DOCUMENT_POSITION_FOLLOWING);
            }"""
        )
        assert_that(
            is_before, equal_to(True), "front matter block is above the Markdown body"
        )
        return self

    @step
    def should_have_only_body_heading(self, heading: str):
        """Body holds the one real heading and no rule/heading made from the delimiters."""
        expect(self.markdown.get_by_role("heading")).to_have_text([heading])
        expect(self.markdown.locator("hr")).to_have_count(0)
        return self

    @step
    def should_show_text(self, text: str):
        """Code block shows ``text`` exactly, indentation included."""
        expect(self.preview_text).to_have_text(_exact_text(text))
        return self

    @step
    def should_not_show_error(self):
        expect(self.alerts).to_have_count(0)
        expect(self.preview).not_to_contain_text(re.compile("error|failed", re.I))
        return self

    @step
    def should_show_no_preview_hint(self):
        """Hint is shown and no Markdown or code-block preview is rendered."""
        expect(self.no_preview_hint).to_be_visible()
        expect(self.markdown).to_have_count(0)
        expect(self.preview_text).to_have_count(0)
        return self

    @step
    def should_show_file_preview(self, file: WorkspaceFile):
        """The selected file is previewed according to its kind."""
        if file.kind is PreviewKind.MARKDOWN:
            expect(
                self.markdown.get_by_role("heading", name=file.heading)
            ).to_be_visible()
        else:
            self.should_show_text(file.shown_text)
        return self

    @step
    def should_offer_expand(self, file: WorkspaceFile):
        """Popup shows the file list panel and the "Expand" control of the preview."""
        expect(self.file_panel).to_be_visible()
        expect(self.expand_control(file)).to_be_visible()
        expect(self.expand_control(file)).to_have_text(EXPAND_LABEL)
        return self

    @step
    def should_show_expanded_view(self, file: WorkspaceFile):
        """Expanded dialog is open: file name as title, the file content and a "Collapse"
        button. Everything is located by role, name or text inside the dialog."""
        dialog = self.expanded_dialog
        expect(dialog).to_be_visible()
        expect(self.collapse_button).to_be_visible()
        expect(dialog.get_by_text(file.path, exact=True).first).to_be_visible()
        if file.kind is PreviewKind.MARKDOWN:
            expect(dialog.get_by_role("heading", name=file.heading)).to_be_visible()
        else:
            for line in file.content.split("\n"):
                expect(dialog).to_contain_text(line)
        return self

    @step
    def should_have_no_expanded_view(self):
        expect(self.expanded_dialog).to_have_count(0)
        return self

    @step
    def should_be_back_to_popup(self, file: WorkspaceFile):
        """Expanded dialog is gone; the popup is open with its file list panel, the file
        still previewed and the Expand control shown."""
        self.should_have_no_expanded_view()
        self.should_be_open()
        self.should_offer_expand(file)
        return self.should_show_file_preview(file)

    @step
    def should_deliver_file(
        self, download: WorkspaceDownload, filename: str, content: str
    ):
        assert_that(download.filename, equal_to(filename), "downloaded file name")
        assert_that(
            download.path.read_text(encoding="utf-8"),
            equal_to(content),
            "downloaded file content",
        )
        return self

    @step
    def should_not_have_run_script(self, flag: str):
        """The payload did not run: its page flag is unset (checked after the UI has settled)."""
        self.page.evaluate(
            "() => new Promise(resolve => requestAnimationFrame("
            "() => requestAnimationFrame(resolve)))"
        )
        assert_that(
            self.page.evaluate(f"() => window['{flag}']"),
            none(),
            f"page flag {flag} set by the payload",
        )
        return self

    @step
    def should_show_payload_inertly(self, file: WorkspaceFile, flag: str):
        """Markdown payload renders no script element, an HTML file shows its literal source;
        either way the payload never ran."""
        if file.kind is PreviewKind.MARKDOWN:
            expect(
                self.markdown.get_by_role("heading", name=file.heading)
            ).to_be_visible()
            expect(self.markdown.locator("script")).to_have_count(0)
        else:
            self.should_show_text(file.content)
        return self.should_not_have_run_script(flag)
