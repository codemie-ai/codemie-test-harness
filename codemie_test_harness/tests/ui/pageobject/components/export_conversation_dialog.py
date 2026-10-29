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
Export Conversation dialog (chat header "Export Conversation" button).

Format radio group (JSON / DOCX / PDF), "Include tool outputs" checkbox and
Cancel / Export buttons. Also provides download, request-capture and
request-holding helpers so tests never touch raw Playwright APIs.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from hamcrest import (
    assert_that,
    contains_string,
    empty,
    ends_with,
    equal_to,
    has_item,
    is_,
    not_,
)
from playwright.sync_api import Locator, Request, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.test_data.export_conversation_test_data import (
    DIALOG_TITLE,
    FORMAT_HEADING,
    INCLUDE_TOOL_OUTPUTS_LABEL,
    DismissMode,
    ExportFormat,
)

EXPORT_URL_PATTERN = re.compile(r"/v1/conversations/[^/]+/export\?")


@dataclass
class ExportedFile:
    """A file downloaded through the dialog: where it was saved and its suggested name."""

    path: Path
    filename: str


class ExportConversationDialog(BasePage):
    """Export Conversation dialog component."""

    def __init__(self, page):
        super().__init__(page)
        self._held_routes = []
        self._export_requests = []
        self._downloads = []

    # ==================== LOCATORS ====================

    @property
    def dialog(self) -> Locator:
        return self.page.get_by_role("dialog", name=DIALOG_TITLE)

    @property
    def format_heading(self) -> Locator:
        return self.dialog.get_by_role("heading", name=FORMAT_HEADING)

    def format_radio(self, export_format: ExportFormat) -> Locator:
        return self.dialog.get_by_role("radio", name=export_format.label)

    def format_label(self, export_format: ExportFormat) -> Locator:
        # The radio input sits under an overlay, so selection goes through its visible label.
        return self.dialog.get_by_text(export_format.label, exact=True)

    def format_description(self, export_format: ExportFormat) -> Locator:
        return self.dialog.get_by_text(export_format.description, exact=True)

    @property
    def include_tool_outputs_checkbox(self) -> Locator:
        return self.dialog.get_by_role("checkbox", name=INCLUDE_TOOL_OUTPUTS_LABEL)

    @property
    def include_tool_outputs_label(self) -> Locator:
        return self.dialog.get_by_text(INCLUDE_TOOL_OUTPUTS_LABEL, exact=True)

    @property
    def tool_outputs_hint(self) -> Locator:
        return self.dialog.get_by_role("status").filter(has_text="always included")

    @property
    def more_information_button(self) -> Locator:
        return self.dialog.get_by_role("button", name="More information")

    @property
    def export_button(self) -> Locator:
        return self.dialog.get_by_role("button", name="Export", exact=True)

    @property
    def export_button_loading_indicator(self) -> Locator:
        return self.export_button.locator(".animate-shimmer")

    @property
    def overlay(self) -> Locator:
        """Backdrop (PrimeReact dialog mask) that wraps the dialog."""
        return self.page.locator('[data-pc-section="mask"]').filter(has=self.dialog)

    @property
    def cancel_button(self) -> Locator:
        return self.dialog.get_by_role("button", name="Cancel")

    @property
    def any_menu(self) -> Locator:
        return self.page.get_by_role("menu")

    def success_toast(self, text: str) -> Locator:
        return self.page.locator(".codemie-toast-header").filter(has_text=text)

    # ==================== ACTIONS ====================

    @step
    def select_format(self, export_format: ExportFormat):
        """Select an export format by clicking its label."""
        self.format_label(export_format).click()
        return self

    @step
    def choose_include_tool_outputs(self, include: bool):
        """Tick "Include tool outputs" when requested; leave the default state otherwise."""
        if include:
            self.include_tool_outputs_label.click()
        return self

    @step
    def dismiss(self, mode: DismissMode):
        """Dismiss the dialog without exporting."""
        if mode is DismissMode.CANCEL_BUTTON:
            self.cancel_button.click()
        elif mode is DismissMode.OVERLAY_CLICK:
            self.click_overlay()
        else:
            self.page.keyboard.press("Escape")
        return self

    @step
    def press_escape(self):
        self.page.keyboard.press("Escape")
        return self

    @step
    def click_overlay(self):
        """Click the backdrop in its top-left corner, outside the dialog."""
        self.overlay.click(position={"x": 5, "y": 5})
        return self

    @step
    def click_export(self):
        self.export_button.click()
        return self

    @step
    def click_export_while_loading(self):
        """Click Export even though it is disabled (forced, to prove no second request is sent)."""
        self.export_button.click(force=True)
        return self

    @step
    def export_and_download(self, target_dir: Path) -> ExportedFile:
        """Click Export and save the downloaded file into target_dir."""
        with self.page.expect_download() as download_info:
            self.export_button.click()
        return self._save(download_info.value, target_dir)

    @step
    def export_and_capture_request(self) -> Request:
        """Click Export and return the export request the UI sent."""
        with self.page.expect_request(EXPORT_URL_PATTERN) as request_info:
            self.export_button.click()
        return request_info.value

    @step
    def hold_export_requests(self):
        """Hold every export request until release_export_requests_and_download()."""
        self._held_routes.clear()
        self._track_export_requests()
        self.page.route(EXPORT_URL_PATTERN, self._hold)
        return self

    @step
    def release_export_requests_and_download(self, target_dir: Path) -> ExportedFile:
        """Let the held export request through and save the resulting download."""
        with self.page.expect_download() as download_info:
            for held in self._held_routes:
                held.continue_()
        return self._save(download_info.value, target_dir)

    @step
    def start_tracking_exports(self):
        """Record export requests and downloads from now on."""
        self._track_export_requests()
        self._downloads.clear()
        self.page.on("download", lambda download: self._downloads.append(download))
        return self

    def _track_export_requests(self):
        self._export_requests.clear()
        self.page.on(
            "request",
            lambda request: self._export_requests.append(request.url)
            if EXPORT_URL_PATTERN.search(request.url)
            else None,
        )

    def _settle(self):
        """Round-trip through the browser (two animation frames) so pending UI updates and
        request events are delivered before a "nothing happened" assertion is evaluated."""
        self.page.evaluate(
            "() => new Promise(resolve => requestAnimationFrame("
            "() => requestAnimationFrame(resolve)))"
        )

    def _hold(self, route):
        self._held_routes.append(route)

    @staticmethod
    def _save(download, target_dir: Path) -> ExportedFile:
        path = target_dir / download.suggested_filename
        download.save_as(path)
        return ExportedFile(path=path, filename=download.suggested_filename)

    # ==================== ASSERTIONS ====================

    @step
    def should_be_visible(self):
        expect(self.dialog).to_be_visible()
        return self

    @step
    def should_be_closed(self):
        expect(self.dialog).to_be_hidden()
        return self

    @step
    def should_be_a_dialog_not_a_menu(self):
        expect(self.dialog).to_be_visible()
        expect(self.any_menu).to_have_count(0)
        return self

    @step
    def should_show_format_options(self):
        """Format heading plus a radio and a description for every format."""
        expect(self.format_heading).to_be_visible()
        for export_format in ExportFormat:
            expect(self.format_radio(export_format)).to_be_attached()
            expect(self.format_label(export_format)).to_be_visible()
            expect(self.format_description(export_format)).to_be_visible()
        return self

    @step
    def should_have_format_selected(self, export_format: ExportFormat):
        expect(self.format_radio(export_format)).to_be_checked()
        return self

    @step
    def should_have_tool_outputs_checkbox_checked_and_disabled(self):
        expect(self.include_tool_outputs_checkbox).to_be_checked()
        expect(self.include_tool_outputs_checkbox).to_be_disabled()
        return self

    @step
    def should_show_json_tool_outputs_hint(self, hint: str):
        expect(self.more_information_button).to_be_visible()
        expect(self.tool_outputs_hint).to_have_text(hint)
        return self

    @step
    def should_have_tool_outputs_checkbox_unchecked_and_enabled(self):
        expect(self.include_tool_outputs_checkbox).not_to_be_checked()
        expect(self.include_tool_outputs_checkbox).to_be_enabled()
        return self

    @step
    def should_have_tool_outputs_checkbox_checked_and_enabled(self):
        expect(self.include_tool_outputs_checkbox).to_be_checked()
        expect(self.include_tool_outputs_checkbox).to_be_enabled()
        return self

    @step
    def should_have_action_buttons_enabled(self):
        expect(self.cancel_button).to_be_enabled()
        expect(self.export_button).to_be_enabled()
        return self

    @step
    def should_have_export_in_progress(self):
        """Export button shows its loading state; Export and Cancel are disabled."""
        expect(self.export_button_loading_indicator).to_be_visible()
        expect(self.export_button).to_be_disabled()
        expect(self.cancel_button).to_be_disabled()
        return self

    @step
    def should_stay_open_while_exporting(self):
        """Dialog is still open and still in its loading state after the UI has settled."""
        self._settle()
        expect(self.dialog).to_be_visible()
        expect(self.export_button_loading_indicator).to_be_visible()
        return self

    @step
    def should_show_success_toast(self, text: str):
        expect(self.success_toast(text)).to_have_text(text)
        return self

    @step
    def should_not_show_success_toast(self):
        self._settle()
        expect(self.success_toast("successfully exported")).to_have_count(0)
        return self

    @step
    def should_have_filename_ending(self, exported: ExportedFile, suffix: str):
        assert_that(
            exported.filename, ends_with(suffix), "Unexpected exported file name."
        )
        return self

    @step
    def should_not_have_filename_ending(self, exported: ExportedFile, suffix: str):
        assert_that(
            exported.filename, not_(ends_with(suffix)), "Unexpected exported file name."
        )
        return self

    @step
    def should_have_export_request_params(
        self, request: Request, export_format: ExportFormat, include_tool_outputs: bool
    ):
        """Check export_format and that include_tool_outputs=true is sent only when expected."""
        params = parse_qs(urlparse(request.url).query)
        assert_that(
            params["export_format"],
            equal_to([export_format.extension]),
            "Unexpected export_format query parameter.",
        )
        assert_that(
            params.get("include_tool_outputs"),
            equal_to(["true"] if include_tool_outputs else None),
            "Unexpected include_tool_outputs query parameter.",
        )
        return self

    @step
    def should_have_sent_export_requests(self, count: int):
        self._settle()
        assert_that(
            len(self._export_requests), is_(count), "Unexpected export request count."
        )
        return self

    @step
    def should_have_downloaded_files(self, count: int):
        self._settle()
        assert_that(len(self._downloads), is_(count), "Unexpected download count.")
        return self

    # ---- assertions on the content of an exported file ----

    @step
    def should_contain_text(self, text: str, expected: str):
        assert_that(text, contains_string(expected), "Exported content mismatch.")
        return self

    @step
    def should_contain_all_text(self, text: str, expected: list):
        for fragment in expected:
            assert_that(text, contains_string(fragment), "Exported content mismatch.")
        return self

    @step
    def should_not_contain_text(self, text: str, unexpected: str):
        assert_that(
            text, not_(contains_string(unexpected)), "Unexpected exported content."
        )
        return self

    @step
    def should_include_item(self, items: list, expected, description: str):
        assert_that(items, has_item(expected), f"{description} not preserved.")
        return self

    @step
    def should_equal(self, actual, expected, description: str):
        assert_that(actual, equal_to(expected), f"{description} not preserved.")
        return self

    @step
    def should_have_entries(self, items: list, description: str):
        assert_that(items, not_(empty()), f"No {description} found.")
        return self

    @step
    def should_have_no_entries(self, items: list, description: str):
        assert_that(items, empty(), f"Unexpected {description}: {items}")
        return self
