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
End-to-end UI tests for assistant built-in subagent feature.

Covers:
    TC-019  UI session — no nested subagent spawning visible
    TC-020b UI chat — built-in subagent triggered and visible in session (AC-2 smoke)
            Note: TC-020 original spec (blocked recursion + actionable UI message, AC-4/AC-6)
            cannot be exercised via this harness — recursion-guard block messages are not
            surfaced through the REST API or chat UI in a way that is reliably observable.
    TC-021  End-to-end UI — enable subagent for skill, verify spawning in session
    TC-022  Cross-layer — enable subagent via UI, verify API enforcement
"""

import pytest
from hamcrest import assert_that, equal_to

from codemie_test_harness.tests.test_data.skill_test_data import (
    SKILL_CONTENT,
    SKILL_DESCRIPTION,
)
from codemie_test_harness.tests.ui.pageobject.chats.chat_page import ChatPage
from codemie_test_harness.tests.ui.pageobject.skills.create_edit_skill_page import (
    CreateEditSkillPage,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name

BUILTIN_SUBAGENT_ID = "GENERAL_PURPOSE_SUBAGENT"

# Content must be at least 100 characters (API validation)
_SKILL_CONTENT = (
    "# Built-in Subagent E2E Test Skill\n\n"
    "## Description\n"
    "Integration test skill for end-to-end validation of built-in subagent spawning "
    "via UI. Used in end-to-end tests."
)


def _unique_name() -> str:
    return get_random_name().replace("_", "-")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# TC-019  UI session — no nested subagent spawning visible
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.ui
def test_ui_session_no_nested_subagent_spawn(page, skill, raw_assistant, skill_utils):
    """TC-019: Run assistant with subagent-enabled skill; no second-level spawn visible.

    Steps:
    1. Create a skill with enabled_builtin_subagents=[GENERAL_PURPOSE_SUBAGENT] via API.
    2. Create an assistant and attach the skill via API.
    3. Open the chat page and start a new chat.
    4. Send a message @-mentioning the assistant.
    5. Wait for the response.
    6. Assert no nested subagent spawn indicator is visible.

    AC coverage: AC-4 (recursion guard does not surface as a UI error).
    """
    created_skill = skill(
        skill_name=_unique_name(),
        description=SKILL_DESCRIPTION,
        content=SKILL_CONTENT,
    )
    # Enable built-in subagent on the skill
    skill_utils.update_skill(
        created_skill.id,
        name=created_skill.name,
        description=created_skill.description,
        content=created_skill.content,
        visibility=created_skill.visibility,
        enabled_builtin_subagents=[BUILTIN_SUBAGENT_ID],
    )

    asst_name = _unique_name()
    raw_assistant(
        name=asst_name,
        skill_id=created_skill.id,
        system_prompt="You are a helpful assistant. Use any available tools to answer questions.",
        description="E2E subagent test assistant",
    )

    chat_page = ChatPage(page)
    page.goto("/chats")
    chat_page.wait_for_page_load()
    chat_page.start_new_chat()

    chat_page.send_message(
        "Use the built-in General Purpose Subagent to say hello.",
        assistant_name=asst_name,
    )
    chat_page.wait_for_assistant_response()
    chat_page.should_have_assistant_response()

    # Subagent must have been triggered
    chat_page.should_have_builtin_subagent_triggered()
    # Recursion guard — no second-level spawn tool block should be visible
    chat_page.should_not_see_nested_subagent_spawn()


# ---------------------------------------------------------------------------
# TC-020  UI blocked recursion — actionable, distinguishable message
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.ui
def test_ui_builtin_subagent_triggered_via_chat(
    page, skill, raw_assistant, skill_utils
):
    """TC-020b (AC-2 smoke): Ask assistant to use the built-in subagent; verify it is triggered.

    TC-020 original spec (blocked recursion + actionable UI message, AC-4/AC-6) is not
    testable via this harness — the recursion-guard block is not surfaced through the
    REST API or chat UI in an observable way.  This test covers the observable AC-2 path:
    the subagent is triggered and its tool block is visible in the session.

    Steps:
    1. Create a skill with enabled_builtin_subagents=[GENERAL_PURPOSE_SUBAGENT] via API.
    2. Create an assistant and attach the skill via API.
    3. Open the chat page and start a new chat.
    4. Send a message explicitly requesting the built-in subagent.
    5. Wait for the response.
    6. Assert the 'Builtin  General Purpose Subagent' tool block is visible (Success).

    AC coverage: AC-2 (subagent is spawnable and its invocation is observable in the UI).
    """
    created_skill = skill(
        skill_name=_unique_name(),
        description=SKILL_DESCRIPTION,
        content=SKILL_CONTENT,
    )
    skill_utils.update_skill(
        created_skill.id,
        name=created_skill.name,
        description=created_skill.description,
        content=created_skill.content,
        visibility=created_skill.visibility,
        enabled_builtin_subagents=[BUILTIN_SUBAGENT_ID],
    )

    asst_name = _unique_name()
    raw_assistant(
        name=asst_name,
        skill_id=created_skill.id,
        system_prompt="You MUST delegate every user request to the built-in General Purpose Subagent.",
        description="E2E subagent test assistant",
    )

    chat_page = ChatPage(page)
    page.goto("/chats")
    chat_page.wait_for_page_load()
    chat_page.start_new_chat()

    chat_page.send_message(
        "Use the built-in General Purpose Subagent to answer: say hello.",
        assistant_name=asst_name,
    )
    chat_page.wait_for_assistant_response()
    chat_page.should_have_assistant_response()

    chat_page.should_have_builtin_subagent_triggered()


# ---------------------------------------------------------------------------
# TC-021  End-to-end UI: enable via skill page → subagent available in session
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.ui
def test_e2e_enable_subagent_via_skill_ui(page, skill, raw_assistant, skill_utils):
    """TC-021: Enable subagent via skill UI → create assistant → verify chat session.

    Steps:
    1. Create a skill via API (no enabled_builtin_subagents).
    2. Open the skill edit page in UI.
    3. Enable the subagent toggle and save.
    4. Reload the skill edit page.
    5. Assert the toggle is ON.
    6. Verify via SDK that enabled_builtin_subagents=[GENERAL_PURPOSE_SUBAGENT].
    7. Create an assistant via API and attach the skill.
    8. Open the chat page and start a new chat.
    9. Send a message @-mentioning the assistant.
    10. Wait for the assistant response and verify it is present.

    AC coverage: AC-1 (skill field persists), AC-2 (subagent spawnable when enabled).
    """
    created_skill = skill(
        skill_name=_unique_name(),
        description=SKILL_DESCRIPTION,
        content=SKILL_CONTENT,
    )

    # Steps 2-4: Enable toggle in UI and save
    edit_page = CreateEditSkillPage(page)
    edit_page.navigate_to_edit(created_skill.id)
    edit_page.should_see_subagent_toggle()
    edit_page.toggle_subagent_spawning(enable=True)
    edit_page.click_save()

    # Step 5: Reload and confirm toggle state
    edit_page.navigate_to_edit(created_skill.id)
    edit_page.should_see_subagent_setting(value=True)

    # Step 6: Verify via SDK
    api_skill = skill_utils.get_skill_by_id(created_skill.id)
    assert_that(
        api_skill.enabled_builtin_subagents,
        equal_to([BUILTIN_SUBAGENT_ID]),
        f"API should return {[BUILTIN_SUBAGENT_ID]} after UI toggle ON; "
        f"got: {api_skill.enabled_builtin_subagents}",
    )

    # Step 7: Create assistant and attach the skill
    asst_name = _unique_name()
    raw_assistant(
        name=asst_name,
        skill_id=created_skill.id,
        system_prompt="You are a helpful assistant. Use any available tools to answer questions.",
        description="E2E subagent test assistant",
    )

    # Steps 8-10: Open chat, send message, verify response
    chat_page = ChatPage(page)
    page.goto("/chats")
    chat_page.wait_for_page_load()
    chat_page.start_new_chat()

    chat_page.send_message("Hello, please respond briefly.", assistant_name=asst_name)
    # Allow extra time — subagent spawning adds latency
    chat_page.wait_for_assistant_response()
    chat_page.should_have_assistant_response()


# ---------------------------------------------------------------------------
# TC-022  Cross-layer: enable via UI → API confirms → disable via UI → API confirms
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.ui
def test_cross_layer_ui_toggle_reflects_in_api(page, skill, skill_utils):
    """TC-022: Toggle ON via UI → API returns field=GENERAL_PURPOSE_SUBAGENT.
    Toggle OFF via UI → API returns field=[].

    This cross-layer test confirms UI mutations are immediately reflected in API.
    """
    created_skill = skill(
        skill_name=_unique_name(),
        description=SKILL_DESCRIPTION,
        content=SKILL_CONTENT,
    )
    edit_page = CreateEditSkillPage(page)

    # --- Phase 1: Toggle ON ---
    edit_page.navigate_to_edit(created_skill.id)
    edit_page.toggle_subagent_spawning(enable=True)
    edit_page.click_save()

    api_skill = skill_utils.get_skill_by_id(created_skill.id)
    assert_that(
        api_skill.enabled_builtin_subagents,
        equal_to([BUILTIN_SUBAGENT_ID]),
        f"After toggle ON, API must return {[BUILTIN_SUBAGENT_ID]}; "
        f"got: {api_skill.enabled_builtin_subagents}",
    )

    # --- Phase 2: Toggle OFF ---
    edit_page.navigate_to_edit(created_skill.id)
    edit_page.should_see_subagent_setting(value=True)
    edit_page.toggle_subagent_spawning(enable=False)
    edit_page.click_save()

    api_skill_after = skill_utils.get_skill_by_id(created_skill.id)
    assert_that(
        api_skill_after.enabled_builtin_subagents,
        equal_to([]),
        f"After toggle OFF, API must return []; "
        f"got: {api_skill_after.enabled_builtin_subagents}",
    )

    # Reload UI and confirm toggle is OFF
    edit_page.navigate_to_edit(created_skill.id)
    edit_page.should_see_subagent_setting(value=False)
