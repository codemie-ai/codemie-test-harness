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

"""Test data for attaching conversation files to a Confluence page with the Generic Confluence tool.

The expected messages are the tool's own output strings (codemie-tools ``confluence/tools.py`` and
``base/generated_files.py``), which the tool returns in the chat thoughts.
"""

import json
from dataclasses import dataclass
from typing import Optional

from codemie_test_harness.tests.utils.base_utils import get_random_name

ATTACHMENT_URL = "/rest/api/content/{page_id}/child/attachment"

# Tool output for one attached file (confluence/tools.py, success message).
ATTACHED_MESSAGE = "Successfully attached file '{name}'"
ATTACHED_TO_PAGE = "to page {page_id}"
# generated_files.py, match_attachment: no candidate matches the requested name.
NOT_FOUND_MESSAGE = "File '{name}' was not found. Available files: {available}."
# confluence/tools.py: a matched file has no content.
EMPTY_MESSAGE = "File '{name}' is empty and was not attached."
# confluence/tools.py: neither ``file`` nor ``files`` was given.
NO_FILE_PARAM_MESSAGE = "Name the file(s) to attach in params"
AVAILABLE_FILES = "Available files: {available}."
# confluence/tools.py, _attach_outcome: what a failed multi-file call attached and never tried.
OUTCOME_MESSAGE = "{error} Already attached: {done}. Not attempted: {remaining}."
# generated_files.py, match_attachment: an upload and a generated file share the requested name.
AMBIGUOUS_MESSAGE = "File name '{name}' is ambiguous:"
# HttpResult of a non-upload request (confluence.request), compact layout:
# "HTTP: {method}{url} -> {status}{reason}{body}", with no space between method and URL.
HTTP_RESULT_PREFIX = "HTTP: {method}"


def random_suffix() -> str:
    return get_random_name()[-10:]


def json_report_name(prefix: str = "report") -> str:
    return f"{prefix}-{random_suffix()}.json"


def json_report_content(marker: str) -> str:
    return json.dumps({"marker": marker, "rows": [1, 2, 3]})


def attachment_page_title() -> str:
    return f"{get_random_name()} attachments"


def page_body(page_marker: str) -> str:
    return f"<p>Attachment test page {page_marker}</p>"


def attach_prompt(page_id: str, method: str, params: Optional[dict]) -> str:
    """Ask for exactly one Generic Confluence call with these arguments, no retry, output verbatim."""
    params_text = (
        f"params {json.dumps(params)}" if params else "no params at all (omit params)"
    )
    return (
        "Call the Generic Confluence tool exactly once with method "
        f'"{method}", relative_url "{ATTACHMENT_URL.format(page_id=page_id)}" and '
        f"{params_text}. Use every file name exactly as written. Do not call any "
        "other tool, do not call the tool a second time even if it fails, and reply "
        "with the tool output verbatim."
    )


@dataclass
class EmptyOrMissingVariant:
    """One way of not attaching a file: an empty named file, or no file named at all."""

    variant: str
    params: dict
    expected: list[str]
    other_variant_message: str


EMPTY_FILE_NAME = "empty.json"

EMPTY_OR_MISSING_VARIANTS = [
    EmptyOrMissingVariant(
        variant="empty-file",
        params={"file": EMPTY_FILE_NAME},
        expected=[EMPTY_MESSAGE.format(name=EMPTY_FILE_NAME)],
        other_variant_message=NO_FILE_PARAM_MESSAGE,
    ),
    EmptyOrMissingVariant(
        variant="no-file-param",
        params={},
        expected=[
            NO_FILE_PARAM_MESSAGE,
            AVAILABLE_FILES.format(available=EMPTY_FILE_NAME),
        ],
        other_variant_message=EMPTY_MESSAGE.format(name=EMPTY_FILE_NAME),
    ),
]


@dataclass
class UnmatchedNameVariant:
    """Names to attach where at least one matches no file; ``unknown`` is the one reported."""

    variant: str
    param: str
    include_known: bool
    # A misspelling of the generated file's "report" prefix.
    unknown_prefix: str = "reprot"

    def requested(self, known: str, unknown: str):
        """The value of ``param``: both names for ``files``, the unknown name alone for ``file``."""
        return [known, unknown] if self.include_known else unknown


UNMATCHED_NAME_VARIANTS = [
    UnmatchedNameVariant(variant="single", param="file", include_known=False),
    UnmatchedNameVariant(variant="several", param="files", include_known=True),
]

PARTIAL_FILES = ["a.json", EMPTY_FILE_NAME, "c.json"]

NON_UPLOAD_METHODS = ["GET", "DELETE"]
