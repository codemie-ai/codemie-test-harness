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
Tests for assistant built-in subagents.

Covers:
    TC-003  Spawned subagent property sweep — inherited vs excluded
    TC-004  Built-in system prompt enforcement
    TC-005  Recursion guard state on spawned subagent
    TC-008  Subassistants never inherited
    TC-011  Builtin subagent registry contents and deduplication
    TC-012  Full flow — skill enabled, subagent spawnable (persistence check)
    TC-013  Full flow — skill disabled, subagent field absent
    TC-014  Multi-skill assistant with mixed subagent settings
    TC-017  Subagent created with safe defaults when parent has empty optional fields
    CR-006  Runtime property sweep — chat endpoint reachable with enabled subagent config

Implementation note:
    `enabled_builtin_subagents` is stored on the assistant record and on each
    skill record.  Skill contributions are merged into the effective set at
    *runtime* inside the engine builder; they are NOT written back to the
    assistant DB row.  Therefore tests here verify:
      (a) The assistant's own `enabled_builtin_subagents` is persisted and
          retrieved correctly via PUT and GET.
      (b) The catalog endpoint lists available built-in subagents.
      (c) Field-level rules (deduplication, inheritance exclusions) hold on
          the assistant record itself.
      (d) The chat endpoint returns a valid response when enabled_builtin_subagents
          is set (runtime path smoke test).
"""

import time

import pytest
from hamcrest import (
    assert_that,
    equal_to,
    greater_than_or_equal_to,
    is_,
    not_none,
)


from codemie_sdk.models.assistant import (
    AssistantUpdateRequest,
    BuiltinSubagent,
)
from codemie_test_harness.tests import PROJECT
from codemie_test_harness.tests.enums.tools import BuiltinSubagentTool
from codemie_test_harness.tests.utils.base_utils import assert_tool_triggered

BUILTIN_SUBAGENT_ID = "GENERAL_PURPOSE_SUBAGENT"
BUILTIN_SUBAGENT_DISPLAY_NAME = "General Purpose"

# Content must be at least 100 characters (API validation)
_SKILL_CONTENT = (
    "# Built-in Subagent Test Skill\n\n"
    "## Description\n"
    "Integration test skill for validating built-in subagent field inheritance and gating behavior.\n"
    "Used in end-to-end tests."
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# TC-011  Built-in subagent registry catalog
# ---------------------------------------------------------------------------


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.api
def test_builtin_subagent_catalog_contains_general_purpose(assistant_utils):
    """TC-011: GET /v1/assistants/builtin_subagents returns at least one entry."""
    catalog: list[BuiltinSubagent] = assistant_utils.get_builtin_subagents()
    assert_that(catalog, not_none())
    assert_that(
        len(catalog),
        greater_than_or_equal_to(1),
        "Catalog should contain at least one built-in subagent",
    )

    ids = [entry.id for entry in catalog]
    assert_that(
        BUILTIN_SUBAGENT_ID in ids,
        is_(True),
        f"Catalog should contain '{BUILTIN_SUBAGENT_ID}'",
    )


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.api
def test_builtin_subagent_catalog_has_display_name(assistant_utils):
    """TC-011b: Catalog entry has expected display_name."""
    catalog: list[BuiltinSubagent] = assistant_utils.get_builtin_subagents()
    gp_entry = next(
        (e for e in catalog if e.id == BUILTIN_SUBAGENT_ID),
        None,
    )
    assert_that(gp_entry, not_none(), "General Purpose entry must be in catalog")
    assert_that(
        gp_entry.display_name,
        equal_to(BUILTIN_SUBAGENT_DISPLAY_NAME),
    )


# ---------------------------------------------------------------------------
# TC-003  Inherited vs excluded properties (persistence check)
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.api
def test_assistant_with_builtin_subagent_persists_own_prompt(
    raw_assistant, assistant_utils
):
    """TC-003/TC-004: Parent keeps its own system_prompt after enabled_builtin_subagents is set.

    The built-in subagent receives its own fixed prompt at runtime; the parent's
    stored system_prompt must remain unchanged.

    Persistence-layer check only. Runtime property sweep of the spawned subagent
    (inherited model, tools, built-in prompt value, empty subassistants) is not
    accessible via the REST API test harness.
    """
    custom_prompt = "This is the parent system prompt that must not be replaced."
    asst_id = raw_assistant([BUILTIN_SUBAGENT_ID])

    fetched = assistant_utils.get_assistant_by_id(asst_id)

    assistant_utils.update_assistant(
        asst_id,
        AssistantUpdateRequest(
            name=fetched.name,
            slug=fetched.slug,
            description="TC-003 test",
            shared=False,
            system_prompt=custom_prompt,
            project=PROJECT,
            llm_model_type=fetched.llm_model_type,
            assistant_ids=[],
            enabled_builtin_subagents=[BUILTIN_SUBAGENT_ID],
        ),
    )
    time.sleep(1)

    fetched = assistant_utils.get_assistant_by_id(asst_id)
    assert_that(
        fetched.system_prompt,
        equal_to(custom_prompt),
        "Parent system_prompt must not be overwritten by built-in subagent prompt",
    )
    assert_that(fetched.enabled_builtin_subagents, equal_to([BUILTIN_SUBAGENT_ID]))
    assert_that(fetched.assistant_ids, equal_to([]))


# ---------------------------------------------------------------------------
# TC-005  Recursion guard — assistant-level field check
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.api
def test_recursion_guard_no_nested_assistant_ids(raw_assistant, assistant_utils):
    """TC-005: Parent with enabled_builtin_subagents has no sub-assistant IDs by default.

    Persistence-layer check only. The spawned subagent's recursion guard state at
    runtime (empty enabled_builtin_subagents on the child) is not observable via
    the REST API test harness.
    """
    asst_id = raw_assistant([BUILTIN_SUBAGENT_ID])
    fetched = assistant_utils.get_assistant_by_id(asst_id)

    assert_that(
        fetched.assistant_ids,
        equal_to([]),
        "Assistant with built-in subagents should start with no sub-assistant IDs",
    )
    assert_that(fetched.enabled_builtin_subagents, equal_to([BUILTIN_SUBAGENT_ID]))


# ---------------------------------------------------------------------------
# TC-008  Sub-assistants are independent of enabled_builtin_subagents
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.api
def test_assistant_ids_and_builtin_subagents_are_independent(
    raw_assistant, assistant_factory, assistant_utils
):
    """TC-008: assistant_ids and enabled_builtin_subagents are stored independently.

    Persistence-layer check only. Confirming the spawned subagent receives an empty
    assistant_ids list at runtime is not accessible via the REST API test harness.
    """
    sub_a = assistant_factory.create(system_prompt="Sub A")
    sub_b = assistant_factory.create(system_prompt="Sub B")

    asst_id = raw_assistant(
        enabled_builtin_subagents=[BUILTIN_SUBAGENT_ID],
        sub_assistant_ids=[sub_a.id, sub_b.id],
        description="TC-008 test",
        system_prompt="Coordinator",
    )

    fetched = assistant_utils.get_assistant_by_id(asst_id)
    assert_that(len(fetched.assistant_ids), equal_to(2))
    assert_that(fetched.enabled_builtin_subagents, equal_to([BUILTIN_SUBAGENT_ID]))


@pytest.mark.assistant
@pytest.mark.api
def test_empty_assistant_ids_with_builtin_subagent(raw_assistant, assistant_utils):
    """TC-008b: Parent with empty assistant_ids and enabled_builtin_subagents — both empty/set."""
    asst_id = raw_assistant([BUILTIN_SUBAGENT_ID])
    fetched = assistant_utils.get_assistant_by_id(asst_id)
    assert_that(fetched.assistant_ids, equal_to([]))
    assert_that(fetched.enabled_builtin_subagents, equal_to([BUILTIN_SUBAGENT_ID]))


# ---------------------------------------------------------------------------
# TC-012  Assistant-level subagent field persistence (full flow — persistence layer)
# ---------------------------------------------------------------------------


@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.api
def test_assistant_with_enabled_builtin_subagent_persists_field(
    raw_assistant, assistant_utils
):
    """TC-012: Create assistant with GENERAL_PURPOSE_SUBAGENT → field persists.

    Persistence-layer check only. Full flow verification (spawned subagent's inherited
    model/tools, built-in prompt content, empty subassistants) is not accessible via
    the REST API test harness; see CR-006 runtime smoke test for triggering coverage.
    """
    asst_id = raw_assistant([BUILTIN_SUBAGENT_ID])
    fetched = assistant_utils.get_assistant_by_id(asst_id)

    assert_that(fetched.enabled_builtin_subagents, equal_to([BUILTIN_SUBAGENT_ID]))
    assert_that(
        fetched.llm_model_type,
        not_none(),
        "Inherited LLM model type must be set",
    )


# ---------------------------------------------------------------------------
# TC-013  Assistant with disabled subagent field
# ---------------------------------------------------------------------------


@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.api
def test_assistant_with_empty_builtin_subagents_field(raw_assistant, assistant_utils):
    """TC-013: Create assistant with enabled_builtin_subagents=[] → field stays empty.

    Persistence-layer check only. Confirming no subagent is spawned during an actual
    chat call is not covered here; a dedicated runtime test would require sending a
    chat message and asserting the absence of any subagent tool call in the response.
    """
    asst_id = raw_assistant([])
    fetched = assistant_utils.get_assistant_by_id(asst_id)
    assert_that(fetched.enabled_builtin_subagents, equal_to([]))


# ---------------------------------------------------------------------------
# TC-014  Update enabled_builtin_subagents on existing assistant
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.api
def test_assistant_builtin_subagents_update_enable_then_disable(
    raw_assistant, assistant_utils
):
    """TC-014: Start with [], update to [GENERAL_PURPOSE_SUBAGENT], update back to []."""
    asst_id = raw_assistant([])
    fetched = assistant_utils.get_assistant_by_id(asst_id)

    # Enable
    assistant_utils.update_assistant(
        asst_id,
        AssistantUpdateRequest(
            name=fetched.name,
            slug=fetched.slug,
            description="TC-014 test",
            shared=False,
            system_prompt="Test",
            project=PROJECT,
            llm_model_type=fetched.llm_model_type,
            assistant_ids=[],
            enabled_builtin_subagents=[BUILTIN_SUBAGENT_ID],
        ),
    )
    time.sleep(1)
    enabled = assistant_utils.get_assistant_by_id(asst_id)
    assert_that(
        enabled.enabled_builtin_subagents,
        equal_to([BUILTIN_SUBAGENT_ID]),
        "Field should be set after update",
    )

    # Disable
    assistant_utils.update_assistant(
        asst_id,
        AssistantUpdateRequest(
            name=fetched.name,
            slug=fetched.slug,
            description="TC-014 test",
            shared=False,
            system_prompt="Test",
            project=PROJECT,
            llm_model_type=fetched.llm_model_type,
            assistant_ids=[],
            enabled_builtin_subagents=[],
        ),
    )
    time.sleep(1)
    disabled = assistant_utils.get_assistant_by_id(asst_id)
    assert_that(
        disabled.enabled_builtin_subagents,
        equal_to([]),
        "Field should be empty after disabling",
    )


# ---------------------------------------------------------------------------
# TC-017  Safe defaults when optional fields are empty
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.api
def test_assistant_with_empty_optional_fields_and_builtin_subagent(
    raw_assistant, assistant_utils
):
    """TC-017: Empty optional fields do not prevent enabled_builtin_subagents from being set."""
    asst_id = raw_assistant(
        enabled_builtin_subagents=[BUILTIN_SUBAGENT_ID],
        system_prompt="",
        description="TC-017 minimal parent",
    )

    fetched = assistant_utils.get_assistant_by_id(asst_id)
    assert_that(
        fetched.id,
        equal_to(asst_id),
        "Assistant with empty optional fields should be created without error",
    )
    assert_that(fetched.enabled_builtin_subagents, equal_to([BUILTIN_SUBAGENT_ID]))
    assert_that(fetched.assistant_ids, equal_to([]))


# ---------------------------------------------------------------------------
# CR-006  Runtime property sweep — chat endpoint smoke test
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.api
def test_assistant_with_enabled_subagent_runtime_chat(raw_assistant, assistant_utils):
    """CR-006 runtime sweep: Assistant with enabled_builtin_subagents triggers the
    built-in subagent and returns it in response thoughts.
    """
    asst_id = raw_assistant(
        [BUILTIN_SUBAGENT_ID],
        system_prompt="You MUST delegate every user request to the built-in General Purpose Subagent.",
    )
    assistant = assistant_utils.get_assistant_by_id(asst_id)

    generated, triggered_tools = assistant_utils.ask_assistant(
        assistant,
        "Use the built-in General Purpose Subagent to say hello briefly.",
        minimal_response=False,
    )
    assert_that(
        generated,
        not_none(),
        "Response.generated must be non-empty; the assistant did not produce a reply",
    )
    assert_tool_triggered(BuiltinSubagentTool.GENERAL_PURPOSE_SUBAGENT, triggered_tools)
