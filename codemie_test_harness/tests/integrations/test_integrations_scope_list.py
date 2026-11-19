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

"""API tests for the combined integrations list, GET /v1/settings with a scope.

Every test builds its rows as fresh users and searches by a per-run token in the alias, so the
assertions hold on a stand that already holds other integrations.
"""

from dataclasses import dataclass

import pytest
from hamcrest import (
    all_of,
    assert_that,
    contains_string,
    empty,
    equal_to,
    is_,
    matches_regexp,
    not_,
    none,
)
from requests import HTTPError

from codemie_sdk.models.integration import CredentialTypes, IntegrationType
from codemie_test_harness.tests.test_data.unified_integrations_list_test_data import (
    BUDGET_ALIAS_PREFIX,
    FILTER_SCENARIOS,
    INVALID_FILTERS_HELP,
    INVALID_FILTERS_MESSAGE,
    MALFORMED_FILTERS,
    OUT_OF_RANGE_PER_PAGE,
    ROW_GIT,
    ROW_GLOBAL,
    ROW_JIRA,
    ROW_PROJECT,
    SCOPE_ALL,
    SCOPE_PROJECT,
    SCOPE_USER,
    UNKNOWN_SCOPE,
    alias_for,
    git_placeholder_credentials,
    resolve_filters,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name, poll_until
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.integration_utils import IntegrationUtils
from codemie_test_harness.tests.utils.logger_util import expected_http_errors

UNPROCESSABLE = 422


def _ids(rows) -> list[str]:
    return [row.id for row in rows]


@pytest.fixture
def token() -> str:
    """Per-run token carried by every alias the test creates."""
    return get_random_name()


@pytest.fixture
def project_admin_integrations(fresh_project_admin_client) -> IntegrationUtils:
    return IntegrationUtils(fresh_project_admin_client)


@dataclass
class FilterRows:
    """The rows the filter scenarios search, by label, and the values their filters name."""

    token: str
    project: str
    creator: str
    rows: dict


@pytest.fixture
def filter_rows(
    project_admin_user,
    default_project_member,
    fresh_project_admin_client,
    project_admin_integrations,
    scoped_integrations,
    token,
) -> FilterRows:
    """Two Jira and one Git user integration, one of the Jira ones global, and one project row."""
    utils = project_admin_integrations
    own_project = project_admin_user.email
    administered = default_project_member.project_a
    rows = {
        ROW_JIRA: scoped_integrations.create(
            utils, IntegrationType.USER, own_project, alias_for(token, ROW_JIRA)
        ),
        ROW_GIT: scoped_integrations.create(
            utils,
            IntegrationType.USER,
            own_project,
            alias_for(token, ROW_GIT),
            credential_type=CredentialTypes.GIT,
            credential_values=git_placeholder_credentials(),
        ),
        ROW_GLOBAL: scoped_integrations.create(
            utils,
            IntegrationType.USER,
            own_project,
            alias_for(token, ROW_GLOBAL),
            is_global=True,
        ),
        ROW_PROJECT: scoped_integrations.create(
            utils, IntegrationType.PROJECT, administered, alias_for(token, ROW_PROJECT)
        ),
    }
    creator = fresh_project_admin_client.users.about_me().name
    assert_that(creator, is_(not_(none())), "The project admin has no display name")
    return FilterRows(token, administered, creator, rows)


# @case unified-integrations-list_TC_001
@pytest.mark.integration
@pytest.mark.api
@pytest.mark.oss_standalone
def test_scope_all_lists_both_scopes_newest_first(
    project_admin_user,
    default_project_member,
    project_admin_integrations,
    scoped_integrations,
    token,
):
    utils = project_admin_integrations
    own_project = project_admin_user.email
    first_user = scoped_integrations.create(
        utils, IntegrationType.USER, own_project, alias_for(token, "user-1")
    )
    project_row = scoped_integrations.create(
        utils,
        IntegrationType.PROJECT,
        default_project_member.project_a,
        alias_for(token, "project"),
    )
    second_user = scoped_integrations.create(
        utils, IntegrationType.USER, own_project, alias_for(token, "user-2")
    )
    newest_first = [second_user.id, project_row.id, first_user.id]
    filters = {"search": token}

    explicit = utils.list_combined(scope=SCOPE_ALL, filters=filters)
    implicit = utils.list_combined(scope=None, filters=filters)

    assert_that(
        _ids(explicit.data), equal_to(newest_first), "scope=all is not newest first"
    )
    assert_that(
        _ids(implicit.data),
        equal_to(newest_first),
        "A request without scope does not match scope=all",
    )
    assert_that(
        [row.setting_type for row in explicit.data],
        equal_to([IntegrationType.USER, IntegrationType.PROJECT, IntegrationType.USER]),
        "Rows do not carry their scope as setting_type",
    )
    assert_that(
        [row.is_global for row in explicit.data],
        equal_to([False, False, False]),
        "Rows do not carry is_global",
    )
    assert_that(
        explicit.pagination.total,
        equal_to(3),
        "The total does not cover both scopes",
    )

    first_page = utils.list_combined(
        scope=SCOPE_ALL, page=0, per_page=1, filters=filters
    )
    second_page = utils.list_combined(
        scope=SCOPE_ALL, page=1, per_page=1, filters=filters
    )

    assert_that(_ids(first_page.data), equal_to([second_user.id]))
    assert_that(_ids(second_page.data), equal_to([project_row.id]))
    assert_that(
        [first_page.pagination.total, second_page.pagination.total],
        equal_to([3, 3]),
        "The total changed by page",
    )
    assert_that(
        [first_page.pagination.pages, second_page.pagination.pages],
        equal_to([3, 3]),
        "The page count changed by page",
    )


# @case unified-integrations-list_TC_002
@pytest.mark.integration
@pytest.mark.api
@pytest.mark.oss_standalone
def test_scope_user_and_project_match_the_per_scope_lists(
    project_admin_user,
    default_project_member,
    project_admin_integrations,
    scoped_integrations,
    token,
):
    utils = project_admin_integrations
    scoped_integrations.create(
        utils, IntegrationType.USER, project_admin_user.email, alias_for(token, "user")
    )
    scoped_integrations.create(
        utils,
        IntegrationType.PROJECT,
        default_project_member.project_a,
        alias_for(token, "project"),
    )

    per_scope_user = utils.list_integrations(IntegrationType.USER, per_page=100)
    per_scope_project = utils.list_integrations(IntegrationType.PROJECT, per_page=100)
    combined_user = utils.list_combined(scope=SCOPE_USER, per_page=100)
    combined_project = utils.list_combined(scope=SCOPE_PROJECT, per_page=100)
    combined_all = utils.list_combined(scope=SCOPE_ALL, per_page=100)

    assert_that(
        _ids(combined_user.data),
        equal_to(_ids(per_scope_user)),
        "scope=user differs from the per-scope user list",
    )
    assert_that(combined_user.pagination.total, equal_to(len(per_scope_user)))
    assert_that(
        _ids(combined_project.data),
        equal_to(_ids(per_scope_project)),
        "scope=project differs from the per-scope project list",
    )
    assert_that(combined_project.pagination.total, equal_to(len(per_scope_project)))
    assert_that(
        _ids(
            row for row in combined_all.data if row.setting_type == IntegrationType.USER
        ),
        equal_to(_ids(per_scope_user)),
        "The user rows of scope=all differ from the per-scope user list",
    )
    assert_that(
        _ids(
            row
            for row in combined_all.data
            if row.setting_type == IntegrationType.PROJECT
        ),
        equal_to(_ids(per_scope_project)),
        "The project rows of scope=all differ from the per-scope project list",
    )
    assert_that(
        combined_all.pagination.total,
        equal_to(len(per_scope_user) + len(per_scope_project)),
    )


# @case unified-integrations-list_TC_003
@pytest.mark.integration
@pytest.mark.api
@pytest.mark.oss_standalone
def test_scope_project_is_limited_by_role(
    admin_client,
    default_project_member,
    project_admin_integrations,
    scoped_integrations,
    token,
):
    admin_utils = IntegrationUtils(admin_client)
    administered = scoped_integrations.create(
        admin_utils,
        IntegrationType.PROJECT,
        default_project_member.project_a,
        alias_for(token, "administered"),
    )
    other = scoped_integrations.create(
        admin_utils,
        IntegrationType.PROJECT,
        default_project_member.project_b,
        alias_for(token, "other"),
    )

    as_admin = admin_utils.list_combined(
        scope=SCOPE_PROJECT, per_page=100, filters={"search": token}
    )
    as_project_admin = poll_until(
        lambda: project_admin_integrations.list_combined(
            scope=SCOPE_PROJECT, per_page=100
        ),
        lambda result: administered.id in _ids(result.data),
        timeout=60,
    )
    as_member = IntegrationUtils(default_project_member.client).list_combined(
        scope=SCOPE_PROJECT, per_page=100
    )

    assert_that(
        sorted(_ids(as_admin.data)),
        equal_to(sorted([administered.id, other.id])),
        "A platform admin does not see the project integrations of every project",
    )
    assert_that(
        _ids(as_project_admin.data),
        equal_to([administered.id]),
        "A project admin sees more than the project they administer",
    )
    assert_that(
        as_member.data, is_(empty()), "A plain member sees project integrations"
    )
    assert_that(
        as_member.pagination.total, equal_to(0), "A plain member's total is not 0"
    )


# @case unified-integrations-list_TC_004
@pytest.mark.parametrize(
    "scenario", list(FILTER_SCENARIOS.values()), ids=list(FILTER_SCENARIOS)
)
@pytest.mark.integration
@pytest.mark.api
@pytest.mark.oss_standalone
def test_filters_narrow_a_scoped_result(
    scenario, filter_rows, project_admin_integrations
):
    filters = resolve_filters(
        scenario.filters,
        token=filter_rows.token,
        project=filter_rows.project,
        creator=filter_rows.creator,
    )
    expected_ids = {filter_rows.rows[label].id for label in scenario.expected}

    result = project_admin_integrations.list_combined(
        scope=scenario.scope, per_page=100, filters=filters
    )

    assert_that(
        set(_ids(result.data)),
        equal_to(expected_ids),
        f"Filters {filters} at scope {scenario.scope} returned other rows",
    )
    assert_that(result.pagination.total, equal_to(len(expected_ids)))


# @case unified-integrations-list_TC_005
@pytest.mark.integration
@pytest.mark.api
@pytest.mark.oss_standalone
def test_project_admin_scope_all_omits_project_budget_litellm_integrations(
    admin_client,
    default_project_member,
    project_admin_integrations,
    scoped_integrations,
    token,
):
    admin_utils = IntegrationUtils(admin_client)
    project = default_project_member.project_a
    budget = scoped_integrations.create(
        admin_utils,
        IntegrationType.PROJECT,
        project,
        f"{BUDGET_ALIAS_PREFIX}{token}",
        credential_type=CredentialTypes.LITE_LLM,
        credential_values=CredentialsManager.lite_llm_credentials(),
    )
    control = scoped_integrations.create(
        admin_utils, IntegrationType.PROJECT, project, alias_for(token, "control")
    )
    filters = {"search": token}

    as_project_admin = poll_until(
        lambda: project_admin_integrations.list_combined(
            scope=SCOPE_ALL, filters=filters
        ),
        lambda result: control.id in _ids(result.data),
        timeout=60,
    )
    as_admin = admin_utils.list_combined(scope=SCOPE_ALL, filters=filters)

    assert_that(
        _ids(as_project_admin.data),
        equal_to([control.id]),
        "A project admin sees the project-budget LiteLLM integration",
    )
    assert_that(
        as_project_admin.pagination.total,
        equal_to(1),
        "The total counts the hidden project-budget integration",
    )
    assert_that(
        set(_ids(as_admin.data)),
        equal_to({budget.id, control.id}),
        "A platform admin does not see the project-budget integration",
    )


# @case unified-integrations-list_TC_006
@pytest.mark.integration
@pytest.mark.api
@pytest.mark.oss_standalone
def test_unknown_scope_is_rejected_with_the_allowed_values(integration_utils):
    with expected_http_errors(), pytest.raises(HTTPError) as error:
        integration_utils.list_combined(scope=UNKNOWN_SCOPE)

    response = error.value.response
    assert_that(response.status_code, equal_to(UNPROCESSABLE))
    assert_that(
        response.text,
        all_of(
            *[
                matches_regexp(rf"\b{value}\b")
                for value in (SCOPE_ALL, SCOPE_USER, SCOPE_PROJECT)
            ]
        ),
        "The error does not name the allowed scopes",
    )


# @case unified-integrations-list_TC_007
@pytest.mark.parametrize(
    "per_page", list(OUT_OF_RANGE_PER_PAGE.values()), ids=list(OUT_OF_RANGE_PER_PAGE)
)
@pytest.mark.integration
@pytest.mark.api
@pytest.mark.oss_standalone
def test_out_of_range_per_page_is_rejected(per_page, integration_utils):
    with expected_http_errors(), pytest.raises(HTTPError) as error:
        integration_utils.list_combined(per_page=per_page)

    assert_that(error.value.response.status_code, equal_to(UNPROCESSABLE))


# @case unified-integrations-list_TC_007
@pytest.mark.parametrize(
    "filters", list(MALFORMED_FILTERS.values()), ids=list(MALFORMED_FILTERS)
)
@pytest.mark.integration
@pytest.mark.api
@pytest.mark.oss_standalone
def test_malformed_filters_are_rejected_with_a_help_message(filters, integration_utils):
    with expected_http_errors(), pytest.raises(HTTPError) as error:
        integration_utils.list_combined(filters=filters)

    response = error.value.response
    assert_that(response.status_code, equal_to(UNPROCESSABLE))
    assert_that(response.json()["error"]["message"], equal_to(INVALID_FILTERS_MESSAGE))
    assert_that(response.text, contains_string(INVALID_FILTERS_HELP))
