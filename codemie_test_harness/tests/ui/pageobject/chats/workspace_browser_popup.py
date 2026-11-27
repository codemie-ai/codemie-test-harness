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

Lists the files of the chat's workspace and offers "Download all", which saves the
whole workspace as one archive. Also reads the saved archive and asserts on it, so
tests never touch raw Playwright or zip APIs.
"""

import hashlib
import re
from pathlib import Path

from hamcrest import assert_that, equal_to, has_item, is_, is_not
from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.test_data.workspace_download_test_data import (
    WORKSPACE_ARCHIVE_NAME,
    WORKSPACE_POPUP_TITLE,
)
from codemie_test_harness.tests.ui.utils.workspace_archive import (
    WorkspaceArchive,
    read_workspace_archive,
)


class WorkspaceBrowserPopup(BasePage):
    """The "Agent workspace" popup with the file list and the "Download all" button."""

    # ====================
    # ELEMENTS
    # ====================

    @property
    def dialog(self) -> Locator:
        """Popup container titled "Agent workspace"."""
        return self.page.get_by_role("dialog").filter(has_text=WORKSPACE_POPUP_TITLE)

    @property
    def file_list(self) -> Locator:
        """List of the workspace files."""
        return self.page.locator('[data-testid="workspace-file-list"]')

    @property
    def file_rows(self) -> Locator:
        """One row per workspace file; the row text is the file name."""
        return self.file_list.locator("button:has(span.break-all)")

    @property
    def empty_state(self) -> Locator:
        """The "No files found." text shown for an empty workspace."""
        return self.file_list.get_by_text("No files found.")

    @property
    def download_all_button(self) -> Locator:
        """The "Download all" button of the popup."""
        return self.page.locator('[data-testid="workspace-download-all"]')

    @property
    def close_button(self) -> Locator:
        """Close button of the popup."""
        return self.dialog.get_by_role("button", name="Close", exact=True).first

    def file_row(self, file_name: str) -> Locator:
        """Row of the file with exactly this name."""
        name_cell = self.page.locator("span.break-all").filter(
            has_text=re.compile(rf"^{re.escape(file_name)}$")
        )
        return self.file_rows.filter(has=name_cell)

    # ====================
    # ACTIONS
    # ====================

    @step
    def close(self):
        """Close the popup."""
        self.close_button.click()
        expect(self.dialog).to_be_hidden()
        return self

    @step
    def download_all(self) -> WorkspaceArchive:
        """Press "Download all" and read the archive the browser saves."""
        expect(self.download_all_button).to_be_enabled()
        with self.page.expect_download() as download_info:
            self.download_all_button.click()
        return read_workspace_archive(download_info.value)

    # ====================
    # VERIFICATIONS
    # ====================

    @step
    def should_be_visible(self, timeout: int = 15000):
        """Verify the popup is open."""
        expect(self.dialog).to_be_visible(timeout=timeout)
        expect(self.download_all_button).to_be_visible(timeout=timeout)
        return self

    @step
    def should_have_download_all_disabled(self):
        """Verify "Download all" cannot be pressed."""
        expect(self.download_all_button).to_be_disabled()
        return self

    @step
    def should_have_download_all_enabled(self, timeout: int = 30000):
        """Verify "Download all" can be pressed."""
        expect(self.download_all_button).to_be_enabled(timeout=timeout)
        return self

    @step
    def should_have_no_files(self):
        """Verify the file list shows the empty-workspace message and no rows."""
        expect(self.empty_state).to_be_visible()
        expect(self.file_rows).to_have_count(0)
        return self

    @step
    def should_list_file(self, file_name: str, timeout: int = 30000):
        """Verify the workspace lists a file with this name."""
        expect(self.file_row(file_name)).to_be_visible(timeout=timeout)
        return self

    @step
    def should_have_archive_named(self, archive: WorkspaceArchive):
        """Verify the browser saved the archive as workspace-files.zip."""
        assert_that(
            archive.filename,
            equal_to(WORKSPACE_ARCHIVE_NAME),
            "File name the browser saved the 'Download all' archive under",
        )
        return self

    @step
    def should_have_archive_entry(self, archive: WorkspaceArchive, file_name: str):
        """Verify the archive holds an entry named exactly like the workspace file."""
        assert_that(
            archive.entry_names,
            has_item(file_name),
            f"Archive entries do not include '{file_name}'",
        )
        return self

    @step
    def should_not_have_archive_entry(self, archive: WorkspaceArchive, file_name: str):
        """Verify the archive holds no entry named like this file."""
        assert_that(
            archive.entry_names,
            is_not(has_item(file_name)),
            f"Archive entries must not include '{file_name}'",
        )
        return self

    @step
    def should_have_archive_entry_equal_to_file(
        self, archive: WorkspaceArchive, file_name: str, original: Path
    ):
        """Verify the entry's bytes are identical to the original local file (compared by SHA-256)."""
        self.should_have_archive_entry(archive, file_name)
        assert_that(
            hashlib.sha256(archive.entries[file_name]).hexdigest(),
            is_(equal_to(hashlib.sha256(Path(original).read_bytes()).hexdigest())),
            f"SHA-256 of archive entry '{file_name}' against the uploaded file",
        )
        return self
