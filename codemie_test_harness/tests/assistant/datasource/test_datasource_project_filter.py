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

"""Tests for Assistant datasource search/list project filtering.

Verifies that GET /v1/assistants/context?project_name=PROJECT returns only
datasources from the specified project, and that listing datasources with a
project filter correctly excludes datasources from other projects — even when
same-name datasources exist across multiple projects.

Covers datasource types: file, Google Docs, Jira, Confluence.
"""

from collections.abc import Callable

import pytest
from hamcrest import assert_that, contains_string, equal_to, is_not

from codemie_test_harness.tests import PROJECT
from codemie_test_harness.tests.enums.tools import Default
from codemie_test_harness.tests.test_data.google_datasource_test_data import (
    get_google_doc_url,
)
from codemie_test_harness.tests.utils.base_utils import (
    assert_tool_triggered,
    get_random_name,
)
from codemie_test_harness.tests.utils.constants import FILES_PATH, test_project_name

# ── DS factory helpers ────────────────────────────────────────────────────────
# Each factory has signature (datasource_utils, request, **kwargs) so that
# integration-dependent types can lazily resolve their fixture via
# request.getfixturevalue() without requiring it in every test signature.

_TXT_FILE = "test.txt"  # content: "This file is for test purpose."
_CSV_FILE = "test.csv"  # content: track/year data (1918: 1922, track A: track B, ...)


def _file_ds(datasource_utils, request, **kwargs):
    return datasource_utils.create_file_datasource(
        files=[str(FILES_PATH / _TXT_FILE)], **kwargs
    )


def _google_ds(datasource_utils, request, **kwargs):
    integration = request.getfixturevalue("google_integration")
    return datasource_utils.create_google_doc_datasource(
        google_doc=get_google_doc_url(), setting_id=integration.id, **kwargs
    )


def _jira_ds(datasource_utils, request, **kwargs):
    integration = request.getfixturevalue("jira_integration")
    return datasource_utils.create_jira_datasource(setting_id=integration.id, **kwargs)


def _confluence_ds(datasource_utils, request, **kwargs):
    integration = request.getfixturevalue("confluence_integration")
    return datasource_utils.create_confluence_datasource(
        setting_id=integration.id, **kwargs
    )


KB_DS_PARAMS = [
    pytest.param(_file_ds, id="file", marks=[pytest.mark.file]),
    pytest.param(_google_ds, id="google", marks=[pytest.mark.google]),
    pytest.param(_jira_ds, id="jira", marks=[pytest.mark.jira, pytest.mark.jira_kb]),
    pytest.param(
        _confluence_ds,
        id="confluence",
        marks=[pytest.mark.confluence, pytest.mark.confluence_kb],
    ),
]

# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.datasource
@pytest.mark.api
@pytest.mark.parametrize("create_ds", KB_DS_PARAMS)
def test_assistant_context_returns_only_project_datasources_when_same_name_exists(
    datasource_utils, assistant_utils, request, create_ds: Callable
):
    """
    AC#1 + AC#2: GET /v1/assistants/context?project_name=PROJECT must list only
    datasources belonging to PROJECT, even when a datasource with the same name
    exists in a different project.
    """
    shared_name = get_random_name()
    ds_project = ds_other = None

    try:
        ds_project = create_ds(datasource_utils, request, name=shared_name)
        ds_other = create_ds(
            datasource_utils, request, name=shared_name, project_name=test_project_name
        )

        contexts = assistant_utils.get_assistant_context(PROJECT)

        # Context objects only carry name + context_type; has_length(1) is sufficient
        # to prove the endpoint scopes results to PROJECT (one DS per project was created).
        matching = [c for c in contexts if c.name == shared_name]
        assert_that(len(matching), equal_to(1))
    finally:
        if ds_project:
            datasource_utils.delete_datasource(ds_project)
        if ds_other:
            datasource_utils.delete_datasource(ds_other)


@pytest.mark.datasource
@pytest.mark.api
@pytest.mark.parametrize("create_ds", KB_DS_PARAMS)
def test_datasource_list_filtered_by_project_excludes_other_project_datasources(
    datasource_utils, client, request, create_ds: Callable
):
    """
    AC#3: When same-name datasources exist in different projects, listing
    datasources filtered by project must return only the one from that project.

    This validates that navigating to an attached datasource from assistant
    details resolves to the correct project's datasource.
    """
    shared_name = get_random_name()
    ds_project = ds_other = None

    try:
        ds_project = create_ds(datasource_utils, request, name=shared_name)
        ds_other = create_ds(
            datasource_utils, request, name=shared_name, project_name=test_project_name
        )

        all_project_datasources = client.datasources.list(
            projects=[PROJECT], per_page=200
        )
        matching = [ds for ds in all_project_datasources if ds.name == shared_name]

        assert_that(len(matching), equal_to(1))
        assert_that(matching[0].id, equal_to(ds_project.id))
        assert_that(matching[0].project_name, equal_to(PROJECT))
    finally:
        if ds_project:
            datasource_utils.delete_datasource(ds_project)
        if ds_other:
            datasource_utils.delete_datasource(ds_other)


@pytest.mark.datasource
@pytest.mark.api
@pytest.mark.smoke
@pytest.mark.parametrize("create_ds", KB_DS_PARAMS)
def test_assistant_context_no_regression_for_unique_datasource_name(
    datasource_utils, assistant_utils, request, create_ds: Callable
):
    """
    AC#4: No regression — a datasource with a unique name (present only in PROJECT)
    must still appear in GET /v1/assistants/context?project_name=PROJECT.
    """
    ds = None
    try:
        ds = create_ds(datasource_utils, request, name=get_random_name())

        contexts = assistant_utils.get_assistant_context(PROJECT)

        matching = [c for c in contexts if c.name == ds.name]
        assert_that(len(matching), equal_to(1))
        assert_that(matching[0].name, equal_to(ds.name))
    finally:
        if ds:
            datasource_utils.delete_datasource(ds)


# ── Content-level KB search (file DS only — requires fully controlled content) ─


@pytest.mark.datasource
@pytest.mark.file
@pytest.mark.api
def test_assistant_searches_correct_file_datasource_when_same_name_exists(
    datasource_utils, assistant, assistant_utils, kb_context
):
    """
    Core bug regression: when an assistant in PROJECT has a KB datasource attached
    by name, and a datasource with the same name exists in a different project with
    different content, the assistant must return content from PROJECT's datasource.

    DS in PROJECT  → test.txt  ("This file is for test purpose.")
    DS in other    → test.csv  (track/year data — "track A", "1918")

    Note: Context is intentionally resolved by name (Context.name = datasource.name),
    which is how the bug manifests — the backend must scope name resolution to the
    assistant's project, not match the first datasource with that name globally.

    File DS is used here because it allows fully deterministic content control.
    The structural filtering tests above (parametrized across all DS types) cover
    the same project-scoping logic for Google, Jira, and Confluence.
    """
    shared_name = get_random_name()
    ds_project = ds_other = None

    try:
        ds_project = datasource_utils.create_file_datasource(
            name=shared_name,
            files=[str(FILES_PATH / _TXT_FILE)],
        )
        ds_other = datasource_utils.create_file_datasource(
            name=shared_name,
            files=[str(FILES_PATH / _CSV_FILE)],
            project_name=test_project_name,
        )

        test_assistant = assistant(context=kb_context(ds_project))

        response, triggered_tools = assistant_utils.ask_assistant(
            test_assistant,
            "What is the content of the knowledge base?",
            minimal_response=False,
        )

        assert_tool_triggered(Default.SEARCH_KB, triggered_tools)
        assert_that(response, contains_string("This file is for test purpose."))
        assert_that(response, is_not(contains_string("track A")))
    finally:
        if ds_project:
            datasource_utils.delete_datasource(ds_project)
        if ds_other:
            datasource_utils.delete_datasource(ds_other)


@pytest.mark.datasource
@pytest.mark.file
@pytest.mark.api
def test_assistant_searches_file_datasource_after_project_transfer(
    datasource_utils, assistant, assistant_utils, kb_context
):
    """
    Regression: after a file datasource is moved from PROJECT to another project,
    an assistant in that new project must still be able to search it and return
    the correct content.

    Steps:
    1. Create DS in PROJECT with test.txt content.
    2. Move DS to test_project_name via new_project_name update field.
    3. Assert DS is now in test_project_name (move was applied).
    4. Create assistant in test_project_name attached to the moved DS.
    5. Ask the assistant about KB content.
    6. Assert search_kb was triggered and response contains txt content.
    """
    ds = None
    try:
        ds = datasource_utils.create_file_datasource(
            name=get_random_name(),
            files=[str(FILES_PATH / _TXT_FILE)],
        )
        assert_that(ds.project_name, equal_to(PROJECT))

        ds = datasource_utils.move_file_datasource(ds.id, test_project_name)
        assert_that(ds.project_name, equal_to(test_project_name))

        test_assistant = assistant(
            context=kb_context(ds), project_name=test_project_name
        )

        response, triggered_tools = assistant_utils.ask_assistant(
            test_assistant,
            "What is the content of the knowledge base?",
            minimal_response=False,
        )

        assert_tool_triggered(Default.SEARCH_KB, triggered_tools)
        assert_that(response, contains_string("This file is for test purpose."))
    finally:
        if ds:
            datasource_utils.delete_datasource(ds)
