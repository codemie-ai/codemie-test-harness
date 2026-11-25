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

"""The Generic Confluence tool attaches files of the current conversation to a page.

A file is generated in the conversation by writing it into the conversation's workspace; an
uploaded file comes with the chat request. Each test checks two things the test can read: the
tool output saved in the conversation thoughts, and the page's attachments read back from
Confluence itself.
"""

from dataclasses import dataclass

import pytest
from hamcrest import (
    all_of,
    assert_that,
    contains_string,
    empty,
    equal_to,
    has_item,
    is_not,
)

from codemie_test_harness.tests.enums.tools import ProjectManagementTool, Toolkit
from codemie_test_harness.tests.test_data.confluence_attachments_test_data import (
    AMBIGUOUS_MESSAGE,
    ATTACHED_MESSAGE,
    ATTACHED_TO_PAGE,
    EMPTY_FILE_NAME,
    EMPTY_MESSAGE,
    EMPTY_OR_MISSING_VARIANTS,
    HTTP_RESULT_PREFIX,
    NON_UPLOAD_METHODS,
    NOT_FOUND_MESSAGE,
    OUTCOME_MESSAGE,
    PARTIAL_FILES,
    UNMATCHED_NAME_VARIANTS,
    attach_prompt,
    attachment_page_title,
    json_report_content,
    json_report_name,
    page_body,
    random_suffix,
)
from codemie_test_harness.tests.utils.base_utils import assert_tool_triggered
from codemie_test_harness.tests.utils.confluence_utils import ConfluenceUtils
from codemie_test_harness.tests.utils.workspace_file_utils import (
    workspace_path_of_upload,
)
from codemie_test_harness.tests.utils.workspace_script_utils import upload_text_file

SUCCESS_WORDING = "Successfully attached"


@dataclass
class AttachmentPage:
    page_id: str
    marker: str


@dataclass
class ConversationWorkspace:
    conversation_id: str
    workspace_id: str


@pytest.fixture(scope="module")
def confluence_utils():
    return ConfluenceUtils(is_cloud=False)


@pytest.fixture
def attachment_page(confluence_utils, confluence_page_cleanup) -> AttachmentPage:
    """A fresh Confluence Server page with no attachments; deleted at teardown with its attachments."""
    title = attachment_page_title()
    confluence_page_cleanup.append(title)
    marker = random_suffix()
    page_id = confluence_utils.create_page(title, page_body(marker))
    return AttachmentPage(page_id=page_id, marker=marker)


@pytest.fixture
def confluence_assistant(assistant, confluence_integration):
    return assistant(
        Toolkit.PROJECT_MANAGEMENT,
        ProjectManagementTool.CONFLUENCE,
        settings=confluence_integration,
    )


@pytest.fixture
def conversation_workspace(client, conversation_utils, confluence_assistant):
    """Factory ``() -> ConversationWorkspace``: a conversation of the default user with its workspace.

    Every conversation is deleted at teardown."""
    created = []

    def _create() -> ConversationWorkspace:
        conversation_id = conversation_utils.create_conversation(
            initial_assistant_id=confluence_assistant.id, folder=""
        ).get("id")
        created.append(conversation_id)
        workspace = client.workspaces.create(conversation_id)
        return ConversationWorkspace(
            conversation_id=conversation_id, workspace_id=workspace.id
        )

    yield _create
    for conversation_id in created:
        try:
            conversation_utils.delete_conversation(conversation_id)
        except Exception:
            pass


def write_generated_file(client, conversation: ConversationWorkspace, name, content):
    """Write a file into the conversation workspace and check it is listed there."""
    client.workspaces.write_file(conversation.workspace_id, name, content)
    paths = [
        item.path for item in client.workspaces.list_files(conversation.workspace_id)
    ]
    assert_that(paths, has_item(name), f"'{name}' is in the workspace")


def ask_to_attach(
    assistant_utils,
    assistant,
    conversation: ConversationWorkspace,
    prompt: str,
    file_urls=(),
):
    """Send the prompt in the conversation and check the Generic Confluence tool ran."""
    _, triggered_tools = assistant_utils.ask_assistant(
        assistant,
        prompt,
        minimal_response=False,
        conversation_id=conversation.conversation_id,
        file_urls=file_urls,
        extract_failed_tools=True,
    )
    assert_tool_triggered(ProjectManagementTool.CONFLUENCE, triggered_tools)


def confluence_tool_output(conversation_utils, conversation_id: str) -> str:
    """Every message the Generic Confluence tool left in the saved conversation thoughts, joined."""
    history = conversation_utils.get_conversation_by_id(conversation_id).history
    return "\n".join(
        thought.message or ""
        for item in history
        for thought in item.thoughts or []
        if "confluence" in thought.author_name.lower()
    )


def attachment_titles(confluence_utils, page_id: str) -> list[str]:
    return [item["title"] for item in confluence_utils.list_attachments(page_id)]


@pytest.mark.assistant
@pytest.mark.project_management
@pytest.mark.confluence
@pytest.mark.api
def test_attach_generated_json_file_to_confluence_page_by_exact_name(
    client,
    assistant_utils,
    conversation_utils,
    confluence_utils,
    confluence_assistant,
    conversation_workspace,
    attachment_page,
):
    # @case confluence-generated-file-attachments_TC_001
    conversation = conversation_workspace()
    name = json_report_name()
    json_marker = random_suffix()
    content = json_report_content(json_marker)
    write_generated_file(client, conversation, name, content)

    ask_to_attach(
        assistant_utils,
        confluence_assistant,
        conversation,
        attach_prompt(attachment_page.page_id, "POST", {"file": name}),
    )

    output = confluence_tool_output(conversation_utils, conversation.conversation_id)
    assert_that(
        output,
        all_of(
            contains_string(ATTACHED_MESSAGE.format(name=name)),
            contains_string(ATTACHED_TO_PAGE.format(page_id=attachment_page.page_id)),
        ),
        "the tool reports the file attached to the page",
    )
    attachments = confluence_utils.list_attachments(attachment_page.page_id)
    assert_that(
        [item["title"] for item in attachments],
        equal_to([name]),
        "the page holds exactly one attachment, named like the generated file",
    )
    assert_that(
        confluence_utils.download_attachment(attachments[0]),
        equal_to(content.encode("utf-8")),
        "the attachment holds the generated file's bytes",
    )
    assert_that(
        confluence_utils.get_page_storage_body(attachment_page.page_id),
        is_not(contains_string(json_marker)),
        "the JSON content is not written into the page body",
    )


@pytest.mark.assistant
@pytest.mark.project_management
@pytest.mark.confluence
@pytest.mark.api
def test_attach_file_generated_in_another_conversation_is_not_found(
    client,
    assistant_utils,
    conversation_utils,
    confluence_utils,
    confluence_assistant,
    conversation_workspace,
    attachment_page,
):
    # @case confluence-generated-file-attachments_TC_002
    conversation_a = conversation_workspace()
    conversation_b = conversation_workspace()
    own_name = json_report_name("own")
    foreign_name = json_report_name()
    write_generated_file(client, conversation_a, own_name, json_report_content("a"))
    write_generated_file(client, conversation_b, foreign_name, json_report_content("b"))

    ask_to_attach(
        assistant_utils,
        confluence_assistant,
        conversation_a,
        attach_prompt(attachment_page.page_id, "POST", {"file": foreign_name}),
    )

    assert_that(
        confluence_tool_output(conversation_utils, conversation_a.conversation_id),
        contains_string(
            NOT_FOUND_MESSAGE.format(name=foreign_name, available=own_name)
        ),
        "the file of conversation B is not found, and only conversation A's file is offered",
    )
    assert_that(
        attachment_titles(confluence_utils, attachment_page.page_id),
        empty(),
        "nothing is attached to the page",
    )


@pytest.mark.assistant
@pytest.mark.project_management
@pytest.mark.confluence
@pytest.mark.api
@pytest.mark.parametrize(
    "variant",
    UNMATCHED_NAME_VARIANTS,
    ids=[variant.variant for variant in UNMATCHED_NAME_VARIANTS],
)
def test_attach_unmatched_file_name_reports_not_found_and_attaches_nothing(
    client,
    assistant_utils,
    conversation_utils,
    confluence_utils,
    confluence_assistant,
    conversation_workspace,
    attachment_page,
    variant,
):
    # @case confluence-generated-file-attachments_TC_003
    conversation = conversation_workspace()
    suffix = random_suffix()
    known_name = f"report-{suffix}.json"
    unknown_name = f"{variant.unknown_prefix}-{suffix}.json"
    write_generated_file(client, conversation, known_name, json_report_content(suffix))
    requested = [known_name, unknown_name] if variant.include_known else unknown_name

    ask_to_attach(
        assistant_utils,
        confluence_assistant,
        conversation,
        attach_prompt(attachment_page.page_id, "POST", {variant.param: requested}),
    )

    assert_that(
        confluence_tool_output(conversation_utils, conversation.conversation_id),
        all_of(
            contains_string(
                NOT_FOUND_MESSAGE.format(name=unknown_name, available=known_name)
            ),
            is_not(contains_string(SUCCESS_WORDING)),
        ),
        "the unmatched name is reported with the available files, and nothing is attached",
    )
    assert_that(
        attachment_titles(confluence_utils, attachment_page.page_id),
        empty(),
        "no attachment, not even the known file",
    )


@pytest.mark.assistant
@pytest.mark.project_management
@pytest.mark.confluence
@pytest.mark.api
@pytest.mark.parametrize(
    "variant",
    EMPTY_OR_MISSING_VARIANTS,
    ids=[variant.variant for variant in EMPTY_OR_MISSING_VARIANTS],
)
def test_attach_empty_file_and_no_file_named_get_distinct_messages(
    client,
    assistant_utils,
    conversation_utils,
    confluence_utils,
    confluence_assistant,
    conversation_workspace,
    attachment_page,
    variant,
):
    # @case confluence-generated-file-attachments_TC_004
    conversation = conversation_workspace()
    # assumed: the workspace write accepts empty content and stores a 0-byte file.
    write_generated_file(client, conversation, EMPTY_FILE_NAME, "")

    ask_to_attach(
        assistant_utils,
        confluence_assistant,
        conversation,
        attach_prompt(attachment_page.page_id, "POST", variant.params),
    )

    assert_that(
        confluence_tool_output(conversation_utils, conversation.conversation_id),
        all_of(
            *[contains_string(expected) for expected in variant.expected],
            is_not(contains_string(variant.other_variant_message)),
        ),
        f"the {variant.variant} message is reported, not the other variant's",
    )
    assert_that(
        attachment_titles(confluence_utils, attachment_page.page_id),
        empty(),
        "nothing is attached to the page",
    )


@pytest.mark.assistant
@pytest.mark.project_management
@pytest.mark.confluence
@pytest.mark.api
def test_attach_several_files_partly_reports_attached_and_not_attempted(
    client,
    assistant_utils,
    conversation_utils,
    confluence_utils,
    confluence_assistant,
    conversation_workspace,
    attachment_page,
):
    # @case confluence-generated-file-attachments_TC_005
    conversation = conversation_workspace()
    first, empty_file, last = PARTIAL_FILES
    write_generated_file(client, conversation, first, json_report_content("a"))
    write_generated_file(client, conversation, empty_file, "")
    write_generated_file(client, conversation, last, json_report_content("c"))

    ask_to_attach(
        assistant_utils,
        confluence_assistant,
        conversation,
        attach_prompt(attachment_page.page_id, "POST", {"files": PARTIAL_FILES}),
    )

    assert_that(
        confluence_tool_output(conversation_utils, conversation.conversation_id),
        contains_string(
            OUTCOME_MESSAGE.format(
                error=EMPTY_MESSAGE.format(name=empty_file),
                done=first,
                remaining=last,
            )
        ),
        "the tool lists the attached file and the file it never tried separately",
    )
    assert_that(
        attachment_titles(confluence_utils, attachment_page.page_id),
        equal_to([first]),
        "only the file before the empty one is attached",
    )


@pytest.mark.assistant
@pytest.mark.project_management
@pytest.mark.confluence
@pytest.mark.api
@pytest.mark.parametrize("method", NON_UPLOAD_METHODS)
def test_non_upload_method_on_attachment_url_is_not_an_upload(
    client,
    assistant_utils,
    conversation_utils,
    confluence_utils,
    confluence_assistant,
    conversation_workspace,
    attachment_page,
    method,
):
    # @case confluence-generated-file-attachments_TC_007
    conversation = conversation_workspace()
    name = json_report_name()
    write_generated_file(client, conversation, name, json_report_content(name))

    ask_to_attach(
        assistant_utils,
        confluence_assistant,
        conversation,
        attach_prompt(attachment_page.page_id, method, None),
    )

    assert_that(
        confluence_tool_output(conversation_utils, conversation.conversation_id),
        all_of(
            contains_string(HTTP_RESULT_PREFIX.format(method=method)),
            is_not(contains_string(SUCCESS_WORDING)),
        ),
        f"{method} goes to Confluence as a plain request, not as an upload",
    )
    assert_that(
        attachment_titles(confluence_utils, attachment_page.page_id),
        empty(),
        "the attachment count is unchanged (zero)",
    )


@pytest.mark.assistant
@pytest.mark.project_management
@pytest.mark.confluence
@pytest.mark.api
def test_attach_name_shared_by_upload_and_generated_file_is_ambiguous(
    client,
    assistant_utils,
    conversation_utils,
    confluence_utils,
    confluence_assistant,
    conversation_workspace,
    attachment_page,
):
    # @case confluence-generated-file-attachments_TC_008
    conversation = conversation_workspace()
    name = json_report_name()
    # assumed: the generated row written first keeps its own content when the upload of the
    # same name is registered in the workspace, so both files stay reachable by that name.
    write_generated_file(client, conversation, name, json_report_content("generated"))
    file_url = upload_text_file(client, name, json_report_content("uploaded"))
    assert_that(
        workspace_path_of_upload(file_url),
        equal_to(name),
        "the upload keeps the generated file's name",
    )

    ask_to_attach(
        assistant_utils,
        confluence_assistant,
        conversation,
        attach_prompt(attachment_page.page_id, "POST", {"file": name}),
        file_urls=[file_url],
    )

    assert_that(
        confluence_tool_output(conversation_utils, conversation.conversation_id),
        all_of(
            contains_string(AMBIGUOUS_MESSAGE.format(name=name)),
            is_not(contains_string(SUCCESS_WORDING)),
        ),
        "the tool refuses the shared name instead of picking one file",
    )
    assert_that(
        attachment_titles(confluence_utils, attachment_page.page_id),
        empty(),
        "nothing is attached to the page",
    )


@pytest.mark.assistant
@pytest.mark.project_management
@pytest.mark.confluence
@pytest.mark.api
def test_attach_file_uploaded_in_chat_is_attached_once(
    client,
    assistant_utils,
    conversation_utils,
    confluence_utils,
    confluence_assistant,
    conversation_workspace,
    attachment_page,
):
    # @case confluence-generated-file-attachments_TC_009
    conversation = conversation_workspace()
    file_url = upload_text_file(
        client, json_report_name("notes"), json_report_content("notes")
    )
    name = workspace_path_of_upload(file_url)

    ask_to_attach(
        assistant_utils,
        confluence_assistant,
        conversation,
        attach_prompt(attachment_page.page_id, "POST", {"file": name}),
        file_urls=[file_url],
    )

    assert_that(
        confluence_tool_output(conversation_utils, conversation.conversation_id),
        all_of(
            contains_string(ATTACHED_MESSAGE.format(name=name)),
            is_not(contains_string(AMBIGUOUS_MESSAGE.format(name=name))),
        ),
        "the upload is attached without an ambiguity error against its own workspace row",
    )
    assert_that(
        attachment_titles(confluence_utils, attachment_page.page_id),
        equal_to([name]),
        "exactly one attachment on the page, named like the uploaded file",
    )
