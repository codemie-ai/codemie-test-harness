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

"""Generated-files block of a chat answer.

Files published during an assistant turn are listed under the answer as chips in a
`generated-files` container. A chip shows the file name, a type badge whose title
attribute is the file's MIME type, and a "Download file" button that saves the file
under the last segment of its name.
"""

import zipfile
from pathlib import Path

from hamcrest import assert_that, contains_inanyorder, equal_to
from playwright.sync_api import Download, Locator, expect
from reportportal_client import step

# Links a chat answer must never show for a file that was not delivered.
_UNDELIVERED_LINK_SELECTOR = (
    "a[href^='filesystem:'], a[href^='file:'], a[href^='sandbox:']"
)


class GeneratedFiles:
    """Component for the generated-files chips of a chat."""

    def __init__(self, scope: Locator):
        """
        Args:
            scope: Locator of the chat history holding the answers
        """
        self.scope = scope

    # Elements

    @property
    def container(self) -> Locator:
        """The `generated-files` block listing the chips of one answer."""
        return self.scope.get_by_test_id("generated-files")

    @property
    def download_buttons(self) -> Locator:
        """'Download file' buttons, one per chip."""
        return self.container.get_by_role("button", name="Download file")

    @property
    def undelivered_links(self) -> Locator:
        """Anchors with a filesystem:, file: or sandbox: href anywhere in the chat."""
        return self.scope.locator(_UNDELIVERED_LINK_SELECTOR)

    def file_name(self, name: str) -> Locator:
        """The text of a chip showing this file name."""
        return self.container.get_by_text(name, exact=True)

    def type_badge(self, mime_type: str) -> Locator:
        """The type badge of a chip; its title attribute is the MIME type."""
        return self.container.get_by_title(mime_type, exact=True)

    # Actions

    @step
    def download_file(self) -> Download:
        """Press 'Download file' on the only chip and return the browser download."""
        expect(self.download_buttons).to_have_count(1)
        with self.container.page.expect_download() as download_info:
            self.download_buttons.click()
        return download_info.value

    # Verifications

    @step
    def should_show_file(self, name: str, mime_type: str, timeout: int = 30000):
        """One chip is shown, with the file name, the MIME type in its badge title and
        a download button."""
        expect(self.container).to_have_count(1, timeout=timeout)
        expect(self.file_name(name)).to_have_count(1)
        expect(self.type_badge(mime_type)).to_have_count(1)
        expect(self.download_buttons).to_have_count(1)
        return self

    @step
    def should_not_show_files(self):
        """No generated-files block is in the chat."""
        expect(self.container).to_have_count(0)
        return self

    @step
    def should_not_have_undelivered_links(self):
        """No anchor in the chat points at a filesystem:, file: or sandbox: location."""
        expect(self.undelivered_links).to_have_count(0)
        return self

    @step
    def should_be_saved_as(self, download: Download, name: str, content: str):
        """The download is saved under `name` and holds the lines of `content`."""
        assert_that(
            download.suggested_filename,
            equal_to(name),
            "The download must be saved under the file's name",
        )
        saved = Path(download.path()).read_text(encoding="utf-8")
        assert_that(
            [line.strip() for line in saved.strip().splitlines()],
            equal_to([line.strip() for line in content.strip().splitlines()]),
            "The saved file must equal the content the server wrote",
        )
        return self

    @step
    def should_be_saved_as_archive(self, download: Download, name: str, members: tuple):
        """The download is saved under `name` as a zip container holding `members`."""
        assert_that(
            download.suggested_filename,
            equal_to(name),
            "The download must be saved under the file's name",
        )
        with zipfile.ZipFile(download.path()) as archive:
            assert_that(
                archive.namelist(),
                contains_inanyorder(*members),
                "The saved file must be a zip container with the members the script wrote",
            )
        return self
