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

import re

import pytest
from codemie_sdk.models.integration import CredentialTypes
from hamcrest import assert_that, is_not

from codemie_test_harness.tests.enums.tools import Toolkit, AzureDevOpsWikiTool
from codemie_test_harness.tests.test_data.ado_wiki_tools_test_data import (
    ado_wiki_get_test_data,
    ADO_WIKI_CREATE_PAGE,
    ADO_WIKI_RENAME_PAGE,
    ADO_WIKI_MODIFY_PAGE,
    ADO_WIKI_DELETE_PAGE,
    ADO_WIKI_CREATE_NESTED_PARENT,
    ADO_WIKI_CREATE_NESTED_CHILD,
    ADO_WIKI_CREATE_NESTED_GRANDCHILD,
    ADO_WIKI_GET_NESTED_CHILD,
    ADO_WIKI_MODIFY_NESTED_PAGE,
    ADO_WIKI_DELETE_NESTED_CHILD,
    ADO_WIKI_DELETE_NESTED_PARENT,
    ADO_WIKI_ADD_ATTACHMENT,
    ADO_WIKI_GET_PAGE_WITH_ATTACHMENT,
    ADO_WIKI_MOVE_PAGE,
    ADO_WIKI_GET_MOVED_PAGE,
    ADO_WIKI_GET_PARENT_AFTER_MOVE,
    ADO_WIKI_ADD_COMMENT_BY_PATH,
    ADO_WIKI_ADD_COMMENT_BY_ID,
    ADO_WIKI_ADD_COMMENT_REPLY,
    ADO_WIKI_ADD_COMMENT_WITH_ATTACHMENT,
    ADO_WIKI_ADD_STANDALONE_ATTACHMENT_COMMENT,
    ADO_WIKI_GET_COMMENTS_AFTER_ADD,
    ADO_WIKI_GET_COMMENTS_AFTER_REPLY,
    ADO_WIKI_GET_COMMENTS_WITH_ATTACHMENT,
)
from codemie_test_harness.tests.utils.base_utils import (
    get_random_name,
    assert_tool_triggered,
)
from codemie_test_harness.tests.utils.constants import FILES_PATH
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager


@pytest.mark.assistant
@pytest.mark.ado
@pytest.mark.api
@pytest.mark.parametrize(
    "toolkit,tool_name,prompt,expected_response",
    ado_wiki_get_test_data,
    ids=[
        f"{getattr(row, 'values', row)[0]}_{getattr(row, 'values', row)[1]}"
        for row in ado_wiki_get_test_data
    ],
)
def test_assistant_with_ado_wiki_get_tools(
    assistant_utils,
    assistant,
    integration_utils,
    similarity_check,
    toolkit,
    tool_name,
    prompt,
    expected_response,
    seeded,
):
    prompt = seeded(prompt)
    expected_response = seeded(expected_response)
    credential_values = CredentialsManager.azure_devops_credentials()
    settings = integration_utils.create_integration(
        CredentialTypes.AZURE_DEVOPS, credential_values
    )
    assistant = assistant(
        toolkit,
        tool_name,
        settings=settings,
    )

    response, triggered_tools = assistant_utils.ask_assistant(
        assistant, prompt, minimal_response=False
    )

    assert_tool_triggered(tool_name, triggered_tools)
    similarity_check.check_similarity(response, expected_response)


@pytest.mark.assistant
@pytest.mark.ado
@pytest.mark.api
def test_assistant_with_ado_wiki_modify_tools(
    assistant_utils,
    assistant,
    integration_utils,
    similarity_check,
):
    page_title = f"Autotest-Page-{get_random_name()}"
    credential_values = CredentialsManager.azure_devops_credentials()
    settings = integration_utils.create_integration(
        CredentialTypes.AZURE_DEVOPS, credential_values
    )
    assistant = assistant(
        Toolkit.AZURE_DEVOPS_WIKI,
        (
            AzureDevOpsWikiTool.MODIFY_WIKI_PAGE,
            AzureDevOpsWikiTool.RENAME_WIKI_PAGE,
            AzureDevOpsWikiTool.DELETE_WIKI_PAGE_BY_PATH,
            AzureDevOpsWikiTool.CREATE_WIKI_PAGE,
        ),
        settings=settings,
    )

    # 1. Create the page
    create_prompt = ADO_WIKI_CREATE_PAGE["prompt_to_assistant"].format(page_title)
    create_expected = ADO_WIKI_CREATE_PAGE["expected_llm_answer"].format(page_title)
    response, triggered_tools = assistant_utils.ask_assistant(
        assistant, create_prompt, minimal_response=False
    )
    assert_tool_triggered(AzureDevOpsWikiTool.CREATE_WIKI_PAGE, triggered_tools)
    similarity_check.check_similarity(response, create_expected)

    # 2. Rename the page
    rename_prompt = ADO_WIKI_RENAME_PAGE["prompt_to_assistant"].format(
        page_title, page_title
    )
    rename_expected = ADO_WIKI_RENAME_PAGE["expected_llm_answer"].format(
        page_title, page_title
    )
    response, triggered_tools = assistant_utils.ask_assistant(
        assistant, rename_prompt, minimal_response=False
    )
    assert_tool_triggered(AzureDevOpsWikiTool.RENAME_WIKI_PAGE, triggered_tools)
    similarity_check.check_similarity(response, rename_expected)

    # 3. Modify the page
    modify_prompt = ADO_WIKI_MODIFY_PAGE["prompt_to_assistant"].format(page_title)
    modify_expected = ADO_WIKI_MODIFY_PAGE["expected_llm_answer"].format(page_title)
    response, triggered_tools = assistant_utils.ask_assistant(
        assistant, modify_prompt, minimal_response=False
    )
    assert_tool_triggered(AzureDevOpsWikiTool.MODIFY_WIKI_PAGE, triggered_tools)
    similarity_check.check_similarity(response, modify_expected)

    # 4. Delete the page
    delete_prompt = ADO_WIKI_DELETE_PAGE["prompt_to_assistant"].format(page_title)
    delete_expected = ADO_WIKI_DELETE_PAGE["expected_llm_answer"].format(page_title)
    response, triggered_tools = assistant_utils.ask_assistant(
        assistant, delete_prompt, minimal_response=False
    )
    assert_tool_triggered(AzureDevOpsWikiTool.DELETE_WIKI_PAGE_BY_PATH, triggered_tools)
    similarity_check.check_similarity(response, delete_expected)


@pytest.mark.assistant
@pytest.mark.ado
@pytest.mark.api
def test_assistant_with_ado_wiki_nested_pages(
    assistant_utils,
    assistant,
    integration_utils,
    similarity_check,
    cleanup_ado_wiki_pages,
):
    """
    Test complete lifecycle of nested wiki pages:
    - Create parent page
    - Create child page under parent
    - Create grandchild page (3-level nesting)
    - Retrieve nested pages by path
    - Modify nested page content
    - Delete nested pages in correct order (child first, then parent)
    """
    parent_title = f"Autotest-Parent-{get_random_name()}"
    child_title = f"Autotest-Child-{get_random_name()}"
    grandchild_title = f"Autotest-Grandchild-{get_random_name()}"

    credential_values = CredentialsManager.azure_devops_credentials()
    settings = integration_utils.create_integration(
        CredentialTypes.AZURE_DEVOPS, credential_values
    )
    test_assistant = assistant(
        Toolkit.AZURE_DEVOPS_WIKI,
        (
            AzureDevOpsWikiTool.CREATE_WIKI_PAGE,
            AzureDevOpsWikiTool.GET_WIKI_PAGE_BY_PATH,
            AzureDevOpsWikiTool.MODIFY_WIKI_PAGE,
            AzureDevOpsWikiTool.DELETE_WIKI_PAGE_BY_PATH,
        ),
        settings=settings,
    )

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
        assistant_utils.ask_assistant(test_assistant, prompt, minimal_response=False)

    register_page = cleanup_ado_wiki_pages(delete_page)

    # 1. Create parent page
    create_parent_prompt = ADO_WIKI_CREATE_NESTED_PARENT["prompt_to_assistant"].format(
        parent_title
    )
    create_parent_expected = ADO_WIKI_CREATE_NESTED_PARENT[
        "expected_llm_answer"
    ].format(parent_title)
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, create_parent_prompt, minimal_response=False
    )
    assert_tool_triggered(AzureDevOpsWikiTool.CREATE_WIKI_PAGE, triggered_tools)
    similarity_check.check_similarity(response, create_parent_expected)

    # Register parent page for cleanup immediately after creation
    register_page(parent_title)

    # 2. Create child page under parent
    create_child_prompt = ADO_WIKI_CREATE_NESTED_CHILD["prompt_to_assistant"].format(
        parent_title, child_title
    )
    create_child_expected = ADO_WIKI_CREATE_NESTED_CHILD["expected_llm_answer"].format(
        child_title, parent_title
    )
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, create_child_prompt, minimal_response=False
    )
    assert_tool_triggered(AzureDevOpsWikiTool.CREATE_WIKI_PAGE, triggered_tools)
    similarity_check.check_similarity(response, create_child_expected)

    # Register child page for cleanup immediately after creation
    register_page(f"{parent_title}/{child_title}")

    # 3. Create grandchild page (3-level nesting)
    create_grandchild_prompt = ADO_WIKI_CREATE_NESTED_GRANDCHILD[
        "prompt_to_assistant"
    ].format(parent_title, child_title, grandchild_title)
    create_grandchild_expected = ADO_WIKI_CREATE_NESTED_GRANDCHILD[
        "expected_llm_answer"
    ].format(grandchild_title, parent_title, child_title)
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, create_grandchild_prompt, minimal_response=False
    )
    assert_tool_triggered(AzureDevOpsWikiTool.CREATE_WIKI_PAGE, triggered_tools)
    similarity_check.check_similarity(response, create_grandchild_expected)

    # Register grandchild page for cleanup immediately after creation
    register_page(f"{parent_title}/{child_title}/{grandchild_title}")

    # 4. Retrieve nested child page by path
    get_child_prompt = ADO_WIKI_GET_NESTED_CHILD["prompt_to_assistant"].format(
        parent_title, child_title
    )
    get_child_expected = ADO_WIKI_GET_NESTED_CHILD["expected_llm_answer"].format(
        parent_title, child_title
    )
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, get_child_prompt, minimal_response=False
    )
    assert_tool_triggered(AzureDevOpsWikiTool.GET_WIKI_PAGE_BY_PATH, triggered_tools)
    similarity_check.check_similarity(response, get_child_expected)

    # 5. Modify nested page content
    modify_child_prompt = ADO_WIKI_MODIFY_NESTED_PAGE["prompt_to_assistant"].format(
        parent_title, child_title
    )
    modify_child_expected = ADO_WIKI_MODIFY_NESTED_PAGE["expected_llm_answer"].format(
        parent_title, child_title
    )
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, modify_child_prompt, minimal_response=False
    )
    assert_tool_triggered(AzureDevOpsWikiTool.MODIFY_WIKI_PAGE, triggered_tools)
    similarity_check.check_similarity(response, modify_child_expected)


@pytest.mark.assistant
@pytest.mark.ado
@pytest.mark.api
@pytest.mark.smoke
def test_assistant_with_ado_wiki_add_attachment(
    assistant_utils,
    assistant,
    integration_utils,
    similarity_check,
    cleanup_ado_wiki_pages,
):
    """
    Test adding an attachment to an ADO wiki page:
    - Create a wiki page
    - Upload a file
    - Attach the uploaded file to the wiki page using ADD_WIKI_ATTACHMENT tool
    - Verify attachment metadata (URL, name) is returned
    """
    page_title = f"Autotest-Page-{get_random_name()}"
    credential_values = CredentialsManager.azure_devops_credentials()
    settings = integration_utils.create_integration(
        CredentialTypes.AZURE_DEVOPS, credential_values
    )
    test_assistant = assistant(
        Toolkit.AZURE_DEVOPS_WIKI,
        (
            AzureDevOpsWikiTool.CREATE_WIKI_PAGE,
            AzureDevOpsWikiTool.ADD_WIKI_ATTACHMENT,
            AzureDevOpsWikiTool.GET_WIKI_PAGE_BY_PATH,
            AzureDevOpsWikiTool.DELETE_WIKI_PAGE_BY_PATH,
        ),
        settings=settings,
    )

    # Setup cleanup
    def delete_page(page_path):
        prompt = ADO_WIKI_DELETE_NESTED_PARENT["prompt_to_assistant"].format(page_path)
        assistant_utils.ask_assistant(test_assistant, prompt, minimal_response=False)

    register_page = cleanup_ado_wiki_pages(delete_page)

    # 1. Create the wiki page
    create_prompt = ADO_WIKI_CREATE_PAGE["prompt_to_assistant"].format(page_title)
    create_expected = ADO_WIKI_CREATE_PAGE["expected_llm_answer"].format(page_title)
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, create_prompt, minimal_response=False
    )
    assert_tool_triggered(AzureDevOpsWikiTool.CREATE_WIKI_PAGE, triggered_tools)
    similarity_check.check_similarity(response, create_expected)
    register_page(page_title)

    # 2. Upload a file to the chat
    uploaded_file = assistant_utils.upload_file_to_chat(
        FILES_PATH / ADO_WIKI_ADD_ATTACHMENT["file_name"]
    )
    file_url = uploaded_file.get("file_url")
    assert_that(file_url, is_not(None))

    # 3. Attach the uploaded file to the wiki page
    attach_prompt = ADO_WIKI_ADD_ATTACHMENT["prompt_to_assistant"].format(page_title)
    attach_expected = ADO_WIKI_ADD_ATTACHMENT["expected_llm_answer"].format(page_title)
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, attach_prompt, file_urls=[file_url], minimal_response=False
    )

    assert_tool_triggered(AzureDevOpsWikiTool.ADD_WIKI_ATTACHMENT, triggered_tools)
    similarity_check.check_similarity(response, attach_expected)

    # 4. Get the page and verify the attachment is present
    get_page_prompt = ADO_WIKI_GET_PAGE_WITH_ATTACHMENT["prompt_to_assistant"].format(
        page_title
    )
    get_page_expected = ADO_WIKI_GET_PAGE_WITH_ATTACHMENT["expected_llm_answer"].format(
        page_title
    )
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, get_page_prompt, minimal_response=False
    )
    assert_tool_triggered(AzureDevOpsWikiTool.GET_WIKI_PAGE_BY_PATH, triggered_tools)
    similarity_check.check_similarity(response, get_page_expected)


@pytest.mark.assistant
@pytest.mark.ado
@pytest.mark.api
@pytest.mark.smoke
def test_assistant_with_ado_wiki_move_page(
    assistant_utils,
    assistant,
    integration_utils,
    similarity_check,
    cleanup_ado_wiki_pages,
):
    """
    Test moving a wiki page under a parent page:
    - Create a parent page
    - Create a source page at root level
    - Move the source page under the parent
    - Verify the parent page is still accessible with its original content
    - Verify the moved page exists at the new nested path with original content
    """
    parent_title = f"Autotest-Parent-{get_random_name()}"
    source_title = f"Autotest-Source-{get_random_name()}"
    nested_path = f"{parent_title}/{source_title}"

    credential_values = CredentialsManager.azure_devops_credentials()
    settings = integration_utils.create_integration(
        CredentialTypes.AZURE_DEVOPS, credential_values
    )
    test_assistant = assistant(
        Toolkit.AZURE_DEVOPS_WIKI,
        (
            AzureDevOpsWikiTool.CREATE_WIKI_PAGE,
            AzureDevOpsWikiTool.MOVE_WIKI_PAGE,
            AzureDevOpsWikiTool.GET_WIKI_PAGE_BY_PATH,
            AzureDevOpsWikiTool.DELETE_WIKI_PAGE_BY_PATH,
        ),
        settings=settings,
    )

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
        assistant_utils.ask_assistant(test_assistant, prompt, minimal_response=False)

    register_page = cleanup_ado_wiki_pages(delete_page)

    # 1. Create the parent page
    create_parent_prompt = ADO_WIKI_CREATE_NESTED_PARENT["prompt_to_assistant"].format(
        parent_title
    )
    create_parent_expected = ADO_WIKI_CREATE_NESTED_PARENT[
        "expected_llm_answer"
    ].format(parent_title)
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, create_parent_prompt, minimal_response=False
    )
    assert_tool_triggered(AzureDevOpsWikiTool.CREATE_WIKI_PAGE, triggered_tools)
    similarity_check.check_similarity(response, create_parent_expected)
    register_page(parent_title)

    # 2. Create the source page at root level
    create_source_prompt = ADO_WIKI_CREATE_PAGE["prompt_to_assistant"].format(
        source_title
    )
    create_source_expected = ADO_WIKI_CREATE_PAGE["expected_llm_answer"].format(
        source_title
    )
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, create_source_prompt, minimal_response=False
    )
    assert_tool_triggered(AzureDevOpsWikiTool.CREATE_WIKI_PAGE, triggered_tools)
    similarity_check.check_similarity(response, create_source_expected)
    register_page(source_title)

    # 3. Move the source page under the parent
    move_prompt = ADO_WIKI_MOVE_PAGE["prompt_to_assistant"].format(
        source_title, parent_title
    )
    move_expected = ADO_WIKI_MOVE_PAGE["expected_llm_answer"].format(
        source_title, parent_title
    )
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, move_prompt, minimal_response=False
    )
    assert_tool_triggered(AzureDevOpsWikiTool.MOVE_WIKI_PAGE, triggered_tools)
    similarity_check.check_similarity(response, move_expected)
    register_page(nested_path)

    # 4. Verify the parent page is still accessible with its original content
    get_parent_prompt = ADO_WIKI_GET_PARENT_AFTER_MOVE["prompt_to_assistant"].format(
        parent_title
    )
    get_parent_expected = ADO_WIKI_GET_PARENT_AFTER_MOVE["expected_llm_answer"].format(
        parent_title
    )
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, get_parent_prompt, minimal_response=False
    )
    assert_tool_triggered(AzureDevOpsWikiTool.GET_WIKI_PAGE_BY_PATH, triggered_tools)
    similarity_check.check_similarity(response, get_parent_expected)

    # 5. Verify the moved page exists at the new nested path with original content
    get_moved_prompt = ADO_WIKI_GET_MOVED_PAGE["prompt_to_assistant"].format(
        nested_path
    )
    get_moved_expected = ADO_WIKI_GET_MOVED_PAGE["expected_llm_answer"].format(
        nested_path
    )
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, get_moved_prompt, minimal_response=False
    )
    assert_tool_triggered(AzureDevOpsWikiTool.GET_WIKI_PAGE_BY_PATH, triggered_tools)
    similarity_check.check_similarity(response, get_moved_expected)


@pytest.mark.assistant
@pytest.mark.ado
@pytest.mark.api
@pytest.mark.smoke
def test_assistant_with_ado_wiki_add_comment_by_path(
    assistant_utils,
    assistant,
    integration_utils,
    similarity_check,
    cleanup_ado_wiki_pages,
):
    page_title = f"Autotest-Page-{get_random_name()}"
    credential_values = CredentialsManager.azure_devops_credentials()
    settings = integration_utils.create_integration(
        CredentialTypes.AZURE_DEVOPS, credential_values
    )
    test_assistant = assistant(
        Toolkit.AZURE_DEVOPS_WIKI,
        (
            AzureDevOpsWikiTool.CREATE_WIKI_PAGE,
            AzureDevOpsWikiTool.ADD_WIKI_COMMENT_BY_PATH,
            AzureDevOpsWikiTool.GET_WIKI_PAGE_COMMENTS_BY_PATH,
            AzureDevOpsWikiTool.DELETE_WIKI_PAGE_BY_PATH,
        ),
        settings=settings,
    )

    def delete_page(page_path):
        prompt = ADO_WIKI_DELETE_NESTED_PARENT["prompt_to_assistant"].format(page_path)
        assistant_utils.ask_assistant(test_assistant, prompt, minimal_response=False)

    register_page = cleanup_ado_wiki_pages(delete_page)

    # 1. Create wiki page
    create_prompt = ADO_WIKI_CREATE_PAGE["prompt_to_assistant"].format(page_title)
    create_expected = ADO_WIKI_CREATE_PAGE["expected_llm_answer"].format(page_title)
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, create_prompt, minimal_response=False
    )
    assert_tool_triggered(AzureDevOpsWikiTool.CREATE_WIKI_PAGE, triggered_tools)
    similarity_check.check_similarity(response, create_expected)
    register_page(page_title)

    # 2. Add a text comment by page path
    comment_prompt = ADO_WIKI_ADD_COMMENT_BY_PATH["prompt_to_assistant"].format(
        page_title
    )
    comment_expected = ADO_WIKI_ADD_COMMENT_BY_PATH["expected_llm_answer"].format(
        page_title
    )
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, comment_prompt, minimal_response=False
    )
    assert_tool_triggered(AzureDevOpsWikiTool.ADD_WIKI_COMMENT_BY_PATH, triggered_tools)
    similarity_check.check_similarity(response, comment_expected)

    # 3. Verify the comment exists on the page
    verify_prompt = ADO_WIKI_GET_COMMENTS_AFTER_ADD["prompt_to_assistant"].format(
        page_name=page_title
    )
    verify_expected = ADO_WIKI_GET_COMMENTS_AFTER_ADD["expected_llm_answer"].format(
        page_name=page_title
    )
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, verify_prompt, minimal_response=False
    )
    assert_tool_triggered(
        AzureDevOpsWikiTool.GET_WIKI_PAGE_COMMENTS_BY_PATH, triggered_tools
    )
    similarity_check.check_similarity(response, verify_expected)


@pytest.mark.assistant
@pytest.mark.ado
@pytest.mark.api
def test_assistant_with_ado_wiki_add_comment_by_id(
    assistant_utils,
    assistant,
    integration_utils,
    similarity_check,
    cleanup_ado_wiki_pages,
):
    page_title = f"Autotest-Page-{get_random_name()}"
    credential_values = CredentialsManager.azure_devops_credentials()
    settings = integration_utils.create_integration(
        CredentialTypes.AZURE_DEVOPS, credential_values
    )
    # Assistant for page lifecycle (create / delete / verify comments)
    page_assistant = assistant(
        Toolkit.AZURE_DEVOPS_WIKI,
        (
            AzureDevOpsWikiTool.CREATE_WIKI_PAGE,
            AzureDevOpsWikiTool.GET_WIKI_PAGE_COMMENTS_BY_PATH,
            AzureDevOpsWikiTool.DELETE_WIKI_PAGE_BY_PATH,
        ),
        settings=settings,
    )
    # Dedicated assistant with only ADD_WIKI_COMMENT_BY_ID — forces the LLM to use it
    comment_assistant = assistant(
        Toolkit.AZURE_DEVOPS_WIKI,
        AzureDevOpsWikiTool.ADD_WIKI_COMMENT_BY_ID,
        settings=settings,
    )

    def delete_page(page_path):
        prompt = ADO_WIKI_DELETE_NESTED_PARENT["prompt_to_assistant"].format(page_path)
        assistant_utils.ask_assistant(page_assistant, prompt, minimal_response=False)

    register_page = cleanup_ado_wiki_pages(delete_page)

    # 1. Create wiki page — ask the LLM to report the 'id' field from the response
    create_prompt = ADO_WIKI_ADD_COMMENT_BY_ID["create_prompt"].format(page_title)
    create_response, triggered_tools = assistant_utils.ask_assistant(
        page_assistant, create_prompt, minimal_response=False
    )
    assert_tool_triggered(AzureDevOpsWikiTool.CREATE_WIKI_PAGE, triggered_tools)
    register_page(page_title)

    # Extract page ID (4+ digit number from the reported 'id' field; skips order=0)
    page_id_match = re.search(r"\b(\d{4,})\b", create_response)
    assert_that(page_id_match, is_not(None))
    page_id = page_id_match.group(1)

    # 2. Add comment by ID using the dedicated single-tool assistant
    comment_prompt = ADO_WIKI_ADD_COMMENT_BY_ID["prompt_to_assistant"].format(page_id)
    comment_expected = ADO_WIKI_ADD_COMMENT_BY_ID["expected_llm_answer"].format(page_id)
    response, triggered_tools = assistant_utils.ask_assistant(
        comment_assistant, comment_prompt, minimal_response=False
    )
    assert_tool_triggered(AzureDevOpsWikiTool.ADD_WIKI_COMMENT_BY_ID, triggered_tools)
    similarity_check.check_similarity(response, comment_expected)

    # 3. Verify the comment exists on the page (using path via page_assistant)
    verify_prompt = ADO_WIKI_GET_COMMENTS_AFTER_ADD["prompt_to_assistant"].format(
        page_name=page_title
    )
    verify_expected = ADO_WIKI_GET_COMMENTS_AFTER_ADD["expected_llm_answer"].format(
        page_name=page_title
    )
    response, triggered_tools = assistant_utils.ask_assistant(
        page_assistant, verify_prompt, minimal_response=False
    )
    assert_tool_triggered(
        AzureDevOpsWikiTool.GET_WIKI_PAGE_COMMENTS_BY_PATH, triggered_tools
    )
    similarity_check.check_similarity(response, verify_expected)


@pytest.mark.assistant
@pytest.mark.ado
@pytest.mark.api
def test_assistant_with_ado_wiki_add_comment_reply(
    assistant_utils,
    assistant,
    integration_utils,
    similarity_check,
    cleanup_ado_wiki_pages,
):
    page_title = f"Autotest-Page-{get_random_name()}"
    credential_values = CredentialsManager.azure_devops_credentials()
    settings = integration_utils.create_integration(
        CredentialTypes.AZURE_DEVOPS, credential_values
    )
    test_assistant = assistant(
        Toolkit.AZURE_DEVOPS_WIKI,
        (
            AzureDevOpsWikiTool.CREATE_WIKI_PAGE,
            AzureDevOpsWikiTool.ADD_WIKI_COMMENT_BY_PATH,
            AzureDevOpsWikiTool.GET_WIKI_PAGE_COMMENTS_BY_PATH,
            AzureDevOpsWikiTool.DELETE_WIKI_PAGE_BY_PATH,
        ),
        settings=settings,
    )

    def delete_page(page_path):
        prompt = ADO_WIKI_DELETE_NESTED_PARENT["prompt_to_assistant"].format(page_path)
        assistant_utils.ask_assistant(test_assistant, prompt, minimal_response=False)

    register_page = cleanup_ado_wiki_pages(delete_page)

    # 1. Create wiki page
    create_prompt = ADO_WIKI_CREATE_PAGE["prompt_to_assistant"].format(page_title)
    create_expected = ADO_WIKI_CREATE_PAGE["expected_llm_answer"].format(page_title)
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, create_prompt, minimal_response=False
    )
    assert_tool_triggered(AzureDevOpsWikiTool.CREATE_WIKI_PAGE, triggered_tools)
    similarity_check.check_similarity(response, create_expected)
    register_page(page_title)

    # 2. Add first comment
    comment_prompt = ADO_WIKI_ADD_COMMENT_BY_PATH["prompt_to_assistant"].format(
        page_title
    )
    comment_expected = ADO_WIKI_ADD_COMMENT_BY_PATH["expected_llm_answer"].format(
        page_title
    )
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, comment_prompt, minimal_response=False
    )
    assert_tool_triggered(AzureDevOpsWikiTool.ADD_WIKI_COMMENT_BY_PATH, triggered_tools)
    similarity_check.check_similarity(response, comment_expected)

    # 3. Get comments and reply to the first one
    reply_prompt = ADO_WIKI_ADD_COMMENT_REPLY["prompt_to_assistant"].format(
        page_name=page_title
    )
    reply_expected = ADO_WIKI_ADD_COMMENT_REPLY["expected_llm_answer"].format(
        page_name=page_title
    )
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, reply_prompt, minimal_response=False
    )
    assert_tool_triggered(AzureDevOpsWikiTool.ADD_WIKI_COMMENT_BY_PATH, triggered_tools)
    similarity_check.check_similarity(response, reply_expected)

    # 4. Verify the reply exists in the page comments
    verify_prompt = ADO_WIKI_GET_COMMENTS_AFTER_REPLY["prompt_to_assistant"].format(
        page_name=page_title
    )
    verify_expected = ADO_WIKI_GET_COMMENTS_AFTER_REPLY["expected_llm_answer"].format(
        page_name=page_title
    )
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, verify_prompt, minimal_response=False
    )
    assert_tool_triggered(
        AzureDevOpsWikiTool.GET_WIKI_PAGE_COMMENTS_BY_PATH, triggered_tools
    )
    similarity_check.check_similarity(response, verify_expected)


@pytest.mark.assistant
@pytest.mark.ado
@pytest.mark.api
def test_assistant_with_ado_wiki_add_comment_with_attachment(
    assistant_utils,
    assistant,
    integration_utils,
    similarity_check,
    cleanup_ado_wiki_pages,
):
    page_title = f"Autotest-Page-{get_random_name()}"
    credential_values = CredentialsManager.azure_devops_credentials()
    settings = integration_utils.create_integration(
        CredentialTypes.AZURE_DEVOPS, credential_values
    )
    test_assistant = assistant(
        Toolkit.AZURE_DEVOPS_WIKI,
        (
            AzureDevOpsWikiTool.CREATE_WIKI_PAGE,
            AzureDevOpsWikiTool.ADD_WIKI_COMMENT_BY_PATH,
            AzureDevOpsWikiTool.GET_WIKI_PAGE_COMMENTS_BY_PATH,
            AzureDevOpsWikiTool.DELETE_WIKI_PAGE_BY_PATH,
        ),
        settings=settings,
    )

    def delete_page(page_path):
        prompt = ADO_WIKI_DELETE_NESTED_PARENT["prompt_to_assistant"].format(page_path)
        assistant_utils.ask_assistant(test_assistant, prompt, minimal_response=False)

    register_page = cleanup_ado_wiki_pages(delete_page)

    # 1. Create wiki page
    create_prompt = ADO_WIKI_CREATE_PAGE["prompt_to_assistant"].format(page_title)
    create_expected = ADO_WIKI_CREATE_PAGE["expected_llm_answer"].format(page_title)
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, create_prompt, minimal_response=False
    )
    assert_tool_triggered(AzureDevOpsWikiTool.CREATE_WIKI_PAGE, triggered_tools)
    similarity_check.check_similarity(response, create_expected)
    register_page(page_title)

    # 2. Upload file
    uploaded_file = assistant_utils.upload_file_to_chat(
        FILES_PATH / ADO_WIKI_ADD_COMMENT_WITH_ATTACHMENT["file_name"]
    )
    file_url = uploaded_file.get("file_url")
    assert_that(file_url, is_not(None))

    # 3. Add comment with file attachment
    comment_prompt = ADO_WIKI_ADD_COMMENT_WITH_ATTACHMENT["prompt_to_assistant"].format(
        page_title
    )
    comment_expected = ADO_WIKI_ADD_COMMENT_WITH_ATTACHMENT[
        "expected_llm_answer"
    ].format(page_title)
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, comment_prompt, file_urls=[file_url], minimal_response=False
    )
    assert_tool_triggered(AzureDevOpsWikiTool.ADD_WIKI_COMMENT_BY_PATH, triggered_tools)
    similarity_check.check_similarity(response, comment_expected)

    # 4. Verify the comment with attachment exists on the page
    verify_prompt = ADO_WIKI_GET_COMMENTS_WITH_ATTACHMENT["prompt_to_assistant"].format(
        page_name=page_title
    )
    verify_expected = ADO_WIKI_GET_COMMENTS_WITH_ATTACHMENT[
        "expected_llm_answer"
    ].format(page_name=page_title)
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, verify_prompt, minimal_response=False
    )
    assert_tool_triggered(
        AzureDevOpsWikiTool.GET_WIKI_PAGE_COMMENTS_BY_PATH, triggered_tools
    )
    similarity_check.check_similarity(response, verify_expected)


@pytest.mark.assistant
@pytest.mark.ado
@pytest.mark.api
def test_assistant_with_ado_wiki_add_standalone_attachment_comment(
    assistant_utils,
    assistant,
    integration_utils,
    similarity_check,
    cleanup_ado_wiki_pages,
):
    page_title = f"Autotest-Page-{get_random_name()}"
    credential_values = CredentialsManager.azure_devops_credentials()
    settings = integration_utils.create_integration(
        CredentialTypes.AZURE_DEVOPS, credential_values
    )
    test_assistant = assistant(
        Toolkit.AZURE_DEVOPS_WIKI,
        (
            AzureDevOpsWikiTool.CREATE_WIKI_PAGE,
            AzureDevOpsWikiTool.ADD_WIKI_COMMENT_BY_PATH,
            AzureDevOpsWikiTool.GET_WIKI_PAGE_COMMENTS_BY_PATH,
            AzureDevOpsWikiTool.DELETE_WIKI_PAGE_BY_PATH,
        ),
        settings=settings,
    )

    def delete_page(page_path):
        prompt = ADO_WIKI_DELETE_NESTED_PARENT["prompt_to_assistant"].format(page_path)
        assistant_utils.ask_assistant(test_assistant, prompt, minimal_response=False)

    register_page = cleanup_ado_wiki_pages(delete_page)

    # 1. Create wiki page
    create_prompt = ADO_WIKI_CREATE_PAGE["prompt_to_assistant"].format(page_title)
    create_expected = ADO_WIKI_CREATE_PAGE["expected_llm_answer"].format(page_title)
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, create_prompt, minimal_response=False
    )
    assert_tool_triggered(AzureDevOpsWikiTool.CREATE_WIKI_PAGE, triggered_tools)
    similarity_check.check_similarity(response, create_expected)
    register_page(page_title)

    # 2. Upload file
    uploaded_file = assistant_utils.upload_file_to_chat(
        FILES_PATH / ADO_WIKI_ADD_STANDALONE_ATTACHMENT_COMMENT["file_name"]
    )
    file_url = uploaded_file.get("file_url")
    assert_that(file_url, is_not(None))

    # 3. Post attachment as standalone comment (empty text body)
    comment_prompt = ADO_WIKI_ADD_STANDALONE_ATTACHMENT_COMMENT[
        "prompt_to_assistant"
    ].format(page_title)
    comment_expected = ADO_WIKI_ADD_STANDALONE_ATTACHMENT_COMMENT[
        "expected_llm_answer"
    ].format(page_title)
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, comment_prompt, file_urls=[file_url], minimal_response=False
    )
    assert_tool_triggered(AzureDevOpsWikiTool.ADD_WIKI_COMMENT_BY_PATH, triggered_tools)
    similarity_check.check_similarity(response, comment_expected)

    # 4. Verify the attachment comment exists on the page
    verify_prompt = ADO_WIKI_GET_COMMENTS_WITH_ATTACHMENT["prompt_to_assistant"].format(
        page_name=page_title
    )
    verify_expected = ADO_WIKI_GET_COMMENTS_WITH_ATTACHMENT[
        "expected_llm_answer"
    ].format(page_name=page_title)
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, verify_prompt, minimal_response=False
    )
    assert_tool_triggered(
        AzureDevOpsWikiTool.GET_WIKI_PAGE_COMMENTS_BY_PATH, triggered_tools
    )
    similarity_check.check_similarity(response, verify_expected)
