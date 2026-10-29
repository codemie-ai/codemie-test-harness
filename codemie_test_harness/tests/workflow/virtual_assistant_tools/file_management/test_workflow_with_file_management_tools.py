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

from codemie_test_harness.tests.enums.tools import FileManagementTool
from codemie_test_harness.tests.test_data.file_management_tools_test_data import (
    file_management_tools_test_data,
    GENERATE_IMAGE_TOOL_TASK,
    WRITE_FILE_TASK,
    READ_FILE_TOOL_TASK,
    RESPONSE_FOR_READ_FILE_TASK,
    create_file_task,
    insert_to_file_task,
    show_file_task,
    show_diff_task,
    RESPONSE_FOR_DIFF_UPDATE,
    RESPONSE_FOR_FILE_EDITOR,
    code_tools_test_data,
)
from codemie_test_harness.tests.utils.base_utils import (
    get_random_name,
    assert_tool_triggered,
    extract_file_id_from_response,
    download_and_verify_file,
)
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver


@pytest.mark.workflow
@pytest.mark.virtual_workflow
@pytest.mark.file_management
@pytest.mark.api
@pytest.mark.parametrize(
    "tool_name, prompt, expected_response",
    file_management_tools_test_data,
)
@pytest.mark.skipif(
    not EnvironmentResolver.is_localhost(),
    reason="Skipping this tests on non local environments",
)
def test_workflow_with_file_management_tools(
    workflow_with_virtual_assistant,
    filesystem_integration,
    workflow_utils,
    similarity_check,
    tool_name,
    prompt,
    expected_response,
):
    assistant_and_state_name = get_random_name()

    test_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name,
        tool_name,
        integration=filesystem_integration,
        task=prompt,
    )
    response = workflow_utils.execute_workflow(
        test_workflow.id, assistant_and_state_name
    )
    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        test_workflow
    )
    assert_tool_triggered(tool_name, triggered_tools)

    similarity_check.check_similarity(response, expected_response)


@pytest.mark.workflow
@pytest.mark.virtual_workflow
@pytest.mark.file_management
@pytest.mark.api
def test_workflow_with_generate_image_tool(
    workflow_with_virtual_assistant, filesystem_integration, workflow_utils
):
    assistant_and_state_name = get_random_name()
    test_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name,
        FileManagementTool.GENERATE_IMAGE,
        integration=filesystem_integration,
        task=GENERATE_IMAGE_TOOL_TASK,
    )
    response = workflow_utils.execute_workflow(
        test_workflow.id, assistant_and_state_name
    )
    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        test_workflow
    )
    assert_tool_triggered(FileManagementTool.GENERATE_IMAGE, triggered_tools)

    assert_that(
        response.lower(),
        all_of(
            contains_string("sandbox:/v1/files"),
            is_not(contains_string("error")),
        ),
    )


@pytest.mark.workflow
@pytest.mark.virtual_workflow
@pytest.mark.file_management
@pytest.mark.api
@pytest.mark.skipif(
    not EnvironmentResolver.is_localhost(),
    reason="Skipping this tests on non local environments",
)
def test_workflow_with_read_file_tool(
    workflow_with_virtual_assistant,
    filesystem_integration,
    workflow_utils,
    similarity_check,
):
    assistant_and_state_name = get_random_name()
    # Step 1: Write file
    write_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name,
        FileManagementTool.WRITE_FILE,
        integration=filesystem_integration,
        task=WRITE_FILE_TASK,
    )
    workflow_utils.execute_workflow(
        write_workflow.id,
        assistant_and_state_name,
    )
    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        write_workflow
    )
    assert_tool_triggered(FileManagementTool.WRITE_FILE, triggered_tools)

    # Step 2: Read file
    read_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name,
        FileManagementTool.READ_FILE,
        integration=filesystem_integration,
        task=READ_FILE_TOOL_TASK,
    )
    response = workflow_utils.execute_workflow(
        read_workflow.id,
        assistant_and_state_name,
    )
    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        read_workflow
    )
    assert_tool_triggered(FileManagementTool.READ_FILE, triggered_tools)
    similarity_check.check_similarity(response, RESPONSE_FOR_READ_FILE_TASK)


@pytest.mark.workflow
@pytest.mark.virtual_workflow
@pytest.mark.file_management
@pytest.mark.skip(reason="Test are flaky, tools work unstable")
@pytest.mark.api
def test_workflow_with_file_editing_tool(
    workflow_with_virtual_assistant,
    workflow_utils,
    filesystem_integration,
    similarity_check,
):
    assistant_and_state_name = get_random_name()
    file_to_update = f"sum_{get_random_name()}.py"
    tool_names = (FileManagementTool.WRITE_FILE, FileManagementTool.DIFF_UPDATE)

    # Create the file
    create_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name,
        tool_names,
        integration=filesystem_integration,
        task=create_file_task(file_to_update),
    )
    workflow_utils.execute_workflow(
        create_workflow.id,
        assistant_and_state_name,
    )
    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        create_workflow
    )
    assert_tool_triggered(FileManagementTool.WRITE_FILE, triggered_tools)

    # Insert to the file
    insert_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name,
        tool_names,
        integration=filesystem_integration,
        task=insert_to_file_task(file_to_update),
    )
    workflow_utils.execute_workflow(
        insert_workflow.id,
        assistant_and_state_name,
    )
    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        insert_workflow
    )
    assert_tool_triggered(FileManagementTool.DIFF_UPDATE, triggered_tools)

    # Show the diff
    diff_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name,
        tool_names,
        integration=filesystem_integration,
        task=show_diff_task(file_to_update),
    )
    response = workflow_utils.execute_workflow(
        diff_workflow.id,
        assistant_and_state_name,
    )
    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        diff_workflow
    )
    assert_tool_triggered(FileManagementTool.DIFF_UPDATE, triggered_tools)

    similarity_check.check_similarity(response, RESPONSE_FOR_DIFF_UPDATE)


@pytest.mark.workflow
@pytest.mark.virtual_workflow
@pytest.mark.file_management
@pytest.mark.skip(reason="Test are flaky, tools work unstable")
@pytest.mark.api
def test_workflow_with_filesystem_tool(
    workflow_with_virtual_assistant,
    workflow_utils,
    filesystem_integration,
    similarity_check,
):
    assistant_and_state_name = get_random_name()
    file_to_update = f"sum_{get_random_name()}.py"

    # Create the file
    create_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name,
        FileManagementTool.FILESYSTEM_EDITOR,
        integration=filesystem_integration,
        task=create_file_task(file_to_update),
    )
    workflow_utils.execute_workflow(
        create_workflow.id,
        assistant_and_state_name,
    )
    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        create_workflow
    )
    assert_tool_triggered(FileManagementTool.FILESYSTEM_EDITOR, triggered_tools)

    # Insert to the file
    insert_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name,
        FileManagementTool.FILESYSTEM_EDITOR,
        integration=filesystem_integration,
        task=insert_to_file_task(file_to_update),
    )
    workflow_utils.execute_workflow(
        insert_workflow.id,
        assistant_and_state_name,
    )
    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        insert_workflow
    )
    assert_tool_triggered(FileManagementTool.FILESYSTEM_EDITOR, triggered_tools)

    # Show the file content
    show_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name,
        FileManagementTool.FILESYSTEM_EDITOR,
        integration=filesystem_integration,
        task=show_file_task(file_to_update),
    )
    response = workflow_utils.execute_workflow(
        show_workflow.id,
        assistant_and_state_name,
    )
    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        show_workflow
    )
    assert_tool_triggered(FileManagementTool.FILESYSTEM_EDITOR, triggered_tools)

    similarity_check.check_similarity(response, RESPONSE_FOR_FILE_EDITOR)


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
def test_workflow_with_code_tools(
    workflow_with_virtual_assistant,
    workflow_utils,
    assistant,
    similarity_check,
    tool_name,
    prompt,
    expected_response,
    expect_file_generation,
    client,
):
    assistant_and_state_name = get_random_name()

    test_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name,
        tool_name,
        task=prompt,
        system_prompt="Embed generated document in the response",
    )
    response = workflow_utils.execute_workflow(
        test_workflow.id, assistant_and_state_name
    )
    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        test_workflow
    )
    assert_tool_triggered(tool_name, triggered_tools)

    similarity_check.check_similarity(response, expected_response)

    if expect_file_generation:
        file_id = extract_file_id_from_response(response)
        download_and_verify_file(client, file_id)
