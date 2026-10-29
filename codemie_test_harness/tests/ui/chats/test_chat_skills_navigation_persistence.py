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

"""
UI Regression Test

Chat with selected skills failed with a `/model` 422 error after the user
navigated away to the Assistants tab and returned to the same chat: the
model request payload's `skill_ids` array degraded to `[null]`.

Root cause, verified against the actual fix commit (codemie-ui 68d1e77f5):
on the first message, the app used to persist the selected skills to
localStorage as a plain array of id *strings* (`chatGeneration.ts`, now
removed: `saveChatSkills(userId, newId, skillIds ?? [])`, where `skillIds`
is `string[]`) into the same slot `useChatConfiguration.tsx` later reads
back expecting `SkillOption[]` (`{value, label}` objects). Navigating away
and back remounts the chat, re-reading that corrupted entry; the pre-fix
`loadChatSkills` had no shape check, so `selectedSkills.map(s => s.value)`
ran against plain strings and yielded `[undefined, ...]` -> JSON `[null]` ->
backend 422 (`skill_ids: list[str]` rejects a `null` element).

The fix adds an `isValidSkillOption` shape guard to `loadChatSkills` (a
non-object/string entry is filtered out) and stops writing the wrong shape
in the first place.

This test reproduces the corrupted-entry precondition directly via
localStorage (seeding the exact wrong shape the old code used to write),
since driving it end-to-end through the "New Chat" button is currently
unreliable on this stand (tracked separately) — see ticket AC "Regression
test covers: new chat -> add skills -> send message -> navigate to
Assistants -> return to chat -> send another message". Everything else
(skill selection, sending, tab navigation) goes through the UI normally.
"""

import json

import pytest
from hamcrest import assert_that, equal_to, has_item, is_not

from codemie_test_harness.tests.utils.client_factory import get_client

FIRST_MESSAGE = "Hello, this is the first message"
SECOND_MESSAGE = "Hello again, this is the second message after navigation"


@pytest.mark.sanity
@pytest.mark.chat
@pytest.mark.skill
@pytest.mark.ui
def test_chat_skills_survive_navigation_to_assistants_and_back(
    page, navigate_to_new_chat_page, skill
):
    """
    Flow:
    1. Create a skill via fixture and open a fresh chat with no messages yet.
    2. Select the skill via the UI and send the first message; it must carry
       the skill's real id (unaffected — nothing is corrupted yet).
    3. Seed localStorage with the exact wrong-shape entry the old buggy code
       used to write for this chat (a plain string instead of a
       `{value, label}` object), simulating the corruption the removed
       `saveChatSkills(userId, newId, skillIds ?? [])` call used to cause.
    4. Navigate away to the Assistants tab (unmounts the chat).
    5. Navigate back to the same chat (remounts it, re-reading the corrupted
       localStorage entry through `loadChatSkills`).
    6. Send a second message: the fixed shape guard must filter the
       malformed entry out — no 422, and `skill_ids` must never contain
       `null` (the entry is gracefully dropped, not resurrected).
    """
    created_skill = skill()
    chat_page = navigate_to_new_chat_page(page)

    chat_page.click_skills_button()
    chat_page.select_skill(created_skill.name)
    chat_page.confirm_skills_selection()

    # Step 2: first message — selection is still correct in-memory here
    first_request = chat_page.send_message_and_capture_model_request(FIRST_MESSAGE)
    first_response = first_request.response()
    assert_that(first_response.status, is_not(equal_to(422)))
    first_skill_ids = first_request.post_data_json.get("skill_ids")
    assert_that(first_skill_ids, is_not(has_item(None)))
    assert_that(first_skill_ids, has_item(created_skill.id))

    chat_page.wait_for_assistant_response()
    chat_page.should_have_message_sent(FIRST_MESSAGE)

    chat_id = chat_page.chat_id
    user_id = get_client().users.about_me().user_id

    # Step 3: seed the wrong-shape entry (plain id string, not {value, label})
    storage_key = f"{user_id}_chat-skills-{chat_id}"
    page.evaluate(
        "([key, value]) => localStorage.setItem(key, value)",
        [storage_key, json.dumps([created_skill.id])],
    )

    # Step 4: navigate away to Assistants
    chat_page.go_to_assistants_page()

    # Step 5: return to the same chat — remounts and re-reads localStorage
    chat_page.navigate_to(chat_id)
    chat_page.should_have_chat_input_visible()

    # Step 6: second message must not 422; the malformed entry must be
    # dropped, never surfacing as a `null` in skill_ids.
    second_request = chat_page.send_message_and_capture_model_request(SECOND_MESSAGE)
    second_response = second_request.response()
    assert_that(second_response.status, is_not(equal_to(422)))

    second_skill_ids = second_request.post_data_json.get("skill_ids")
    assert_that(second_skill_ids, is_not(has_item(None)))

    chat_page.wait_for_assistant_response()
    chat_page.should_have_message_sent(SECOND_MESSAGE)
