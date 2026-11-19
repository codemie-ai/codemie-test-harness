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

"""API tests for deselecting the default tools a datasource adds to an assistant.

An assistant lists the default tools it does not want in ``disabled_context_tools``
(``get_repository_file_tree``, ``search_code_repo``, ``search_kb``). The tests cover the
tools listing, run-time gating, save and validation, versioning and the export.
"""

import json

import pytest
from hamcrest import (
    assert_that,
    contains_inanyorder,
    contains_string,
    equal_to,
    has_items,
    not_none,
)
from requests import HTTPError

from codemie_test_harness.tests.enums.tools import Toolkit
from codemie_test_harness.tests.test_data.default_datasource_tools_test_data import (
    CODE_TOOL_ROWS,
    CODEBASE_TOOLKIT_TOOL_NAMES,
    GET_REPOSITORY_FILE_TREE,
    KB_TOOL_ROWS,
    SEARCH_CODE_REPO,
    SEARCH_KB,
    SYSTEM_PROMPT_RUN_TOOLS,
    UNKNOWN_TOOL_NAME,
    UNKNOWN_TOOLS_MESSAGE,
)


def _row_id(row):
    state = "selected" if not row.disabled_context_tools else "deselected"
    return f"{row.tool.value}-{state}"


@pytest.mark.assistant
@pytest.mark.requires_capability("retrieval")
@pytest.mark.api
def test_codebase_tools_listing_holds_standard_filtering_and_kb_tools(assistant_utils):
    # @case deselect-default-datasource-tools_TC_001
    toolkits = assistant_utils.get_assistant_tools()

    codebase = next(
        (kit for kit in toolkits if kit.toolkit == Toolkit.CODEBASE_TOOLS.value), None
    )
    assert_that(codebase, not_none(), "Toolkit 'Codebase Tools' is not listed")
    assert_that(
        [tool.name for tool in codebase.tools],
        has_items(*CODEBASE_TOOLKIT_TOOL_NAMES),
        "Codebase Tools must list the standard, with-filtering and search_kb tools",
    )


@pytest.mark.assistant
@pytest.mark.datasource
@pytest.mark.api
@pytest.mark.parametrize(
    "row",
    [
        *[
            pytest.param(
                row, id=_row_id(row), marks=[pytest.mark.gitlab, pytest.mark.github]
            )
            for row in CODE_TOOL_ROWS
        ],
        *[pytest.param(row, id=_row_id(row)) for row in KB_TOOL_ROWS],
    ],
)
def test_default_datasource_tool_follows_disabled_context_tools_at_run_time(
    request, assistant_factory, assistant_utils, row
):
    # @case deselect-default-datasource-tools_TC_002
    datasource = request.getfixturevalue(row.datasource_fixture)
    context = request.getfixturevalue(row.context_fixture)(datasource)

    created = assistant_factory.create(
        context=[context],
        system_prompt=SYSTEM_PROMPT_RUN_TOOLS,
        disabled_context_tools=row.disabled_context_tools,
    )

    stored = assistant_utils.get_assistant_by_id(created.id)
    assert_that(
        stored.disabled_context_tools,
        equal_to(row.disabled_context_tools),
        "The assistant must return the deselected list it was created with",
    )

    _, triggered_tools = assistant_utils.ask_assistant(
        created, row.prompt, minimal_response=False
    )
    row.assert_tool_state(row.tool, triggered_tools)


@pytest.mark.assistant
@pytest.mark.api
@pytest.mark.parametrize(
    "initial, updated",
    [
        pytest.param([], [SEARCH_KB], id="save_search_kb"),
        pytest.param([SEARCH_KB], [], id="clear_with_empty_list"),
    ],
)
def test_assistant_update_saves_and_returns_disabled_context_tools(
    assistant_factory, assistant_utils, initial, updated
):
    # @case deselect-default-datasource-tools_TC_003
    created = assistant_factory.create(disabled_context_tools=initial)

    assistant_utils.update_assistant_disabled_context_tools(created.id, updated)

    stored = assistant_utils.get_assistant_by_id(created.id)
    assert_that(stored.disabled_context_tools, equal_to(updated))


@pytest.mark.assistant
@pytest.mark.api
def test_assistant_update_refuses_unknown_disabled_context_tool(
    assistant_factory, assistant_utils
):
    # @case deselect-default-datasource-tools_TC_003
    created = assistant_factory.create(disabled_context_tools=[SEARCH_KB])

    with pytest.raises(HTTPError) as exc_info:
        assistant_utils.update_assistant_disabled_context_tools(
            created.id, [UNKNOWN_TOOL_NAME]
        )

    assert_that(
        exc_info.value.response.text,
        contains_string(f"{UNKNOWN_TOOLS_MESSAGE}: {UNKNOWN_TOOL_NAME}"),
    )
    stored = assistant_utils.get_assistant_by_id(created.id)
    assert_that(
        stored.disabled_context_tools,
        equal_to([SEARCH_KB]),
        "A refused update must leave the stored list unchanged",
    )


@pytest.mark.assistant
@pytest.mark.api
def test_disabled_context_tools_survive_new_version_restore_and_compare(
    assistant_factory, assistant_utils
):
    # @case deselect-default-datasource-tools_TC_004
    first_list = [SEARCH_KB]
    second_list = [GET_REPOSITORY_FILE_TREE, SEARCH_CODE_REPO]
    created = assistant_factory.create(disabled_context_tools=first_list)

    assistant_utils.update_assistant_disabled_context_tools(created.id, second_list)

    versions = assistant_utils.list_assistant_versions(created.id)
    first_version, second_version = sorted(v.version_number for v in versions)[:2]
    assert_that(
        assistant_utils.get_assistant_version(
            created.id, first_version
        ).disabled_context_tools,
        equal_to(first_list),
        "The first version must keep the list it was created with",
    )
    assert_that(
        assistant_utils.get_assistant_version(
            created.id, second_version
        ).disabled_context_tools,
        contains_inanyorder(*second_list),
        "The new version must hold the changed list",
    )

    comparison = assistant_utils.compare_assistant_versions(
        created.id, first_version, second_version
    )
    assert_that(
        json.dumps(comparison),
        contains_string("disabled_context_tools"),
        "The version compare result must include disabled_context_tools",
    )

    assistant_utils.rollback_to_version(created.id, first_version)

    restored = assistant_utils.get_assistant_by_id(created.id)
    assert_that(
        restored.disabled_context_tools,
        equal_to(first_list),
        "A restore must bring back the first version's list",
    )
