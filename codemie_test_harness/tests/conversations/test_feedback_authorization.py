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

"""Authorization of the feedback routes.

GET /v1/feedback and GET /v1/feedback/{id} used to return every user's feedback
entries to any caller, and POST/DELETE /v1/feedback did not check who owned the
conversation. Expected behaviour:
- a non-admin lists and reads only the entries on their own conversations; another
  user's entry is answered 404 "Feedback not found";
- an admin lists and reads every entry;
- only the conversation owner may add feedback (403 for anyone else, admin included);
- the owner or an admin may remove feedback, and only through the conversation the
  entry belongs to (404 "Feedback not found" otherwise).

Evidence: backend routers/feedback.py (index, show, create, delete) and
models/feedback.py (get_all_for_user, find_by_id_for_user).
"""

import pytest
from hamcrest import (
    assert_that,
    contains_exactly,
    contains_string,
    equal_to,
    has_item,
    has_length,
    is_not,
    none,
    not_none,
)
from requests import HTTPError

from codemie_test_harness.tests.test_data.feedback_test_data import (
    ACCESS_DENIED_MESSAGE,
    FEEDBACK_NOT_FOUND_MESSAGE,
    FEEDBACK_REMOVED_MESSAGE,
)
from codemie_test_harness.tests.utils.base_utils import assert_error_details
from codemie_test_harness.tests.utils.conversation_utils import ConversationUtils


def _answer_mark(owner_utils, item):
    """The user mark on the answer of the owner's conversation, read by the owner."""
    conversation = owner_utils.get_conversation_by_id(item.conversation_id)
    return conversation.history[item.message_index].userMark


# @case feedback-routes-all-users-entries_TC_001
@pytest.mark.conversations
@pytest.mark.api
def test_non_admin_lists_only_own_feedback_entries(
    platform_user, second_platform_user, feedback_conversation
):
    own = feedback_conversation(platform_user)
    other = feedback_conversation(second_platform_user)

    entries = ConversationUtils(platform_user.client).list_feedback()

    entry_ids = [entry.id for entry in entries]
    assert_that(
        entry_ids,
        contains_exactly(own.feedback_id),
        "A non-admin must get only the entries on their own conversations",
    )
    assert_that(
        entry_ids,
        is_not(has_item(other.feedback_id)),
        "Another user's entry must not be listed",
    )


# @case feedback-routes-all-users-entries_TC_002
@pytest.mark.conversations
@pytest.mark.api
def test_non_admin_cannot_read_another_users_feedback_entry_by_id(
    platform_user, second_platform_user, feedback_conversation
):
    own = feedback_conversation(platform_user)
    other = feedback_conversation(second_platform_user)
    utils = ConversationUtils(platform_user.client)

    with pytest.raises(HTTPError) as exc_info:
        utils.get_feedback(other.feedback_id)
    assert_error_details(
        exc_info.value.response, 404, FEEDBACK_NOT_FOUND_MESSAGE, field="message"
    )
    assert_that(
        exc_info.value.response.text,
        is_not(contains_string(other.seed.response)),
        "The other user's entry content must not be returned",
    )

    entry = utils.get_feedback(own.feedback_id)
    assert_that(entry.id, equal_to(own.feedback_id), "Own entry must be returned")
    assert_that(entry.conversation_id, equal_to(own.conversation_id))
    assert_that(entry.response, equal_to(own.seed.response))


# @case feedback-routes-all-users-entries_TC_003
@pytest.mark.conversations
@pytest.mark.api
def test_admin_lists_every_feedback_entry_and_reads_any_by_id(
    platform_user, second_platform_user, admin_client, feedback_conversation
):
    first = feedback_conversation(platform_user)
    second = feedback_conversation(second_platform_user)
    admin_utils = ConversationUtils(admin_client)

    # The list endpoint has no ordering guarantee that keeps new rows inside its row cap,
    # so each entry is read by id; the list is only checked to be non-empty.
    assert_that(
        admin_utils.list_feedback(), is_not(has_length(0)), "Admin list is empty"
    )
    for item in (first, second):
        entry = admin_utils.get_feedback(item.feedback_id)
        assert_that(entry.id, equal_to(item.feedback_id))
        assert_that(entry.conversation_id, equal_to(item.conversation_id))
        assert_that(entry.response, equal_to(item.seed.response))


# @case feedback-routes-all-users-entries_TC_004
@pytest.mark.conversations
@pytest.mark.api
def test_non_owner_cannot_add_feedback_to_another_users_conversation(
    platform_user, second_platform_user, feedback_conversation
):
    owned = feedback_conversation(platform_user, with_feedback=False)
    seed = owned.seed

    with pytest.raises(HTTPError) as exc_info:
        ConversationUtils(second_platform_user.client).submit_feedback(
            conversation_id=owned.conversation_id,
            message_index=owned.message_index,
            assistant_id=owned.assistant_id,
            request=seed.request,
            response=seed.response,
            comments=seed.comments,
            feedback_type="Other",
        )
    assert_error_details(
        exc_info.value.response, 403, ACCESS_DENIED_MESSAGE, field="message"
    )

    owner_utils = ConversationUtils(platform_user.client)
    conversation = owner_utils.get_conversation_by_id(owned.conversation_id)
    assert_that(conversation.history, has_length(2), "History must be unchanged")
    assert_that(
        conversation.history[owned.message_index].userMark,
        none(),
        "No feedback mark may be set on the owner's answer",
    )
    assert_that(
        owner_utils.list_feedback(), has_length(0), "No feedback entry may be saved"
    )


# @case feedback-routes-all-users-entries_TC_005
@pytest.mark.conversations
@pytest.mark.api
def test_non_owner_cannot_remove_feedback_from_another_users_conversation(
    platform_user, second_platform_user, feedback_conversation
):
    owned = feedback_conversation(platform_user)

    with pytest.raises(HTTPError) as exc_info:
        ConversationUtils(second_platform_user.client).delete_feedback(
            conversation_id=owned.conversation_id,
            feedback_id=owned.feedback_id,
            message_index=owned.message_index,
            assistant_id=owned.assistant_id,
        )
    assert_error_details(
        exc_info.value.response, 403, ACCESS_DENIED_MESSAGE, field="message"
    )

    owner_utils = ConversationUtils(platform_user.client)
    mark = _answer_mark(owner_utils, owned)
    assert_that(mark, not_none(), "The feedback mark must still be on the answer")
    assert_that(mark.feedback_id, equal_to(owned.feedback_id))
    entry = owner_utils.get_feedback(owned.feedback_id)
    assert_that(entry.id, equal_to(owned.feedback_id), "The entry must still exist")


# @case feedback-routes-all-users-entries_TC_015
@pytest.mark.conversations
@pytest.mark.api
def test_admin_removes_feedback_on_another_users_conversation_but_cannot_add_it(
    platform_user, admin_client, feedback_conversation
):
    owned = feedback_conversation(platform_user)
    admin_utils = ConversationUtils(admin_client)
    seed = owned.seed

    with pytest.raises(HTTPError) as exc_info:
        admin_utils.submit_feedback(
            conversation_id=owned.conversation_id,
            message_index=owned.message_index,
            assistant_id=owned.assistant_id,
            request=seed.request,
            response=seed.response,
            comments=seed.comments,
            feedback_type="Other",
        )
    assert_error_details(
        exc_info.value.response, 403, ACCESS_DENIED_MESSAGE, field="message"
    )

    result = admin_utils.delete_feedback(
        conversation_id=owned.conversation_id,
        feedback_id=owned.feedback_id,
        message_index=owned.message_index,
        assistant_id=owned.assistant_id,
    )
    assert_that(result.message, equal_to(FEEDBACK_REMOVED_MESSAGE))

    owner_utils = ConversationUtils(platform_user.client)
    assert_that(
        _answer_mark(owner_utils, owned),
        none(),
        "The owner's mark must be gone after the admin removed it",
    )
    with pytest.raises(HTTPError) as exc_info:
        owner_utils.get_feedback(owned.feedback_id)
    assert_error_details(
        exc_info.value.response, 404, FEEDBACK_NOT_FOUND_MESSAGE, field="message"
    )


# @case feedback-routes-all-users-entries_TC_016
@pytest.mark.conversations
@pytest.mark.api
def test_remove_feedback_through_a_different_conversation_id_is_refused(
    platform_user, feedback_conversation
):
    first = feedback_conversation(platform_user)
    second = feedback_conversation(platform_user)
    owner_utils = ConversationUtils(platform_user.client)

    with pytest.raises(HTTPError) as exc_info:
        owner_utils.delete_feedback(
            conversation_id=first.conversation_id,
            feedback_id=second.feedback_id,
            message_index=first.message_index,
            assistant_id=first.assistant_id,
        )
    assert_error_details(
        exc_info.value.response, 404, FEEDBACK_NOT_FOUND_MESSAGE, field="message"
    )

    mark = _answer_mark(owner_utils, second)
    assert_that(mark, not_none(), "The other conversation's mark must remain")
    assert_that(mark.feedback_id, equal_to(second.feedback_id))
    entry = owner_utils.get_feedback(second.feedback_id)
    assert_that(entry.id, equal_to(second.feedback_id), "The entry must remain")
    assert_that(
        _answer_mark(owner_utils, first).feedback_id,
        equal_to(first.feedback_id),
        "The first conversation's own mark must remain too",
    )
