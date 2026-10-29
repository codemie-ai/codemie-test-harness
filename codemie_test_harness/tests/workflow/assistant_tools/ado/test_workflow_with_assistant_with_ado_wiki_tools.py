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

from codemie_test_harness.tests.enums.tools import AzureDevOpsWikiTool, Toolkit
from codemie_test_harness.tests.test_data.ado_wiki_tools_test_data import (
    ado_wiki_get_test_data,
    ADO_WIKI_CREATE_PAGE,
    ADO_WIKI_RENAME_PAGE,
    ADO_WIKI_MODIFY_PAGE,
    ADO_WIKI_DELETE_PAGE,
    ADO_WIKI_CREATE_NESTED_PARENT,
    ADO_WIKI_CREATE_NESTED_CHILD,
    ADO_WIKI_GET_NESTED_CHILD,
    ADO_WIKI_MODIFY_NESTED_PAGE,
    ADO_WIKI_DELETE_NESTED_CHILD,
    ADO_WIKI_DELETE_NESTED_PARENT,
    ADO_WIKI_MOVE_PAGE,
    ADO_WIKI_GET_MOVED_PAGE,
    ADO_WIKI_GET_PARENT_AFTER_MOVE,
)
from codemie_test_harness.tests.utils.base_utils import (
    get_random_name,
    assert_tool_triggered,
)


@pytest.mark.workflow
@pytest.mark.workflow_with_assistant
@pytest.mark.ado
@pytest.mark.api
@pytest.mark.parametrize(
    "toolkit, tool_name, prompt, expected_response",
    ado_wiki_get_test_data,
    ids=[f"{getattr(row, 'values', row)[1]}" for row in ado_wiki_get_test_data],
)
def test_workflow_with_assistant_with_ado_wiki_get_tools(
    ado_integration,
    assistant,
    similarity_check,
    workflow_with_assistant,
    workflow_utils,
    toolkit,
    tool_name,
    prompt,
    expected_response,
    seeded,
):
    prompt = seeded(prompt)
    expected_response = seeded(expected_response)
    assistant = assistant(toolkit, tool_name, settings=ado_integration)
    workflow_with_assistant = workflow_with_assistant(assistant, prompt)
    response = workflow_utils.execute_workflow(
        workflow_with_assistant.id, assistant.name
    )

    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        workflow_with_assistant
    )
    assert_tool_triggered(tool_name, triggered_tools)

    similarity_check.check_similarity(response, expected_response)


@pytest.mark.workflow
@pytest.mark.workflow_with_assistant
@pytest.mark.ado
@pytest.mark.api
def test_workflow_with_assistant_with_ado_wiki_modify_tools(
    ado_integration,
    assistant,
    similarity_check,
    workflow_with_assistant,
    workflow_utils,
):
    assistant = assistant(
        Toolkit.AZURE_DEVOPS_WIKI,
        (
            AzureDevOpsWikiTool.MODIFY_WIKI_PAGE,
            AzureDevOpsWikiTool.RENAME_WIKI_PAGE,
            AzureDevOpsWikiTool.DELETE_WIKI_PAGE_BY_PATH,
            AzureDevOpsWikiTool.CREATE_WIKI_PAGE,
        ),
        settings=ado_integration,
    )
    workflow_with_assistant = workflow_with_assistant(assistant, "Run")

    # 1. Create the page
    page_title = f"Autotest-Page-{get_random_name()}"
    create_prompt = ADO_WIKI_CREATE_PAGE["prompt_to_assistant"].format(page_title)
    create_expected = ADO_WIKI_CREATE_PAGE["expected_llm_answer"].format(page_title)
    create_response = workflow_utils.execute_workflow(
        workflow_with_assistant.id, assistant.name, create_prompt
    )

    # Assert that modify wiki page tool was triggered
    create_triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        workflow_with_assistant
    )
    assert_tool_triggered(AzureDevOpsWikiTool.CREATE_WIKI_PAGE, create_triggered_tools)

    similarity_check.check_similarity(create_response, create_expected)

    # 2. Rename the page
    rename_prompt = ADO_WIKI_RENAME_PAGE["prompt_to_assistant"].format(
        page_title, page_title
    )
    rename_expected = ADO_WIKI_RENAME_PAGE["expected_llm_answer"].format(
        page_title, page_title
    )
    rename_response = workflow_utils.execute_workflow(
        workflow_with_assistant.id, assistant.name, rename_prompt
    )

    # Assert that rename wiki page tool was triggered
    rename_triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        workflow_with_assistant
    )
    assert_tool_triggered(AzureDevOpsWikiTool.RENAME_WIKI_PAGE, rename_triggered_tools)

    similarity_check.check_similarity(rename_response, rename_expected)

    # 3. Modify the page
    modify_prompt = ADO_WIKI_MODIFY_PAGE["prompt_to_assistant"].format(page_title)
    modify_expected = ADO_WIKI_MODIFY_PAGE["expected_llm_answer"].format(page_title)
    modify_response = workflow_utils.execute_workflow(
        workflow_with_assistant.id, assistant.name, modify_prompt
    )

    # Assert that modify wiki page tool was triggered
    modify_triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        workflow_with_assistant
    )
    assert_tool_triggered(AzureDevOpsWikiTool.MODIFY_WIKI_PAGE, modify_triggered_tools)

    similarity_check.check_similarity(modify_response, modify_expected)

    # 4. Delete the page
    delete_prompt = ADO_WIKI_DELETE_PAGE["prompt_to_assistant"].format(page_title)
    delete_expected = ADO_WIKI_DELETE_PAGE["expected_llm_answer"].format(page_title)
    delete_response = workflow_utils.execute_workflow(
        workflow_with_assistant.id, assistant.name, delete_prompt
    )

    # Assert that delete wiki page tool was triggered
    delete_triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        workflow_with_assistant
    )
    assert_tool_triggered(
        AzureDevOpsWikiTool.DELETE_WIKI_PAGE_BY_PATH, delete_triggered_tools
    )

    similarity_check.check_similarity(delete_response, delete_expected)


@pytest.mark.workflow
@pytest.mark.workflow_with_assistant
@pytest.mark.ado
@pytest.mark.api
def test_workflow_with_assistant_with_ado_wiki_nested_pages(
    ado_integration,
    assistant,
    similarity_check,
    workflow_with_assistant,
    workflow_utils,
    cleanup_ado_wiki_pages,
):
    """
    Test complete lifecycle of nested wiki pages using workflow with assistant:
    - Create parent page
    - Create child page under parent
    - Retrieve nested pages by path
    - Modify nested page content
    - Delete nested pages in correct order
    """
    parent_title = f"Autotest-Parent-{get_random_name()}"
    child_title = f"Autotest-Child-{get_random_name()}"

    # Create assistant with all required tools
    test_assistant = assistant(
        Toolkit.AZURE_DEVOPS_WIKI,
        (
            AzureDevOpsWikiTool.CREATE_WIKI_PAGE,
            AzureDevOpsWikiTool.GET_WIKI_PAGE_BY_PATH,
            AzureDevOpsWikiTool.MODIFY_WIKI_PAGE,
            AzureDevOpsWikiTool.DELETE_WIKI_PAGE_BY_PATH,
        ),
        settings=ado_integration,
    )
    test_workflow = workflow_with_assistant(test_assistant, "Run")

    # Setup cleanup with deletion function
    def delete_page(page_path):
        if "/" in page_path:
            parent = page_path.rsplit("/", 1)[0]
            child = page_path.rsplit("/", 1)[1]
            prompt = ADO_WIKI_DELETE_NESTED_CHILD["prompt_to_assistant"].format(
                parent, child
            )
        else:
            prompt = ADO_WIKI_DELETE_NESTED_PARENT["prompt_to_assistant"].format(
                page_path
            )
        workflow_utils.execute_workflow(test_workflow.id, test_assistant.name, prompt)

    register_page = cleanup_ado_wiki_pages(delete_page)

    # 1. Create parent page
    create_parent_prompt = ADO_WIKI_CREATE_NESTED_PARENT["prompt_to_assistant"].format(
        parent_title
    )
    create_parent_expected = ADO_WIKI_CREATE_NESTED_PARENT[
        "expected_llm_answer"
    ].format(parent_title)
    create_parent_response = workflow_utils.execute_workflow(
        test_workflow.id, test_assistant.name, create_parent_prompt
    )
    create_parent_tools = workflow_utils.extract_triggered_tools_from_execution(
        test_workflow
    )
    assert_tool_triggered(AzureDevOpsWikiTool.CREATE_WIKI_PAGE, create_parent_tools)
    similarity_check.check_similarity(create_parent_response, create_parent_expected)

    # Register parent page for cleanup immediately after creation
    register_page(parent_title)

    # 2. Create child page under parent
    create_child_prompt = ADO_WIKI_CREATE_NESTED_CHILD["prompt_to_assistant"].format(
        parent_title, child_title
    )
    create_child_expected = ADO_WIKI_CREATE_NESTED_CHILD["expected_llm_answer"].format(
        child_title, parent_title
    )
    create_child_response = workflow_utils.execute_workflow(
        test_workflow.id, test_assistant.name, create_child_prompt
    )
    create_child_tools = workflow_utils.extract_triggered_tools_from_execution(
        test_workflow
    )
    assert_tool_triggered(AzureDevOpsWikiTool.CREATE_WIKI_PAGE, create_child_tools)
    similarity_check.check_similarity(create_child_response, create_child_expected)

    # Register child page for cleanup immediately after creation
    register_page(f"{parent_title}/{child_title}")

    # 3. Retrieve nested child page by path
    get_child_prompt = ADO_WIKI_GET_NESTED_CHILD["prompt_to_assistant"].format(
        parent_title, child_title
    )
    get_child_expected = ADO_WIKI_GET_NESTED_CHILD["expected_llm_answer"].format(
        parent_title, child_title
    )
    get_child_response = workflow_utils.execute_workflow(
        test_workflow.id, test_assistant.name, get_child_prompt
    )
    get_child_tools = workflow_utils.extract_triggered_tools_from_execution(
        test_workflow
    )
    assert_tool_triggered(AzureDevOpsWikiTool.GET_WIKI_PAGE_BY_PATH, get_child_tools)
    similarity_check.check_similarity(get_child_response, get_child_expected)

    # 4. Modify nested page content
    modify_child_prompt = ADO_WIKI_MODIFY_NESTED_PAGE["prompt_to_assistant"].format(
        parent_title, child_title
    )
    modify_child_expected = ADO_WIKI_MODIFY_NESTED_PAGE["expected_llm_answer"].format(
        parent_title, child_title
    )
    modify_child_response = workflow_utils.execute_workflow(
        test_workflow.id, test_assistant.name, modify_child_prompt
    )
    modify_child_tools = workflow_utils.extract_triggered_tools_from_execution(
        test_workflow
    )
    assert_tool_triggered(AzureDevOpsWikiTool.MODIFY_WIKI_PAGE, modify_child_tools)
    similarity_check.check_similarity(modify_child_response, modify_child_expected)


@pytest.mark.workflow
@pytest.mark.workflow_with_assistant
@pytest.mark.ado
@pytest.mark.api
def test_workflow_with_assistant_with_ado_wiki_move_page(
    ado_integration,
    assistant,
    similarity_check,
    workflow_with_assistant,
    workflow_utils,
    cleanup_ado_wiki_pages,
):
    """
    Test moving a wiki page under a parent page using workflow with assistant:
    - Create a parent page
    - Create a source page at root level
    - Move the source page under the parent
    - Verify the parent page is still accessible with its original content
    - Verify the moved page exists at the new nested path with original content
    """
    parent_title = f"Autotest-Parent-{get_random_name()}"
    source_title = f"Autotest-Source-{get_random_name()}"
    nested_path = f"{parent_title}/{source_title}"

    test_assistant = assistant(
        Toolkit.AZURE_DEVOPS_WIKI,
        (
            AzureDevOpsWikiTool.CREATE_WIKI_PAGE,
            AzureDevOpsWikiTool.MOVE_WIKI_PAGE,
            AzureDevOpsWikiTool.GET_WIKI_PAGE_BY_PATH,
            AzureDevOpsWikiTool.DELETE_WIKI_PAGE_BY_PATH,
        ),
        settings=ado_integration,
    )
    test_workflow = workflow_with_assistant(test_assistant, "Run")

    # Setup cleanup — handles both root and nested paths
    def delete_page(page_path):
        if "/" in page_path:
            parent = page_path.rsplit("/", 1)[0]
            child = page_path.rsplit("/", 1)[1]
            prompt = ADO_WIKI_DELETE_NESTED_CHILD["prompt_to_assistant"].format(
                parent, child
            )
        else:
            prompt = ADO_WIKI_DELETE_NESTED_PARENT["prompt_to_assistant"].format(
                page_path
            )
        workflow_utils.execute_workflow(test_workflow.id, test_assistant.name, prompt)

    register_page = cleanup_ado_wiki_pages(delete_page)

    # 1. Create the parent page
    create_parent_prompt = ADO_WIKI_CREATE_NESTED_PARENT["prompt_to_assistant"].format(
        parent_title
    )
    create_parent_expected = ADO_WIKI_CREATE_NESTED_PARENT[
        "expected_llm_answer"
    ].format(parent_title)
    create_parent_response = workflow_utils.execute_workflow(
        test_workflow.id, test_assistant.name, create_parent_prompt
    )
    create_parent_tools = workflow_utils.extract_triggered_tools_from_execution(
        test_workflow
    )
    assert_tool_triggered(AzureDevOpsWikiTool.CREATE_WIKI_PAGE, create_parent_tools)
    similarity_check.check_similarity(create_parent_response, create_parent_expected)
    register_page(parent_title)

    # 2. Create the source page at root level
    create_source_prompt = ADO_WIKI_CREATE_PAGE["prompt_to_assistant"].format(
        source_title
    )
    create_source_expected = ADO_WIKI_CREATE_PAGE["expected_llm_answer"].format(
        source_title
    )
    create_source_response = workflow_utils.execute_workflow(
        test_workflow.id, test_assistant.name, create_source_prompt
    )
    create_source_tools = workflow_utils.extract_triggered_tools_from_execution(
        test_workflow
    )
    assert_tool_triggered(AzureDevOpsWikiTool.CREATE_WIKI_PAGE, create_source_tools)
    similarity_check.check_similarity(create_source_response, create_source_expected)
    register_page(source_title)

    # 3. Move the source page under the parent
    move_prompt = ADO_WIKI_MOVE_PAGE["prompt_to_assistant"].format(
        source_title, parent_title
    )
    move_expected = ADO_WIKI_MOVE_PAGE["expected_llm_answer"].format(
        source_title, parent_title
    )
    move_response = workflow_utils.execute_workflow(
        test_workflow.id, test_assistant.name, move_prompt
    )
    move_tools = workflow_utils.extract_triggered_tools_from_execution(test_workflow)
    assert_tool_triggered(AzureDevOpsWikiTool.MOVE_WIKI_PAGE, move_tools)
    similarity_check.check_similarity(move_response, move_expected)
    register_page(nested_path)

    # 4. Verify the parent page is still accessible with its original content
    get_parent_prompt = ADO_WIKI_GET_PARENT_AFTER_MOVE["prompt_to_assistant"].format(
        parent_title
    )
    get_parent_expected = ADO_WIKI_GET_PARENT_AFTER_MOVE["expected_llm_answer"].format(
        parent_title
    )
    get_parent_response = workflow_utils.execute_workflow(
        test_workflow.id, test_assistant.name, get_parent_prompt
    )
    get_parent_tools = workflow_utils.extract_triggered_tools_from_execution(
        test_workflow
    )
    assert_tool_triggered(AzureDevOpsWikiTool.GET_WIKI_PAGE_BY_PATH, get_parent_tools)
    similarity_check.check_similarity(get_parent_response, get_parent_expected)

    # 5. Verify the moved page exists at the new nested path with original content
    get_moved_prompt = ADO_WIKI_GET_MOVED_PAGE["prompt_to_assistant"].format(
        nested_path
    )
    get_moved_expected = ADO_WIKI_GET_MOVED_PAGE["expected_llm_answer"].format(
        nested_path
    )
    get_moved_response = workflow_utils.execute_workflow(
        test_workflow.id, test_assistant.name, get_moved_prompt
    )
    get_moved_tools = workflow_utils.extract_triggered_tools_from_execution(
        test_workflow
    )
    assert_tool_triggered(AzureDevOpsWikiTool.GET_WIKI_PAGE_BY_PATH, get_moved_tools)
    similarity_check.check_similarity(get_moved_response, get_moved_expected)
