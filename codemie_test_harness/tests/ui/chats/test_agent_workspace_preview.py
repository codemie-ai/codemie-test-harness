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
UI Test Suite: Agent workspace browser, readable preview of documents, data and logs

Covers:
  TC_001  Markdown files (.md, .markdown) render as formatted Markdown (AC-1)
  TC_002  Front matter shows as a monospace block above the formatted body (AC-2)
  TC_003  JSON is pretty-printed; invalid JSON and 16+ digit integers stay unchanged (AC-3, AC-4)
  TC_004  Text extensions show their raw text (AC-5)
  TC_005  Unknown extension, no extension or dotfile shows the no-preview hint (AC-6)
  TC_006  Expand control enlarges the preview and collapses it again (AC-7)
  TC_009  Download still delivers the file (AC-9)
  TC_010  HTML is shown as text and Markdown scripts do not execute (AC-10)
  TC_011  Expanded state resets after the browser is closed and reopened

Manual only (no scenarios): expanded image preview (write_file stores text only), Esc closing
only the expanded view.

Each test seeds its own conversation and workspace through the SDK, so the preview is
checked against known content.
"""

import pytest
from requests import HTTPError

from codemie_test_harness.tests.ui.pageobject.chats.chat_page import ChatPage
from codemie_test_harness.tests.ui.pageobject.components.agent_workspace_browser import (
    AgentWorkspaceBrowser,
)
from codemie_test_harness.tests.ui.test_data.agent_workspace_preview_test_data import (
    DOWNLOAD_FILE,
    EXPAND_FILES,
    EXPAND_IDS,
    FRONT_MATTER_BODY_HEADING,
    FRONT_MATTER_CASES,
    JSON_FILES,
    MARKDOWN_CODE_LINE,
    MARKDOWN_FILES,
    MARKDOWN_HEADING,
    MARKDOWN_LIST_ITEMS,
    MARKDOWN_SOURCE_MARKERS,
    MARKDOWN_TABLE_CELL,
    NO_PREVIEW_FILES,
    NO_PREVIEW_IDS,
    PAYLOAD_CASES,
    PAYLOAD_IDS,
    TEXT_FILES,
    TEXT_FILE_IDS,
    VIEWPORT,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def open_workspace_browser(page, client, conversation_utils):
    """Factory: create a conversation, seed its agent workspace and open the browser popup.

    The conversation id is registered right after creation, so teardown deletes it
    (and with it the workspace) even when seeding or opening the popup fails.
    """
    created_ids = []

    def _open(files) -> AgentWorkspaceBrowser:
        conversation = conversation_utils.create_conversation()
        conversation_id = conversation.get("id")
        created_ids.append(conversation_id)

        workspace = client.workspaces.create(conversation_id, name=get_random_name())
        for file in files:
            client.workspaces.write_file(workspace.id, file.path, file.content)

        page.set_viewport_size(VIEWPORT)
        ChatPage(page).navigate_to(conversation_id)
        return AgentWorkspaceBrowser(page).dismiss_guided_tour().open()

    yield _open

    for conversation_id in created_ids:
        try:
            conversation_utils.delete_conversation(conversation_id)
        except HTTPError:
            pass


# ---------------------------------------------------------------------------
# TC_001 — Markdown renders as formatted elements
# ---------------------------------------------------------------------------


# @case agent-workspace-browser-readable-preview_TC_001
@pytest.mark.chat
@pytest.mark.ui
@pytest.mark.parametrize(
    "file", MARKDOWN_FILES, ids=[file.path for file in MARKDOWN_FILES]
)
def test_workspace_preview_renders_markdown_as_formatted_elements(
    open_workspace_browser, file
):
    """
    TC_001: A .md / .markdown file shows a heading, a list, a table and a code block as
    formatted elements, not as raw Markdown source.

    AC-1: Markdown files render as formatted Markdown.
    """
    browser = open_workspace_browser([file])

    browser.select_file(file.path)

    browser.should_show_formatted_markdown(
        MARKDOWN_HEADING,
        MARKDOWN_LIST_ITEMS,
        MARKDOWN_TABLE_CELL,
        MARKDOWN_CODE_LINE,
        MARKDOWN_SOURCE_MARKERS,
    )


# ---------------------------------------------------------------------------
# TC_002 — front matter block above the body
# ---------------------------------------------------------------------------


# @case agent-workspace-browser-readable-preview_TC_002
@pytest.mark.chat
@pytest.mark.ui
@pytest.mark.parametrize(
    "case", FRONT_MATTER_CASES, ids=[case.variant for case in FRONT_MATTER_CASES]
)
def test_workspace_preview_shows_front_matter_above_formatted_body(
    open_workspace_browser, case
):
    """
    TC_002: A Markdown file that starts with a --- block shows the block text in a
    monospace block above the formatted body; the body has no horizontal rule or heading
    made from the delimiters. An empty block is still rendered; a leading BOM is tolerated.

    AC-2: Front matter shows as a monospace block above the formatted body.
    """
    browser = open_workspace_browser([case.file])

    browser.select_file(case.file.path)

    browser.should_show_front_matter(case.block_text)
    browser.should_show_front_matter_above_body()
    browser.should_have_only_body_heading(FRONT_MATTER_BODY_HEADING)


# ---------------------------------------------------------------------------
# TC_003 — JSON pretty-printing
# ---------------------------------------------------------------------------


# @case agent-workspace-browser-readable-preview_TC_003
@pytest.mark.chat
@pytest.mark.ui
@pytest.mark.parametrize("file", list(JSON_FILES.values()), ids=list(JSON_FILES))
def test_workspace_preview_pretty_prints_json_or_keeps_text_unchanged(
    open_workspace_browser, file
):
    """
    TC_003: Valid JSON is shown with a 2-space indent; invalid JSON and JSON with an integer
    of 16 or more digits are shown unchanged. No error is shown in any variant.

    AC-3: JSON is pretty-printed with 2 spaces.
    AC-4: Invalid JSON stays unchanged and raises no error.
    """
    browser = open_workspace_browser([file])

    browser.select_file(file.path)

    browser.should_show_text(file.shown_text)
    browser.should_not_show_error()


# ---------------------------------------------------------------------------
# TC_004 — text extensions
# ---------------------------------------------------------------------------


# @case agent-workspace-browser-readable-preview_TC_004
@pytest.mark.chat
@pytest.mark.ui
@pytest.mark.parametrize("file", TEXT_FILES, ids=TEXT_FILE_IDS)
def test_workspace_preview_shows_raw_text_for_text_extensions(
    open_workspace_browser, file
):
    """
    TC_004: A file with a text extension (any letter case) shows its text unchanged.

    AC-5: Text extensions show their raw text.
    """
    browser = open_workspace_browser([file])

    browser.select_file(file.path)

    browser.should_show_text(file.content)


# ---------------------------------------------------------------------------
# TC_005 — no-preview hint
# ---------------------------------------------------------------------------


# @case agent-workspace-browser-readable-preview_TC_005
@pytest.mark.chat
@pytest.mark.ui
@pytest.mark.parametrize("file", NO_PREVIEW_FILES, ids=NO_PREVIEW_IDS)
def test_workspace_preview_shows_hint_for_file_without_preview(
    open_workspace_browser, file
):
    """
    TC_005: A file with an unknown extension, no extension or only a leading dot shows the
    no-preview hint listing Markdown, JSON, text formats and images, and no preview.

    AC-6: Files the preview cannot render show the hint.
    """
    browser = open_workspace_browser([file])

    browser.select_file(file.path)

    browser.should_show_no_preview_hint()


# ---------------------------------------------------------------------------
# TC_006 — expand and collapse
# ---------------------------------------------------------------------------


# @case agent-workspace-browser-readable-preview_TC_006
@pytest.mark.chat
@pytest.mark.ui
@pytest.mark.parametrize("file", EXPAND_FILES, ids=EXPAND_IDS)
def test_workspace_preview_expands_and_collapses(open_workspace_browser, file):
    """
    TC_006: Expand relabels the control to "Collapse preview", hides the file list panel
    and widens the popup to nearly the whole viewport with the same file shown; the
    control again restores "Expand preview", the file list and the normal size.

    AC-7: Expand control enlarges the preview and collapses it again.
    """
    browser = open_workspace_browser([file])
    browser.select_file(file.path)
    browser.should_show_file_preview(file)
    browser.should_offer_expand()
    normal_width = browser.popup_width()

    browser.toggle_expand()

    browser.should_be_expanded()
    browser.should_show_file_preview(file)

    browser.toggle_expand()

    browser.should_offer_expand()
    browser.should_have_popup_width(normal_width)
    browser.should_show_file_preview(file)


# ---------------------------------------------------------------------------
# TC_009 — download
# ---------------------------------------------------------------------------


# @case agent-workspace-browser-readable-preview_TC_009
@pytest.mark.chat
@pytest.mark.ui
def test_workspace_download_delivers_the_selected_file(
    open_workspace_browser, tmp_path
):
    """
    TC_009: Download starts a browser download with the seeded file name and content.

    AC-9: Download still delivers the file.
    """
    browser = open_workspace_browser([DOWNLOAD_FILE])
    browser.select_file(DOWNLOAD_FILE.path)
    browser.should_show_text(DOWNLOAD_FILE.content)

    download = browser.download_selected_file(tmp_path)

    browser.should_deliver_file(download, DOWNLOAD_FILE.path, DOWNLOAD_FILE.content)


# ---------------------------------------------------------------------------
# TC_010 — HTML and Markdown payloads do not execute
# ---------------------------------------------------------------------------


# @case agent-workspace-browser-readable-preview_TC_010
@pytest.mark.chat
@pytest.mark.ui
@pytest.mark.parametrize("file, flag", PAYLOAD_CASES, ids=PAYLOAD_IDS)
def test_workspace_preview_does_not_execute_html_or_markdown_scripts(
    open_workspace_browser, file, flag
):
    """
    TC_010: An .html file is shown as its literal source and a Markdown file with script and
    onerror payloads renders no script element; in both cases the payload never runs.

    AC-10: HTML is shown as text and Markdown scripts do not execute.
    """
    browser = open_workspace_browser([file])

    browser.select_file(file.path)

    browser.should_show_payload_inertly(file, flag)


# ---------------------------------------------------------------------------
# TC_011 — expanded state resets on reopen
# ---------------------------------------------------------------------------


# @case agent-workspace-browser-readable-preview_TC_011
@pytest.mark.chat
@pytest.mark.ui
def test_workspace_expanded_state_resets_after_reopening_browser(
    open_workspace_browser,
):
    """
    TC_011: After the preview is expanded and the browser is closed and reopened, the file
    list panel is visible and the control reads "Expand preview" again.

    Gap from the change: stale expanded state would hide the file list.
    """
    file = EXPAND_FILES[0]
    browser = open_workspace_browser([file])
    browser.select_file(file.path)
    browser.toggle_expand()
    browser.should_be_expanded()

    browser.close()
    browser.should_be_closed()
    browser.open()
    browser.select_file(file.path)

    browser.should_offer_expand()
    browser.should_show_file_preview(file)
