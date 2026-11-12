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
UI Test Suite — Long plain-text tool output shows a preview with a toggle

A tool result of 60 or more non-empty lines is rendered as its first 20 and last 20
lines with a "Show N hidden lines" button; shorter results are shown in full.

Covers:
  TC_002  100 lines: 20 + 20 preview with "Show 60 hidden lines", expand, collapse
  TC_009  59 lines: shown in full, no toggle

The output comes from the code_executor tool of an assistant created through the
assistant fixture, so the number of lines is controlled by the prompt.
"""

import pytest

from codemie_test_harness.tests.enums.tools import FileManagementTool, Toolkit
from codemie_test_harness.tests.ui.test_data.tool_output_preview_test_data import (
    BELOW_THRESHOLD_OUTPUT_PROMPT,
    CODE_EXECUTOR_SYSTEM_PROMPT,
    CODE_EXECUTOR_TOOL_LABEL,
    LONG_OUTPUT_PROMPT,
)

TOOL_RESPONSE_TIMEOUT_MS = 120000


# @case long-tool-output-shows-its_TC_002
@pytest.mark.chat
@pytest.mark.ui
def test_long_tool_output_shows_preview_and_expands_and_collapses(
    page, navigate_to_new_chat_page, assistant
):
    """
    A 100-line code_executor result is previewed as lines 1-20 and 81-100 with a
    'Show 60 hidden lines' button; the button expands to all 100 lines and
    'Collapse' returns to the preview.

    AC-1: first 20 and last 20 lines with a hidden-lines control.
    AC-2: the control expands the output to every line.
    """
    chat_page = navigate_to_new_chat_page(page)
    test_assistant = assistant(
        Toolkit.FILE_MANAGEMENT.value,
        FileManagementTool.CODE_EXECUTOR.value,
        system_prompt=CODE_EXECUTOR_SYSTEM_PROMPT,
    )

    chat_page.send_message(
        message=LONG_OUTPUT_PROMPT.content, assistant_name=test_assistant.name
    )
    chat_page.wait_for_assistant_response(timeout=TOOL_RESPONSE_TIMEOUT_MS)
    chat_page.should_have_tool_used(
        CODE_EXECUTOR_TOOL_LABEL, timeout=TOOL_RESPONSE_TIMEOUT_MS
    )

    tool_output = chat_page.open_tool_output(CODE_EXECUTOR_TOOL_LABEL)
    tool_output.should_show_preview(LONG_OUTPUT_PROMPT.line_count)

    tool_output.expand(LONG_OUTPUT_PROMPT.line_count)
    tool_output.should_show_all_lines_expanded(LONG_OUTPUT_PROMPT.line_count)

    tool_output.collapse()
    tool_output.should_show_preview(LONG_OUTPUT_PROMPT.line_count)


# @case long-tool-output-shows-its_TC_009
@pytest.mark.chat
@pytest.mark.ui
def test_tool_output_below_threshold_is_shown_in_full_without_toggle(
    page, navigate_to_new_chat_page, assistant
):
    """
    A 59-line code_executor result (one below the 60-line threshold) is shown in
    full, with no hidden-lines button.

    AC-4: output below the threshold has no control.
    """
    chat_page = navigate_to_new_chat_page(page)
    test_assistant = assistant(
        Toolkit.FILE_MANAGEMENT.value,
        FileManagementTool.CODE_EXECUTOR.value,
        system_prompt=CODE_EXECUTOR_SYSTEM_PROMPT,
    )

    chat_page.send_message(
        message=BELOW_THRESHOLD_OUTPUT_PROMPT.content,
        assistant_name=test_assistant.name,
    )
    chat_page.wait_for_assistant_response(timeout=TOOL_RESPONSE_TIMEOUT_MS)
    chat_page.should_have_tool_used(
        CODE_EXECUTOR_TOOL_LABEL, timeout=TOOL_RESPONSE_TIMEOUT_MS
    )

    tool_output = chat_page.open_tool_output(CODE_EXECUTOR_TOOL_LABEL)
    tool_output.should_show_all_lines_without_toggle(
        BELOW_THRESHOLD_OUTPUT_PROMPT.line_count
    )
