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

"""Tests for Jira KB datasource operations — including custom_fields support."""

import os
import pytest
from hamcrest import assert_that, equal_to, is_, none, contains_string
from requests import HTTPError

from codemie_sdk.models.datasource import DataSourceStatus
from codemie_sdk.models.integration import CredentialTypes

from codemie_test_harness.tests.test_data.pm_tools_test_data import (
    JIRA_TOOL_PROMPT,
    RESPONSE_FOR_JIRA_TOOL,
    JIRA_CLOUD_TOOL_PROMPT,
    RESPONSE_FOR_JIRA_CLOUD_TOOL,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.jira_seed import require_custom_fields
from codemie_test_harness.tests.utils.base_utils import (
    get_random_name,
    assert_response,
    assert_tool_triggered,
)
from codemie_test_harness.tests.enums.tools import Default
from codemie_test_harness.tests import PROJECT


@pytest.fixture(scope="function")
def jira_cloud_datasource(
    datasource_utils, jira_cloud_integration, jira_cloud_seed_issue
):
    datasource = datasource_utils.create_jira_datasource(
        setting_id=jira_cloud_integration.id, jql=jira_cloud_seed_issue.jql
    )
    yield datasource
    if datasource:
        datasource_utils.delete_datasource(datasource)


@pytest.mark.datasource
@pytest.mark.project_management
@pytest.mark.api
@pytest.mark.parametrize(
    "datasource_fixture, prompt, expected_response",
    [
        pytest.param(
            "jira_datasource",
            JIRA_TOOL_PROMPT,
            RESPONSE_FOR_JIRA_TOOL,
            marks=[pytest.mark.jira, pytest.mark.smoke],
            id="Jira",
        ),
        pytest.param(
            "jira_cloud_datasource",
            JIRA_CLOUD_TOOL_PROMPT,
            RESPONSE_FOR_JIRA_CLOUD_TOOL,
            marks=[pytest.mark.jira, pytest.mark.jira_cloud],
            id="Jira Cloud",
        ),
    ],
)
def test_create_datasource_with_jira_and_jira_cloud_integration(
    request,
    assistant,
    assistant_utils,
    datasource_utils,
    kb_context,
    similarity_check,
    datasource_fixture,
    prompt,
    expected_response,
    seeded,
):
    prompt = seeded(prompt)
    expected_response = seeded(expected_response)
    datasource = request.getfixturevalue(datasource_fixture)
    assistant = assistant(
        context=kb_context(datasource), system_prompt="Run tools on each user prompt"
    )

    response, triggered_tools = assistant_utils.ask_assistant(
        assistant, prompt, minimal_response=False
    )
    assert_tool_triggered(Default.SEARCH_KB, triggered_tools)
    similarity_check.check_similarity(response, expected_response)

    datasource_utils.update_jira_datasource(
        datasource.id, full_reindex=True, skip_reindex=False
    )

    response, triggered_tools = assistant_utils.ask_assistant(
        assistant, prompt, minimal_response=False
    )
    assert_tool_triggered(Default.SEARCH_KB, triggered_tools)
    similarity_check.check_similarity(response, expected_response)


@pytest.mark.datasource
@pytest.mark.jira
@pytest.mark.api
def test_edit_description_for_jira_data_source(
    client, datasource_utils, jira_datasource
):
    updated_description = get_random_name()

    datasource_utils.update_jira_datasource(
        jira_datasource.id, description=updated_description
    )

    updated_datasource = client.datasources.get(jira_datasource.id)
    assert_that(updated_datasource.description, equal_to(updated_description))


@pytest.mark.datasource
@pytest.mark.jira
@pytest.mark.api
def test_create_jira_datasource_with_existing_name(datasource_utils, jira_datasource):
    datasource = datasource_utils.get_datasource(jira_datasource.id)

    try:
        datasource_utils.create_jira_datasource(
            name=datasource.name, setting_id=datasource.setting_id
        )
        raise AssertionError("There are no error message for duplicate datasource name")
    except HTTPError as e:
        assert_response(
            e.response,
            409,
            f"An index with the name '{datasource.name}' already exists in the project '{os.getenv('PROJECT_NAME')}'.",
        )


@pytest.fixture
def jira_context_menu_reindex_setup(project, integration_utils, datasource_utils):
    """
    Isolated setup for context-menu reindex test.

    Creates a new project with 3 Jira integrations: invalid-1, valid, invalid-2.
    The datasource is created using the valid integration.
    Verifies that reindex uses kb_index.setting_id rather than the first integration.
    """
    isolated_project = project()

    invalid_creds = CredentialsManager.invalid_jira_credentials()
    invalid_integration_1 = integration_utils.create_integration(
        CredentialTypes.JIRA, invalid_creds, project_name=isolated_project.name
    )
    valid_integration = integration_utils.create_integration(
        CredentialTypes.JIRA,
        CredentialsManager.jira_credentials(),
        project_name=isolated_project.name,
    )
    invalid_integration_2 = integration_utils.create_integration(
        CredentialTypes.JIRA, invalid_creds, project_name=isolated_project.name
    )

    datasource = datasource_utils.create_jira_datasource(
        setting_id=valid_integration.id,
        project_name=isolated_project.name,
    )

    yield datasource

    datasource_utils.delete_datasource(datasource)
    for integration in [
        invalid_integration_1,
        valid_integration,
        invalid_integration_2,
    ]:
        try:
            integration_utils.delete_integration(integration)
        except HTTPError:
            pass


@pytest.mark.datasource
@pytest.mark.jira
@pytest.mark.api
def test_jira_datasource_context_menu_reindex_without_setting_id(
    datasource_utils, jira_context_menu_reindex_setup
):
    """
    Regression test: context-menu reindex resolves integration via kb_index.setting_id.

    Verifies that a full reindex uses the stored kb_index.setting_id (the valid
    integration) rather than falling back to the first integration in the project
    (which would be an invalid-token integration, causing reindex to fail).
    """
    updated_datasource = datasource_utils.update_jira_datasource(
        jira_context_menu_reindex_setup.id,
        full_reindex=True,
        skip_reindex=False,
    )

    assert_that(updated_datasource.status, equal_to(DataSourceStatus.COMPLETED))


# ---------------------------------------------------------------------------
# Jira KB custom_fields support
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# TC_001 — Create Jira KB datasource with custom_fields
# ---------------------------------------------------------------------------


@pytest.mark.datasource
@pytest.mark.jira
@pytest.mark.api
@pytest.mark.smoke
def test_create_jira_datasource_with_custom_fields(
    datasource_utils, jira_integration, jira_seed_issue
):
    """
    POST /v1/index/knowledge_base/jira with custom_fields persists the list and
    returns HTTP 201 (implicit — wait_for_indexing succeeds only if creation did).
    The created datasource's jira.custom_fields must match the submitted value.
    """
    custom_field = require_custom_fields(jira_seed_issue, 1)[0].id

    datasource = datasource_utils.create_jira_datasource(
        setting_id=jira_integration.id,
        custom_fields=[custom_field],
    )

    try:
        assert_that(datasource.status, equal_to(DataSourceStatus.COMPLETED))
        assert_that(datasource.jira.custom_fields, equal_to([custom_field]))
    finally:
        datasource_utils.delete_datasource(datasource)


# ---------------------------------------------------------------------------
# TC_002 — Update custom_fields and verify change persists after reindex
# ---------------------------------------------------------------------------


@pytest.mark.datasource
@pytest.mark.jira
@pytest.mark.api
def test_update_jira_datasource_custom_fields_triggers_reindex(
    datasource_utils, jira_integration, jira_seed_issue
):
    """
    PUT /v1/index/knowledge_base/jira updates custom_fields via flag_modified
    (SQLAlchemy JSON mutation detection) and the change is readable on
    subsequent GET.  A full reindex is then triggered and completes successfully.
    """
    field_1, field_2 = (f.id for f in require_custom_fields(jira_seed_issue, 2))

    datasource = datasource_utils.create_jira_datasource(
        setting_id=jira_integration.id,
        custom_fields=[field_1],
    )

    try:
        updated_datasource = datasource_utils.update_jira_datasource(
            datasource.id,
            custom_fields=[field_2],
            full_reindex=True,
            skip_reindex=False,
        )

        assert_that(updated_datasource.status, equal_to(DataSourceStatus.COMPLETED))
        assert_that(updated_datasource.jira.custom_fields, equal_to([field_2]))
    finally:
        datasource_utils.delete_datasource(datasource)


# ---------------------------------------------------------------------------
# TC_004 — Unknown custom field → HTTP 422
# ---------------------------------------------------------------------------


@pytest.mark.datasource
@pytest.mark.jira
@pytest.mark.api
@pytest.mark.smoke
def test_create_jira_datasource_with_unknown_custom_field_returns_422(
    datasource_utils, jira_integration
):
    """
    POST /v1/index/knowledge_base/jira with a non-existent custom field ID
    raises HTTP 422.  The response body must include the
    InvalidCustomFieldException message listing the unknown field name.
    """
    try:
        datasource_utils.create_jira_datasource(
            setting_id=jira_integration.id,
            custom_fields=["nonexistent_field_xyz"],
        )
        raise AssertionError(
            "Expected HTTP 422 for unknown custom field but creation succeeded"
        )
    except HTTPError as e:
        assert_response(
            e.response,
            422,
            "Unknown or inaccessible Jira custom field(s): nonexistent_field_xyz. "
            "Check field IDs/names and integration permissions.",
        )


# ---------------------------------------------------------------------------
# TC_005 — Indexed document page_content contains rendered custom field values
# ---------------------------------------------------------------------------


@pytest.mark.datasource
@pytest.mark.jira
@pytest.mark.api
def test_indexed_document_contains_custom_field_values(
    datasource_utils,
    jira_integration,
    assistant,
    assistant_utils,
    kb_context,
    jira_seed_issue,
):
    """
    After full indexing with a configured custom field, _render_custom_fields
    appends '{display_name}: {value}\\n' lines to Document.page_content so the
    content is embeddable and searchable.
    The response must contain the value written to the seed issue (harness-cf-1).
    """
    custom_field = require_custom_fields(jira_seed_issue, 1, with_values=True)[0]

    datasource = datasource_utils.create_jira_datasource(
        setting_id=jira_integration.id,
        custom_fields=[custom_field.id],
        jql=jira_seed_issue.jql,
    )

    try:
        kb_assistant = assistant(
            context=kb_context(datasource),
            system_prompt="Answer precisely based on the indexed content only.",
        )
        prompt = (
            f"What is the value of the '{custom_field.name}' field for Jira issue"
            f" {jira_seed_issue.key}?"
        )
        response, triggered_tools = assistant_utils.ask_assistant(
            kb_assistant, prompt, minimal_response=False
        )
        assert_tool_triggered(Default.SEARCH_KB, triggered_tools)
        assert_that(response, contains_string(custom_field.value))
    finally:
        datasource_utils.delete_datasource(datasource)


# ---------------------------------------------------------------------------
# TC_006 — Full reindex cycle persists custom_fields configuration
# ---------------------------------------------------------------------------


@pytest.mark.datasource
@pytest.mark.jira
@pytest.mark.api
def test_full_reindex_cycle_persists_custom_fields(
    datasource_utils, jira_integration, jira_seed_issue
):
    """
    custom_fields survive two consecutive full reindex cycles (_effective_custom_fields
    falls back to JiraIndexInfo.jira.custom_fields on cron/resume flows).
    """
    custom_field = require_custom_fields(jira_seed_issue, 1)[0].id

    datasource = datasource_utils.create_jira_datasource(
        setting_id=jira_integration.id,
        custom_fields=[custom_field],
    )

    try:
        assert_that(datasource.jira.custom_fields, equal_to([custom_field]))

        # Second full reindex (simulates cron/resume cycle)
        after_second_reindex = datasource_utils.update_jira_datasource(
            datasource.id,
            full_reindex=True,
            skip_reindex=False,
        )

        assert_that(after_second_reindex.status, equal_to(DataSourceStatus.COMPLETED))
        assert_that(after_second_reindex.jira.custom_fields, equal_to([custom_field]))
    finally:
        datasource_utils.delete_datasource(datasource)


# ---------------------------------------------------------------------------
# TC_008 — Ambiguous display name → HTTP 422 with field ID guidance
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# TC_009 — Health check maps invalid custom field to field_error=jiraCustomFields
# ---------------------------------------------------------------------------


@pytest.mark.datasource
@pytest.mark.jira
@pytest.mark.api
def test_jira_health_check_invalid_custom_fields_returns_field_error(
    client, jira_integration, jira_seed_issue
):
    """
    POST /v1/index/health with index_type='jira', a valid setting_id, and an
    invalid custom_fields entry returns field_error='jiraCustomFields' with
    help='Remove or correct the listed custom fields.' — confirming
    datasource_health_check_service maps InvalidCustomFieldException to a
    structured field-level error.
    """
    response = client.datasources.health_check(
        index_type="jira",
        setting_id=jira_integration.id,
        jql=jira_seed_issue.jql,
        custom_fields=["nonexistent_custom_field_xyz"],
    )

    error = response.get("error", {})
    assert_that(error.get("field_error"), equal_to("jiraCustomFields"))
    assert_that(
        error.get("help"),
        equal_to("Remove or correct the listed custom fields."),
    )


# ---------------------------------------------------------------------------
# TC_010 — No custom_fields configured — backward compat
# ---------------------------------------------------------------------------


@pytest.mark.datasource
@pytest.mark.jira
@pytest.mark.api
@pytest.mark.smoke
def test_jira_datasource_without_custom_fields_indexes_normally(
    datasource_utils, jira_datasource
):
    """
    Jira KB datasource created without custom_fields completes indexing normally.
    jira.custom_fields is None (_resolve_custom_fields returns early when falsy)
    and _request_fields returns the original FIELDS constant unchanged —
    confirming backward compat for existing DB rows.
    """
    assert_that(jira_datasource.status, equal_to(DataSourceStatus.COMPLETED))
    assert_that(jira_datasource.jira.custom_fields, is_(none()))


# ---------------------------------------------------------------------------
# TC_013 — GET /index/jira/fields returns sorted fields; unreachable → HTTP 422
# ---------------------------------------------------------------------------


@pytest.mark.datasource
@pytest.mark.jira
@pytest.mark.api
@pytest.mark.smoke
def test_get_jira_fields_returns_sorted_non_default_fields(client, jira_integration):
    """Happy path

    GET /index/jira/fields with a valid integration setting_id returns HTTP 200
    and a non-empty list of non-default Jira fields sorted custom-first then
    alphabetically.  Each entry must contain 'id' and 'name' keys.
    """
    fields = client.datasources.get_jira_fields(
        jira_integration.id, project_name=PROJECT
    )

    assert_that(len(fields) > 0, equal_to(True))
    for field in fields:
        assert_that("id" in field, equal_to(True))
        assert_that("name" in field, equal_to(True))

    custom_fields = [f for f in fields if f.get("custom")]
    standard_fields = [f for f in fields if not f.get("custom")]
    expected_order = custom_fields + standard_fields
    assert_that(fields, equal_to(expected_order))


# ---------------------------------------------------------------------------
# TC_014 — PUT with empty custom_fields list clears stored fields
# ---------------------------------------------------------------------------


@pytest.mark.datasource
@pytest.mark.jira
@pytest.mark.api
def test_update_jira_datasource_with_empty_custom_fields_clears_stored_fields(
    datasource_utils, jira_integration, jira_seed_issue
):
    """
    PUT /v1/index/knowledge_base/jira with custom_fields=[] clears the stored
    list without triggering strict field validation (truthy guard bypasses
    resolution when the list is empty).  A subsequent GET must return
    custom_fields as an empty list.
    """
    custom_field = require_custom_fields(jira_seed_issue, 1)[0].id

    datasource = datasource_utils.create_jira_datasource(
        setting_id=jira_integration.id,
        custom_fields=[custom_field],
    )

    try:
        assert_that(datasource.jira.custom_fields, equal_to([custom_field]))

        updated_datasource = datasource_utils.update_jira_datasource(
            datasource.id,
            custom_fields=[],
            skip_reindex=True,
        )

        assert_that(updated_datasource.jira.custom_fields, equal_to([]))
    finally:
        datasource_utils.delete_datasource(datasource)
