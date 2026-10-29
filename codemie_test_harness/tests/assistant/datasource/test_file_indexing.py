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

import pytest

from hamcrest import (
    assert_that,
    equal_to,
)
from requests import HTTPError
from _pytest.mark.structures import ParameterSet

from codemie_test_harness.tests.enums.tools import Default
from codemie_test_harness.tests.test_data.file_test_data import (
    file_test_data,
    RESPONSE_FOR_TWO_FILES_INDEXED,
)
from codemie_test_harness.tests.utils.base_utils import (
    get_random_name,
    assert_response,
    assert_tool_triggered,
)
from codemie_test_harness.tests.test_data.index_test_data import index_test_data
from codemie_test_harness.tests.utils.constants import FILES_PATH


def pytest_generate_tests(metafunc):
    if "embeddings_model" in metafunc.fixturenames:
        mark_expr = metafunc.config.option.markexpr
        if "sanity" in mark_expr:
            models = [m for m in index_test_data if "ada" in m.values[0]]
        else:
            models = index_test_data
        metafunc.parametrize("embeddings_model", models)

    # Excluding not supported extensions for now
    files_to_exclude = [
        "test.jpg",
        "test.gif",
        "test.jpeg",
        "test.png",
    ]
    if (
        "file_name" in metafunc.fixturenames
        and "expected_response" in metafunc.fixturenames
    ):
        test_data = []
        for file_data in file_test_data:
            # Handle both pytest.param objects and plain tuples
            if isinstance(file_data, ParameterSet):
                file_name = file_data.values[0]
                expected_response = file_data.values[1]
                existing_marks = list(file_data.marks)
            else:
                file_name = file_data[0]
                expected_response = file_data[1]
                existing_marks = []

            # Build skipif mark
            skipif_mark = pytest.mark.skipif(
                file_name in files_to_exclude,
                reason=f"Skip {file_name} for indexing test. Will be implemented later",
            )

            test_data.append(
                pytest.param(
                    file_name,
                    expected_response,
                    id=f"{file_name}",
                    marks=[*existing_marks, skipif_mark],
                )
            )

        metafunc.parametrize("file_name,expected_response", test_data)


@pytest.mark.datasource
@pytest.mark.file
@pytest.mark.api
def test_create_assistant_with_file_datasource(
    assistant,
    assistant_utils,
    datasource_utils,
    embeddings_model,
    similarity_check,
    kb_context,
    file_name,
    expected_response,
):
    datasource = datasource_utils.create_file_datasource(
        name=get_random_name(),
        description=f"[Autotest] {file_name} with {embeddings_model} embedding model",
        files=[str(FILES_PATH / file_name)],
        embeddings_model=embeddings_model,
    )

    test_assistant = assistant(context=kb_context(datasource))

    prompt = "Show KB context. Return all information available in the context. Query may be 'Show content of the KB'"
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, prompt, minimal_response=False
    )
    assert_tool_triggered(Default.SEARCH_KB, triggered_tools)

    similarity_check.check_similarity(
        response, expected_response, assistant_name=test_assistant.name
    )


@pytest.mark.sanity
@pytest.mark.datasource
@pytest.mark.file
@pytest.mark.api
def test_edit_description_for_file_datasource(datasource_utils):
    initial_description = "[Autotest] Initial CSV datasource description"

    datasource = datasource_utils.create_file_datasource(
        name=get_random_name(),
        description=initial_description,
        files=[str(FILES_PATH / "test.csv")],
    )

    assert_that(datasource.description, equal_to(initial_description))

    updated_description = (
        "[Autotest] Updated CSV datasource description with new details"
    )
    updated_datasource = datasource_utils.update_file_datasource(
        datasource.id, name=datasource.name, description=updated_description
    )
    assert_that(updated_datasource.description, equal_to(updated_description))


@pytest.mark.datasource
@pytest.mark.file
@pytest.mark.api
def test_create_file_datasource_with_large_files(datasource_utils, large_file_fixture):
    try:
        datasource_utils.create_file_datasource(
            name=get_random_name(),
            description="[Autotest] Test datasource with unsupported video-file.mp4",
            files=[str(large_file_fixture)],
        )
        raise AssertionError("There is no error for large files")
    except HTTPError as e:
        assert_response(e.response, 422, "File too large. Maximum size is 100 MB")


@pytest.mark.datasource
@pytest.mark.file
@pytest.mark.api
def test_create_file_datasource_with_big_number_of_files(datasource_utils):
    files = [str(FILES_PATH / "test.txt") for _ in range(11)]

    try:
        datasource_utils.create_file_datasource(
            name=get_random_name(),
            description="[Autotest] Test datasource with unsupported video-file.mp4",
            files=files,
        )
        raise AssertionError("There is no error for large files")
    except HTTPError as e:
        assert_response(e.response, 422, "Too many files. Maximum count is 10")


@pytest.mark.sanity
@pytest.mark.datasource
@pytest.mark.file
@pytest.mark.api
@pytest.mark.smoke
def test_create_file_datasource_with_two_files(
    assistant, assistant_utils, datasource_utils, kb_context, similarity_check
):
    csv_path = FILES_PATH / "test.csv"
    json_path = FILES_PATH / "test.json"

    datasource = datasource_utils.create_file_datasource(
        name=get_random_name(),
        description="[Autotest] Test datasource with two files",
        files=[str(csv_path), str(json_path)],
    )

    test_assistant = assistant(context=kb_context(datasource))

    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant,
        "What types of data do we have available?",
        minimal_response=False,
    )
    assert_tool_triggered(Default.SEARCH_KB, triggered_tools)

    similarity_check.check_similarity(response, RESPONSE_FOR_TWO_FILES_INDEXED)
