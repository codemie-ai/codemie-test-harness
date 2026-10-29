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

"""Assistant tests for the xWiki toolkit's 24 tools.

Scenarios:
    Read-only tools (List Wikis, Get Wiki, List Spaces, Get Space, List Pages,
    List Wiki Pages, Get Page, Search Wiki, Search Space) are parametrized
    against the persistent seed page/space — no page has to be created for them.

    Page/tag/comment tools (Create/Modify/Delete Page, List Page Children, tags,
    comments) are exercised as one page lifecycle, against a fresh space created
    for the test run, so writes never touch the seed page.

    Attachment tools (Create/List/Get/Read/Delete Page Attachment) are exercised
    separately, against a fresh page created for the test run. CreatePageAttachmentTool
    used to multipart-POST to the attachments collection resource, which xWiki's CSRF
    filter rejected with a 403 even under Basic/Bearer REST auth (verified live); it now
    PUTs to the named attachment resource instead, which isn't subject to that filter.

    A dedicated test re-runs Get Page under both Bearer-token and Basic-Auth
    (username/password) credentials to prove both auth paths work end to end.
"""

import re

import pytest
from hamcrest import assert_that, contains_string, is_not

from codemie_test_harness.tests.enums.tools import Toolkit, XWikiTool
from codemie_test_harness.tests.test_data.xwiki_tools_test_data import (
    XWIKI_CREATE_CHILD_PAGE,
    XWIKI_CREATE_PAGE_ATTACHMENT,
    XWIKI_CREATE_PAGE_COMMENT,
    XWIKI_CREATE_WEBHOME,
    XWIKI_DELETE_PAGE,
    XWIKI_DELETE_PAGE_ATTACHMENT,
    XWIKI_GET_PAGE_ATTACHMENT,
    XWIKI_GET_PAGE_COMMENT,
    XWIKI_LIST_PAGE_ATTACHMENTS,
    XWIKI_LIST_PAGE_CHILDREN,
    XWIKI_LIST_PAGE_COMMENTS,
    XWIKI_LIST_PAGE_TAGS,
    XWIKI_LIST_WIKI_TAGS,
    XWIKI_MODIFY_CHILD_PAGE,
    XWIKI_READ_PAGE_ATTACHMENT_CONTENT,
    XWIKI_SET_PAGE_TAGS,
    xwiki_read_test_data,
)
from codemie_test_harness.tests.utils.base_utils import (
    assert_tool_triggered,
    get_random_name,
)
from codemie_test_harness.tests.utils.constants import FILES_PATH
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager

pytestmark = [
    pytest.mark.skip(reason="No xwiki test environment configured"),
]

_PAGE_LIFECYCLE_TOOLS = (
    XWikiTool.CREATE_PAGE,
    XWikiTool.LIST_PAGE_CHILDREN,
    XWikiTool.MODIFY_PAGE,
    XWikiTool.SET_PAGE_TAGS,
    XWikiTool.LIST_PAGE_TAGS,
    XWikiTool.LIST_WIKI_TAGS,
    XWikiTool.CREATE_PAGE_COMMENT,
    XWikiTool.LIST_PAGE_COMMENTS,
    XWikiTool.GET_PAGE_COMMENT,
    XWikiTool.DELETE_PAGE,
)

_ATTACHMENT_TOOLS = (
    XWikiTool.CREATE_PAGE,
    XWikiTool.CREATE_PAGE_ATTACHMENT,
    XWikiTool.LIST_PAGE_ATTACHMENTS,
    XWikiTool.GET_PAGE_ATTACHMENT,
    XWikiTool.READ_PAGE_ATTACHMENT_CONTENT,
    XWikiTool.DELETE_PAGE_ATTACHMENT,
    XWikiTool.DELETE_PAGE,
)


@pytest.mark.assistant
@pytest.mark.xwiki
@pytest.mark.api
@pytest.mark.parametrize(
    "tool_name,prompt,expected_response",
    xwiki_read_test_data,
    ids=[f"{getattr(row, 'values', row)[0]}" for row in xwiki_read_test_data],
)
def test_assistant_with_xwiki_read_tools(
    assistant,
    assistant_utils,
    integration_utils,
    xwiki_integration,
    tool_name,
    prompt,
    expected_response,
    seeded,
):
    """
    Covers the 9 read-only xWiki tools (List Wikis, Get Wiki, List Spaces,
    Get Space, List Pages, List Wiki Pages, Get Page, Search Wiki, Search
    Space) against the persistent seed page/space.

    Asserted with a plain substring, not similarity_check — see
    xwiki_read_test_data's comment for why.
    """
    prompt = seeded(prompt)
    expected_substring = seeded(expected_response)

    test_assistant = assistant(
        Toolkit.XWIKI,
        tool_name,
        settings=xwiki_integration,
    )

    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, prompt, minimal_response=False
    )

    assert_tool_triggered(tool_name, triggered_tools)
    assert_that(
        response,
        contains_string(expected_substring),
        f"{tool_name} response should mention '{expected_substring}'",
    )


@pytest.mark.assistant
@pytest.mark.xwiki
@pytest.mark.api
@pytest.mark.smoke
def test_assistant_with_xwiki_page_lifecycle(
    assistant,
    assistant_utils,
    integration_utils,
    similarity_check,
    xwiki_integration,
    cleanup_xwiki_pages,
):
    """
    Full lifecycle of a page created for this test run (a fresh space, never
    the seed page), covering 10 xWiki tools:
    - Create a WebHome page and a child page under it
    - List the child page's own children — verified empty live, since none of
      these tools can set a page's 'parent' field (it stays blank on creation,
      so a freshly created leaf page never has children)
    - Modify the child page's content
    - Set/list page tags, and confirm the new tag shows up in List Wiki Tags
    - Add/list/get a page comment
    - Delete the child and WebHome pages
    """
    space = get_random_name()
    child_page = get_random_name()
    tag = get_random_name()
    comment_text = f"Autotest comment {get_random_name()}"

    test_assistant = assistant(
        Toolkit.XWIKI,
        _PAGE_LIFECYCLE_TOOLS,
        settings=xwiki_integration,
    )

    def delete_page(page_name):
        prompt = XWIKI_DELETE_PAGE["prompt_to_assistant"].format(space, page_name)
        assistant_utils.ask_assistant(test_assistant, prompt, minimal_response=False)

    register_page = cleanup_xwiki_pages(delete_page)

    # 1. Create the WebHome page (home of the new space)
    create_home_prompt = XWIKI_CREATE_WEBHOME["prompt_to_assistant"].format(space)
    create_home_expected = XWIKI_CREATE_WEBHOME["expected_llm_answer"].format(space)
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, create_home_prompt, minimal_response=False
    )
    assert_tool_triggered(XWikiTool.CREATE_PAGE, triggered_tools)
    similarity_check.check_similarity(response, create_home_expected)
    register_page("WebHome")

    # 2. Create a child page in the same space
    create_child_prompt = XWIKI_CREATE_CHILD_PAGE["prompt_to_assistant"].format(
        space, child_page
    )
    create_child_expected = XWIKI_CREATE_CHILD_PAGE["expected_llm_answer"].format(
        space, child_page
    )
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, create_child_prompt, minimal_response=False
    )
    assert_tool_triggered(XWikiTool.CREATE_PAGE, triggered_tools)
    similarity_check.check_similarity(response, create_child_expected)
    register_page(child_page)

    # 3. The freshly created child page has no children of its own
    list_children_prompt = XWIKI_LIST_PAGE_CHILDREN["prompt_to_assistant"].format(
        space, child_page
    )
    list_children_expected = XWIKI_LIST_PAGE_CHILDREN["expected_llm_answer"].format(
        space, child_page
    )
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, list_children_prompt, minimal_response=False
    )
    assert_tool_triggered(XWikiTool.LIST_PAGE_CHILDREN, triggered_tools)
    similarity_check.check_similarity(response, list_children_expected)

    # 4. Modify the child page's content
    modify_prompt = XWIKI_MODIFY_CHILD_PAGE["prompt_to_assistant"].format(
        space, child_page
    )
    modify_expected = XWIKI_MODIFY_CHILD_PAGE["expected_llm_answer"].format(
        space, child_page
    )
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, modify_prompt, minimal_response=False
    )
    assert_tool_triggered(XWikiTool.MODIFY_PAGE, triggered_tools)
    similarity_check.check_similarity(response, modify_expected)

    # 5. Set tags on the child page
    set_tags_prompt = XWIKI_SET_PAGE_TAGS["prompt_to_assistant"].format(
        space, child_page, tag
    )
    set_tags_expected = XWIKI_SET_PAGE_TAGS["expected_llm_answer"].format(
        space, child_page, tag
    )
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, set_tags_prompt, minimal_response=False
    )
    assert_tool_triggered(XWikiTool.SET_PAGE_TAGS, triggered_tools)
    similarity_check.check_similarity(response, set_tags_expected)

    # 6. List the page's own tags
    list_page_tags_prompt = XWIKI_LIST_PAGE_TAGS["prompt_to_assistant"].format(
        space, child_page
    )
    list_page_tags_expected = XWIKI_LIST_PAGE_TAGS["expected_llm_answer"].format(
        space, child_page, tag
    )
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, list_page_tags_prompt, minimal_response=False
    )
    assert_tool_triggered(XWikiTool.LIST_PAGE_TAGS, triggered_tools)
    similarity_check.check_similarity(response, list_page_tags_expected)

    # 7. Confirm the new tag is visible wiki-wide. Checked with contains_string,
    # not similarity_check: the wiki-wide tag list grows over time and under
    # xdist other workers' tests add their own tags concurrently, so a short
    # expected claim would get swamped the same way the read-tools test's did.
    list_wiki_tags_prompt = XWIKI_LIST_WIKI_TAGS["prompt_to_assistant"].format(
        space, child_page, tag
    )
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, list_wiki_tags_prompt, minimal_response=False
    )
    assert_tool_triggered(XWikiTool.LIST_WIKI_TAGS, triggered_tools)
    assert_that(
        response,
        contains_string(tag),
        "List Wiki Tags response should mention the tag just set on the page",
    )

    # 8. Add a comment and capture its numeric id (xWiki numbers comments
    # per-page starting at 0, so a plain \d+ match is used, not a non-zero one)
    create_comment_prompt = XWIKI_CREATE_PAGE_COMMENT["prompt_to_assistant"].format(
        space, child_page, comment_text
    )
    create_comment_response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, create_comment_prompt, minimal_response=False
    )
    assert_tool_triggered(XWikiTool.CREATE_PAGE_COMMENT, triggered_tools)
    comment_id_match = re.search(r"COMMENT_ID:\s*(\d+)", create_comment_response)
    assert_that(comment_id_match, is_not(None))
    comment_id = comment_id_match.group(1)

    # 9. List comments on the page
    list_comments_prompt = XWIKI_LIST_PAGE_COMMENTS["prompt_to_assistant"].format(
        space, child_page
    )
    list_comments_expected = XWIKI_LIST_PAGE_COMMENTS["expected_llm_answer"].format(
        space, child_page, comment_text
    )
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, list_comments_prompt, minimal_response=False
    )
    assert_tool_triggered(XWikiTool.LIST_PAGE_COMMENTS, triggered_tools)
    similarity_check.check_similarity(response, list_comments_expected)

    # 10. Get the single comment by its id
    get_comment_prompt = XWIKI_GET_PAGE_COMMENT["prompt_to_assistant"].format(
        space, child_page, comment_text, comment_id
    )
    get_comment_expected = XWIKI_GET_PAGE_COMMENT["expected_llm_answer"].format(
        space, child_page, comment_text, comment_id
    )
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, get_comment_prompt, minimal_response=False
    )
    assert_tool_triggered(XWikiTool.GET_PAGE_COMMENT, triggered_tools)
    similarity_check.check_similarity(response, get_comment_expected)

    # 11. Delete the child page (WebHome is deleted by cleanup_xwiki_pages)
    delete_prompt = XWIKI_DELETE_PAGE["prompt_to_assistant"].format(space, child_page)
    delete_expected = XWIKI_DELETE_PAGE["expected_llm_answer"].format(space, child_page)
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, delete_prompt, minimal_response=False
    )
    assert_tool_triggered(XWikiTool.DELETE_PAGE, triggered_tools)
    similarity_check.check_similarity(response, delete_expected)


@pytest.mark.assistant
@pytest.mark.xwiki
@pytest.mark.api
def test_assistant_with_xwiki_page_attachments(
    assistant,
    assistant_utils,
    integration_utils,
    similarity_check,
    xwiki_integration,
    cleanup_xwiki_pages,
):
    """
    Attachment lifecycle for the 5 remaining xWiki tools (Create/List/Get/Read/
    Delete Page Attachment), against a fresh page created for this test run.
    """
    space = get_random_name()

    test_assistant = assistant(
        Toolkit.XWIKI,
        _ATTACHMENT_TOOLS,
        settings=xwiki_integration,
    )

    def delete_page(page_name):
        prompt = XWIKI_DELETE_PAGE["prompt_to_assistant"].format(space, page_name)
        assistant_utils.ask_assistant(test_assistant, prompt, minimal_response=False)

    register_page = cleanup_xwiki_pages(delete_page)

    # 1. Create the page to attach a file to
    create_prompt = XWIKI_CREATE_WEBHOME["prompt_to_assistant"].format(space)
    create_expected = XWIKI_CREATE_WEBHOME["expected_llm_answer"].format(space)
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, create_prompt, minimal_response=False
    )
    assert_tool_triggered(XWikiTool.CREATE_PAGE, triggered_tools)
    similarity_check.check_similarity(response, create_expected)
    register_page("WebHome")

    # 2. Upload and attach a file to the page
    uploaded_file = assistant_utils.upload_file_to_chat(
        FILES_PATH / XWIKI_CREATE_PAGE_ATTACHMENT["file_name"]
    )
    file_url = uploaded_file.get("file_url")
    assert_that(file_url, is_not(None))

    create_attachment_prompt = XWIKI_CREATE_PAGE_ATTACHMENT[
        "prompt_to_assistant"
    ].format(space, "WebHome")
    create_attachment_expected = XWIKI_CREATE_PAGE_ATTACHMENT[
        "expected_llm_answer"
    ].format(space, "WebHome")
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant,
        create_attachment_prompt,
        file_urls=[file_url],
        minimal_response=False,
    )
    assert_tool_triggered(XWikiTool.CREATE_PAGE_ATTACHMENT, triggered_tools)
    similarity_check.check_similarity(response, create_attachment_expected)

    # 3. List attachments on the page
    list_attachments_prompt = XWIKI_LIST_PAGE_ATTACHMENTS["prompt_to_assistant"].format(
        space, "WebHome"
    )
    list_attachments_expected = XWIKI_LIST_PAGE_ATTACHMENTS[
        "expected_llm_answer"
    ].format(space, "WebHome")
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, list_attachments_prompt, minimal_response=False
    )
    assert_tool_triggered(XWikiTool.LIST_PAGE_ATTACHMENTS, triggered_tools)
    similarity_check.check_similarity(response, list_attachments_expected)

    # 4. Get the attachment's metadata
    get_attachment_prompt = XWIKI_GET_PAGE_ATTACHMENT["prompt_to_assistant"].format(
        space, "WebHome"
    )
    get_attachment_expected = XWIKI_GET_PAGE_ATTACHMENT["expected_llm_answer"].format(
        space, "WebHome"
    )
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, get_attachment_prompt, minimal_response=False
    )
    assert_tool_triggered(XWikiTool.GET_PAGE_ATTACHMENT, triggered_tools)
    similarity_check.check_similarity(response, get_attachment_expected)

    # 5. Read the attachment's actual content
    read_attachment_prompt = XWIKI_READ_PAGE_ATTACHMENT_CONTENT[
        "prompt_to_assistant"
    ].format(space, "WebHome")
    read_attachment_expected = XWIKI_READ_PAGE_ATTACHMENT_CONTENT[
        "expected_llm_answer"
    ].format(space, "WebHome")
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, read_attachment_prompt, minimal_response=False
    )
    assert_tool_triggered(XWikiTool.READ_PAGE_ATTACHMENT_CONTENT, triggered_tools)
    similarity_check.check_similarity(response, read_attachment_expected)

    # 6. Delete the attachment
    delete_attachment_prompt = XWIKI_DELETE_PAGE_ATTACHMENT[
        "prompt_to_assistant"
    ].format(space, "WebHome")
    delete_attachment_expected = XWIKI_DELETE_PAGE_ATTACHMENT[
        "expected_llm_answer"
    ].format(space, "WebHome")
    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, delete_attachment_prompt, minimal_response=False
    )
    assert_tool_triggered(XWikiTool.DELETE_PAGE_ATTACHMENT, triggered_tools)
    similarity_check.check_similarity(response, delete_attachment_expected)


@pytest.mark.assistant
@pytest.mark.xwiki
@pytest.mark.api
@pytest.mark.skipif(
    not (
        CredentialsManager.get_parameter("XWIKI_USERNAME")
        and CredentialsManager.get_parameter("XWIKI_PASSWORD")
    ),
    reason="No xwiki Basic Auth credentials configured",
)
def test_assistant_with_xwiki_get_page_basic_and_bearer_auth(
    assistant,
    assistant_utils,
    integration_utils,
    xwiki_integration,
    xwiki_basic_integration,
    xwiki_seed_page,
):
    """
    Retrieves the same seed page under both xWiki auth modes — Bearer token
    (xwiki_integration) and Basic Auth username/password (xwiki_basic_integration)
    — to prove GET_PAGE (and therefore the shared _build_auth_headers) works
    identically for both, not just the Bearer path the rest of this file covers.
    """
    prompt = (
        f"Get the page '{xwiki_seed_page.page}' in space '{xwiki_seed_page.space}' "
        "of the 'xwiki' wiki and tell me the token value stored in it."
    )

    for integration in (xwiki_integration, xwiki_basic_integration):
        test_assistant = assistant(
            Toolkit.XWIKI,
            XWikiTool.GET_PAGE,
            settings=integration,
        )
        response, triggered_tools = assistant_utils.ask_assistant(
            test_assistant, prompt, minimal_response=False
        )
        assert_tool_triggered(XWikiTool.GET_PAGE, triggered_tools)
        assert_that(
            response,
            contains_string(xwiki_seed_page.token),
            f"GET_PAGE should return the seed token regardless of auth mode "
            f"(integration: {integration.id})",
        )
