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

"""Calls history popup of a workflow execution node, with its Download and Copy actions."""

import json
import re
from pathlib import Path
from typing import List

from hamcrest import (
    all_of,
    assert_that,
    contains_exactly,
    equal_to,
    greater_than,
    has_length,
    instance_of,
    is_in,
    not_none,
)
from playwright.sync_api import Download, Locator, Page, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.test_data.call_history_export_test_data import (
    CALL_HISTORY_TITLE_PREFIX,
    DEFAULT_CALL_LABEL,
    EXPORT_CALL_KEYS,
    EXPORT_CALL_REQUIRED_KEYS,
    EXPORT_INDENT,
    EXPORT_TOP_LEVEL_KEYS,
    expected_call_history_filename,
)


class CallHistoryPopup:
    """Popup 'Calls history for <node>' with the call list and the Download / Copy actions."""

    def __init__(self, page: Page):
        self.page = page

    # ====================
    # PROPERTIES
    # ====================

    @property
    def dialog(self) -> Locator:
        """Popup dialog that carries the 'Calls history for <node>' title."""
        return self.page.get_by_role("dialog").filter(
            has=self.page.get_by_role(
                "heading", name=re.compile(rf"^{CALL_HISTORY_TITLE_PREFIX}")
            )
        )

    @property
    def title(self) -> Locator:
        """Popup title 'Calls history for <node>'."""
        return self.dialog.get_by_role(
            "heading", name=re.compile(rf"^{CALL_HISTORY_TITLE_PREFIX}")
        )

    @property
    def download_button(self) -> Locator:
        """'Download' button in the popup header."""
        return self.dialog.get_by_role("button", name="Download", exact=True)

    @property
    def copy_button(self) -> Locator:
        """'Copy to clipboard' button in the popup header."""
        return self.dialog.get_by_role("button", name="Copy to clipboard", exact=True)

    @property
    def call_entries(self) -> Locator:
        """Header buttons of the top-level calls; the popup opens them expanded (nested calls stay collapsed)."""
        return self.dialog.get_by_role("button", expanded=True)

    def toast(self, text: str) -> Locator:
        """Toast notification with the given header text."""
        return self.page.locator(".codemie-toast-header").filter(has_text=text)

    # ====================
    # ACTIONS
    # ====================

    @step
    def get_node_name(self) -> str:
        """Node name from the popup title."""
        expect(self.title).to_be_visible()
        return self.title.inner_text().removeprefix(CALL_HISTORY_TITLE_PREFIX).strip()

    @step
    def get_call_labels(self) -> List[str]:
        """Labels of the calls shown in the popup, in display order."""
        expect(self.call_entries.first).to_be_visible()
        return [
            (label or "").strip()
            for label in self.call_entries.evaluate_all(
                "els => els.map(el => el.getAttribute('aria-label'))"
            )
        ]

    @step
    def click_download(self) -> Download:
        """Press 'Download' and return the browser download."""
        expect(self.download_button).to_be_visible()
        with self.page.expect_download() as download_info:
            self.download_button.click()
        return download_info.value

    @step
    def click_copy(self):
        """Press 'Copy to clipboard'."""
        expect(self.copy_button).to_be_visible()
        self.copy_button.click()

    @step
    def read_clipboard(self) -> str:
        """Text currently on the clipboard."""
        return self.page.evaluate("() => navigator.clipboard.readText()")

    # ====================
    # VERIFICATIONS
    # ====================

    @step
    def should_be_visible(self):
        """Verify the popup is open and shows its title."""
        expect(self.dialog).to_be_visible()
        expect(self.title).to_be_visible()
        return self

    @step
    def should_have_title_with_node_name(self):
        """Verify the title is 'Calls history for <node>' with a non-empty node name."""
        expect(self.title).to_have_text(re.compile(rf"^{CALL_HISTORY_TITLE_PREFIX}\S+"))

    @step
    def should_have_call_list(self):
        """Verify at least one call is listed and its body (Result) is rendered."""
        expect(self.call_entries.first).to_be_visible()
        expect(self.dialog.get_by_text("Result:", exact=True).first).to_be_visible()

    @step
    def should_show_toast(self, text: str):
        """Verify a toast whose header contains ``text`` is shown."""
        expect(self.toast(text)).to_be_visible()

    @step
    def should_have_download_named(
        self, download: Download, node_name: str, execution_id: str
    ):
        """Verify the browser suggested ``call-history-<node-slug>-<execution_id>.json``."""
        assert_that(
            download.suggested_filename,
            equal_to(expected_call_history_filename(node_name, execution_id)),
            "Suggested file name of the call history download",
        )

    @step
    def should_have_export_matching_popup(
        self,
        exported_text: str,
        execution_id: str,
        node_name: str,
        popup_call_labels: List[str],
    ):
        """Verify the exported JSON has the documented fields and exactly the calls shown in the popup."""
        exported = json.loads(exported_text)

        assert_that(
            set(exported.keys()),
            equal_to(set(EXPORT_TOP_LEVEL_KEYS)),
            "Top-level keys of the exported call history",
        )
        assert_that(
            exported["execution_id"], equal_to(execution_id), "Exported execution_id"
        )
        assert_that(exported["node"], equal_to(node_name), "Exported node name")
        assert_that(exported["state_id"], all_of(instance_of(str), not_none()))
        assert_that(exported["status"], all_of(instance_of(str), not_none()))

        calls = exported["calls"]
        assert_that(
            calls, has_length(len(popup_call_labels)), "Exported calls vs popup calls"
        )
        assert_that(
            [c["index"] for c in calls],
            equal_to(list(range(1, len(calls) + 1))),
            "Exported calls are indexed from 1 in view order",
        )
        assert_that(
            [self._call_label(c) for c in calls],
            contains_exactly(*popup_call_labels),
            "Exported calls are the calls shown in the popup, in the same order",
        )

        for call in calls:
            keys = set(call.keys())
            assert_that(
                keys >= EXPORT_CALL_REQUIRED_KEYS,
                equal_to(True),
                f"Call {call.get('index')} is missing a required key: "
                f"{sorted(EXPORT_CALL_REQUIRED_KEYS - keys)}",
            )
            for key in keys:
                assert_that(
                    key,
                    is_in(EXPORT_CALL_KEYS),
                    f"Call {call['index']} has an undocumented key",
                )
            assert_that(call["message"], instance_of(str), "Call message is raw text")
            assert_that(
                call["content"],
                equal_to(self._expected_content(call["message"])),
                f"Call {call['index']} content is the parsed message JSON, or the raw text",
            )

    @step
    def should_be_indented_json(self, text: str):
        """Verify ``text`` is valid JSON indented with 2 spaces."""
        assert_that(len(text), greater_than(0), "Exported text is empty")
        parsed = json.loads(text)
        assert_that(
            text,
            equal_to(json.dumps(parsed, indent=EXPORT_INDENT, ensure_ascii=False)),
            "Text is not JSON indented with 2 spaces",
        )

    @staticmethod
    def read_downloaded_text(download: Download) -> str:
        """Content of the downloaded file."""
        return Path(download.path()).read_text(encoding="utf-8")

    @staticmethod
    def _call_label(call: dict) -> str:
        """Label the popup shows for a call: author name, else tool name, else 'Tool'."""
        label = call.get("author_name")
        if label is None:
            label = call.get("tool_name")
        if label is None:
            label = DEFAULT_CALL_LABEL
        return label.strip()

    @staticmethod
    def _expected_content(message: str):
        """``content`` of a call: the message parsed when it is a JSON object or array, else the raw text."""
        try:
            parsed = json.loads(message)
        except ValueError:
            return message
        return parsed if isinstance(parsed, (dict, list)) else message
