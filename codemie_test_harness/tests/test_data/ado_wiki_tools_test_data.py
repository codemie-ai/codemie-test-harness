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
from codemie_test_harness.tests.utils.ado_names import ado_text
from codemie_test_harness.tests.utils.ado_seed import ADO_SEED
from codemie_test_harness.tests.utils.jira_seed import Seeded


def _format_wiki_comments(comments) -> str:
    return "\n\n".join(
        f"{comment.text}\nAuthor: {comment.author}\nCreated: {comment.created_date}"
        for comment in reversed(comments)
    )


def _comment_texts(comments) -> str:
    return "\n".join(comment.text for comment in comments)


ado_wiki_get_test_data = [
    pytest.param(
        Toolkit.AZURE_DEVOPS_WIKI,
        AzureDevOpsWikiTool.GET_WIKI_PAGE_BY_ID,
        Seeded(
            ADO_SEED,
            lambda seed: ado_text(
                f"In the <ADO_WIKI> show page id {seed.wiki_parent.id} content"
            ),
        ),
        Seeded(
            ADO_SEED,
            lambda seed: ado_text(f"""
            The content of the page with ID {seed.wiki_parent.id} in the `<ADO_WIKI>` is:

            ```
                {seed.wiki_parent.content}
            ```
        """),
        ),
        marks=pytest.mark.smoke,
    ),
    (
        Toolkit.AZURE_DEVOPS_WIKI,
        AzureDevOpsWikiTool.GET_WIKI,
        ado_text("Show the details for <ADO_WIKI>"),
        Seeded(
            ADO_SEED,
            lambda seed: ado_text(f"""
            - **Name**: <ADO_WIKI>
            - **Project ID**: {seed.project_id}
            - **Repository ID**: {seed.wiki_repository_id}
            - **Type**: projectWiki
            - **ID**: {seed.wiki_repository_id}
            - **Remote URL**: [<ADO_WIKI> Remote URL](<ADO_URL>/<ADO_ORG>/{seed.project_id}/_wiki/wikis/{seed.wiki_repository_id})
            - **API URL**: [<ADO_WIKI> API URL](<ADO_URL>/<ADO_ORG>/{seed.project_id}/_apis/wiki/wikis/{seed.wiki_repository_id})
        """),
        ),
    ),
    (
        Toolkit.AZURE_DEVOPS_WIKI,
        AzureDevOpsWikiTool.GET_WIKI_PAGE_BY_PATH,
        Seeded(
            ADO_SEED,
            lambda seed: ado_text(
                f"Show the content of the root page with '{seed.wiki_parent.path}' path in '<ADO_WIKI>' project wiki."
            ),
        ),
        Seeded(
            ADO_SEED,
            lambda seed: ado_text(f"""
            The content of the page with the path {seed.wiki_parent.path} in the <ADO_WIKI> project wiki is:
            ```
                {seed.wiki_parent.content}
            ```
        """),
        ),
    ),
    pytest.param(
        Toolkit.AZURE_DEVOPS_WIKI,
        AzureDevOpsWikiTool.GET_WIKI_PAGE_COMMENTS_BY_ID,
        Seeded(
            ADO_SEED,
            lambda seed: ado_text(
                f"Get all comments from wiki page with ID {seed.wiki_child.id} in <ADO_WIKI>"
            ),
        ),
        Seeded(
            ADO_SEED,
            lambda seed: f"""
            Here are the comments for the {seed.wiki_child.title} wiki page:

            {_format_wiki_comments(seed.wiki_child.comments)}
        """,
        ),
        marks=pytest.mark.smoke,
    ),
    pytest.param(
        Toolkit.AZURE_DEVOPS_WIKI,
        AzureDevOpsWikiTool.GET_WIKI_PAGE_STATS_BY_ID,
        Seeded(
            ADO_SEED,
            lambda seed: ado_text(
                f"Get the page view statistics for the wiki page with ID {seed.wiki_child.id} in '<ADO_WIKI>' for the last 30 days."
            ),
        ),
        Seeded(
            ADO_SEED,
            lambda seed: ado_text(f"""
            Here are the page view statistics for the wiki page with ID {seed.wiki_child.id} in '<ADO_WIKI>' over the last 30 days:

            - Wiki Page Path: {seed.wiki_child.path}

            View-count data (total views, days with views, and a daily breakdown) for this period is returned.
            Let me know if you need a chart or any further detail!
        """),
        ),
        marks=pytest.mark.smoke,
    ),
    (
        Toolkit.AZURE_DEVOPS_WIKI,
        AzureDevOpsWikiTool.GET_WIKI_PAGE_STATS_BY_PATH,
        Seeded(
            ADO_SEED,
            lambda seed: ado_text(
                f"Get the page view statistics for the wiki page '{seed.wiki_child.path}' in '<ADO_WIKI>' for the last 30 days."
            ),
        ),
        Seeded(
            ADO_SEED,
            lambda seed: ado_text(f"""
            Here are the page view statistics for the wiki page with ID {seed.wiki_child.id} in '<ADO_WIKI>' over the last 30 days:

            - Wiki Page Path: {seed.wiki_child.path}

            View-count data (total views, days with views, and a daily breakdown) for this period is returned.
            Let me know if you need a chart or any further detail!
        """),
        ),
    ),
    (
        Toolkit.AZURE_DEVOPS_WIKI,
        AzureDevOpsWikiTool.GET_WIKI_PAGE_COMMENTS_BY_PATH,
        Seeded(
            ADO_SEED,
            lambda seed: ado_text(
                f"Retrieve all comments from wiki page '{seed.wiki_child.path}' in <ADO_WIKI>"
            ),
        ),
        Seeded(
            ADO_SEED,
            lambda seed: f"""
            Here are the comments for the {seed.wiki_child.title} wiki page:

            {_format_wiki_comments(seed.wiki_child.comments)}
        """,
        ),
    ),
]

ADO_WIKI_CREATE_PAGE = {
    "prompt_to_assistant": ado_text("""
        Create a new root page in '<ADO_WIKI>' project wiki with title '{}' and content 'Greeting from CodeMie!'.
        version_identifier = 'main'
    """),
    "expected_llm_answer": ado_text("""
        The page titled "{}" has been successfully created in the "<ADO_WIKI>" project wiki with the content:

        ```
        Greeting from CodeMie!
        ```
    """),
}

ADO_WIKI_RENAME_PAGE = {
    "prompt_to_assistant": ado_text("""
        Rename the page in '<ADO_WIKI>' project wiki '/{}' with new title '{}-Renamed'.
        Use 'version_identifier': 'main', 'version_type': 'branch'
    """),
    "expected_llm_answer": ado_text("""
        The page in the `<ADO_PROJECT>` wiki has been successfully renamed from `{}` to `{}-Renamed`.
    """),
}

ADO_WIKI_MODIFY_PAGE = {
    "prompt_to_assistant": ado_text("""
        Update the content of '/{}-Renamed' page in '<ADO_WIKI>' project wiki by adding new string: 
        'Updated content' to the end of the page. Assume you are appending to an empty page.
        Use 'version_identifier': 'main', 'version_type': 'branch'
    """),
    "expected_llm_answer": ado_text("""
        The content of the '{}-Renamed' page in the '<ADO_WIKI>' project wiki has been successfully 
        updated to include the string 'Updated content'.
    """),
}

ADO_WIKI_DELETE_PAGE = {
    "prompt_to_assistant": ado_text(
        "Delete the '/{}-Renamed' page located on root level in '<ADO_WIKI>' project wiki."
    ),
    "expected_llm_answer": ado_text("""
        The '{}-Renamed' page in the '<ADO_WIKI>' project wiki has been successfully deleted.
    """),
}

# === NESTED WIKI PAGES TEST DATA ===

ADO_WIKI_CREATE_NESTED_PARENT = {
    "prompt_to_assistant": ado_text("""
        Create a new root page in '<ADO_WIKI>' project wiki with title '{}' and content 'Parent Page Content'.
        version_identifier = 'main'
    """),
    "expected_llm_answer": ado_text("""
        The page titled "{}" has been successfully created in the "<ADO_WIKI>" project wiki with the content:

        ```
        Parent Page Content
        ```
    """),
}

ADO_WIKI_CREATE_NESTED_CHILD = {
    "prompt_to_assistant": ado_text("""
        Create a child page in '<ADO_WIKI>' project wiki under parent page '/{}'
        with title '{}' and content 'Child Page Content'.
        version_identifier = 'main'
    """),
    "expected_llm_answer": ado_text("""
        The child page titled "{}" has been successfully created under parent page "{}"
        in the "<ADO_WIKI>" project wiki with the content:

        ```
        Child Page Content
        ```
    """),
}

ADO_WIKI_CREATE_NESTED_GRANDCHILD = {
    "prompt_to_assistant": ado_text("""
        Create a nested page in '<ADO_WIKI>' project wiki under parent page '/{}/{}'
        with title '{}' and content 'Grandchild Page Content'.
        version_identifier = 'main'
    """),
    "expected_llm_answer": ado_text("""
        The nested page titled "{}" has been successfully created under parent page "{}/{}"
        in the "<ADO_WIKI>" project wiki.
    """),
}

ADO_WIKI_GET_NESTED_CHILD = {
    "prompt_to_assistant": ado_text("""
        Show the content of the nested page with '/{}/{}' path in '<ADO_WIKI>' project wiki.
    """),
    "expected_llm_answer": ado_text("""
        The content of the nested page with the path /{}/{} in the <ADO_WIKI> project wiki is:
        ```
        Child Page Content
        ```
    """),
}

ADO_WIKI_MODIFY_NESTED_PAGE = {
    "prompt_to_assistant": ado_text("""
        Update the content of '/{}/{}' nested page in '<ADO_WIKI>' project wiki
        by adding new string: 'Updated nested content' to the end of the page.
        Use 'version_identifier': 'main', 'version_type': 'branch'
    """),
    "expected_llm_answer": ado_text("""
        The content of the '{}/{}' nested page in the '<ADO_WIKI>' project wiki
        has been successfully updated to include the string 'Updated nested content'.
    """),
}

ADO_WIKI_DELETE_NESTED_CHILD = {
    "prompt_to_assistant": ado_text(
        "Delete the '/{}/{}' nested page in '<ADO_WIKI>' project wiki."
    ),
    "expected_llm_answer": ado_text("""
        The '{}/{}' nested page in the '<ADO_WIKI>' project wiki has been successfully deleted.
    """),
}

ADO_WIKI_DELETE_NESTED_PARENT = {
    "prompt_to_assistant": ado_text(
        "Delete the '/{}' parent page in '<ADO_WIKI>' project wiki."
    ),
    "expected_llm_answer": ado_text("""
        The '{}' parent page in the '<ADO_WIKI>' project wiki has been successfully deleted.
    """),
}

ADO_WIKI_MOVE_PAGE = {
    "prompt_to_assistant": ado_text("""
        Move the page '/{0}' in '<ADO_WIKI>' project wiki.
        source_page_path: '/{0}'
        destination_page_path: '/{1}/{0}'
        Use 'version_identifier': 'main', 'version_type': 'branch'
    """),
    "expected_llm_answer": ado_text("""
        The page '/{0}' in the '<ADO_WIKI>' project wiki has been successfully moved to '/{1}/{0}'.
    """),
}

ADO_WIKI_GET_MOVED_PAGE = {
    "prompt_to_assistant": ado_text("""
        Show the content of the page '/{0}' in '<ADO_WIKI>' project wiki.
    """),
    "expected_llm_answer": ado_text("""
        The content of the page '/{0}' in the '<ADO_WIKI>' project wiki is:
        ```
        Greeting from CodeMie!
        ```
    """),
}

ADO_WIKI_GET_PARENT_AFTER_MOVE = {
    "prompt_to_assistant": ado_text("""
        Show the content of the page '/{0}' in '<ADO_WIKI>' project wiki.
    """),
    "expected_llm_answer": ado_text("""
        The content of the page '/{0}' in the '<ADO_WIKI>' project wiki is:
        ```
        Parent Page Content
        ```
    """),
}

ADO_WIKI_ADD_ATTACHMENT = {
    "file_name": "test.txt",
    "prompt_to_assistant": ado_text("""
        Attach the uploaded file to the wiki page '/{}'
        in '<ADO_WIKI>'. Use 'autotest-attachment' as the attachment name.
    """),
    "expected_llm_answer": ado_text("""
        The file has been successfully attached to the wiki page '/{}' in '<ADO_WIKI>'.
        You can view the updated page at <ADO_URL>/<ADO_ORG>/<ADO_PROJECT>/_wiki/
    """),
}

ADO_WIKI_GET_PAGE_WITH_ATTACHMENT = {
    "prompt_to_assistant": ado_text("""
        Get the content of the '/{}' page in '<ADO_WIKI>' project wiki.
    """),
    "expected_llm_answer": ado_text("""
        The content of the "/{}" page in the "<ADO_WIKI>" wiki includes:

        Greeting from CodeMie!

        The page has an attachment listed in the Attachments section.
    """),
}

ADO_WIKI_ADD_COMMENT_BY_PATH = {
    "prompt_to_assistant": ado_text("""
        Add a comment 'Autotest comment' to the wiki page '/{}'
        in '<ADO_WIKI>'.
    """),
    "expected_llm_answer": ado_text("""
        The comment has been successfully added to the wiki page '/{}' in '<ADO_WIKI>'.
    """),
}

ADO_WIKI_ADD_COMMENT_BY_ID = {
    "create_prompt": ado_text("""
        Create a new root page in '<ADO_WIKI>' project wiki with title '{}' and content 'Greeting from CodeMie!'.
        version_identifier = 'main'.
        After creating, report the numeric value of the 'id' field from the page response.
    """),
    "prompt_to_assistant": ado_text(
        "Add the comment 'Autotest comment' to the wiki page with ID {} in '<ADO_WIKI>'."
    ),
    "expected_llm_answer": ado_text("""
        The comment has been successfully added to the wiki page with ID {} in '<ADO_WIKI>'.
    """),
}

ADO_WIKI_ADD_COMMENT_REPLY = {
    "prompt_to_assistant": ado_text("""
        On wiki page '/{page_name}' in '<ADO_WIKI>':
        1. Get all comments on this page to find the most recent comment ID.
        2. Add a reply 'Autotest reply comment' to that comment thread using the comment ID as parent_comment_id.
    """),
    "expected_llm_answer": ado_text("""
        The reply 'Autotest reply comment' has been successfully added to the comment thread
        on wiki page '/{page_name}' in '<ADO_WIKI>'.
    """),
}

ADO_WIKI_ADD_COMMENT_WITH_ATTACHMENT = {
    "file_name": "test.txt",
    "prompt_to_assistant": ado_text("""
        Add a comment 'Autotest comment with attachment' to the wiki page '/{}'
        in '<ADO_WIKI>' and attach the uploaded file to the comment.
    """),
    "expected_llm_answer": ado_text("""
        The comment with attachment has been successfully added to the wiki page '/{}' in '<ADO_WIKI>'.
        The file test.txt has been uploaded and linked to the comment.
    """),
}

ADO_WIKI_ADD_STANDALONE_ATTACHMENT_COMMENT = {
    "file_name": "test.txt",
    "prompt_to_assistant": ado_text("""
        Post the uploaded file as a standalone comment (without any text body)
        on the wiki page '/{}'  in '<ADO_WIKI>'.
    """),
    "expected_llm_answer": ado_text("""
        The file attachment has been successfully posted as a comment on the wiki page '/{}' in '<ADO_WIKI>'.
        The file test.txt has been uploaded and linked to the comment.
    """),
}

ADO_WIKI_DATASOURCE = {
    "prompt_to_assistant": Seeded(
        ADO_SEED,
        lambda seed: ado_text(
            f"Show page under <ADO_WIKI> named {seed.wiki_parent.title}."
        ),
    ),
    "expected_llm_answer": Seeded(
        ADO_SEED,
        lambda seed: ado_text(f"""
        Here is the content of the page {seed.wiki_parent.title} under <ADO_WIKI>:
            {seed.wiki_parent.content}
        Let me know if you need more information or details from other pages
    """),
    ),
}

ADO_WIKI_DATASOURCE_COMMENTS = {
    "prompt_to_assistant": Seeded(
        ADO_SEED,
        lambda seed: ado_text(
            f"Search for comments on the '{seed.wiki_child.title}' in <ADO_WIKI>. Show me what comments exist on this page."
        ),
    ),
    "expected_llm_answer": Seeded(
        ADO_SEED,
        lambda seed: f"""
        Here are the comments on the {seed.wiki_child.title} page:

        {_comment_texts(seed.wiki_child.comments)}
    """,
    ),
}

ADO_WIKI_DATASOURCE_ATTACHMENTS = {
    "prompt_to_assistant": Seeded(
        ADO_SEED,
        lambda seed: (
            ado_text(
                "Search for information about the CodeMie Test Harness seed attachment "
                "in <ADO_WIKI>. What page and file contains this info?"
            )
        ),
    ),
    "expected_llm_answer": Seeded(
        ADO_SEED,
        lambda seed: ado_text(f"""
        The information about the CodeMie Test Harness seed attachment in <ADO_WIKI> is found on the following page and file:

       - **Page:** {seed.wiki_child.title}
       - **File:** `{seed.wiki_child.attachment.name}` (attached to the above page)
    """),
    ),
}

ADO_WIKI_DATASOURCE_PAGE_CONTENT = {
    "prompt_to_assistant": Seeded(
        ADO_SEED,
        lambda seed: ado_text(
            f"Search for the page '{seed.wiki_child.title}' in <ADO_WIKI>. Show me the content of this page."
        ),
    ),
    "expected_llm_answer": Seeded(
        ADO_SEED,
        lambda seed: ado_text(f"""
        The page {seed.wiki_child.title} contains the following content:
        {seed.wiki_child.content}
    """),
    ),
}

ADO_WIKI_GET_COMMENTS_AFTER_ADD = {
    "prompt_to_assistant": ado_text(
        "Get all comments on the wiki page '/{page_name}' in '<ADO_WIKI>'."
    ),
    "expected_llm_answer": """
        The comments on the wiki page '/{page_name}' include:
        Autotest comment
    """,
}

ADO_WIKI_GET_COMMENTS_AFTER_REPLY = {
    "prompt_to_assistant": ado_text(
        "Get all comments on the wiki page '/{page_name}' in '<ADO_WIKI>'."
    ),
    "expected_llm_answer": """
        The comments on the wiki page '/{page_name}' include the reply:
        Autotest reply comment
    """,
}

ADO_WIKI_GET_COMMENTS_WITH_ATTACHMENT = {
    "prompt_to_assistant": ado_text(
        "Get all comments on the wiki page '/{page_name}' in '<ADO_WIKI>' and list any attachments in those comments."
    ),
    "expected_llm_answer": """
        The comments on the wiki page '/{page_name}' include a comment with an attached file test.txt.
    """,
}
