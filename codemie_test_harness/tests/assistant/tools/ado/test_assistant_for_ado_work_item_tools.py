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

import base64
import hashlib
import re
import uuid
from pathlib import Path

import pytest
import requests
from codemie_sdk.models.integration import CredentialTypes
from hamcrest import assert_that, contains_string, equal_to, is_not, not_

from codemie_test_harness.tests.enums.tools import Toolkit, AzureDevOpsWorkItemTool
from codemie_test_harness.tests.test_data.ado_work_item_tools_test_data import (
    ado_work_item_get_test_data,
    ADO_WORK_ITEM_CREATE,
    ADO_WORK_ITEM_UPDATE,
    ADO_WORK_ITEM_LINK,
    ADO_WORK_ITEM_CREATE_WITH_FILE,
    ADO_WORK_ITEM_UPDATE_WITH_FILE,
    ADO_WORK_ITEM_UPDATE_TITLE_ONLY,
    ADO_WORK_ITEM_ATTACH_ADDITIONAL_FILE,
    ADO_WORK_ITEM_ATTACH_MULTIPLE_FILES,
    ADO_WORK_ITEM_REATTACH_REVISED_FILE,
    ADO_WORK_ITEM_GET_WITH_ATTACHMENTS,
    ADO_WORK_ITEM_CREATE_COMMENT,
    ADO_WORK_ITEM_MOVE,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.base_utils import (
    get_random_name,
    assert_tool_triggered,
)
from codemie_test_harness.tests.utils.constants import WORK_ITEM_ID_PATTERN, FILES_PATH
from codemie_test_harness.tests.utils.json_utils import extract_id_from_ado_response


@pytest.mark.assistant
@pytest.mark.ado
@pytest.mark.api
@pytest.mark.parametrize(
    "toolkit,tool_name,prompt,expected_response",
    ado_work_item_get_test_data,
    ids=[
        f"{getattr(row, 'values', row)[0]}_{getattr(row, 'values', row)[1]}"
        for row in ado_work_item_get_test_data
    ],
)
def test_assistant_with_ado_work_item_get_tools(
    assistant_utils,
    assistant,
    integration_utils,
    similarity_check,
    seeded,
    toolkit,
    tool_name,
    prompt,
    expected_response,
):
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
        assistant, seeded(prompt), minimal_response=False
    )

    assert_tool_triggered(tool_name, triggered_tools)
    similarity_check.check_similarity(response, seeded(expected_response))


@pytest.mark.assistant
@pytest.mark.ado
@pytest.mark.api
def test_assistant_with_ado_work_item_modify_tools(
    assistant_utils,
    assistant,
    integration_utils,
    similarity_check,
    ado_work_item_ids_to_cleanup,
    ado_seed,
):
    credential_values = CredentialsManager.azure_devops_credentials()
    settings = integration_utils.create_integration(
        CredentialTypes.AZURE_DEVOPS, credential_values
    )
    assistant = assistant(
        Toolkit.AZURE_DEVOPS_WORK_ITEM,
        (
            AzureDevOpsWorkItemTool.CREATE_WORK_ITEM,
            AzureDevOpsWorkItemTool.UPDATE_WORK_ITEM,
            AzureDevOpsWorkItemTool.LINK_WORK_ITEMS,
        ),
        settings=settings,
    )

    work_item_title = f"Autotest Task {get_random_name()}"

    create_prompt = ADO_WORK_ITEM_CREATE["prompt_to_assistant"].format(work_item_title)
    create_response, create_triggered_tools = assistant_utils.ask_assistant(
        assistant, create_prompt, minimal_response=False
    )

    work_item_id = extract_id_from_ado_response(create_response, WORK_ITEM_ID_PATTERN)
    ado_work_item_ids_to_cleanup.append(work_item_id)
    create_expected = ADO_WORK_ITEM_CREATE["expected_llm_answer"].format(
        work_item_title, work_item_id
    )
    assert_tool_triggered(
        AzureDevOpsWorkItemTool.CREATE_WORK_ITEM, create_triggered_tools
    )
    similarity_check.check_similarity(create_response, create_expected)

    new_title = f"Autotest Epic {get_random_name()}"
    update_prompt = ADO_WORK_ITEM_UPDATE["prompt_to_assistant"].format(
        work_item_id, new_title
    )
    update_response, update_triggered_tools = assistant_utils.ask_assistant(
        assistant, update_prompt, minimal_response=False
    )

    update_expected = ADO_WORK_ITEM_UPDATE["expected_llm_answer"].format(
        work_item_id, new_title
    )
    assert_tool_triggered(
        AzureDevOpsWorkItemTool.UPDATE_WORK_ITEM, update_triggered_tools
    )
    similarity_check.check_similarity(update_response, update_expected)

    parent_id = ado_seed.parent_work_item.id
    link_prompt = ADO_WORK_ITEM_LINK["prompt_to_assistant"].format(
        child_id=work_item_id, parent_id=parent_id
    )
    link_response, link_triggered_tools = assistant_utils.ask_assistant(
        assistant, link_prompt, minimal_response=False
    )

    link_expected = ADO_WORK_ITEM_LINK["expected_llm_answer"].format(
        child_id=work_item_id, parent_id=parent_id
    )
    assert_tool_triggered(AzureDevOpsWorkItemTool.LINK_WORK_ITEMS, link_triggered_tools)
    similarity_check.check_similarity(link_response, link_expected)


@pytest.mark.assistant
@pytest.mark.ado
@pytest.mark.api
def test_assistant_with_ado_work_item_create_with_file_upload(
    assistant_utils,
    assistant,
    integration_utils,
    similarity_check,
    ado_work_item_ids_to_cleanup,
):
    credential_values = CredentialsManager.azure_devops_credentials()
    settings = integration_utils.create_integration(
        CredentialTypes.AZURE_DEVOPS, credential_values
    )
    assistant = assistant(
        Toolkit.AZURE_DEVOPS_WORK_ITEM,
        (
            AzureDevOpsWorkItemTool.CREATE_WORK_ITEM,
            AzureDevOpsWorkItemTool.GET_WORK_ITEM,
        ),
        settings=settings,
    )

    uploaded_file = assistant_utils.upload_file_to_chat(
        FILES_PATH / ADO_WORK_ITEM_CREATE_WITH_FILE["file_name"]
    )
    file_url = uploaded_file.get("file_url")
    assert_that(file_url, is_not(None))

    work_item_title = f"Autotest Task {get_random_name()}"
    prompt = ADO_WORK_ITEM_CREATE_WITH_FILE["prompt_to_assistant"].format(
        work_item_title
    )
    response, triggered_tools = assistant_utils.ask_assistant(
        assistant, prompt, file_urls=[file_url], minimal_response=False
    )

    assert_tool_triggered(AzureDevOpsWorkItemTool.CREATE_WORK_ITEM, triggered_tools)
    expected = ADO_WORK_ITEM_CREATE_WITH_FILE["expected_llm_answer"].format(
        work_item_title
    )
    similarity_check.check_similarity(response, expected)

    work_item_id = extract_id_from_ado_response(response, WORK_ITEM_ID_PATTERN)
    ado_work_item_ids_to_cleanup.append(work_item_id)
    get_prompt = ADO_WORK_ITEM_GET_WITH_ATTACHMENTS["prompt_to_assistant"].format(
        work_item_id
    )
    get_response, get_triggered_tools = assistant_utils.ask_assistant(
        assistant, get_prompt, minimal_response=False
    )

    assert_tool_triggered(AzureDevOpsWorkItemTool.GET_WORK_ITEM, get_triggered_tools)
    similarity_check.check_similarity(
        get_response,
        ADO_WORK_ITEM_GET_WITH_ATTACHMENTS["expected_llm_answer"].format(work_item_id),
    )


@pytest.mark.assistant
@pytest.mark.ado
@pytest.mark.api
def test_assistant_with_ado_work_item_create_comment(
    assistant_utils,
    assistant,
    integration_utils,
    similarity_check,
    ado_work_item_ids_to_cleanup,
):
    credential_values = CredentialsManager.azure_devops_credentials()
    settings = integration_utils.create_integration(
        CredentialTypes.AZURE_DEVOPS, credential_values
    )
    assistant = assistant(
        Toolkit.AZURE_DEVOPS_WORK_ITEM,
        (
            AzureDevOpsWorkItemTool.CREATE_WORK_ITEM,
            AzureDevOpsWorkItemTool.CREATE_COMMENT,
        ),
        settings=settings,
    )

    work_item_title = f"Autotest Task {get_random_name()}"
    create_response, _ = assistant_utils.ask_assistant(
        assistant,
        ADO_WORK_ITEM_CREATE["prompt_to_assistant"].format(work_item_title),
        minimal_response=False,
    )
    work_item_id = extract_id_from_ado_response(create_response, WORK_ITEM_ID_PATTERN)
    ado_work_item_ids_to_cleanup.append(work_item_id)

    comment_prompt = ADO_WORK_ITEM_CREATE_COMMENT["prompt_to_assistant"].format(
        work_item_id
    )
    comment_response, comment_triggered_tools = assistant_utils.ask_assistant(
        assistant, comment_prompt, minimal_response=False
    )

    assert_tool_triggered(
        AzureDevOpsWorkItemTool.CREATE_COMMENT, comment_triggered_tools
    )
    comment_expected = ADO_WORK_ITEM_CREATE_COMMENT["expected_llm_answer"].format(
        work_item_id
    )
    similarity_check.check_similarity(comment_response, comment_expected)


@pytest.mark.assistant
@pytest.mark.ado
@pytest.mark.api
def test_assistant_with_ado_work_item_update_with_file_upload(
    assistant_utils,
    assistant,
    integration_utils,
    similarity_check,
    ado_work_item_ids_to_cleanup,
):
    """Covers TC-001/TC-002/TC-003 as chained checkpoints of one
    chat session (shared conversation_id): a repeat update with no new
    file_urls must not reattach the already-attached file, on either the
    first (TC-001) or second (TC-002) repeat, while a genuinely new,
    distinct file offered afterwards is still attached (TC-003). The shared
    conversation_id is what routes the already-uploaded file back into
    config.input_files on the no-file repeats (build_unique_file_objects /
    _collect_files_from_conversation), which is what actually exercises the
    dedup guard under test (tools.py:171-201) instead of short-circuiting on
    `if not files: return []` (tools.py:173).
    """
    credential_values = CredentialsManager.azure_devops_credentials()
    settings = integration_utils.create_integration(
        CredentialTypes.AZURE_DEVOPS, credential_values
    )
    assistant = assistant(
        Toolkit.AZURE_DEVOPS_WORK_ITEM,
        (
            AzureDevOpsWorkItemTool.CREATE_WORK_ITEM,
            AzureDevOpsWorkItemTool.UPDATE_WORK_ITEM,
            AzureDevOpsWorkItemTool.GET_WORK_ITEM,
        ),
        settings=settings,
    )

    conversation_id = str(uuid.uuid4())

    uploaded_file = assistant_utils.upload_file_to_chat(
        FILES_PATH / ADO_WORK_ITEM_UPDATE_WITH_FILE["file_name"]
    )
    file_url = uploaded_file.get("file_url")
    assert_that(file_url, is_not(None))

    work_item_title = f"Autotest Task {get_random_name()}"
    create_response, _ = assistant_utils.ask_assistant(
        assistant,
        ADO_WORK_ITEM_CREATE["prompt_to_assistant"].format(work_item_title),
        conversation_id=conversation_id,
        minimal_response=False,
    )
    work_item_id = extract_id_from_ado_response(create_response, WORK_ITEM_ID_PATTERN)
    ado_work_item_ids_to_cleanup.append(work_item_id)

    new_title = f"Autotest Epic {get_random_name()}"
    update_prompt = ADO_WORK_ITEM_UPDATE_WITH_FILE["prompt_to_assistant"].format(
        work_item_id, new_title
    )
    update_response, update_triggered_tools = assistant_utils.ask_assistant(
        assistant,
        update_prompt,
        file_urls=[file_url],
        conversation_id=conversation_id,
        minimal_response=False,
    )

    assert_tool_triggered(
        AzureDevOpsWorkItemTool.UPDATE_WORK_ITEM, update_triggered_tools
    )
    update_expected = ADO_WORK_ITEM_UPDATE_WITH_FILE["expected_llm_answer"].format(
        work_item_id, new_title
    )
    similarity_check.check_similarity(update_response, update_expected)

    get_prompt = ADO_WORK_ITEM_GET_WITH_ATTACHMENTS["prompt_to_assistant"].format(
        work_item_id
    )
    get_response, get_triggered_tools = assistant_utils.ask_assistant(
        assistant, get_prompt, conversation_id=conversation_id, minimal_response=False
    )

    assert_tool_triggered(AzureDevOpsWorkItemTool.GET_WORK_ITEM, get_triggered_tools)
    similarity_check.check_similarity(
        get_response,
        ADO_WORK_ITEM_GET_WITH_ATTACHMENTS["expected_llm_answer"].format(work_item_id),
    )

    # Independent-channel baseline: exactly one AttachedFile relation for
    # test.txt, read directly from the ADO REST API (not the chat response).
    txt_hash = _sha256_of_file(FILES_PATH / ADO_WORK_ITEM_UPDATE_WITH_FILE["file_name"])
    attached = _ado_get_attached_files(work_item_id)
    assert_that(len(attached), equal_to(1))
    assert_that(attached[0]["name"], equal_to("test.txt"))
    assert_that(attached[0]["sha256"], equal_to(txt_hash))

    # TC-001 (R-1): a single repeat update in the same chat, no new
    # file_urls, must not reattach test.txt.
    repeat_1_title = f"Autotest Epic {get_random_name()}"
    repeat_1_prompt = ADO_WORK_ITEM_UPDATE_TITLE_ONLY["prompt_to_assistant"].format(
        work_item_id, repeat_1_title
    )
    repeat_1_response, repeat_1_triggered_tools = assistant_utils.ask_assistant(
        assistant,
        repeat_1_prompt,
        conversation_id=conversation_id,
        minimal_response=False,
    )
    assert_tool_triggered(
        AzureDevOpsWorkItemTool.UPDATE_WORK_ITEM, repeat_1_triggered_tools
    )
    similarity_check.check_similarity(
        repeat_1_response,
        ADO_WORK_ITEM_UPDATE_TITLE_ONLY["expected_llm_answer"].format(
            work_item_id, repeat_1_title
        ),
    )

    attached_after_repeat_1 = _ado_get_attached_files(work_item_id)
    assert_that(len(attached_after_repeat_1), equal_to(1))
    assert_that(attached_after_repeat_1[0]["name"], equal_to("test.txt"))
    assert_that(attached_after_repeat_1[0]["sha256"], equal_to(txt_hash))

    # TC-002 (R-2): a second repeat (third overall update call) in the same
    # chat must still not reattach test.txt.
    repeat_2_title = f"Autotest Epic {get_random_name()}"
    repeat_2_prompt = ADO_WORK_ITEM_UPDATE_TITLE_ONLY["prompt_to_assistant"].format(
        work_item_id, repeat_2_title
    )
    repeat_2_response, repeat_2_triggered_tools = assistant_utils.ask_assistant(
        assistant,
        repeat_2_prompt,
        conversation_id=conversation_id,
        minimal_response=False,
    )
    assert_tool_triggered(
        AzureDevOpsWorkItemTool.UPDATE_WORK_ITEM, repeat_2_triggered_tools
    )
    similarity_check.check_similarity(
        repeat_2_response,
        ADO_WORK_ITEM_UPDATE_TITLE_ONLY["expected_llm_answer"].format(
            work_item_id, repeat_2_title
        ),
    )

    attached_after_repeat_2 = _ado_get_attached_files(work_item_id)
    assert_that(len(attached_after_repeat_2), equal_to(1))
    assert_that(attached_after_repeat_2[0]["name"], equal_to("test.txt"))
    assert_that(attached_after_repeat_2[0]["sha256"], equal_to(txt_hash))

    # TC-003 (R-3): a genuinely new, distinct file offered afterwards must
    # still be attached, even while test.txt remains attached and untouched.
    csv_uploaded_file = assistant_utils.upload_file_to_chat(FILES_PATH / "test.csv")
    csv_file_url = csv_uploaded_file.get("file_url")
    assert_that(csv_file_url, is_not(None))

    new_file_prompt = ADO_WORK_ITEM_ATTACH_ADDITIONAL_FILE[
        "prompt_to_assistant"
    ].format(work_item_id)
    new_file_response, new_file_triggered_tools = assistant_utils.ask_assistant(
        assistant,
        new_file_prompt,
        file_urls=[csv_file_url],
        conversation_id=conversation_id,
        minimal_response=False,
    )
    assert_tool_triggered(
        AzureDevOpsWorkItemTool.UPDATE_WORK_ITEM, new_file_triggered_tools
    )
    similarity_check.check_similarity(
        new_file_response,
        ADO_WORK_ITEM_ATTACH_ADDITIONAL_FILE["expected_llm_answer"].format(
            work_item_id
        ),
    )

    csv_hash = _sha256_of_file(FILES_PATH / "test.csv")
    attached_after_new_file = _ado_get_attached_files(work_item_id)
    assert_that(len(attached_after_new_file), equal_to(2))
    by_name = {f["name"]: f["sha256"] for f in attached_after_new_file}
    assert_that(by_name.get("test.txt"), equal_to(txt_hash))
    assert_that(by_name.get("test.csv"), equal_to(csv_hash))


def _sha256_of_file(path) -> str:
    """Compute the sha256 hex digest of a local fixture file's raw bytes —
    the same hash the dedup guard under test embeds into the relation
    comment (tools.py: `hashlib.sha256(content).hexdigest()`)."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _ado_get_attached_files(item_id) -> list:
    """Read a work item's AttachedFile relations directly from the ADO REST
    API — a channel independent of the assistant chat and of the dedup
    guard under test, so it cannot be fooled by the same code path it is
    used to verify. Mirrors `conftest.py`'s `_delete_ado_work_item` auth
    pattern, which is the harness's own established idiom for calling the ADO REST API
    directly (raw `requests`, not the codemie-sdk client, since ADO's own
    API is an external system, not part of the CodeMie platform SDK).
    """
    token = CredentialsManager.get_parameter("AZURE_DEVOPS_TOKEN")
    org = CredentialsManager.get_parameter("AZURE_DEVOPS_ORGANIZATION_NAME")
    auth_header = f"Basic {base64.b64encode(f':{token}'.encode()).decode()}"
    response = requests.get(
        f"{CredentialsManager.get_parameter('AZURE_DEVOPS_URL')}/{org}/_apis/wit/workitems/{item_id}"
        "?$expand=Relations&api-version=7.1",
        headers={"Authorization": auth_header},
        timeout=30,
    )
    response.raise_for_status()
    relations = response.json().get("relations", [])
    attached_files = []
    for relation in relations:
        if relation.get("rel") != "AttachedFile":
            continue
        attributes = relation.get("attributes", {})
        comment = attributes.get("comment", "")
        hash_match = re.search(r"\[sha256:([a-f0-9]{64})\]", comment)
        attached_files.append(
            {
                "name": attributes.get("name"),
                "sha256": hash_match.group(1) if hash_match else None,
            }
        )
    return attached_files


@pytest.mark.assistant
@pytest.mark.ado
@pytest.mark.api
def test_assistant_with_ado_work_item_move_to_new_parent(
    assistant_utils,
    assistant,
    integration_utils,
    similarity_check,
    ado_work_item_ids_to_cleanup,
    ado_seed,
):
    """TC-01: Move ADO work item to a new parent via assistant.

    Creates a child Task, links it to an initial parent, then asks the assistant
    to move it to a different parent using the move_work_item tool.
    Asserts the tool was triggered and the response confirms the move without TF201036.
    """
    credential_values = CredentialsManager.azure_devops_credentials()
    settings = integration_utils.create_integration(
        CredentialTypes.AZURE_DEVOPS, credential_values
    )
    assistant = assistant(
        Toolkit.AZURE_DEVOPS_WORK_ITEM,
        (
            AzureDevOpsWorkItemTool.CREATE_WORK_ITEM,
            AzureDevOpsWorkItemTool.LINK_WORK_ITEMS,
            AzureDevOpsWorkItemTool.MOVE_WORK_ITEM,
        ),
        settings=settings,
    )

    work_item_title = f"Autotest Task {get_random_name()}"
    create_response, _ = assistant_utils.ask_assistant(
        assistant,
        ADO_WORK_ITEM_CREATE["prompt_to_assistant"].format(work_item_title),
        minimal_response=False,
    )
    child_id = extract_id_from_ado_response(create_response, WORK_ITEM_ID_PATTERN)
    ado_work_item_ids_to_cleanup.append(child_id)

    parent_1_id = ado_seed.work_item.id
    parent_2_id = ado_seed.parent_work_item.id

    link_prompt = ADO_WORK_ITEM_MOVE["prompt_link_to_parent_1"].format(
        child_id=child_id, parent_1_id=parent_1_id
    )
    assistant_utils.ask_assistant(assistant, link_prompt, minimal_response=False)

    move_prompt = ADO_WORK_ITEM_MOVE["prompt_move_to_parent_2"].format(
        child_id=child_id, parent_2_id=parent_2_id
    )
    move_response, move_triggered_tools = assistant_utils.ask_assistant(
        assistant, move_prompt, minimal_response=False
    )

    assert_tool_triggered(AzureDevOpsWorkItemTool.MOVE_WORK_ITEM, move_triggered_tools)
    assert_that(
        move_response,
        not_(contains_string("TF201036")),
        "Response must not contain ADO error TF201036",
    )
    expected_move = ADO_WORK_ITEM_MOVE["expected_move_response"].format(
        child_id=child_id, parent_2_id=parent_2_id
    )
    similarity_check.check_similarity(move_response, expected_move)


@pytest.mark.assistant
@pytest.mark.ado
@pytest.mark.api
def test_assistant_with_ado_work_item_update_with_multiple_files_in_one_call(
    assistant_utils,
    assistant,
    integration_utils,
    similarity_check,
    ado_work_item_ids_to_cleanup,
):
    """Covers TC-004 (R-4): two distinct files offered in a
    single UPDATE_WORK_ITEM call — with no prior relations to dedup against
    — are each attached exactly once. Exercises the per-update files loop
    (tools.py:204) across two iterations in one pass; a cross-file leakage
    bug in that loop would either drop one relation or write a relation
    with the wrong hash, both caught by the exact per-filename hash match
    below.
    """
    credential_values = CredentialsManager.azure_devops_credentials()
    settings = integration_utils.create_integration(
        CredentialTypes.AZURE_DEVOPS, credential_values
    )
    assistant = assistant(
        Toolkit.AZURE_DEVOPS_WORK_ITEM,
        (
            AzureDevOpsWorkItemTool.CREATE_WORK_ITEM,
            AzureDevOpsWorkItemTool.UPDATE_WORK_ITEM,
        ),
        settings=settings,
    )

    work_item_title = f"Autotest Task {get_random_name()}"
    create_response, _ = assistant_utils.ask_assistant(
        assistant,
        ADO_WORK_ITEM_CREATE["prompt_to_assistant"].format(work_item_title),
        minimal_response=False,
    )
    work_item_id = extract_id_from_ado_response(create_response, WORK_ITEM_ID_PATTERN)
    ado_work_item_ids_to_cleanup.append(work_item_id)

    txt_url = assistant_utils.upload_file_to_chat(FILES_PATH / "test.txt").get(
        "file_url"
    )
    pdf_url = assistant_utils.upload_file_to_chat(FILES_PATH / "test.pdf").get(
        "file_url"
    )
    assert_that(txt_url, is_not(None))
    assert_that(pdf_url, is_not(None))

    update_prompt = ADO_WORK_ITEM_ATTACH_MULTIPLE_FILES["prompt_to_assistant"].format(
        work_item_id
    )
    update_response, update_triggered_tools = assistant_utils.ask_assistant(
        assistant, update_prompt, file_urls=[txt_url, pdf_url], minimal_response=False
    )

    assert_tool_triggered(
        AzureDevOpsWorkItemTool.UPDATE_WORK_ITEM, update_triggered_tools
    )
    similarity_check.check_similarity(
        update_response,
        ADO_WORK_ITEM_ATTACH_MULTIPLE_FILES["expected_llm_answer"].format(work_item_id),
    )

    txt_hash = _sha256_of_file(FILES_PATH / "test.txt")
    pdf_hash = _sha256_of_file(FILES_PATH / "test.pdf")
    attached = _ado_get_attached_files(work_item_id)
    assert_that(len(attached), equal_to(2))
    by_name = {f["name"]: f["sha256"] for f in attached}
    assert_that(by_name.get("test.txt"), equal_to(txt_hash))
    assert_that(by_name.get("test.pdf"), equal_to(pdf_hash))


@pytest.mark.assistant
@pytest.mark.ado
@pytest.mark.api
def test_assistant_with_ado_work_item_reattaches_revised_file_with_same_name(
    assistant_utils,
    assistant,
    integration_utils,
    similarity_check,
    ado_work_item_ids_to_cleanup,
    tmp_path,
):
    """Covers TC-005 (R-8): a revised file uploaded under the
    same filename but with different content is re-attached, not silently
    skipped. The dedup key is (name.lower(), sha256(content)), not name
    alone (tools.py:199) — the exact regression class flagged by reviewer
    sviatoslav_likhtarchyk in MR !4192. Own data: the revised-content
    fixture is generated at runtime under a temp path named `test.txt` (no
    permanent fixture file needed, per TC-005's data note).
    """
    credential_values = CredentialsManager.azure_devops_credentials()
    settings = integration_utils.create_integration(
        CredentialTypes.AZURE_DEVOPS, credential_values
    )
    assistant = assistant(
        Toolkit.AZURE_DEVOPS_WORK_ITEM,
        (
            AzureDevOpsWorkItemTool.CREATE_WORK_ITEM,
            AzureDevOpsWorkItemTool.UPDATE_WORK_ITEM,
        ),
        settings=settings,
    )

    work_item_title = f"Autotest Task {get_random_name()}"
    create_response, _ = assistant_utils.ask_assistant(
        assistant,
        ADO_WORK_ITEM_CREATE["prompt_to_assistant"].format(work_item_title),
        minimal_response=False,
    )
    work_item_id = extract_id_from_ado_response(create_response, WORK_ITEM_ID_PATTERN)
    ado_work_item_ids_to_cleanup.append(work_item_id)

    original_url = assistant_utils.upload_file_to_chat(FILES_PATH / "test.txt").get(
        "file_url"
    )
    assert_that(original_url, is_not(None))

    attach_prompt = ADO_WORK_ITEM_REATTACH_REVISED_FILE["prompt_to_assistant"].format(
        work_item_id
    )
    first_response, first_triggered_tools = assistant_utils.ask_assistant(
        assistant, attach_prompt, file_urls=[original_url], minimal_response=False
    )
    assert_tool_triggered(
        AzureDevOpsWorkItemTool.UPDATE_WORK_ITEM, first_triggered_tools
    )
    similarity_check.check_similarity(
        first_response,
        ADO_WORK_ITEM_REATTACH_REVISED_FILE["expected_llm_answer"].format(work_item_id),
    )

    original_hash = _sha256_of_file(FILES_PATH / "test.txt")
    attached_after_first = _ado_get_attached_files(work_item_id)
    assert_that(len(attached_after_first), equal_to(1))
    assert_that(attached_after_first[0]["name"], equal_to("test.txt"))
    assert_that(attached_after_first[0]["sha256"], equal_to(original_hash))

    # Own data: a distinct-content revision of test.txt, uploaded under the
    # identical filename via a temp file — no shared/permanent fixture.
    revised_content = (
        f"This file is a revised test purpose document, revision {get_random_name()}."
    ).encode()
    revised_path = tmp_path / "test.txt"
    revised_path.write_bytes(revised_content)
    revised_hash = hashlib.sha256(revised_content).hexdigest()
    assert_that(revised_hash, is_not(equal_to(original_hash)))

    revised_url = assistant_utils.upload_file_to_chat(revised_path).get("file_url")
    assert_that(revised_url, is_not(None))

    second_response, second_triggered_tools = assistant_utils.ask_assistant(
        assistant, attach_prompt, file_urls=[revised_url], minimal_response=False
    )
    assert_tool_triggered(
        AzureDevOpsWorkItemTool.UPDATE_WORK_ITEM, second_triggered_tools
    )
    similarity_check.check_similarity(
        second_response,
        ADO_WORK_ITEM_REATTACH_REVISED_FILE["expected_llm_answer"].format(work_item_id),
    )

    attached_after_second = _ado_get_attached_files(work_item_id)
    assert_that(len(attached_after_second), equal_to(2))
    names = {f["name"] for f in attached_after_second}
    hashes = {f["sha256"] for f in attached_after_second}
    assert_that(names, equal_to({"test.txt"}))
    assert_that(hashes, equal_to({original_hash, revised_hash}))
