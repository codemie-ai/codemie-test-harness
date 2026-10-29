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

"""API tests for xWiki datasource support.

Scenarios:
    TC-002  Create an xWiki datasource, ingest a Space, retrieve content via SEARCH_KB
    TC-003  Full reindex of an xWiki datasource returns to COMPLETED and stays searchable
    TC-004  Creating an xWiki datasource with no xWiki integration configured is
            rejected with HTTP 400 before any indexing starts
    TC-005  xWiki health check with a mismatched base URL surfaces a field-specific error
    TC-006  Create an xWiki datasource authenticated with Basic Auth (username/password)
            and retrieve content via SEARCH_KB, mirroring TC-002's Bearer-token flow
"""

import pytest
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    has_item,
    is_,
    is_not,
    none,
)
from requests import HTTPError

from codemie_sdk.models.datasource import DataSourceStatus, XWikiDataSourceRequest

from codemie_test_harness.tests import PROJECT
from codemie_test_harness.tests.enums.tools import Default
from codemie_test_harness.tests.test_data.xwiki_tools_test_data import (
    XWIKI_DATASOURCE_PROMPT,
)
from codemie_test_harness.tests.utils.base_utils import (
    assert_response,
    assert_tool_triggered,
    get_random_name,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager

pytestmark = [
    pytest.mark.skip(reason="No xwiki test environment configured"),
]


# ---------------------------------------------------------------------------
# TC-002 — Create xWiki datasource, ingest Space, retrieve via SEARCH_KB
# ---------------------------------------------------------------------------


@pytest.mark.datasource
@pytest.mark.xwiki
@pytest.mark.api
@pytest.mark.smoke
def test_create_xwiki_datasource_with_assistant(
    xwiki_datasource,
    xwiki_seed_page,
    assistant,
    assistant_utils,
    kb_context,
):
    """
    Validates:
    - POST /v1/index/knowledge_base/xwiki creates the datasource and indexing completes
    - IndexInfo.xwiki (space) is persisted on the returned datasource
    - The assistant's SEARCH_KB tool retrieves the ingested Space content
    """
    assert_that(xwiki_datasource.status, equal_to(DataSourceStatus.COMPLETED))
    assert_that(xwiki_datasource.xwiki.space, equal_to(xwiki_seed_page.space))

    test_assistant = assistant(
        context=kb_context(xwiki_datasource),
        system_prompt="Search the knowledge base for relevant information on each user prompt",
    )

    answer, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, XWIKI_DATASOURCE_PROMPT, minimal_response=False
    )

    assert_tool_triggered(Default.SEARCH_KB, triggered_tools)
    assert_that(
        answer,
        contains_string(xwiki_seed_page.token),
        "Assistant response should mention the token value from the seed page",
    )


# ---------------------------------------------------------------------------
# TC-003 — Full reindex returns to COMPLETED and content stays searchable
# ---------------------------------------------------------------------------


@pytest.mark.datasource
@pytest.mark.xwiki
@pytest.mark.api
def test_reindex_xwiki_datasource(
    xwiki_datasource,
    xwiki_seed_page,
    datasource_utils,
    assistant,
    assistant_utils,
    kb_context,
):
    """
    Validates:
    - PUT /v1/index/knowledge_base/xwiki with full_reindex=true schedules reindex_xwiki
    - Datasource status returns to COMPLETED after reindex
    - Content remains searchable via SEARCH_KB after reindex
    """
    test_assistant = assistant(
        context=kb_context(xwiki_datasource),
        system_prompt="Search the knowledge base for relevant information on each user prompt",
    )

    reindexed_datasource = datasource_utils.update_xwiki_datasource(
        xwiki_datasource.id, full_reindex=True, skip_reindex=False
    )

    assert_that(reindexed_datasource.status, equal_to(DataSourceStatus.COMPLETED))

    answer, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, XWIKI_DATASOURCE_PROMPT, minimal_response=False
    )

    assert_tool_triggered(Default.SEARCH_KB, triggered_tools)
    assert_that(
        answer,
        contains_string(xwiki_seed_page.token),
        "Content should remain searchable via SEARCH_KB after a full reindex",
    )


# ---------------------------------------------------------------------------
# TC-004 — No xWiki integration configured is blocked with 400
# ---------------------------------------------------------------------------


@pytest.mark.datasource
@pytest.mark.xwiki
@pytest.mark.api
def test_create_xwiki_datasource_without_integration_rejected_400(
    client, project, xwiki_seed_page
):
    """
    Validates:
    - POST /v1/index/knowledge_base/xwiki with no resolvable xWiki integration
      is rejected with HTTP 400 and INCORRECT_DATASOURCE_SETUP_MESSAGE details
    - No datasource row is created/scheduled as a result of the rejected request
    """
    isolated_project = project()
    datasource_name = get_random_name()

    create_request = XWikiDataSourceRequest(
        project_name=isolated_project.name,
        name=datasource_name,
        description=get_random_name(),
        space=xwiki_seed_page.space,
        # setting_id intentionally omitted — no xWiki integration configured
    )

    with pytest.raises(HTTPError) as exc_info:
        client.datasources.create(create_request)

    assert_response(
        exc_info.value.response,
        400,
        f"No xWiki integration is configured for project '{isolated_project.name}'.",
    )

    datasources = client.datasources.list(
        per_page=200, projects=[isolated_project.name]
    )
    assert_that(
        [ds.name for ds in datasources],
        is_not(has_item(datasource_name)),
        "No datasource should have been created when no xWiki integration is configured",
    )


# ---------------------------------------------------------------------------
# TC-005 — Mismatched base URL surfaces a field-specific error
# ---------------------------------------------------------------------------


@pytest.mark.datasource
@pytest.mark.xwiki
@pytest.mark.api
def test_health_check_xwiki_with_mismatched_base_url_returns_field_error(
    client, xwiki_invalid_url_integration, xwiki_seed_page
):
    """
    Validates:
    - POST /v1/index/health with index_type=knowledge_base_xwiki against an
      integration whose base URL is mismatched returns a field-specific error
      (field_error="url"), not a generic failure.
    """
    response = client.datasources.health_check(
        index_type="xwiki",
        setting_id=xwiki_invalid_url_integration.id,
        project_name=PROJECT,
        space=xwiki_seed_page.space,
    )

    error = response.get("error")
    assert_that(
        error,
        is_not(none()),
        "Health check against a mismatched base URL should return an error",
    )
    assert_that(
        error.get("field_error"),
        equal_to("url"),
        "Health check error should point at the 'url' field for a base-URL mismatch, "
        "not fail generically",
    )


# ---------------------------------------------------------------------------
# TC-006 — Basic Auth (username/password) datasource ingests and is searchable
# ---------------------------------------------------------------------------


@pytest.mark.datasource
@pytest.mark.xwiki
@pytest.mark.api
@pytest.mark.skipif(
    not (
        CredentialsManager.get_parameter("XWIKI_USERNAME")
        and CredentialsManager.get_parameter("XWIKI_PASSWORD")
    ),
    reason="No xwiki Basic Auth credentials configured",
)
def test_create_xwiki_datasource_with_basic_auth_retrieves_content(
    xwiki_basic_datasource,
    xwiki_seed_page,
    assistant,
    assistant_utils,
    kb_context,
):
    """
    Validates:
    - POST /v1/index/knowledge_base/xwiki with a Basic Auth integration creates
      the datasource and indexing completes
    - The seeded Space is ingested under Basic Auth, not just resolved as guest
    - The assistant's SEARCH_KB tool retrieves the ingested Space content
    """
    assert_that(xwiki_basic_datasource.status, equal_to(DataSourceStatus.COMPLETED))
    assert_that(xwiki_basic_datasource.xwiki.space, equal_to(xwiki_seed_page.space))

    test_assistant = assistant(
        context=kb_context(xwiki_basic_datasource),
        system_prompt="Search the knowledge base for relevant information on each user prompt",
    )

    answer, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, XWIKI_DATASOURCE_PROMPT, minimal_response=False
    )

    assert_tool_triggered(Default.SEARCH_KB, triggered_tools)
    assert_that(
        answer,
        contains_string(xwiki_seed_page.token),
        "Assistant response should mention the token value from the seed page "
        "when the datasource authenticates with Basic Auth",
    )


# ---------------------------------------------------------------------------
# TC-007 — Health check with a Basic Auth integration reports no error
# ---------------------------------------------------------------------------


@pytest.mark.datasource
@pytest.mark.xwiki
@pytest.mark.api
@pytest.mark.skipif(
    not (
        CredentialsManager.get_parameter("XWIKI_USERNAME")
        and CredentialsManager.get_parameter("XWIKI_PASSWORD")
    ),
    reason="No xwiki Basic Auth credentials configured",
)
def test_health_check_xwiki_with_basic_auth_returns_no_error(
    client, xwiki_basic_integration, xwiki_seed_page
):
    """
    Validates:
    - POST /v1/index/health with index_type=knowledge_base_xwiki against a valid
      Basic Auth integration and the seeded Space returns no error
    """
    response = client.datasources.health_check(
        index_type="xwiki",
        setting_id=xwiki_basic_integration.id,
        project_name=PROJECT,
        space=xwiki_seed_page.space,
    )

    assert_that(
        response.get("error"),
        is_(none()),
        "Health check with valid Basic Auth credentials should not report an error",
    )
