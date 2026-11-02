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

"""Expanded YAML configuration dialog shared by the workflow editor and execution details."""

import re
from dataclasses import dataclass
from pathlib import Path

from hamcrest import assert_that, equal_to
from playwright.sync_api import Download, Locator, Page, expect
from reportportal_client import step

EXPANDED_EDITOR_NAME = "yaml_config_expanded"

# Delay between keystrokes. The editor is a controlled component: every change is pushed
# to the parent and the parent's value is written back into Ace after a re-render, so
# keys sent faster than a re-render are overwritten by that write-back.
TYPING_DELAY_MS = 100


@dataclass(frozen=True)
class ExpandedYamlSize:
    """Layout size of the expanded dialog and of its ``.expanded-yaml-frame`` container."""

    dialog_width: int
    dialog_height: int
    frame_width: int
    frame_height: int


class ExpandedYamlDialog:
    """Expanded YAML dialog: shell (label + Collapse) around a frame (header + Ace editor)."""

    def __init__(self, page: Page):
        self.page = page

    # ====================
    # PROPERTIES
    # ====================

    @property
    def dialog(self) -> Locator:
        """Dialog that contains the expanded YAML frame."""
        return self.page.get_by_role("dialog").filter(
            has=self.page.locator(".expanded-yaml-frame")
        )

    @property
    def label(self) -> Locator:
        """Dialog label shown on the left of the dialog header."""
        return self.dialog.get_by_text("YAML Configuration", exact=True)

    @property
    def collapse_button(self) -> Locator:
        """'Collapse' button on the right of the dialog header."""
        return self.dialog.get_by_role("button", name="Collapse")

    @property
    def frame(self) -> Locator:
        """Frame root with the 'expanded-yaml-frame' class."""
        return self.dialog.locator(".expanded-yaml-frame")

    @property
    def frame_header(self) -> Locator:
        """Frame header with the 'code-block-header' class."""
        return self.frame.locator(".code-block-header")

    @property
    def frame_title(self) -> Locator:
        """Title text on the left of the frame header."""
        return self.frame_header.locator("p")

    @property
    def frame_body(self) -> Locator:
        """Editor container of the frame (the closest block that wraps the editor)."""
        return (
            self.frame.locator("div")
            .filter(has=self.page.locator(f'[data-name="{EXPANDED_EDITOR_NAME}"]'))
            .last
        )

    @property
    def editor(self) -> Locator:
        """Ace editor of the expanded dialog."""
        return self.dialog.locator(f'[data-name="{EXPANDED_EDITOR_NAME}"]')

    @property
    def text_layer(self) -> Locator:
        """Rendered (visible) lines of the Ace editor."""
        return self.editor.locator(".ace_text-layer")

    @property
    def text_input(self) -> Locator:
        """Hidden textarea of the Ace editor that receives the keystrokes."""
        return self.editor.locator(".ace_text-input")

    @property
    def key_tokens(self) -> Locator:
        """Ace tokens that highlight YAML keys."""
        return self.text_layer.locator(".ace_meta.ace_tag")

    @property
    def string_tokens(self) -> Locator:
        """Ace tokens that highlight YAML strings."""
        return self.text_layer.locator(".ace_string")

    @property
    def horizontal_scrollbar(self) -> Locator:
        """Horizontal scrollbar of the Ace editor (hidden when nothing overflows)."""
        return self.editor.locator(".ace_scrollbar-h")

    @property
    def copy_button(self) -> Locator:
        """'Copy' button in the frame header."""
        return self.frame_header.get_by_role("button", name="Copy")

    @property
    def download_button(self) -> Locator:
        """'Download' button in the frame header."""
        return self.frame_header.get_by_role("button", name="Download")

    @property
    def yaml_error(self) -> Locator:
        """'YAML Error: <message>' text above the frame."""
        return self.dialog.get_by_text(re.compile(r"^YAML Error:"))

    def toast(self, text: str) -> Locator:
        """Toast notification with the given header text."""
        return self.page.locator(".codemie-toast-header").filter(has_text=text)

    # ====================
    # ACTIONS
    # ====================

    @step
    def collapse(self):
        """Press 'Collapse' to close the dialog."""
        self.collapse_button.click()

    @step
    def append_line(self, text: str):
        """Type a new line with ``text`` at the end of the document, key by key."""
        self._place_cursor("el => el.env.editor.navigateFileEnd()")
        self.text_input.press("Enter")
        self.text_input.press_sequentially(text, delay=TYPING_DELAY_MS)

    @step
    def append_to_line_containing(self, marker: str, text: str):
        """Type ``text`` at the end of the first line that contains ``marker``, key by key."""
        self._place_cursor(
            """(el, marker) => {
                const lines = el.env.editor.getValue().split("\\n");
                const row = lines.findIndex((line) => line.includes(marker));
                el.env.editor.gotoLine(row + 1, lines[row].length);
            }""",
            marker,
        )
        self.text_input.press_sequentially(text, delay=TYPING_DELAY_MS)

    @step
    def type_into_editor(self, text: str):
        """Click into the editor and type ``text`` at the end of the document."""
        self._place_cursor("el => el.env.editor.navigateFileEnd()")
        self.text_input.press_sequentially(text, delay=TYPING_DELAY_MS)

    @step
    def scroll_to_end(self) -> str:
        """Go to the last row of the document, which scrolls the editor viewport there.

        ``navigateFileEnd()`` only moves the cursor; Ace scrolls as a side effect of its
        keyboard commands, not of that call. ``gotoLine`` moves the cursor and scrolls
        the row into view.

        Returns:
            The last non-empty line of the document.
        """
        self.editor.evaluate(
            "el => el.env.editor.gotoLine(el.env.editor.getSession().getLength(), 0, false)"
        )
        return self.get_content().rstrip().split("\n")[-1].strip()

    @step
    def click_copy(self):
        """Press 'Copy' in the frame header."""
        self.copy_button.click()

    @step
    def click_download(self) -> Download:
        """Press 'Download' in the frame header and return the browser download."""
        with self.page.expect_download() as download_info:
            self.download_button.click()
        return download_info.value

    @step
    def get_content(self) -> str:
        """Full text of the expanded editor, read through the Ace API."""
        expect(self.editor).to_be_visible()
        return self.editor.evaluate("el => el.env.editor.getValue()")

    @step
    def get_size(self) -> ExpandedYamlSize:
        """Layout size of the dialog and the frame once the open transition has finished."""
        self._wait_for_open_transition()
        dialog_size = self.dialog.evaluate(
            "el => ({width: el.offsetWidth, height: el.offsetHeight})"
        )
        frame_size = self.frame.evaluate(
            "el => ({width: el.offsetWidth, height: el.offsetHeight})"
        )
        return ExpandedYamlSize(
            dialog_width=dialog_size["width"],
            dialog_height=dialog_size["height"],
            frame_width=frame_size["width"],
            frame_height=frame_size["height"],
        )

    def _wait_for_open_transition(self):
        """Wait until the dialog's open transition has finished and the layout is stable."""
        expect(self.frame).to_be_visible()
        self.dialog.evaluate(
            "el => Promise.all(el.getAnimations().map((animation) => animation.finished))"
        )

    def _place_cursor(self, script: str, arg=None):
        """Focus the Ace input with a real click, then run ``script`` (Ace API) to place the cursor.

        The dialog moves focus to its first control when it opens, so the editor is
        clicked only after the open transition, and the keystrokes are sent to the
        Ace input only once it is confirmed focused.
        """
        expect(self.editor).to_be_visible()
        self._wait_for_open_transition()
        self.editor.click()
        expect(self.text_input).to_be_focused()
        self.editor.evaluate(script, arg)

    def _read_clipboard(self) -> str:
        return self.page.evaluate("() => navigator.clipboard.readText()")

    # ====================
    # VERIFICATIONS
    # ====================

    @step
    def should_be_visible(self):
        """Verify that the expanded dialog is open."""
        expect(self.dialog).to_be_visible()
        return self

    @step
    def should_be_hidden(self):
        """Verify that the expanded dialog is closed."""
        expect(self.dialog).to_be_hidden()

    @step
    def should_have_shell(self):
        """Verify the dialog label and the 'Collapse' button."""
        expect(self.label).to_be_visible()
        expect(self.collapse_button).to_be_visible()

    @step
    def should_have_frame(self, title: str):
        """Verify the frame, its header with ``title``, and the Ace editor."""
        expect(self.frame).to_be_visible()
        expect(self.frame_header).to_be_visible()
        expect(self.frame_title).to_have_text(title)
        expect(self.editor).to_be_visible()

    @step
    def should_have_copy_and_download(self, expected: bool):
        """Verify that 'Copy' and 'Download' are in the frame header, or that neither is."""
        expected_count = 1 if expected else 0
        expect(self.copy_button).to_have_count(expected_count)
        expect(self.download_button).to_have_count(expected_count)

    @step
    def should_be_readonly(self, readonly: bool):
        """Verify the editor read-only state; invisible characters are shown only when editable."""
        self.page.wait_for_function(
            """([name, readonly]) => {
                const el = document.querySelector(`[data-name="${name}"]`);
                return !!(el && el.env && el.env.editor && el.env.editor.getReadOnly() === readonly);
            }""",
            arg=[EXPANDED_EDITOR_NAME, readonly],
        )
        if readonly:
            expect(self.editor).not_to_have_class(re.compile(r"ace-show-tabs"))
        else:
            expect(self.editor).to_have_class(re.compile(r"ace-show-tabs"))

    @step
    def should_have_content(self, expected: str):
        """Verify the full editor text equals ``expected`` (surrounding whitespace ignored)."""
        assert_that(
            self.get_content().strip(),
            equal_to(expected.strip()),
            "Expanded editor content differs from the expected YAML",
        )

    @step
    def should_have_size(self, expected: ExpandedYamlSize):
        """Verify the dialog and the frame have exactly the ``expected`` width and height."""
        assert_that(
            self.get_size(),
            equal_to(expected),
            "Expanded dialog/frame size differs from the reference context",
        )

    @step
    def should_show_yaml_error(self):
        """Verify 'YAML Error: <message>' with a non-empty message is shown above the frame."""
        expect(self.yaml_error).to_be_visible()
        expect(self.yaml_error).to_have_text(re.compile(r"^YAML Error: \S+"))

    @step
    def should_not_show_yaml_error(self):
        """Verify no YAML error text is shown."""
        expect(self.yaml_error).to_have_count(0)

    @step
    def should_have_failed_border(self, failed: bool):
        """Verify the frame header and body carry the failed border, or neither does."""
        failed_border = re.compile(r"border-failed-secondary")
        if failed:
            expect(self.frame_header).to_have_class(failed_border)
            expect(self.frame_body).to_have_class(failed_border)
        else:
            expect(self.frame_header).not_to_have_class(failed_border)
            expect(self.frame_body).not_to_have_class(failed_border)

    @step
    def should_have_syntax_highlighting(self):
        """Verify Ace token classes are rendered for keys and strings."""
        expect(self.key_tokens.first).to_be_visible()
        expect(self.string_tokens.first).to_be_visible()

    @step
    def should_have_content_containing(self, text: str):
        """Verify the editor document (read through the Ace API) contains ``text``."""
        self.page.wait_for_function(
            """([name, text]) => {
                const el = document.querySelector(`[data-name="${name}"]`);
                return !!(el && el.env && el.env.editor && el.env.editor.getValue().includes(text));
            }""",
            arg=[EXPANDED_EDITOR_NAME, text],
        )

    @step
    def should_show_text(self, text: str):
        """Verify ``text`` is rendered in the editor viewport.

        ``text`` must not contain spaces: an editable Ace editor renders each space as
        an invisible-character marker, so the rendered text never holds a plain space.
        """
        expect(self.text_layer).to_contain_text(text)

    @step
    def should_show_last_line(self, last_line: str):
        """Verify the viewport reached the last line of the document and renders it."""
        self.page.wait_for_function(
            """(name) => {
                const el = document.querySelector(`[data-name="${name}"]`);
                if (!el || !el.env || !el.env.editor) return false;
                const editor = el.env.editor;
                const lastRow = editor.getValue().replace(/\\s+$/, "").split("\\n").length - 1;
                return editor.renderer.getLastVisibleRow() >= lastRow;
            }""",
            arg=EXPANDED_EDITOR_NAME,
        )
        self.should_show_text(last_line.split()[-1])

    @step
    def should_wrap_long_lines(self):
        """Verify wrap mode splits long lines into several rows and nothing overflows horizontally."""
        self.page.wait_for_function(
            """(name) => {
                const el = document.querySelector(`[data-name="${name}"]`);
                if (!el || !el.env || !el.env.editor) return false;
                const session = el.env.editor.getSession();
                return session.getUseWrapMode() && session.getScreenLength() > session.getLength();
            }""",
            arg=EXPANDED_EDITOR_NAME,
        )
        expect(self.horizontal_scrollbar).to_be_hidden()

    @step
    def should_show_copied_toast(self):
        """Verify the 'Copied to clipboard' toast."""
        expect(self.toast("Copied to clipboard")).to_be_visible()

    @step
    def should_have_copied_to_clipboard(self, expected: str):
        """Verify the clipboard holds ``expected`` (surrounding whitespace ignored)."""
        assert_that(
            self._read_clipboard().strip(),
            equal_to(expected.strip()),
            "Clipboard content differs from the YAML configuration",
        )

    @step
    def should_show_download_toast(self, download: Download):
        """Verify the 'Code downloaded as <fileName>' toast for the given download."""
        expect(
            self.toast(f"Code downloaded as {download.suggested_filename}")
        ).to_be_visible()

    @step
    def should_have_downloaded_content(self, download: Download, expected: str):
        """Verify the downloaded file holds ``expected`` (surrounding whitespace ignored)."""
        downloaded = Path(download.path()).read_text(encoding="utf-8")
        assert_that(
            downloaded.strip(),
            equal_to(expected.strip()),
            "Downloaded file content differs from the YAML configuration",
        )
