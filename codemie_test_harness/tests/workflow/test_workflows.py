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

import json
import uuid

import pytest
from datetime import datetime
from hamcrest import (
    assert_that,
    equal_to,
    has_length,
    less_than_or_equal_to,
    all_of,
    instance_of,
    has_property,
    is_not,
    none,
    is_in,
)

from codemie_sdk.models.workflow import Workflow, WorkflowMode
from codemie_test_harness.tests.assistant.test_assistants import (
    system_prompt_for_chatting_with_files,
)
from codemie_test_harness.tests.enums.tools import Default
from codemie_test_harness.tests.test_data.assistant_test_data import (
    EXCEL_TOOL_TEST_DATA,
    DOCX_TOOL_TEST_DATA,
)
from codemie_test_harness.tests.test_data.file_test_data import file_test_data
from codemie_test_harness.tests.test_data.output_schema_test_data import output_schema
from codemie_test_harness.tests.utils.base_utils import (
    get_random_name,
    assert_tool_triggered,
)
from codemie_test_harness.tests.utils.constants import FILES_PATH
from codemie_test_harness.tests.utils.yaml_utils import AssistantModel, StateModel


@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.smoke
def test_list_workflows(search_utils):
    # Test pagination with per_page=2
    workflows = search_utils.list_workflows(per_page=2)
    assert_that(workflows, has_length(equal_to(2)))

    # Verify the first workflow has all expected properties
    assert_that(len(workflows), is_not(equal_to(0)), "Expected at least one workflow")

    first_workflow = workflows[0]

    # Validate all workflow properties
    assert_that(
        first_workflow,
        all_of(
            instance_of(Workflow),
            # Core workflow properties
            has_property("id", is_not(none())),
            has_property("project", is_not(none())),
            has_property("name", is_not(none())),
            has_property("description"),
            has_property("yaml_config"),
            has_property("mode", is_not(none())),
            has_property("shared", instance_of(bool)),
            has_property("icon_url"),
            has_property("created_date"),
            has_property("update_date"),
            has_property("created_by"),
        ),
        "First workflow should have all expected properties",
    )

    # Validate mode is one of the valid WorkflowMode values
    assert_that(
        first_workflow.mode,
        is_in([WorkflowMode.SEQUENTIAL, WorkflowMode.AUTONOMOUS]),
        f"Workflow mode should be either SEQUENTIAL or AUTONOMOUS, got {first_workflow.mode}",
    )

    # Validate created_date is a datetime instance if present
    if first_workflow.created_date is not None:
        assert_that(
            first_workflow.created_date,
            instance_of(datetime),
            "created_date should be a datetime instance",
        )

    # Validate update_date is a datetime instance if present
    if first_workflow.update_date is not None:
        assert_that(
            first_workflow.update_date,
            instance_of(datetime),
            "update_date should be a datetime instance",
        )

    # Test pagination with page parameter
    workflows_page2 = search_utils.list_workflows(per_page=2, page=1)
    assert_that(workflows_page2, has_length(less_than_or_equal_to(2)))

    # Verify properties on second page as well
    if len(workflows_page2) > 0:
        first_workflow_page2 = workflows_page2[0]

        # Validate all workflow properties on page 2
        assert_that(
            first_workflow_page2,
            all_of(
                instance_of(Workflow),
                # Core workflow properties
                has_property("id", is_not(none())),
                has_property("project", is_not(none())),
                has_property("name", is_not(none())),
                has_property("description"),
                has_property("yaml_config"),
                has_property("mode", is_not(none())),
                has_property("shared", instance_of(bool)),
                has_property("icon_url"),
                has_property("created_date"),
                has_property("update_date"),
                has_property("created_by"),
            ),
            "Workflow on page 2 should have all expected properties",
        )

        # Validate mode for page 2 workflow
        assert_that(
            first_workflow_page2.mode,
            is_in([WorkflowMode.SEQUENTIAL, WorkflowMode.AUTONOMOUS]),
            f"Workflow mode should be either SEQUENTIAL or AUTONOMOUS, got {first_workflow_page2.mode}",
        )

        # Validate dates on page 2 workflow
        if first_workflow_page2.created_date is not None:
            assert_that(
                first_workflow_page2.created_date,
                instance_of(datetime),
                "created_date should be a datetime instance",
            )

        if first_workflow_page2.update_date is not None:
            assert_that(
                first_workflow_page2.update_date,
                instance_of(datetime),
                "update_date should be a datetime instance",
            )


@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.smoke
def test_workflow_with_json_output_schema(default_llm, workflow, workflow_utils):
    assistant_and_state_name = get_random_name()

    assistant = AssistantModel(
        id=assistant_and_state_name,
        model=default_llm.base_name,
        system_prompt="You are a helpful assistant.",
    )

    state = StateModel(
        id=assistant_and_state_name,
        assistant_id=assistant_and_state_name,
        output_schema=json.dumps(output_schema),
    )

    workflow = workflow(
        workflow_name=get_random_name(),
        assistant_model=assistant,
        state_model=state,
    )

    response = workflow_utils.execute_workflow(
        workflow.id, assistant_and_state_name, user_input="1+1?"
    )

    assert_that(json.loads(response)["results"][0], equal_to(2))


@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.file
@pytest.mark.parametrize(
    "file_name, expected_response, expected_tool",
    file_test_data,
    ids=[f"{getattr(row, 'values', row)[0]}" for row in file_test_data],
)
def test_workflow_with_user_input_and_file_attachment(
    workflow_with_virtual_assistant,
    workflow_utils,
    assistant_utils,
    file_name,
    expected_response,
    expected_tool,
    similarity_check,
):
    """
    Test workflow execution with user input that includes file attachment.

    This test demonstrates how workflows can handle file attachments by:
    1. Uploading a file
    2. Creating a workflow with file processing capabilities
    3. Executing the workflow with user input that references the uploaded file
    4. Verifying that file processing tools are triggered
    """
    assistant_and_state_name = get_random_name()

    # Upload file to get file URL
    upload_response = workflow_utils.upload_file(FILES_PATH / file_name)
    file_url = upload_response.files[0].file_url

    # Create workflow with virtual assistant that has file analysis capabilities
    # Note: File analysis tools are automatically available when files are processed
    task = (
        f"What is the content/text of the {file_name}. Show information from ALL pages. "
        "For PDF use 'Text' for query. If provided file is CSV then run csv tool and show first 5 rows."
        "For images explain what you see on it."
        "For excel show data from the sheet with name 'Sheet1'. Fow .xlsb show data from all sheets including hidden"
    )

    workflow_instance = workflow_with_virtual_assistant(
        assistant_and_state_name=assistant_and_state_name,
        system_prompt=system_prompt_for_chatting_with_files,
        task=task,
    )

    # Prepare user input that includes file reference
    user_input = "Please provide a summary about file content."

    # Execute workflow
    response = workflow_utils.execute_workflow(
        workflow_instance.id,
        assistant_and_state_name,
        user_input=user_input,
        file_name=file_url,
    )

    # Extract triggered tools from execution
    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        workflow_instance
    )

    assert_tool_triggered(expected_tool, triggered_tools)
    similarity_check.check_similarity(response, expected_response)


@pytest.mark.workflow
@pytest.mark.file
@pytest.mark.api
@pytest.mark.parametrize("file_name, prompt, expected_response", EXCEL_TOOL_TEST_DATA)
def test_workflow_excel_tool_extended_functionality(
    workflow_with_virtual_assistant,
    workflow_utils,
    similarity_check,
    file_name,
    prompt,
    expected_response,
):
    """
    Test extended Excel tool functionality with various scenarios in workflow.

    This test covers:
    - Data extraction from visible sheets only
    - All data including hidden sheets
    - Sheet name listing functionality
    - File statistics and structure analysis
    - Single sheet extraction by index and name
    - Data cleaning and normalization
    - Hidden sheet visibility control
    - Column structure and data type analysis
    - Tabular structure normalization
    - Multi-sheet comprehensive analysis

    """
    assistant_and_state_name = get_random_name()

    # Upload file to get file URL
    upload_response = workflow_utils.upload_file(FILES_PATH / file_name)
    file_url = upload_response.files[0].file_url

    # Create workflow with virtual assistant that has Excel file processing capabilities
    system_prompt = "You have all required information in initial prompt. Do not ask additional questions and proceed with request."

    workflow_instance = workflow_with_virtual_assistant(
        assistant_and_state_name=assistant_and_state_name,
        system_prompt=system_prompt,
        task=prompt,
    )

    # Execute workflow with the file URL
    response = workflow_utils.execute_workflow(
        workflow_instance.id,
        assistant_and_state_name,
        user_input="Process the uploaded Excel file as requested.",
        file_name=file_url,
    )

    # Extract triggered tools from execution
    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        workflow_instance
    )

    assert_tool_triggered(Default.EXCEL_TOOL, triggered_tools)
    similarity_check.check_similarity(response, expected_response)


@pytest.mark.workflow
@pytest.mark.file
@pytest.mark.api
@pytest.mark.parametrize("prompt, expected_response", DOCX_TOOL_TEST_DATA)
def test_workflow_docx_tool_extended_functionality(
    workflow_with_virtual_assistant,
    workflow_utils,
    similarity_check,
    prompt,
    expected_response,
):
    """
    Test extended Docx tool functionality with various scenarios in workflow.

    This test covers:
    - Extract plain text using 'text' query
    - Extract text with metadata using 'text_with_metadata' query
    - Extract document structure using 'structure_only' query
    - Extract tables using 'table_extraction' query
    - Generate summary using 'summary' query
    - Perform analysis with custom instructions using 'analyze' query
    - Process specific pages '1-3' using pages parameter
    - Process specific pages '1,5,10' using pages parameter
    - Extract images using 'image_extraction' query
    - Extract text with OCR from images using 'text_with_images' query

    """
    assistant_and_state_name = get_random_name()

    # Upload file to get file URL
    upload_response = workflow_utils.upload_file(FILES_PATH / "test_extended.docx")
    file_url = upload_response.files[0].file_url

    # Create workflow with virtual assistant that has DOCX file processing capabilities
    system_prompt = """You are a helpful assistant that can analyze and process DOCX files.
                       You have all required information in initial prompt.
                       Do not ask additional questions and proceed with request."""

    workflow_instance = workflow_with_virtual_assistant(
        assistant_and_state_name=assistant_and_state_name,
        system_prompt=system_prompt,
        task=prompt,
    )

    # Execute workflow with the file URL
    response = workflow_utils.execute_workflow(
        workflow_instance.id,
        assistant_and_state_name,
        user_input="Process the uploaded DOCX file as requested.",
        file_name=file_url,
    )

    # Extract triggered tools from execution
    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        workflow_instance
    )

    assert_tool_triggered(Default.DOCX_TOOL, triggered_tools)
    similarity_check.check_similarity(response, expected_response)


@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.smoke
def test_workflow_execution_with_tags(workflow_utils, default_llm, workflow):
    assistant_and_state_name = get_random_name()

    assistant = AssistantModel(
        id=assistant_and_state_name,
        model=default_llm.base_name,
        system_prompt="You are a helpful assistant.",
    )

    state = StateModel(
        id=assistant_and_state_name,
        assistant_id=assistant_and_state_name,
        output_schema=json.dumps(output_schema),
    )

    workflow = workflow(
        workflow_name=get_random_name(),
        assistant_model=assistant,
        state_model=state,
    )

    response = workflow_utils.execute_workflow(
        workflow.id,
        assistant_and_state_name,
        user_input="1+1?",
        tags=["test-tag", "sdk-test"],
    )

    assert_that(json.loads(response)["results"][0], equal_to(2))


@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.smoke
def test_workflow_execution_with_session_id(workflow_utils, default_llm, workflow):
    assistant_and_state_name = get_random_name()

    assistant = AssistantModel(
        id=assistant_and_state_name,
        model=default_llm.base_name,
        system_prompt="You are a helpful assistant.",
    )

    state = StateModel(
        id=assistant_and_state_name,
        assistant_id=assistant_and_state_name,
        output_schema=json.dumps(output_schema),
    )

    workflow = workflow(
        workflow_name=get_random_name(),
        assistant_model=assistant,
        state_model=state,
    )

    session_id = str(uuid.uuid4())

    response = workflow_utils.execute_workflow(
        workflow.id,
        assistant_and_state_name,
        user_input="1+1?",
        session_id=session_id,
    )

    assert_that(json.loads(response)["results"][0], equal_to(2))
