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
Test data for the chat "Agent workspace" browser preview UI tests.

Holds the files seeded into the agent workspace (path, content, preview kind), the
expected preview text for each, the XSS payloads and the labels of the expand control.
"""

from dataclasses import dataclass
from enum import Enum


class PreviewKind(Enum):
    """How the browser renders a file: formatted Markdown or a text (code) block."""

    MARKDOWN = "markdown"
    TEXT = "text"


@dataclass(frozen=True)
class WorkspaceFile:
    """A file seeded into the agent workspace.

    ``expected_text`` is what the text preview must show (defaults to the content);
    ``heading`` is the first Markdown heading, used to tell a Markdown file is rendered.
    """

    path: str
    content: str
    kind: PreviewKind = PreviewKind.TEXT
    expected_text: str | None = None
    heading: str | None = None

    @property
    def shown_text(self) -> str:
        return self.content if self.expected_text is None else self.expected_text


# Live names of the expand control (popup) and of the button that closes the expanded dialog.
EXPAND_LABEL = "Expand"
COLLAPSE_LABEL = "Collapse"
DOWNLOAD_BUTTON_LABEL = "Download selected file"
NO_PREVIEW_HINT_PATTERN = (
    r"Preview is (currently )?available for Markdown.*JSON.*text.*image"
)

VIEWPORT = {"width": 1920, "height": 980}

# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

MARKDOWN_HEADING = "Readable heading"
MARKDOWN_LIST_ITEMS = ("first item", "second item")
MARKDOWN_TABLE_CELL = "cell one"
MARKDOWN_CODE_LINE = 'print("code block line")'
MARKDOWN_SOURCE_MARKERS = ("```", "| col a", "# Readable")
MARKDOWN_CONTENT = (
    f"# {MARKDOWN_HEADING}\n\n"
    "Intro paragraph for the readable preview check.\n\n"
    "- first item\n- second item\n\n"
    "| col a | col b |\n|-------|-------|\n| cell one | cell two |\n\n"
    f"```python\n{MARKDOWN_CODE_LINE}\n```\n"
)

MARKDOWN_FILES = [
    WorkspaceFile(
        "spec.md", MARKDOWN_CONTENT, PreviewKind.MARKDOWN, heading=MARKDOWN_HEADING
    ),
    WorkspaceFile(
        "notes.markdown",
        MARKDOWN_CONTENT,
        PreviewKind.MARKDOWN,
        heading=MARKDOWN_HEADING,
    ),
]

# ---------------------------------------------------------------------------
# Front matter
# ---------------------------------------------------------------------------

FRONT_MATTER_BODY_HEADING = "Body heading"
_FRONT_MATTER_BODY = f"\n\n# {FRONT_MATTER_BODY_HEADING}\n\nBody text."


@dataclass(frozen=True)
class FrontMatterCase:
    """A Markdown file with a leading front matter block and the block text expected."""

    variant: str
    content: str
    block_text: str

    @property
    def file(self) -> WorkspaceFile:
        return WorkspaceFile(
            "front.md",
            self.content,
            PreviewKind.MARKDOWN,
            heading=FRONT_MATTER_BODY_HEADING,
        )


FRONT_MATTER_CASES = [
    FrontMatterCase(
        "with-keys",
        "---\ntitle: Front matter title\nowner: qa" + "\n---" + _FRONT_MATTER_BODY,
        "title: Front matter title\nowner: qa",
    ),
    FrontMatterCase("empty", "---\n---" + _FRONT_MATTER_BODY, ""),
    FrontMatterCase(
        "leading-bom",
        "﻿---\ntitle: BOM title\n---" + _FRONT_MATTER_BODY,
        "title: BOM title",
    ),
]

# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------

JSON_FILES = {
    "valid-compact": WorkspaceFile(
        "data.json",
        '{"b":2,"a":{"nested":[1,2,3]},"name":"sample"}',
        expected_text=(
            '{\n  "b": 2,\n  "a": {\n    "nested": [\n      1,\n      2,\n      3\n'
            '    ]\n  },\n  "name": "sample"\n}'
        ),
    ),
    "unparsable": WorkspaceFile("broken.json", '{"name": "broken", "items": [1, 2,'),
    "large-integer": WorkspaceFile(
        "big.json", '{"id":12345678901234567890,"name":"big"}'
    ),
}

# ---------------------------------------------------------------------------
# Text extensions
# ---------------------------------------------------------------------------

_TEXT_CONTENT = {
    "ts": "export const answer: number = 42;\nfunction greet(name: string): string {\n  return name;\n}",
    "tsx": "export const App = () => <div>hello</div>;",
    "jsx": "const App = () => <span>hello</span>;",
    "yaml": "name: sample\nitems:\n  - one\n  - two",
    "yml": "name: sample\nitems:\n  - one\n  - two",
    "sh": '#!/bin/sh\necho "hello"',
    "css": ".box {\n  color: red;\n}",
    "html": '<div class="box">\n  <p>Hello</p>\n</div>',
    "log": "2026-01-01 10:00:00 INFO started\n2026-01-01 10:00:01 WARN slow",
    "diff": "--- a/file.txt\n+++ b/file.txt\n@@ -1 +1 @@\n-old\n+new",
    "txt": "plain line one\nplain line two",
    "py": "def add(a, b):\n    return a + b",
    "js": "const add = (a, b) => a + b;",
}

TEXT_FILES = [
    WorkspaceFile(f"sample.{extension}", content)
    for extension, content in _TEXT_CONTENT.items()
] + [
    WorkspaceFile("SAMPLE.TXT", _TEXT_CONTENT["txt"]),
    # A dotfile has no extension but is previewed as a text file (text/plain).
    WorkspaceFile(".env", "SAMPLE_KEY=sample"),
]
TEXT_FILE_IDS = list(_TEXT_CONTENT) + ["TXT-upper-case", "dotfile"]

# ---------------------------------------------------------------------------
# No preview
# ---------------------------------------------------------------------------

NO_PREVIEW_FILES = [
    WorkspaceFile("data.xyz", "unknown extension payload"),
    WorkspaceFile("README_noext", "no extension file"),
]
NO_PREVIEW_IDS = ["unknown-extension", "no-extension"]

# ---------------------------------------------------------------------------
# Expand / collapse
# ---------------------------------------------------------------------------

EXPAND_FILES = [
    WorkspaceFile("report.txt", "report line one\nreport line two"),
    MARKDOWN_FILES[0],
]
EXPAND_IDS = ["text", "markdown"]

# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

DOWNLOAD_FILE = WorkspaceFile(
    "download.txt", "downloaded line one\ndownloaded line two"
)

# ---------------------------------------------------------------------------
# Injection payloads
# ---------------------------------------------------------------------------

HTML_FLAG = "__workspacePreviewHtmlRan"
MARKDOWN_FLAG = "__workspacePreviewMarkdownRan"

HTML_PAYLOAD_FILE = WorkspaceFile(
    "page.html",
    f"<html>\n<body>\n<h1>Raw HTML</h1>\n<script>window.{HTML_FLAG} = true</script>\n</body>\n</html>",
)
MARKDOWN_PAYLOAD_FILE = WorkspaceFile(
    "payload.md",
    f"# Payload check\n\n<script>window.{MARKDOWN_FLAG} = true</script>\n\n"
    f'<img src="x" onerror="window.{MARKDOWN_FLAG} = true">',
    PreviewKind.MARKDOWN,
    heading="Payload check",
)
PAYLOAD_CASES = [
    (HTML_PAYLOAD_FILE, HTML_FLAG),
    (MARKDOWN_PAYLOAD_FILE, MARKDOWN_FLAG),
]
PAYLOAD_IDS = ["html-source", "markdown-script"]
