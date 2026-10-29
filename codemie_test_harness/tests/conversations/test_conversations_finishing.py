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

"""API tests for platform-enforced conversation finishing.

Covers AC-1 through AC-5 and AC-7 of the ticket: the finished_at lifecycle,
the user single-finish and admin bulk-finish endpoints, mutation guards on
finished conversations, the isFinished list filter, and permission/error
handling (404/403/409).
"""

from datetime import datetime

import pytest
from hamcrest import (
    all_of,
    assert_that,
    equal_to,
    has_property,
    instance_of,
    is_not,
    none,
)
from requests import HTTPError

from codemie_sdk.models.assistant import AssistantChatRequest
from codemie_sdk.models.conversation import ConversationFinishResponse
from codemie_test_harness.tests.utils.assistant_utils import AssistantUtils
from codemie_test_harness.tests.utils.base_utils import (
    assert_error_details,
    get_random_name,
)
from codemie_test_harness.tests.utils.conversation_utils import ConversationUtils


def _create_conversation(assistant_obj, assistant_utils, conversation_utils) -> str:
    """Create an assistant conversation and return its conversation_id."""
    assistant_utils.ask_assistant(assistant_obj, f"prompt {get_random_name()}")
    conversations = conversation_utils.get_conversation_by_assistant_id(
        assistant_obj.id
    )
    return conversations[0].id


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_finish_conversation_transitions_finished_at_from_null_to_timestamp(
    assistant, assistant_utils, conversation_utils
):
    """finished_at is null before finish and a timestamp after finish."""
    assistant_obj = assistant()
    conversation_id = _create_conversation(
        assistant_obj, assistant_utils, conversation_utils
    )

    conversation_before = conversation_utils.get_conversation_by_id(conversation_id)
    assert_that(
        conversation_before,
        has_property("finished_at", none()),
        "finished_at should be null before finish",
    )

    finish_response = conversation_utils.finish_conversation(conversation_id)
    assert_that(
        finish_response,
        has_property("finished_at", is_not(none())),
        "finish response should return a non-null finishedAt timestamp",
    )

    conversation_after = conversation_utils.get_conversation_by_id(conversation_id)
    assert_that(
        conversation_after,
        has_property("finished_at", equal_to(finish_response.finished_at)),
        "finished_at should be populated with the returned timestamp",
    )


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_user_finish_endpoint_finishes_owned_conversation(
    assistant, assistant_utils, conversation_utils
):
    """POST /conversations/{id}/finish returns ConversationFinishResponse{conversationId, finishedAt}."""
    assistant_obj = assistant()
    conversation_id = _create_conversation(
        assistant_obj, assistant_utils, conversation_utils
    )

    finish_response = conversation_utils.finish_conversation(conversation_id)

    assert_that(
        finish_response,
        all_of(
            instance_of(ConversationFinishResponse),
            has_property("conversation_id", equal_to(conversation_id)),
            has_property("finished_at", instance_of(datetime)),
        ),
    )


@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_admin_bulk_finish_is_idempotent_for_already_finished_conversation(
    assistant, assistant_utils, conversation_utils, promoted_admin_user
):
    """Bulk-finishing an already-finished conversation reports already_finished=true, no error."""
    assistant_obj = assistant()
    conversation_id = _create_conversation(
        assistant_obj, assistant_utils, conversation_utils
    )
    finish_response = conversation_utils.finish_conversation(conversation_id)

    _, _, admin_client = promoted_admin_user
    admin_conversation_utils = ConversationUtils(admin_client)

    bulk_response = admin_conversation_utils.finish_conversations_bulk(
        [conversation_id]
    )

    assert_that(bulk_response.total, equal_to(len(bulk_response.results)))
    assert_that(
        bulk_response.results[0],
        all_of(
            has_property("conversation_id", equal_to(conversation_id)),
            has_property("already_finished", equal_to(True)),
            has_property("finished_at", equal_to(finish_response.finished_at)),
            has_property("error", none()),
        ),
    )


@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_repeat_single_finish_call_returns_409(
    assistant, assistant_utils, conversation_utils
):
    """A second call to the single-finish endpoint returns 409, not a repeated 200."""
    assistant_obj = assistant()
    conversation_id = _create_conversation(
        assistant_obj, assistant_utils, conversation_utils
    )
    conversation_utils.finish_conversation(conversation_id)

    with pytest.raises(HTTPError) as exc_info:
        conversation_utils.finish_conversation(conversation_id)

    assert_that(
        exc_info.value.response.status_code,
        equal_to(409),
        "Repeat call to the single-finish endpoint must return 409, not succeed again",
    )


@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_admin_bulk_finish_reports_per_id_results_for_mixed_batch(
    assistant, assistant_utils, conversation_utils, promoted_admin_user
):
    """Bulk finish reports correct per-ID results/total for unfinished + already-finished + unknown IDs."""
    unfinished_assistant = assistant()
    unfinished_id = _create_conversation(
        unfinished_assistant, assistant_utils, conversation_utils
    )

    already_finished_assistant = assistant()
    already_finished_id = _create_conversation(
        already_finished_assistant, assistant_utils, conversation_utils
    )
    conversation_utils.finish_conversation(already_finished_id)

    unknown_id = get_random_name()

    _, _, admin_client = promoted_admin_user
    admin_conversation_utils = ConversationUtils(admin_client)

    bulk_response = admin_conversation_utils.finish_conversations_bulk(
        [unfinished_id, already_finished_id, unknown_id]
    )

    assert_that(bulk_response.total, equal_to(len(bulk_response.results)))
    results_by_id = {result.conversation_id: result for result in bulk_response.results}

    assert_that(
        results_by_id[unfinished_id],
        all_of(
            has_property("already_finished", equal_to(False)),
            has_property("finished_at", is_not(none())),
            has_property("error", none()),
        ),
    )
    assert_that(
        results_by_id[already_finished_id],
        has_property("already_finished", equal_to(True)),
    )
    assert_that(
        results_by_id[unknown_id],
        has_property("error", equal_to("not_found")),
    )


@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_chat_message_to_finished_conversation_returns_409(
    assistant, assistant_utils, conversation_utils
):
    """A chat message sent to a finished conversation is rejected with 409."""
    assistant_obj = assistant()
    conversation_id = _create_conversation(
        assistant_obj, assistant_utils, conversation_utils
    )
    conversation_utils.finish_conversation(conversation_id)

    chat_request = AssistantChatRequest(
        text=f"prompt {get_random_name()}", conversation_id=conversation_id
    )
    with pytest.raises(HTTPError) as exc_info:
        assistant_utils.send_chat_request(assistant_obj, chat_request)

    assert_that(
        exc_info.value.response.status_code,
        equal_to(409),
        "Chat message on a finished conversation must be rejected with 409 before inference runs",
    )


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_finished_conversation_rejects_clear_history_and_remove_history_index(
    assistant, assistant_utils, conversation_utils
):
    """Clearing history and removing a history-index entry on a finished conversation both return 409."""
    assistant_obj = assistant()
    conversation_id = _create_conversation(
        assistant_obj, assistant_utils, conversation_utils
    )
    conversation_utils.finish_conversation(conversation_id)

    with pytest.raises(HTTPError) as exc_info:
        conversation_utils.delete_history(conversation_id)
    assert_that(
        exc_info.value.response.status_code,
        equal_to(409),
        "Clearing history on a finished conversation must return 409",
    )

    with pytest.raises(HTTPError) as exc_info:
        conversation_utils.delete_history_by_index(conversation_id, 0)
    assert_that(
        exc_info.value.response.status_code,
        equal_to(409),
        "Removing a history-index entry on a finished conversation must return 409",
    )


@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_conversations_list_filters_by_is_finished(
    assistant, assistant_utils, conversation_utils
):
    """GET conversations with isFinished=true/false returns only matching conversations."""
    finished_assistant = assistant()
    finished_id = _create_conversation(
        finished_assistant, assistant_utils, conversation_utils
    )
    conversation_utils.finish_conversation(finished_id)

    unfinished_assistant = assistant()
    unfinished_id = _create_conversation(
        unfinished_assistant, assistant_utils, conversation_utils
    )

    finished_only_ids = {
        c.id for c in conversation_utils.list_conversations(is_finished=True)
    }
    assert_that(finished_id in finished_only_ids)
    assert_that(unfinished_id not in finished_only_ids)

    unfinished_only_ids = {
        c.id for c in conversation_utils.list_conversations(is_finished=False)
    }
    assert_that(unfinished_id in unfinished_only_ids)
    assert_that(finished_id not in unfinished_only_ids)


@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_get_and_list_responses_expose_finished_at_reflecting_current_state(
    assistant, assistant_utils, conversation_utils
):
    """get and list response bodies carry finished_at reflecting the current state."""
    finished_assistant = assistant()
    finished_id = _create_conversation(
        finished_assistant, assistant_utils, conversation_utils
    )
    finish_response = conversation_utils.finish_conversation(finished_id)

    unfinished_assistant = assistant()
    unfinished_id = _create_conversation(
        unfinished_assistant, assistant_utils, conversation_utils
    )

    # get
    finished_details = conversation_utils.get_conversation_by_id(finished_id)
    assert_that(
        finished_details,
        has_property("finished_at", equal_to(finish_response.finished_at)),
    )
    unfinished_details = conversation_utils.get_conversation_by_id(unfinished_id)
    assert_that(unfinished_details, has_property("finished_at", none()))

    # list
    conversations_by_id = {c.id: c for c in conversation_utils.list_conversations()}
    assert_that(conversations_by_id[finished_id].finished_at, is_not(none()))
    assert_that(conversations_by_id[unfinished_id].finished_at, none())

    # VERIFY: assert finished_at also reflects current state on the conversation
    # search endpoint response. The search route and an SDK client method for it
    # are not grounded in available evidence — the diff excerpt shows
    # SearchResultItem gaining a finished_at field (conversation.py:967) but not
    # the router path backing it, so no selector/route is asserted here.


@pytest.mark.smoke
@pytest.mark.conversations
@pytest.mark.api
def test_finish_nonexistent_conversation_returns_404(conversation_utils):
    """Finishing an unknown conversation ID returns 404 CONVERSATION_NOT_FOUND_MESSAGE."""
    invalid_id = get_random_name()

    with pytest.raises(HTTPError) as exc_info:
        conversation_utils.finish_conversation(invalid_id)

    assert_error_details(
        exc_info.value.response,
        404,
        f"The conversation with ID [{invalid_id}] could not be found in the system.",
    )


@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_non_owner_finish_rejected_and_read_access_checked_before_finished_guard(
    assistant, assistant_utils, conversation_utils, non_admin_user
):
    """Non-owner finish attempts get 403; unauthorized mutation of a finished
    conversation gets 401 (read-access checked before the finished guard),
    never 409 -- confirmed empirically against the target environment: an
    unauthorized caller gets the same 401 on a chat request regardless of
    whether the conversation is finished, so the finished state is never
    leaked via a 409."""
    assistant_obj = assistant()
    conversation_id = _create_conversation(
        assistant_obj, assistant_utils, conversation_utils
    )

    _, _, other_client = non_admin_user
    other_conversation_utils = ConversationUtils(other_client)

    with pytest.raises(HTTPError) as exc_info:
        other_conversation_utils.finish_conversation(conversation_id)
    assert_that(
        exc_info.value.response.status_code,
        equal_to(403),
        "Non-owner finish attempt must be rejected with 403",
    )

    conversation_utils.finish_conversation(conversation_id)

    other_assistant_utils = AssistantUtils(other_client)
    chat_request = AssistantChatRequest(
        text=f"prompt {get_random_name()}", conversation_id=conversation_id
    )
    with pytest.raises(HTTPError) as exc_info:
        other_assistant_utils.send_chat_request(assistant_obj, chat_request)

    # The read-access check on the assistant/chat route denies with 401
    # ("Access denied ... You do not have the necessary permissions"), not
    # 403, in this codebase's convention. Verified directly against the
    # target environment: an unauthorized caller gets this same 401 on a
    # chat request whether or not the conversation is finished -- so the
    # finished-conversation 409 guard is never reached and never leaks
    # conversation state to a caller without read access.
    assert_that(
        exc_info.value.response.status_code,
        equal_to(401),
        "An unauthorized caller targeting a finished conversation must get 401 "
        "(read-access checked before the finished guard), never 409",
    )


@pytest.mark.smoke
@pytest.mark.conversations
@pytest.mark.api
def test_admin_endpoints_reject_non_admin_caller(conversation_utils, non_admin_user):
    """Non-admin callers are rejected by both admin-only conversation endpoints."""
    _, _, other_client = non_admin_user
    other_conversation_utils = ConversationUtils(other_client)

    bulk_status = other_conversation_utils.finish_conversations_bulk_status_code(
        [get_random_name()]
    )
    assert_that(
        bulk_status,
        equal_to(403),
        "Non-admin should be rejected from POST /admin/conversations/finish-bulk "
        "with 403 (admin_access_only raises ExtendedHTTPException(403))",
    )

    list_status = other_conversation_utils.list_admin_conversations_status_code()
    assert_that(
        list_status,
        equal_to(403),
        "Non-admin should be rejected from GET /admin/conversations "
        "with 403 (admin_access_only raises ExtendedHTTPException(403))",
    )


@pytest.mark.conversations
@pytest.mark.api
def test_admin_conversations_list_project_filter_scopes_to_one_project(
    assistant,
    assistant_utils,
    conversation_utils,
    promoted_admin_user,
    admin_utils,
    project_utils,
    user_utils,
):
    """GET /admin/conversations?project=<id> only returns that project's conversations."""
    scoped_project_name = get_random_name()
    admin_utils.create_project(scoped_project_name)
    me = user_utils.get_about_me()
    project_utils.assign_user_to_project(
        scoped_project_name, me.user_id, is_project_admin=False
    )

    default_project_assistant = assistant()
    default_conv_id = _create_conversation(
        default_project_assistant, assistant_utils, conversation_utils
    )

    # Created directly via assistant_utils (not the `assistant` factory
    # fixture) so it can be torn down explicitly below, before the project
    # delete: deleting a project 409s while it still owns an assistant, and
    # the `assistant` factory only tracks/cleans up the single most-recently
    # created assistant, with teardown firing after this test function
    # returns -- too late to unblock the project delete in this `finally`.
    scoped_assistant = assistant_utils.create_assistant(
        project_name=scoped_project_name
    )
    try:
        scoped_conv_id = _create_conversation(
            scoped_assistant, assistant_utils, conversation_utils
        )

        _, _, admin_client = promoted_admin_user
        admin_conversation_utils = ConversationUtils(admin_client)

        response = admin_conversation_utils.list_admin_conversations(
            project=scoped_project_name, per_page=100
        )
        returned_ids = {item.id for item in response.data}

        assert_that(scoped_conv_id in returned_ids)
        assert_that(default_conv_id not in returned_ids)
    finally:
        assistant_utils.delete_assistant(scoped_assistant)
        for conversation in conversation_utils.get_conversation_by_assistant_id(
            scoped_assistant.id
        ):
            conversation_utils.delete_conversation(conversation.id)
        project_utils.remove_user_from_project(scoped_project_name, me.user_id)
        project_utils.delete_project(scoped_project_name)
