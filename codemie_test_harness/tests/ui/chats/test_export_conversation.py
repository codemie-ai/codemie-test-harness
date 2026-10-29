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
UI Test Suite: Export Conversation dialog (DOCX / PDF / JSON)

Covers:
  TC-001  Dialog opens with Format options and JSON as default (AC-4, AC-5, AC-6, AC-15)
  TC-002  "Include tool outputs" checkbox state follows the selected format (AC-5, AC-6)
  TC-003  JSON export keeps tool outputs (AC-4, AC-13, AC-14, AC-15)
  TC-004  Default DOCX/PDF export has no tool outputs (AC-1, AC-2, AC-3, AC-6, AC-13, AC-15)
  TC-005  DOCX/PDF export with tool outputs is labelled and contains them (AC-3, AC-5, AC-6, AC-13)
  TC-006  Loading state and duplicate-click protection (AC-11, AC-12, AC-13)
  TC-007  Export request parameters (AC-4, AC-5, AC-14)
  TC-008  DOCX/PDF preserve assistant response formatting (AC-7)
  TC-009  Cancelling or dismissing the dialog exports nothing (AC-15)

Manual only (no scenarios): AC-8, AC-9, AC-10, failure half of AC-13, permissions half of AC-15.

Tool-output marker: the environment's default model does not invoke tools, but every assistant
message still carries a "Codemie Thoughts" thought. That thought is rendered only in "with tool
outputs" exports, so its heading is the marker of tool outputs in DOCX/PDF.
"""

import pytest
from requests import HTTPError

from codemie_sdk.models.conversation import ConversationCreateRequest
from codemie_test_harness.tests.conftest import COMMON_ASSISTANT_SYSTEM_PROMPT
from codemie_test_harness.tests.ui.pageobject.chats.chat_page import ChatPage
from codemie_test_harness.tests.ui.test_data.assistant_test_data import (
    ResearchTool,
    Toolkit,
)
from codemie_test_harness.tests.ui.test_data.export_conversation_test_data import (
    DOCUMENT_FORMATS,
    EXPORT_REQUEST_CASES,
    JSON_TOOL_OUTPUTS_HINT,
    MARKDOWN_SYSTEM_PROMPT_TEMPLATE,
    MARKDOWN_USER_PROMPT,
    TOOL_OUTPUTS_SECTION_HEADING,
    DismissMode,
    ExportFormat,
    create_export_conversation_data,
    create_markdown_sample,
    filename_suffix,
    success_toast_text,
)
from codemie_test_harness.tests.ui.utils.export_file_parser import (
    extract_docx,
    extract_pdf_links,
    extract_text,
    json_thought_authors,
)
from codemie_test_harness.tests.utils.client_factory import get_client


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def open_seeded_chat(page, assistant_utils):
    """Factory: create a conversation, seed it through the API and open it in the UI.

    The conversation id is registered right after creation, so teardown deletes it
    even when seeding or opening the chat fails afterwards.
    """
    created_ids = []

    def _open(test_assistant, prompt):
        conversation = get_client().conversations.create(
            ConversationCreateRequest(initial_assistant_id=test_assistant.id, folder="")
        )
        conversation_id = conversation.get("id")
        created_ids.append(conversation_id)
        assistant_utils.ask_assistant(
            test_assistant, prompt, conversation_id=conversation_id
        )
        return ChatPage(page).open_conversation_with_export_button(conversation_id)

    yield _open

    for conversation_id in created_ids:
        try:
            get_client().conversations.delete(conversation_id)
        except HTTPError:
            pass


@pytest.fixture(scope="function")
def export_data():
    """Unique prompt/answer tokens for one test."""
    return create_export_conversation_data()


@pytest.fixture(scope="function")
def chat_with_tool_outputs(assistant, open_seeded_chat, export_data):
    """Open chat of a conversation whose assistant message carries tool outputs."""
    test_assistant = assistant(
        Toolkit.RESEARCH.value,
        ResearchTool.WIKIPEDIA.value,
        system_prompt=COMMON_ASSISTANT_SYSTEM_PROMPT
        + export_data.system_prompt_addition,
    )
    return open_seeded_chat(test_assistant, export_data.user_prompt)


@pytest.fixture(scope="function")
def chat_with_markdown_reply(assistant, open_seeded_chat):
    """Open chat whose assistant replied with a fixed rich-markdown sample."""
    sample = create_markdown_sample()
    test_assistant = assistant(
        system_prompt=MARKDOWN_SYSTEM_PROMPT_TEMPLATE.format(markdown=sample.markdown)
    )
    return open_seeded_chat(test_assistant, MARKDOWN_USER_PROMPT), sample


# ---------------------------------------------------------------------------
# TC-001 — dialog content and defaults
# ---------------------------------------------------------------------------


@pytest.mark.chat
@pytest.mark.ui
def test_export_dialog_opens_with_format_options_and_json_default(
    page, navigate_to_new_chat_page
):
    """
    TC-001: The header Export button opens a dialog (not a menu) listing JSON/DOCX/PDF
    with descriptions, JSON selected, "Include tool outputs" checked and disabled
    with its hint, and enabled Cancel/Export buttons.

    AC-4: JSON export keeps tool outputs.
    AC-5: DOCX/PDF offer a separate tool-outputs option.
    AC-6: Labels distinguish the export variants.
    AC-15: Export entry point is unchanged.
    """
    chat_page = navigate_to_new_chat_page(page)

    dialog = chat_page.open_export_conversation_dialog()

    dialog.should_be_a_dialog_not_a_menu()
    dialog.should_show_format_options()
    dialog.should_have_format_selected(ExportFormat.JSON)
    dialog.should_have_tool_outputs_checkbox_checked_and_disabled()
    dialog.should_show_json_tool_outputs_hint(JSON_TOOL_OUTPUTS_HINT)
    dialog.should_have_action_buttons_enabled()


# ---------------------------------------------------------------------------
# TC-002 — checkbox state follows the selected format
# ---------------------------------------------------------------------------


@pytest.mark.chat
@pytest.mark.ui
@pytest.mark.parametrize("export_format", DOCUMENT_FORMATS, ids=lambda f: f.label)
def test_export_dialog_tool_outputs_checkbox_follows_format(
    page, navigate_to_new_chat_page, export_format
):
    """
    TC-002: For DOCX/PDF the checkbox is unchecked and enabled and can be ticked;
    switching to JSON shows it checked and disabled; switching back resets it to
    unchecked and enabled.

    AC-5: DOCX/PDF offer a separate tool-outputs option.
    AC-6: Labels distinguish the export variants.
    """
    chat_page = navigate_to_new_chat_page(page)
    dialog = chat_page.open_export_conversation_dialog()

    dialog.select_format(export_format)
    dialog.should_have_tool_outputs_checkbox_unchecked_and_enabled()

    dialog.choose_include_tool_outputs(True)
    dialog.should_have_tool_outputs_checkbox_checked_and_enabled()

    dialog.select_format(ExportFormat.JSON)
    dialog.should_have_tool_outputs_checkbox_checked_and_disabled()

    dialog.select_format(export_format)
    dialog.should_have_tool_outputs_checkbox_unchecked_and_enabled()


# ---------------------------------------------------------------------------
# TC-003 — JSON export keeps tool outputs
# ---------------------------------------------------------------------------


@pytest.mark.chat
@pytest.mark.ui
def test_export_json_downloads_file_with_tool_outputs(
    chat_with_tool_outputs, export_data, tmp_path
):
    """
    TC-003: JSON export downloads a plain .json file that includes tool outputs,
    shows the success toast and closes the dialog.

    AC-4: JSON export keeps tool outputs.
    AC-13: Success state is shown.
    AC-14: JSON export with tool outputs still works.
    AC-15: Download behavior is unchanged.
    """
    dialog = chat_with_tool_outputs.open_export_conversation_dialog()
    dialog.select_format(ExportFormat.JSON)

    exported = dialog.export_and_download(tmp_path)

    dialog.should_have_filename_ending(
        exported, filename_suffix(ExportFormat.JSON, False)
    )
    dialog.should_not_have_filename_ending(
        exported, filename_suffix(ExportFormat.JSON, True)
    )
    dialog.should_contain_text(
        extract_text(exported.path, ExportFormat.JSON), export_data.prompt_token
    )
    dialog.should_have_entries(
        json_thought_authors(exported.path), "tool outputs (thoughts) in JSON export"
    )
    dialog.should_be_closed()
    dialog.should_show_success_toast(success_toast_text(ExportFormat.JSON, False))


# ---------------------------------------------------------------------------
# TC_016 — JSON export of a flagged assistant has no tool outputs
# ---------------------------------------------------------------------------


@pytest.mark.chat
@pytest.mark.ui
def test_export_json_of_flagged_assistant_has_no_tool_outputs(
    assistant,
    enable_hide_tool_outputs_on_assistant,
    open_seeded_chat,
    export_data,
    tmp_path,
):
    """
    JSON export normally includes tool outputs (see TC-003 above), but
    for an assistant with 'Hide tool outputs from end users' ON the export must carry
    the prompt and the final answer and no thoughts at all.
    """
    test_assistant = assistant(
        Toolkit.RESEARCH.value,
        ResearchTool.WIKIPEDIA.value,
        system_prompt=COMMON_ASSISTANT_SYSTEM_PROMPT
        + export_data.system_prompt_addition,
    )
    enable_hide_tool_outputs_on_assistant(test_assistant.name)
    chat_page = open_seeded_chat(test_assistant, export_data.user_prompt)

    dialog = chat_page.open_export_conversation_dialog()
    dialog.select_format(ExportFormat.JSON)
    exported = dialog.export_and_download(tmp_path)

    exported_text = extract_text(exported.path, ExportFormat.JSON)
    dialog.should_contain_text(exported_text, export_data.prompt_token)
    dialog.should_contain_text(exported_text, export_data.answer_token)
    dialog.should_have_no_entries(
        json_thought_authors(exported.path),
        "tool outputs (thoughts) in JSON export of a flagged assistant",
    )


# ---------------------------------------------------------------------------
# TC-004 — default DOCX/PDF export has no tool outputs
# ---------------------------------------------------------------------------


@pytest.mark.chat
@pytest.mark.ui
@pytest.mark.parametrize("export_format", DOCUMENT_FORMATS, ids=lambda f: f.label)
def test_export_default_document_has_only_prompts_and_responses(
    chat_with_tool_outputs, export_data, tmp_path, export_format
):
    """
    TC-004: With the checkbox left unchecked, the DOCX/PDF contains the user prompt and the
    assistant answer but no tool outputs, and is not labelled "with tool outputs".

    AC-1/AC-2: Default DOCX/PDF export has only prompts and responses.
    AC-3: Tool outputs are excluded.
    AC-6: Labels distinguish the export variants.
    AC-13: Success state is shown.
    AC-15: Download behavior is unchanged.
    """
    dialog = chat_with_tool_outputs.open_export_conversation_dialog()
    dialog.select_format(export_format)

    exported = dialog.export_and_download(tmp_path)

    dialog.should_have_filename_ending(exported, filename_suffix(export_format, False))
    dialog.should_not_have_filename_ending(
        exported, filename_suffix(export_format, True)
    )
    text = extract_text(exported.path, export_format)
    dialog.should_contain_text(text, export_data.prompt_token)
    dialog.should_contain_text(text, export_data.answer_token)
    dialog.should_not_contain_text(text, TOOL_OUTPUTS_SECTION_HEADING)
    dialog.should_be_closed()
    dialog.should_show_success_toast(success_toast_text(export_format, False))


# ---------------------------------------------------------------------------
# TC-005 — DOCX/PDF export with tool outputs
# ---------------------------------------------------------------------------


@pytest.mark.chat
@pytest.mark.ui
@pytest.mark.parametrize("export_format", DOCUMENT_FORMATS, ids=lambda f: f.label)
def test_export_document_with_tool_outputs_is_labelled_and_complete(
    chat_with_tool_outputs, export_data, tmp_path, export_format
):
    """
    TC-005: With "Include tool outputs" ticked, the file name carries the
    "_with_tool_outputs" suffix, the toast says "(with tool outputs)" and the document
    contains prompt, answer and the tool outputs.

    AC-3: Tool outputs are available through the dedicated option.
    AC-5: DOCX/PDF offer a separate tool-outputs option.
    AC-6: Labels distinguish the export variants.
    AC-13: Success state is shown.
    """
    dialog = chat_with_tool_outputs.open_export_conversation_dialog()
    dialog.select_format(export_format)
    dialog.choose_include_tool_outputs(True)

    exported = dialog.export_and_download(tmp_path)

    dialog.should_have_filename_ending(exported, filename_suffix(export_format, True))
    text = extract_text(exported.path, export_format)
    dialog.should_contain_text(text, export_data.prompt_token)
    dialog.should_contain_text(text, export_data.answer_token)
    dialog.should_contain_text(text, TOOL_OUTPUTS_SECTION_HEADING)
    dialog.should_be_closed()
    dialog.should_show_success_toast(success_toast_text(export_format, True))


# ---------------------------------------------------------------------------
# TC-006 — loading state and duplicate protection
# ---------------------------------------------------------------------------


@pytest.mark.chat
@pytest.mark.ui
def test_export_shows_loading_state_and_blocks_duplicates(
    chat_with_tool_outputs, tmp_path
):
    """
    TC-006: While the export request is pending, Export shows its loading state and is
    disabled, Cancel is disabled, Escape/overlay clicks do not close the dialog and a
    second Export click sends no second request. Releasing the request downloads the
    file, closes the dialog and shows the success toast.

    AC-11: In-progress indicator is visible.
    AC-12: Duplicate export clicks are prevented.
    AC-13: Success state is shown.
    """
    dialog = chat_with_tool_outputs.open_export_conversation_dialog()
    dialog.select_format(ExportFormat.DOCX)
    dialog.hold_export_requests()

    dialog.click_export()

    dialog.should_have_export_in_progress()
    dialog.press_escape()
    dialog.should_stay_open_while_exporting()
    dialog.click_overlay()
    dialog.should_stay_open_while_exporting()
    dialog.click_export_while_loading()
    dialog.should_have_sent_export_requests(1)

    dialog.release_export_requests_and_download(tmp_path)

    dialog.should_be_closed()
    dialog.should_show_success_toast(success_toast_text(ExportFormat.DOCX, False))


# ---------------------------------------------------------------------------
# TC-007 — export request parameters
# ---------------------------------------------------------------------------


@pytest.mark.chat
@pytest.mark.ui
@pytest.mark.parametrize(
    "case",
    EXPORT_REQUEST_CASES,
    ids=[
        "json",
        "docx-unchecked",
        "pdf-checked",
        "docx-checked-then-json",
    ],
)
def test_export_request_carries_tool_outputs_flag_only_when_expected(
    page, navigate_to_new_chat_page, case
):
    """
    TC-007: The export request has export_format=<format> and include_tool_outputs=true
    only for DOCX/PDF with the checkbox ticked; a ticked box does not leak into JSON.

    AC-4: JSON export keeps tool outputs.
    AC-5: DOCX/PDF offer a separate tool-outputs option.
    AC-14: JSON export request is unchanged.
    """
    chat_page = navigate_to_new_chat_page(page)
    dialog = chat_page.open_export_conversation_dialog()
    dialog.select_format(case.first_format)
    dialog.choose_include_tool_outputs(case.check_tool_outputs)
    dialog.select_format(case.final_format)

    request = dialog.export_and_capture_request()

    dialog.should_have_export_request_params(
        request, case.final_format, case.expected_include_tool_outputs
    )


# ---------------------------------------------------------------------------
# TC-008 — formatting preserved
# ---------------------------------------------------------------------------


@pytest.mark.chat
@pytest.mark.ui
def test_export_docx_preserves_assistant_formatting(chat_with_markdown_reply, tmp_path):
    """
    TC-008 (DOCX): headings (levels 1/2), bullet and numbered lists, table, hyperlink and a
    monospace-font code block of the assistant reply are preserved as native DOCX structures.

    AC-7: DOCX preserves assistant formatting.
    """
    chat_page, sample = chat_with_markdown_reply
    dialog = chat_page.open_export_conversation_dialog()
    dialog.select_format(ExportFormat.DOCX)

    exported = dialog.export_and_download(tmp_path)

    content = extract_docx(exported.path)
    dialog.should_include_item(content.heading_1, sample.heading_1, "Heading 1")
    dialog.should_include_item(content.heading_2, sample.heading_2, "Heading 2")
    dialog.should_equal(content.bullets, list(sample.bullet_items), "Bullet list")
    dialog.should_equal(content.numbered, list(sample.numbered_items), "Numbered list")
    dialog.should_include_item(content.tables, sample.table, "Table")
    dialog.should_include_item(content.hyperlinks, sample.link_url, "Hyperlink")
    dialog.should_include_item(
        content.monospace_blocks, sample.code_line, "Monospace code block"
    )


@pytest.mark.chat
@pytest.mark.ui
def test_export_pdf_preserves_assistant_formatting(chat_with_markdown_reply, tmp_path):
    """
    TC-008 (PDF): text-level check that headings, list items, table cells, link text and
    code survive, and that the link is a URI annotation. No layout assertions.

    AC-7: PDF preserves assistant formatting.
    """
    chat_page, sample = chat_with_markdown_reply
    dialog = chat_page.open_export_conversation_dialog()
    dialog.select_format(ExportFormat.PDF)

    exported = dialog.export_and_download(tmp_path)

    dialog.should_contain_all_text(
        extract_text(exported.path, ExportFormat.PDF), sample.pdf_texts
    )
    dialog.should_include_item(
        extract_pdf_links(exported.path), sample.link_url, "PDF hyperlink"
    )


# ---------------------------------------------------------------------------
# TC-009 — cancel / dismiss exports nothing
# ---------------------------------------------------------------------------


@pytest.mark.chat
@pytest.mark.ui
@pytest.mark.parametrize("dismiss_mode", list(DismissMode), ids=lambda m: m.value)
def test_export_dialog_dismiss_triggers_no_export(
    page, navigate_to_new_chat_page, dismiss_mode
):
    """
    TC-009: Closing the dialog via Cancel, Escape or an overlay click after changing options sends no export
    request, starts no download and shows no success toast.

    AC-15: Export behavior is unchanged.
    """
    chat_page = navigate_to_new_chat_page(page)
    dialog = chat_page.open_export_conversation_dialog()
    dialog.start_tracking_exports()
    dialog.select_format(ExportFormat.DOCX)
    dialog.choose_include_tool_outputs(True)

    dialog.dismiss(dismiss_mode)

    dialog.should_be_closed()
    dialog.should_have_sent_export_requests(0)
    dialog.should_have_downloaded_files(0)
    dialog.should_not_show_success_toast()
