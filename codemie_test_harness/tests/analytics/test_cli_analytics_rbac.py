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

"""Live AI Attribution role matrix with positive data and privacy controls."""

import pytest
from hamcrest import any_of, assert_that, empty, equal_to, instance_of

from codemie_test_harness.tests.test_data.cli_analytics_rbac_test_data import (
    DETAIL_CASES,
    GLOBAL_READERS,
    ROLES,
    SHARED_CASES,
)
from codemie_test_harness.tests.utils.cli_analytics_api_utils import INGEST_PREFIX
from codemie_test_harness.tests.utils.cli_analytics_rbac_utils import read_data

pytestmark = pytest.mark.xdist_group("cli_analytics_rbac_api")


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.cli_analytics
@pytest.mark.api
def test_every_role_can_read_frameworks(cli_rbac_world, role):
    data = read_data(cli_rbac_world.api(role), "frameworks", **cli_rbac_world.filters)
    assert_that(data, any_of(instance_of(dict), instance_of(list)))


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.cli_analytics
@pytest.mark.api
def test_shared_sessions_follow_the_role_matrix(cli_rbac_world, role):
    rows = cli_rbac_world.rows(role)
    assert_that(
        {r["trace_id"] for r in rows},
        equal_to({s.trace_id for s in cli_rbac_world.shared(role)}),
    )


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("endpoint", ("cost", "overview"))
@pytest.mark.cli_analytics
@pytest.mark.api
def test_dashboard_totals_include_only_authorized_shared_sessions(
    cli_rbac_world, role, endpoint
):
    data = read_data(cli_rbac_world.api(role), endpoint, **cli_rbac_world.filters)
    expected = cli_rbac_world.shared(role)
    assert_that(data["kpis"]["total_sessions"], equal_to(len(expected)))
    assert_that(data["kpis"]["total_tokens"], equal_to(sum(s.tokens for s in expected)))


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("endpoint", ("users", "user-charts"))
@pytest.mark.cli_analytics
@pytest.mark.api
def test_user_breakdown_contains_only_authorized_owners(cli_rbac_world, role, endpoint):
    data = read_data(cli_rbac_world.api(role), endpoint, **cli_rbac_world.filters)
    expected = {
        cli_rbac_world.users[s.owner].email.lower() for s in cli_rbac_world.shared(role)
    }
    assert_that(len(data["rows"]), equal_to(len(expected)))
    assert_that(
        {r["developer_name"] for r in data["rows"]},
        equal_to(expected),
    )


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.cli_analytics
@pytest.mark.api
def test_foreign_project_and_user_filters_do_not_expand_access(cli_rbac_world, role):
    owner = cli_rbac_world.users["owner"]
    rows = cli_rbac_world.rows(
        role, projects=cli_rbac_world.projects[1], users=owner.email
    )
    expected = (
        {cli_rbac_world.sessions["owner_b"].trace_id}
        if role in GLOBAL_READERS
        else set()
    )
    assert_that({r["trace_id"] for r in rows}, equal_to(expected))
    data = read_data(
        cli_rbac_world.api(role),
        "cost",
        projects=cli_rbac_world.projects[1],
        users=owner.email,
    )
    assert_that(data["kpis"]["total_sessions"], equal_to(len(expected)))


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize(
    "foreign_user_filter", (False, True), ids=("unfiltered", "foreign-user-filter")
)
@pytest.mark.cli_analytics
@pytest.mark.api
def test_personal_only_lists_exactly_the_permitted_private_sessions(
    cli_rbac_world, role, foreign_user_filter
):
    rows = cli_rbac_world.private_rows(role, foreign_user_filter)
    assert_that(len(rows), equal_to(len(cli_rbac_world.private(role))))
    assert_that(
        {r["trace_id"] for r in rows},
        equal_to({s.trace_id for s in cli_rbac_world.private(role)}),
    )


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("case", DETAIL_CASES)
@pytest.mark.cli_analytics
@pytest.mark.api
def test_session_detail_and_prompt_visibility_follow_the_role(
    cli_rbac_world, role, case
):
    seed = cli_rbac_world.detail_case(role, case)
    expected = 200 if cli_rbac_world.may_read(role, seed) else 404
    r = cli_rbac_world.api(role).request(
        "GET", f"{INGEST_PREFIX}/sessions/{seed.trace_id}"
    )
    assert_that(r.status_code, equal_to(expected), f"{role}/{case}: {r.text[:300]}")
    assert_that(
        seed.prompt in r.text, equal_to(expected == 200), "Prompt body visibility"
    )


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.cli_analytics
@pytest.mark.api
def test_missing_session_is_a_404_without_seeded_prompts(cli_rbac_world, role):
    r = cli_rbac_world.api(role).request(
        "GET", f"{INGEST_PREFIX}/sessions/missing-{cli_rbac_world.prefix}"
    )
    assert_that(r.status_code, equal_to(404))
    assert_that(
        [s.prompt for s in cli_rbac_world.sessions.values() if s.prompt in r.text],
        empty(),
    )


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.cli_analytics
@pytest.mark.api
def test_repositories_contain_only_authorized_sessions(cli_rbac_world, role):
    rows = read_data(
        cli_rbac_world.api(role), "repositories", per_page=100, **cli_rbac_world.filters
    )["rows"]
    expected = {cli_rbac_world.repository(s): 1 for s in cli_rbac_world.shared(role)}
    assert_that(len(rows), equal_to(len(expected)))
    assert_that({r["repository"]: r["session_count"] for r in rows}, equal_to(expected))


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.cli_analytics
@pytest.mark.api
def test_projects_contain_only_authorized_repositories(cli_rbac_world, role):
    rows = read_data(
        cli_rbac_world.api(role), "projects", per_page=100, **cli_rbac_world.filters
    )["rows"]
    expected = cli_rbac_world.project_counts(role)
    assert_that(len(rows), equal_to(len(expected)))
    assert_that(
        {r["project_name"]: r["session_count"] for r in rows}, equal_to(expected)
    )
    assert_that(
        {repo["repository"] for row in rows for repo in row["repositories"]},
        equal_to({cli_rbac_world.repository(s) for s in cli_rbac_world.shared(role)}),
    )


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("case", SHARED_CASES)
@pytest.mark.cli_analytics
@pytest.mark.api
def test_branches_follow_repository_access(cli_rbac_world, role, case):
    seed = cli_rbac_world.detail_case(role, case)
    rows = read_data(
        cli_rbac_world.api(role),
        "branches",
        repository=cli_rbac_world.repository(seed),
        **cli_rbac_world.filters,
    )["rows"]
    assert_that(
        {r["branch"]: r["session_count"] for r in rows},
        equal_to({"autotest": 1} if cli_rbac_world.may_read(role, seed) else {}),
    )


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.cli_analytics
@pytest.mark.api
def test_activity_counts_only_authorized_sessions(cli_rbac_world, role):
    data = read_data(cli_rbac_world.api(role), "activity", **cli_rbac_world.filters)
    expected = len(cli_rbac_world.shared(role))
    assert_that(sum(data["by_hour"]), equal_to(expected))
    assert_that(sum(data["by_weekday"]), equal_to(expected))


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.cli_analytics
@pytest.mark.api
def test_model_tokens_include_only_authorized_sessions(cli_rbac_world, role):
    data = read_data(cli_rbac_world.api(role), "tools", **cli_rbac_world.filters)
    assert_that(
        sum(row["total_tokens"] for row in data["tokens_by_model"]),
        equal_to(sum(s.tokens for s in cli_rbac_world.shared(role))),
    )


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.cli_analytics
@pytest.mark.api
def test_session_depth_counts_only_authorized_sessions(cli_rbac_world, role):
    data = read_data(cli_rbac_world.api(role), "efficiency", **cli_rbac_world.filters)
    assert_that(
        sum(row["count"] for row in data["session_depth"]),
        equal_to(len(cli_rbac_world.shared(role))),
    )
