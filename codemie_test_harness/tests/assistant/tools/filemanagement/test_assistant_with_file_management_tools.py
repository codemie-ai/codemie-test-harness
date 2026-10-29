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
from hamcrest import assert_that, contains_string, is_not, all_of

from codemie_test_harness.tests.enums.tools import Toolkit, FileManagementTool
from codemie_test_harness.tests.test_data.file_management_tools_test_data import (
    file_management_tools_test_data,
    GENERATE_IMAGE_TOOL_TASK,
    WRITE_FILE_TASK,
    READ_FILE_TOOL_TASK,
    RESPONSE_FOR_READ_FILE_TASK,
    create_file_task,
    insert_to_file_task,
    show_file_task,
    file_editing_tools_test_data,
    show_diff_task,
    code_tools_test_data,
)
from codemie_test_harness.tests.utils.base_utils import (
    get_random_name,
    assert_tool_triggered,
    extract_file_id_from_response,
    download_and_verify_file,
)
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver


@pytest.mark.skipif(
    not EnvironmentResolver.is_localhost(),
    reason="Skipping this tests on non local environments",
)
@pytest.mark.assistant
@pytest.mark.file_management
@pytest.mark.api
@pytest.mark.parametrize(
    "tool_name,prompt,expected_response",
    file_management_tools_test_data,
)
def test_create_assistant_with_file_management_tool(
    filesystem_integration,
    assistant,
    assistant_utils,
    similarity_check,
    tool_name,
    prompt,
    expected_response,
):
    assistant = assistant(
        Toolkit.FILE_MANAGEMENT, tool_name, settings=filesystem_integration
    )

    response, triggered_tools = assistant_utils.ask_assistant(
        assistant, prompt, minimal_response=False
    )

    assert_tool_triggered(tool_name, triggered_tools)
    similarity_check.check_similarity(response, expected_response)


@pytest.mark.assistant
@pytest.mark.file_management
@pytest.mark.api
def test_create_assistant_with_file_management_generate_image_tool(
    filesystem_integration, assistant, assistant_utils, similarity_check
):
    assistant = assistant(
        Toolkit.FILE_MANAGEMENT,
        FileManagementTool.GENERATE_IMAGE,
        settings=filesystem_integration,
    )

    response, triggered_tools = assistant_utils.ask_assistant(
        assistant, GENERATE_IMAGE_TOOL_TASK, minimal_response=False
    )

    assert_tool_triggered(FileManagementTool.GENERATE_IMAGE, triggered_tools)

    assert_that(
        response.lower(),
        all_of(
            contains_string("sandbox:/v1/files"),
            is_not(contains_string("error")),
        ),
    )


@pytest.mark.assistant
@pytest.mark.file_management
@pytest.mark.api
@pytest.mark.skipif(
    not EnvironmentResolver.is_localhost(),
    reason="Skipping this tests on non local environments",
)
def test_create_assistant_with_file_management_read_file_tool(
    filesystem_integration, assistant, assistant_utils, similarity_check
):
    assistant = assistant(
        Toolkit.FILE_MANAGEMENT,
        (FileManagementTool.WRITE_FILE, FileManagementTool.READ_FILE),
        settings=filesystem_integration,
    )

    _, write_triggered_tools = assistant_utils.ask_assistant(
        assistant, WRITE_FILE_TASK, minimal_response=False
    )
    assert_tool_triggered(FileManagementTool.WRITE_FILE, write_triggered_tools)

    response, read_triggered_tools = assistant_utils.ask_assistant(
        assistant, READ_FILE_TOOL_TASK, minimal_response=False
    )
    assert_tool_triggered(FileManagementTool.READ_FILE, read_triggered_tools)

    similarity_check.check_similarity(response, RESPONSE_FOR_READ_FILE_TASK)


@pytest.mark.skip(reason="Tests are flaky, tools work unstable")
@pytest.mark.assistant
@pytest.mark.file_management
@pytest.mark.api
@pytest.mark.parametrize(
    "tool_name,expected_response",
    file_editing_tools_test_data,
    ids=[f"{getattr(row, 'values', row)[0]}" for row in file_editing_tools_test_data],
)
def test_create_assistant_with_file_management_file_editing_tool(
    filesystem_integration,
    assistant,
    assistant_utils,
    similarity_check,
    tool_name,
    expected_response,
):
    assistant = assistant(
        Toolkit.FILE_MANAGEMENT,
        tool_name,
        settings=filesystem_integration,
    )
    file_to_update = f"sum_{get_random_name()}.py"
    _, create_triggered_tools = assistant_utils.ask_assistant(
        assistant, create_file_task(file_to_update), minimal_response=False
    )
    assert_tool_triggered(tool_name, create_triggered_tools)

    _, insert_triggered_tools = assistant_utils.ask_assistant(
        assistant, insert_to_file_task(file_to_update), minimal_response=False
    )
    assert_tool_triggered(tool_name, insert_triggered_tools)

    prompt = (
        show_file_task(file_to_update)
        if tool_name == FileManagementTool.FILESYSTEM_EDITOR
        else show_diff_task(file_to_update)
    )

    response, triggered_tools = assistant_utils.ask_assistant(
        assistant, prompt, minimal_response=False
    )

    assert_tool_triggered(tool_name, triggered_tools)
    similarity_check.check_similarity(response, expected_response)


@pytest.mark.assistant
@pytest.mark.file_management
@pytest.mark.api
@pytest.mark.parametrize(
    "tool_name,prompt,expected_response,expect_file_generation",
    code_tools_test_data,
)
@pytest.mark.skipif(
    EnvironmentResolver.is_sandbox(),
    reason="Skipping this tests on sandbox environments",
)
def test_create_assistant_with_code_tools(
    assistant_utils,
    assistant,
    similarity_check,
    tool_name,
    prompt,
    expected_response,
    expect_file_generation,
    client,
):
    assistant = assistant(
        Toolkit.FILE_MANAGEMENT,
        tool_name,
        system_prompt="Embed generated document in the response",
    )

    response, triggered_tools = assistant_utils.ask_assistant(
        assistant, prompt, minimal_response=False, extract_failed_tools=True
    )

    assert_tool_triggered(tool_name, triggered_tools)

    similarity_check.check_similarity(response, expected_response)

    if expect_file_generation:
        file_id = extract_file_id_from_response(response)
        download_and_verify_file(client, file_id)
