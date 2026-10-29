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
Test data for the "Export Conversation" dialog UI tests.

Holds the dialog labels, per-format metadata, expected toast/filename patterns, the
markdown sample used to verify DOCX/PDF formatting and the parametrisation cases.
"""

import uuid
from dataclasses import dataclass
from enum import Enum

DIALOG_TITLE = "Export Conversation"
FORMAT_HEADING = "Format"
INCLUDE_TOOL_OUTPUTS_LABEL = "Include tool outputs"
JSON_TOOL_OUTPUTS_HINT = "Tool outputs are always included in JSON exports."
WITH_TOOL_OUTPUTS_SUFFIX = "_with_tool_outputs"

# Heading of the tool-output section (thought author) rendered in "with tool outputs" exports
TOOL_OUTPUTS_SECTION_HEADING = "Codemie Thoughts"


class ExportFormat(Enum):
    """Export formats offered by the dialog: (label, description, file extension)."""

    JSON = (
        "JSON",
        "Raw conversation data, best for backup or re-importing elsewhere.",
        "json",
    )
    DOCX = (
        "DOCX",
        "Formatted document, best for sharing or editing in Word.",
        "docx",
    )
    PDF = (
        "PDF",
        "Formatted document, best for sharing or printing.",
        "pdf",
    )

    @property
    def label(self) -> str:
        return self.value[0]

    @property
    def description(self) -> str:
        return self.value[1]

    @property
    def extension(self) -> str:
        return self.value[2]


DOCUMENT_FORMATS = [ExportFormat.DOCX, ExportFormat.PDF]


def success_toast_text(export_format: ExportFormat, with_tool_outputs: bool) -> str:
    """Success toast shown after an export completes."""
    qualifier = " (with tool outputs)" if with_tool_outputs else ""
    return (
        f"Your conversation has been successfully exported as "
        f"{export_format.label}{qualifier}. "
        f"The file is now ready in your downloads folder."
    )


def filename_suffix(export_format: ExportFormat, with_tool_outputs: bool) -> str:
    """Expected end of the downloaded file name."""
    qualifier = WITH_TOOL_OUTPUTS_SUFFIX if with_tool_outputs else ""
    return f"{qualifier}.{export_format.extension}"


@dataclass
class ExportConversationData:
    """Unique tokens used to recognise the conversation content inside exported files."""

    user_prompt: str
    prompt_token: str
    answer_token: str
    system_prompt_addition: str


def create_export_conversation_data() -> ExportConversationData:
    """Conversation that triggers the Wikipedia tool and ends its answer with a unique token."""
    suffix = uuid.uuid4().hex[:10]
    answer_token = f"EXPORTANSWER{suffix}"
    prompt_token = f"EXPORTPROMPT{suffix}"
    return ExportConversationData(
        prompt_token=prompt_token,
        user_prompt=(
            f"{prompt_token}: You must call the Wikipedia tool right now. "
            "Search Wikipedia for 'Python programming language'."
        ),
        answer_token=answer_token,
        system_prompt_addition=(
            f"\nAlways finish your final answer with the exact word {answer_token}."
        ),
    )


@dataclass
class MarkdownSample:
    """Markdown the assistant replies with, and the exported content expected for it."""

    markdown: str
    heading_1: str = "Export Heading One"
    heading_2: str = "Export Heading Two"
    bullet_items: tuple = ("Bullet alpha", "Bullet beta")
    numbered_items: tuple = ("Numbered first", "Numbered second")
    table_header: tuple = ("Column A", "Column B")
    table_row: tuple = ("cell_a1", "cell_b1")
    link_text: str = "Export sample link"
    link_url: str = "https://example.com/export-sample"
    code_line: str = 'print("export_code_sample")'
    code_token: str = "export_code_sample"

    @property
    def table(self) -> list:
        """Expected table rows: header row followed by the data row."""
        return [list(self.table_header), list(self.table_row)]

    @property
    def pdf_texts(self) -> list:
        """Every text fragment that must survive in the extracted PDF text."""
        return [
            self.heading_1,
            self.heading_2,
            *self.bullet_items,
            *self.numbered_items,
            *self.table_header,
            *self.table_row,
            self.link_text,
            self.code_token,
        ]


def create_markdown_sample() -> MarkdownSample:
    """Rich markdown: headings, bullet/numbered lists, table, link and fenced code block."""
    markdown = (
        "# Export Heading One\n\n"
        "## Export Heading Two\n\n"
        "- Bullet alpha\n- Bullet beta\n\n"
        "1. Numbered first\n2. Numbered second\n\n"
        "| Column A | Column B |\n|----------|----------|\n| cell_a1 | cell_b1 |\n\n"
        "[Export sample link](https://example.com/export-sample)\n\n"
        '```python\nprint("export_code_sample")\n```\n'
    )
    return MarkdownSample(markdown=markdown)


MARKDOWN_SYSTEM_PROMPT_TEMPLATE = (
    "Reply to every message with EXACTLY the following markdown, character for "
    "character, with no extra text, no preamble, and without wrapping it in a "
    "code fence:\n\n{markdown}"
)
MARKDOWN_USER_PROMPT = "Send the markdown sample."


class DismissMode(Enum):
    """Ways to dismiss the dialog without exporting."""

    CANCEL_BUTTON = "cancel button"
    ESCAPE_KEY = "escape key"
    OVERLAY_CLICK = "overlay click"


@dataclass
class ExportRequestCase:
    """Dialog interaction and the export request it must produce."""

    first_format: ExportFormat
    check_tool_outputs: bool
    final_format: ExportFormat
    expected_include_tool_outputs: bool


EXPORT_REQUEST_CASES = [
    ExportRequestCase(ExportFormat.JSON, False, ExportFormat.JSON, False),
    ExportRequestCase(ExportFormat.DOCX, False, ExportFormat.DOCX, False),
    ExportRequestCase(ExportFormat.PDF, True, ExportFormat.PDF, True),
    ExportRequestCase(ExportFormat.DOCX, True, ExportFormat.JSON, False),
]
