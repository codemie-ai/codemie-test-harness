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

from codemie_test_harness.tests.enums.tools import Toolkit, AzureDevOpsWorkItemTool
from codemie_test_harness.tests.utils.ado_names import ADO_PROJECT_NAME, ado_text
from codemie_test_harness.tests.utils.ado_seed import ADO_SEED
from codemie_test_harness.tests.utils.jira_seed import Seeded

ado_work_item_get_test_data = [
    pytest.param(
        Toolkit.AZURE_DEVOPS_WORK_ITEM,
        AzureDevOpsWorkItemTool.GET_WORK_ITEM,
        Seeded(
            ADO_SEED,
            lambda seed: f"Show work item with id {seed.work_item.id}",
        ),
        Seeded(
            ADO_SEED,
            lambda seed: f"""
            Here are the details of work item with ID {seed.work_item.id}:

            - Title: {seed.work_item.title}
            - Type: {seed.work_item.type}
            - State: {seed.work_item.state}
            - Priority: {seed.work_item.priority}
            - Created Date: {seed.work_item.created_date}
            - Description: {seed.work_item.description}
            - Area Path: {ADO_PROJECT_NAME}
            - Iteration Path: {ADO_PROJECT_NAME}
            - Work Item URL: View in Azure DevOps

            If you need more details or want to view attachments or comments, please let me know!
        """,
        ),
        marks=pytest.mark.smoke,
    ),
    (
        Toolkit.AZURE_DEVOPS_WORK_ITEM,
        AzureDevOpsWorkItemTool.GET_COMMENTS,
        Seeded(
            ADO_SEED,
            lambda seed: f"Show the comments of work item with ID={seed.parent_work_item.id}",
        ),
        Seeded(
            ADO_SEED,
            lambda seed: f"""
            Here are the comments for work item ID {seed.parent_work_item.id}:

            - Author: {seed.parent_work_item.comments[0].author}
            - Date: {seed.parent_work_item.comments[0].created_date}
            - Comment: {seed.parent_work_item.comments[0].text}

            Let me know if you want more details or other work item comments!
        """,
        ),
    ),
    (
        Toolkit.AZURE_DEVOPS_WORK_ITEM,
        AzureDevOpsWorkItemTool.GET_RELATION_TYPES,
        "Show the relation types available. Provide the list of types only.",
        """
            Here are the available relation types:

            - Affects
            - Affected By
            - Referenced By
            - References
            - Tested By
            - Tests
            - Test Case
            - Shared Steps
            - Produces For
            - Consumes From
            - Duplicate
            - Duplicate Of
            - Successor
            - Predecessor
            - Child
            - Parent
            - Related
            - Remote Related
            - Attached File
            - Hyperlink
            - Artifact Link
        """,
    ),
    (
        Toolkit.AZURE_DEVOPS_WORK_ITEM,
        AzureDevOpsWorkItemTool.SEARCH_WORK_ITEMS,
        Seeded(
            ADO_SEED,
            lambda seed: (
                "Search Work Items using this query: SELECT [System.Id], [System.Title], [System.State] "
                f"FROM WorkItems WHERE [System.TeamProject] = '{ADO_PROJECT_NAME}' "
                f"AND [System.Title] = '{seed.work_item.title}'; "
                "Return the only first item.\n"
                "Output Format:\n"
                "**ID**: <id>\n"
                "   - **Title**: <title>\n"
                "   - **State**: <state>\n"
                "   - **URL**: <url>"
            ),
        ),
        Seeded(
            ADO_SEED,
            lambda seed: f"""
            Here are the work items matching your query:
            1. **ID**: {seed.work_item.id}
               - **Title**: {seed.work_item.title}
               - **State**: {seed.work_item.state}
               - **URL**: [Work Item #{seed.work_item.id}]({seed.work_item.url}).
        """,
        ),
    ),
    pytest.param(
        Toolkit.AZURE_DEVOPS_WORK_ITEM,
        AzureDevOpsWorkItemTool.GET_WORK_ITEM_ATTACHMENT_CONTENT,
        Seeded(
            ADO_SEED,
            lambda seed: (
                f"Get attachment content {seed.work_item.attachment.name} "
                f"for work item {seed.work_item.id}"
            ),
        ),
        Seeded(
            ADO_SEED,
            lambda seed: f"""
            Attachment content for **work item {seed.work_item.id}** — **{seed.work_item.attachment.name}**:

            - **MIME type:** {seed.work_item.attachment.mime_type}
            - **Size:** {seed.work_item.attachment.size} bytes
            - **Extracted content (text):**
            ```text
            {seed.work_item.attachment.content}
            ```
        """,
        ),
        marks=pytest.mark.smoke,
    ),
]

ADO_WORK_ITEM_CREATE = {
    "prompt_to_assistant": ado_text("""
        Create a new Work Item with type 'Task' and title '{}' and description 'Greeting from CodeMie!'
        in the project '<ADO_PROJECT>'. Provide link to the created Work Item.
    """),
    "expected_llm_answer": ado_text("""
        The work item has been successfully created. Below are the details:

        - **Title**: {}
        - **Description**: Greeting from CodeMie!
        - **Type**: Task
        - **Project**: <ADO_PROJECT>

        You can view the work item using [this link](<ADO_URL>/<ADO_ORG>/<ADO_PROJECT>/_apis/wit/workItems/{}).
    """),
}

ADO_WORK_ITEM_UPDATE = {
    "prompt_to_assistant": ado_text("""
        Update the Work Item with the ID '{}' in the project '<ADO_PROJECT>'.
        Change the type to 'Epic' and title to '{}' and description to 'Updated description'.
    """),
    "expected_llm_answer": ado_text("""
        The work item with ID `{}` in the project `<ADO_PROJECT>` has been successfully updated with the following changes:
        - Type: `Epic`
        - Title: `{}`
        - Description: `Updated description`
    """),
}

ADO_WORK_ITEM_LINK = {
    "prompt_to_assistant": ado_text("""
        Run {{'source_id': {child_id}, 'target_id': {parent_id}, 'link_type': 'System.LinkTypes.Hierarchy-Reverse'}} to
        link the Work Items with the ID {parent_id} to be the parent of Work Item with ID '{child_id}' in
        the project '<ADO_PROJECT>'
    """),
    "expected_llm_answer": """
        The Work Item with ID {parent_id} has been successfully linked as the parent of the Work Item with ID `{child_id}`
        using the `System.LinkTypes.Hierarchy-Reverse` link type.
    """,
}

ADO_WORK_ITEM_CREATE_WITH_FILE = {
    "file_name": "test.txt",
    "prompt_to_assistant": ado_text("""
        Create a new Work Item with type 'Task' and title '{}' and description 'Greeting from CodeMie!'
        in the project '<ADO_PROJECT>'. Attach the uploaded file to the work item.
        Provide link to the created Work Item.
    """),
    "expected_llm_answer": ado_text("""
        The work item has been successfully created. Below are the details:

        - **Title**: {}
        - **Description**: Greeting from CodeMie!
        - **Type**: Task
        - **Project**: <ADO_PROJECT>

        The file test.txt has been attached to the work item.
    """),
}

ADO_WORK_ITEM_UPDATE_WITH_FILE = {
    "file_name": "test.txt",
    "prompt_to_assistant": ado_text("""
        Update the Work Item with the ID '{}' in the project '<ADO_PROJECT>'.
        Change the type to 'Epic' and title to '{}' and description to 'Updated description'.
        Attach the uploaded file to the work item.
    """),
    "expected_llm_answer": ado_text("""
        The work item with ID `{}` in the project `<ADO_PROJECT>` has been successfully updated with the following changes:
        - Type: `Epic`
        - Title: `{}`
        - Description: `Updated description`

        The file test.txt has been attached to the work item.
    """),
}

ADO_WORK_ITEM_UPDATE_TITLE_ONLY = {
    "prompt_to_assistant": ado_text("""
        Update the Work Item with the ID '{}' in the project '<ADO_PROJECT>'.
        Change the title to '{}'. Do not attach or change any files.
    """),
    "expected_llm_answer": ado_text("""
        The work item with ID `{}` in the project `<ADO_PROJECT>` has been successfully updated with the following changes:
        - Title: `{}`
    """),
}

ADO_WORK_ITEM_ATTACH_ADDITIONAL_FILE = {
    "prompt_to_assistant": ado_text("""
        Update the Work Item with the ID '{}' in the project '<ADO_PROJECT>'.
        Attach the uploaded file(s) to the work item. Do not change the title or description.
    """),
    "expected_llm_answer": """
        The uploaded file(s) have been successfully attached to the work item with ID `{}`.
    """,
}

ADO_WORK_ITEM_REATTACH_REVISED_FILE = {
    "prompt_to_assistant": ado_text("""
        Update the Work Item with the ID '{}' in the project '<ADO_PROJECT>' using the
        update_work_item tool. Attach the uploaded file directly as a file attachment to
        the work item. Do not read, parse, summarize, or extract content from the file —
        treat it as an opaque attachment only. Do not change the title or description.
    """),
    "expected_llm_answer": """
        The uploaded file has been successfully attached to the work item with ID `{}`.
    """,
}

ADO_WORK_ITEM_ATTACH_MULTIPLE_FILES = {
    "prompt_to_assistant": ado_text("""
        Update the Work Item with the ID '{}' in the project '<ADO_PROJECT>' using the
        update_work_item tool. Attach both previously uploaded files directly as file
        attachments to the work item. Do not read, parse, summarize, or extract content
        from either file — treat them as opaque attachments only. Do not change the
        title or description.
    """),
    "expected_llm_answer": """
        The uploaded files have been successfully attached to the work item with ID `{}`.
    """,
}

ADO_WORK_ITEM_GET_WITH_ATTACHMENTS = {
    "prompt_to_assistant": "Get work item with ID {} including its attachments. Show the content of all attached files.",
    "expected_llm_answer": """
        Work item #{} has an attached file.

        **Attachment(s):**

        File: test.txt
        Content:
        ```txt
        This file is for test purpose.
        ```
    """,
}

ADO_WORK_ITEM_CREATE_COMMENT = {
    "prompt_to_assistant": ado_text("""
        Create a comment 'Autotest comment from CodeMie!' on the Work Item with ID '{}' in the project '<ADO_PROJECT>'.
    """),
    "expected_llm_answer": """
        The comment has been successfully added to work item ID `{}`.

        - **Comment**: Autotest comment from CodeMie!
    """,
}

ADO_WORK_ITEM_MOVE = {
    "prompt_link_to_parent_1": ado_text(
        "Run {{'source_id': {child_id}, 'target_id': {parent_1_id}, "
        "'link_type': 'System.LinkTypes.Hierarchy-Reverse'}} to set work item "
        "{parent_1_id} as the parent of work item {child_id} in project '<ADO_PROJECT>'."
    ),
    "prompt_move_to_parent_2": ado_text(
        "Move the ADO work item {child_id} in project '<ADO_PROJECT>' to be a child of "
        "work item {parent_2_id}. It currently has a different parent — remove the old "
        "parent relation and add the new one."
    ),
    "expected_move_response": (
        "Work item {child_id} has been successfully moved to parent work item {parent_2_id}."
    ),
}

ADO_WORK_ITEMS_DATASOURCE = {
    "prompt_to_assistant": Seeded(
        ADO_SEED,
        lambda seed: f"Show work item with id {seed.work_item.id}",
    ),
    "expected_llm_answer": Seeded(
        ADO_SEED,
        lambda seed: f"""
        Here is the information about the work item with ID {seed.work_item.id}:

        - **Title:** {seed.work_item.title}
        - **Description:** {seed.work_item.description}
        - **Type:** {seed.work_item.type}
        - **State:** {seed.work_item.state}
        - **Area:** {ADO_PROJECT_NAME}
        - **Iteration:** {ADO_PROJECT_NAME}
        - **Priority:** {seed.work_item.priority}

        Let me know if you need more details or actions on this work item.
    """,
    ),
}
