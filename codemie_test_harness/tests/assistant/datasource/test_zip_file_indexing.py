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

import zipfile

import pytest
from hamcrest import assert_that, equal_to
from requests import HTTPError

from codemie_test_harness.tests.enums.tools import Default
from codemie_test_harness.tests.test_data.file_test_data import (
    RESPONSE_FOR_ZIP_ARCHIVE_TEST_TXT,
    RESPONSE_FOR_ZIP_ARCHIVE_TEST_YAML,
    ZIP_ARCHIVE_FILE_COUNT,
)
from codemie_test_harness.tests.utils.base_utils import (
    assert_response,
    assert_tool_triggered,
    get_random_name,
)
from codemie_test_harness.tests.utils.constants import FILES_PATH

# Guards shipped in src/codemie/service/datasource/zip_utils.py,
# verified verbatim against the implementation diff:
#   _ZIP_MAX_UNCOMPRESSED_BYTES = 500 * 1024 * 1024   # cumulative, across the whole archive
#   _ZIP_MAX_FILE_COUNT = 1000                         # successfully extracted/passing files
#   _ZIP_MAX_ENTRY_COUNT = 10 * _ZIP_MAX_FILE_COUNT    # raw entries, 10000 (not targeted here)
_ZIP_MAX_UNCOMPRESSED_MB = 500
_ZIP_MAX_FILE_COUNT = 1000


@pytest.fixture
def oversized_zip_path(tmp_path):
    """Build (at setup time, not committed) a ZIP whose single entry's
    cumulative uncompressed content exceeds the 500 MB guard. The written
    content is a repeated byte pattern so the on-disk archive stays tiny
    despite decompressing to >500 MB.
    """
    path = tmp_path / "oversized.zip"
    chunk = b"0" * (10 * 1024 * 1024)
    target_bytes = (_ZIP_MAX_UNCOMPRESSED_MB + 1) * 1024 * 1024

    with (
        zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf,
        zf.open("big.txt", "w") as entry,
    ):
        written = 0
        while written < target_bytes:
            entry.write(chunk)
            written += len(chunk)

    return path


@pytest.fixture
def too_many_files_zip_path(tmp_path):
    """Build (at setup time, not committed) a ZIP with more entries than the
    1000-file guard allows, while staying well under the separate
    10000-raw-entry guard and the 500 MB cumulative-size guard.
    """
    path = tmp_path / "too_many_files.zip"

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for i in range(_ZIP_MAX_FILE_COUNT + 1):
            zf.writestr(f"file_{i}.txt", "x")

    return path


@pytest.mark.smoke
@pytest.mark.datasource
@pytest.mark.file
@pytest.mark.api
@pytest.mark.sanity
def test_create_file_datasource_from_zip_with_mixed_file_types(
    assistant, assistant_utils, datasource_utils, kb_context, similarity_check
):
    """Uploading a ZIP with mixed file types extracts and indexes every file
    inside it, and the extracted content is queryable via the assistant.
    """
    datasource = datasource_utils.create_file_datasource(
        name=get_random_name(),
        description="[Autotest] ZIP archive with mixed file types",
        files=[str(FILES_PATH / "test.zip")],
    )

    assert_that(
        datasource.processing_info.processed_documents_count,
        equal_to(ZIP_ARCHIVE_FILE_COUNT),
    )

    test_assistant = assistant(context=kb_context(datasource))
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant,
        "Quote the exact literal text content of the source file named exactly "
        "'test.txt'. Do not describe or mention any images, photos, or other files.",
        minimal_response=False,
    )
    assert_tool_triggered(Default.SEARCH_KB, triggered_tools)

    similarity_check.check_similarity(
        response,
        RESPONSE_FOR_ZIP_ARCHIVE_TEST_TXT,
        assistant_name=test_assistant.name,
    )


@pytest.mark.datasource
@pytest.mark.file
@pytest.mark.api
def test_add_zip_to_existing_file_datasource_via_update(datasource_utils):
    datasource = datasource_utils.create_file_datasource(
        name=get_random_name(),
        description="[Autotest] Add ZIP to existing file datasource via update",
        files=[str(FILES_PATH / "test.txt")],
    )

    updated_datasource = datasource_utils.update_file_datasource(
        datasource.id,
        files=[str(FILES_PATH / "test.zip")],
    )

    assert_that(
        updated_datasource.processing_info.processed_documents_count,
        equal_to(ZIP_ARCHIVE_FILE_COUNT + 1),
    )


@pytest.mark.datasource
@pytest.mark.file
@pytest.mark.api
def test_create_file_datasource_with_zip_exceeding_max_uncompressed_size(
    datasource_utils, oversized_zip_path
):
    try:
        datasource_utils.create_file_datasource(
            name=get_random_name(),
            description="[Autotest] ZIP exceeding the 500 MB uncompressed limit",
            files=[str(oversized_zip_path)],
        )
        raise AssertionError("There is no error for a ZIP archive that is too large")
    except HTTPError as e:
        assert_response(
            e.response, 422, "Uncompressed content exceeds the 500 MB limit."
        )


@pytest.mark.datasource
@pytest.mark.file
@pytest.mark.api
def test_create_file_datasource_with_zip_exceeding_max_file_count(
    datasource_utils, too_many_files_zip_path
):
    try:
        datasource_utils.create_file_datasource(
            name=get_random_name(),
            description="[Autotest] ZIP exceeding the 1000-file limit",
            files=[str(too_many_files_zip_path)],
        )
        raise AssertionError("There is no error for a ZIP archive with too many files")
    except HTTPError as e:
        assert_response(e.response, 422, "Archives are limited to 1000 files.")


@pytest.mark.datasource
@pytest.mark.file
@pytest.mark.api
def test_assistant_query_returns_content_from_zip_extracted_file(
    assistant, assistant_utils, datasource_utils, kb_context, similarity_check
):
    """A second, distinct file extracted from the same ZIP archive
    (test.yaml, alongside test.txt covered by the mixed-file-types test) is
    also indexed and independently queryable via the assistant.
    """
    datasource = datasource_utils.create_file_datasource(
        name=get_random_name(),
        description="[Autotest] Assistant query sourced from ZIP-extracted file",
        files=[str(FILES_PATH / "test.zip")],
    )

    test_assistant = assistant(context=kb_context(datasource))
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant,
        "What is the YAML configuration in the context about?",
        minimal_response=False,
    )
    assert_tool_triggered(Default.SEARCH_KB, triggered_tools)

    similarity_check.check_similarity(
        response,
        RESPONSE_FOR_ZIP_ARCHIVE_TEST_YAML,
        assistant_name=test_assistant.name,
    )
