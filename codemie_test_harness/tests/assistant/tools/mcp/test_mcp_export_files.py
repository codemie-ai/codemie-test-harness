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

"""API tests for files an MCP server exports as downloadable chat artifacts.

An opted-in stdio MCP server (CODEMIE_EXPORT_FILES=true in its own env) lets the model
export files it wrote with `codemie_export_files`. The back end stores each file in the
conversation and links it as `sandbox:/v1/files/<token>`; GET /v1/files/<token> serves it.

The filesystem MCP server writes text only, so it covers csv and json. A shell MCP server
(cli-mcp-server running python3 with the standard library) writes the binary types xlsx,
zip and pdf.
"""

import base64
import io
import re
import zipfile

import pytest
from hamcrest import (
    assert_that,
    contains_inanyorder,
    equal_to,
    has_length,
    less_than,
)
from requests import HTTPError

from codemie_test_harness.tests.test_data.mcp_export_files_test_data import (
    EXPORT_WITH_LINKS_SYSTEM_PROMPT,
    FILES_WRITTEN,
    MAX_DELIVERED_FILES,
    SANDBOX_FILE_LINK_PREFIX,
    SHELL_MCP_SERVER,
    build_csv_file,
    build_json_file,
    build_many_files_export,
    build_pdf_file,
    build_xlsx_file,
    build_zip_file,
    export_prompt,
    many_files_export_prompt,
    shell_export_prompt,
)
from codemie_test_harness.tests.test_data.mcp_server_test_data import (
    FILESYSTEM_MCP_SERVER,
)

_FILE_LINK_PATTERN = re.compile(
    re.escape(SANDBOX_FILE_LINK_PREFIX) + r"([A-Za-z0-9+/=]+)"
)


def _file_tokens(response: str) -> set:
    """Tokens of the distinct sandbox file links in an answer."""
    return set(_FILE_LINK_PATTERN.findall(response))


def _decode_token(token: str) -> list:
    """Split a file token into its parts.

    The token is base64 over `<length>~<part>` repeated; the back end builds it as
    [mime_type, owner, name] (StringSerializer in the product's file object).
    """
    raw = base64.b64decode(token).decode("utf-8")
    parts = []
    while raw:
        length, _, rest = raw.partition("~")
        parts.append(rest[: int(length)])
        raw = rest[int(length) :]
    return parts


def _lines(text: str) -> list:
    return [line.strip() for line in text.strip().splitlines()]


def _zip_members(data: bytes) -> list:
    """Member names of a zip container; empty when the bytes are not one."""
    if not zipfile.is_zipfile(io.BytesIO(data)):
        return []
    return zipfile.ZipFile(io.BytesIO(data)).namelist()


def _last_assistant_file_names(conversation_utils, assistant_id: str) -> list:
    """File names the saved assistant message lists for the only turn of a chat."""
    conversations = conversation_utils.get_conversation_by_assistant_id(assistant_id)
    history = conversation_utils.get_conversation_by_id(conversations[0].id).history
    return history[-1].fileNames


# @case downloadable-chat-artifacts-mcp-files_TC_001
@pytest.mark.assistant
@pytest.mark.mcp
@pytest.mark.api
@pytest.mark.parametrize(
    "build_file", [build_csv_file, build_json_file], ids=["csv", "json"]
)
def test_exported_mcp_file_is_downloadable_by_token(
    client, assistant, assistant_utils, conversation_utils, build_file
):
    """An opted-in server's exported file is linked once in the answer and the link
    serves the bytes the server wrote, stored under the file's MIME type.

    AC-1: exported file is delivered as a sandbox link; AC-5: csv; AC-6: json.
    """
    file = build_file()
    exporter = assistant(
        mcp_server=FILESYSTEM_MCP_SERVER,
        system_prompt=EXPORT_WITH_LINKS_SYSTEM_PROMPT,
    )

    response = assistant_utils.ask_assistant(exporter, export_prompt(file))

    tokens = _file_tokens(response)
    assert_that(
        tokens, has_length(1), f"Expected one sandbox link in the answer: {response}"
    )
    token = tokens.pop()
    assert_that(
        _decode_token(token)[0],
        equal_to(file.mime_type),
        "The stored file must carry the MIME type of its extension",
    )
    downloaded = client.files.get_file(token).decode("utf-8")
    assert_that(
        _lines(downloaded),
        equal_to(_lines(file.content)),
        "The download must equal the content the server wrote",
    )
    assert_that(
        _last_assistant_file_names(conversation_utils, exporter.id),
        has_length(1),
        "The assistant message must list the exported file",
    )


# @case downloadable-chat-artifacts-mcp-files_TC_001
@pytest.mark.assistant
@pytest.mark.mcp
@pytest.mark.api
@pytest.mark.parametrize(
    "build_file",
    [build_xlsx_file, build_zip_file, build_pdf_file],
    ids=["xlsx", "zip", "pdf"],
)
def test_exported_binary_mcp_file_is_downloadable_by_token(
    client, assistant, assistant_utils, conversation_utils, build_file
):
    """A binary file a shell MCP server wrote is linked once in the answer and the
    link serves it with the signature of its type: the zip family starts with PK and
    holds its members (an xlsx holds xl/workbook.xml), a pdf starts with %PDF- and
    holds the bytes the script wrote.

    AC-1: exported file is delivered as a sandbox link; AC-5: xlsx and zip; AC-6: pdf.
    """
    file = build_file()
    exporter = assistant(
        mcp_server=SHELL_MCP_SERVER,
        system_prompt=EXPORT_WITH_LINKS_SYSTEM_PROMPT,
    )

    response = assistant_utils.ask_assistant(exporter, shell_export_prompt(file))

    tokens = _file_tokens(response)
    assert_that(
        tokens, has_length(1), f"Expected one sandbox link in the answer: {response}"
    )
    token = tokens.pop()
    assert_that(
        _decode_token(token)[0],
        equal_to(file.mime_type),
        "The stored file must carry the MIME type of its extension",
    )
    downloaded = client.files.get_file(token)
    assert_that(
        downloaded.startswith(file.signature),
        equal_to(True),
        f"The download must start with {file.signature!r}, got {downloaded[:8]!r}",
    )
    assert_that(
        file.contains in downloaded,
        equal_to(True),
        f"The download must hold {file.contains!r}",
    )
    assert_that(
        _zip_members(downloaded),
        contains_inanyorder(*file.zip_members),
        "The download must hold the zip members the script wrote",
    )
    assert_that(
        _last_assistant_file_names(conversation_utils, exporter.id),
        has_length(1),
        "The assistant message must list the exported file",
    )


# @case downloadable-chat-artifacts-mcp-files_TC_008
@pytest.mark.assistant
@pytest.mark.mcp
@pytest.mark.api
def test_export_of_more_files_than_the_cap_delivers_only_the_cap(
    assistant, assistant_utils, conversation_utils
):
    """One export call that names one file more than the cap delivers only the cap: the
    assistant message lists 20 files and the answer does not link all of them.

    The wording of the note for the file left out is model-driven and not asserted.
    Only the file-count cap is in scope, not the 50 MiB cap.
    """
    batch = build_many_files_export()
    exporter = assistant(
        mcp_server=SHELL_MCP_SERVER,
        system_prompt=EXPORT_WITH_LINKS_SYSTEM_PROMPT,
    )

    response = assistant_utils.ask_assistant(exporter, many_files_export_prompt(batch))

    assert_that(
        _last_assistant_file_names(conversation_utils, exporter.id),
        has_length(MAX_DELIVERED_FILES),
        f"Only {MAX_DELIVERED_FILES} of the {FILES_WRITTEN} files may be delivered",
    )
    assert_that(
        len(_file_tokens(response)),
        less_than(FILES_WRITTEN),
        "The answer must not link every file that was written",
    )


# @case downloadable-chat-artifacts-mcp-files_TC_007
@pytest.mark.assistant
@pytest.mark.mcp
@pytest.mark.api
def test_exported_mcp_file_is_not_downloadable_by_another_user(
    client, assistant, assistant_utils, second_platform_user
):
    """A file published in one user's conversation answers 404 to another user, while
    its owner downloads the content the server wrote.

    AC-6: the stored artifact is isolated per user.
    """
    exporter = assistant(
        mcp_server=FILESYSTEM_MCP_SERVER,
        system_prompt=EXPORT_WITH_LINKS_SYSTEM_PROMPT,
    )
    file = build_csv_file()
    response = assistant_utils.ask_assistant(exporter, export_prompt(file))
    tokens = _file_tokens(response)
    assert_that(
        tokens, has_length(1), f"Expected one sandbox link in the answer: {response}"
    )
    token = tokens.pop()
    assert_that(
        _lines(client.files.get_file(token).decode("utf-8")),
        equal_to(_lines(file.content)),
        "The owner must download the content the server wrote",
    )

    with pytest.raises(HTTPError) as exc_info:
        second_platform_user.client.files.get_file(token)

    assert_that(
        exc_info.value.response.status_code,
        equal_to(404),
        "Another user's download of the artifact must be rejected with 404",
    )
