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

from dataclasses import dataclass
from datetime import timedelta

import pytest
from hamcrest import assert_that, is_

# The CLI Analytics fixtures of the API suite: the UI tests seed the same sessions through them.
from codemie_test_harness.tests.analytics.conftest import (  # noqa: F401
    cli_analytics_enabled,
    cli_analytics_project,
    cli_analytics_users,
    create_cli_analytics_project,
    ingest_cli_sessions,
    seed_cli_sessions,
)
from codemie_test_harness.tests.test_data.cli_analytics_test_data import (
    OWNER,
    CliSessionSeed,
    catalog_cost,
    priced_model,
    seed_day_start,
)
from codemie_test_harness.tests.test_data.projects_test_data import (
    get_project_create_data,
)
from codemie_test_harness.tests.test_data.run_attributes_test_data import (
    WORKFLOW_TASK,
)
from codemie_test_harness.tests.ui.pageobject.analytics.analytics_page import (
    AnalyticsPage,
)
from codemie_test_harness.tests.ui.pageobject.analytics.usage_attribution_page import (
    UsageAttributionPage,
)
from codemie_test_harness.tests.ui.pageobject.analytics.usage_attribution_table import (
    UsageAttributionTable,
)
from codemie_test_harness.tests.ui.test_data.analytics_test_data import (
    INSIGHTS_SEEDED_RUN_COUNTS,
    INSIGHTS_TIME_PERIOD,
)
from codemie_test_harness.tests.ui.test_data.cli_analytics_tool_success_test_data import (
    TOOL_SUCCESS_CASES,
    ToolSuccessCase,
)
from codemie_test_harness.tests.ui.test_data.cli_analytics_pricing_test_data import (
    PricingSession,
    get_pricing_session_seeds,
    unpriced_model_name,
)
from codemie_test_harness.tests.ui.utils.money import format_money
from codemie_test_harness.tests.utils.analytics_utils import CLIAnalyticsTestSession
from codemie_test_harness.tests.utils.base_utils import poll_until
from codemie_test_harness.tests.utils.cli_analytics_api_utils import (
    delete_projects_strict,
)
from codemie_test_harness.tests.utils.run_attributes_utils import (
    ChatRunSurface,
    WorkflowRunSurface,
)


@pytest.fixture(scope="session")
def cli_analytics_session(
    analytics_utils, admin_utils, project_utils
) -> CLIAnalyticsTestSession:
    """A CLI Analytics session of the test user, seeded through the ingest API.

    The ingest API discards data of projects with CLI analytics disabled, so the session is
    sent to an isolated project that is enabled explicitly. The sending user is the harness
    admin, which the BE accepts into an enabled project without membership (gate case TC-005),
    so it is not assigned to the project. A new session is created once per pytest session
    (per xdist worker). The ingested data cannot be deleted (see
    AnalyticsUtils.create_cli_session); the project itself is removed at the end, a failure
    is an error of the run.
    """
    project = get_project_create_data()["name"]
    try:
        admin_utils.create_project(project)
        project_utils.update_project(project, cli_analytics_enabled=True)
        yield analytics_utils.create_cli_session(project=project)
    finally:
        delete_projects_strict(project_utils, [project])


@dataclass(frozen=True)
class ToolSuccessScenario:
    """A user whose one CLI session made the case's tool calls, in a project of its own."""

    case: ToolSuccessCase
    project: str
    user_email: str


@pytest.fixture(scope="module", params=TOOL_SUCCESS_CASES, ids=lambda case: case.id)
def tool_success_scenario(
    request,
    create_cli_analytics_project,  # noqa: F811
    seed_cli_sessions,  # noqa: F811
    cli_analytics_users,  # noqa: F811
) -> ToolSuccessScenario:
    """One session of a fresh CLI Analytics user, seeded through the ingest API.

    The project holds only this session, so filtering the dashboard by it shows this user's
    tool calls alone. The ingested data cannot be deleted; the project, the user and its
    membership go at the end of the module.
    """
    case = request.param
    project = create_cli_analytics_project()
    seed_cli_sessions(
        [
            CliSessionSeed(
                key=case.id,
                started_at=seed_day_start() + timedelta(hours=10),
                input_tokens=1000,
                output_tokens=10,
                user=OWNER,
                tool_calls_succeeded=case.tool_calls_succeeded,
                tool_calls_failed=case.tool_calls_failed,
            )
        ],
        project,
    )
    return ToolSuccessScenario(case, project, cli_analytics_users[OWNER].email)


@pytest.fixture(scope="session")
def catalog_priced_model(client):
    """A model the stand's catalog prices: CLI Analytics money is tokens x its price."""
    model = priced_model(client.llms.list())
    if model is None:
        pytest.skip("no LLM with an input and output price in the catalog")
    return model


def _lists_models(row, models: list[str]) -> bool:
    """Whether the session row names every model; it joins their names with ", "."""
    return row is not None and set(models) <= {
        name.strip() for name in row.model_name.split(",")
    }


@pytest.fixture
def seed_pricing_session(
    analytics_utils, admin_utils, project_utils, catalog_priced_model
):
    """Factory of CLI sessions in a project of their own, one request per named model.

    A name from ``catalog_priced_model`` is a priced model, any other name is unpriced. The
    project is enabled for CLI analytics, the sender is the harness admin (see
    ``cli_analytics_session``), and the factory returns once the session is rolled up with all
    its models. The ingested data cannot be deleted; the projects are removed after the test,
    a failure is an error of the run.
    """
    projects = []

    def _seed(models: list[str]) -> PricingSession:
        project = get_project_create_data()["name"]
        admin_utils.create_project(project)
        projects.append(project)
        project_utils.update_project(project, cli_analytics_enabled=True)
        seeds = get_pricing_session_seeds(models)
        for seed in seeds:
            analytics_utils.ingest_cli_event_hooks(
                seed.events(project), project=project
            )
        session_id = seeds[0].session_id
        analytics_utils.wait_for_cli_session(session_id)
        row = poll_until(
            lambda: analytics_utils.find_cli_analytics_session(session_id),
            lambda row: _lists_models(row, models),
            timeout=120,
            interval=5,
        )
        assert_that(
            _lists_models(row, models),
            is_(True),
            f"session {session_id} not rolled up with models {models}; last row: {row}",
        )
        priced = [s for s in seeds if s.model == catalog_priced_model.base_name]
        unpriced = [s for s in seeds if s.model != catalog_priced_model.base_name]
        return PricingSession(
            project=project,
            session_id=session_id,
            started_at=seeds[0].started_at,
            priced_model=priced[0].model if priced else None,
            priced_cost=(
                format_money(catalog_cost(priced, catalog_priced_model.cost))
                if priced
                else None
            ),
            unpriced_model=unpriced[0].model if unpriced else None,
        )

    yield _seed
    delete_projects_strict(project_utils, projects)


@pytest.fixture
def mixed_pricing_session(seed_pricing_session, catalog_priced_model):
    """One session that used a priced model and a model without a catalog price."""
    return seed_pricing_session([catalog_priced_model.base_name, unpriced_model_name()])


@pytest.fixture
def fully_priced_session(seed_pricing_session, catalog_priced_model):
    """One session that used a priced model only."""
    return seed_pricing_session([catalog_priced_model.base_name])


@pytest.fixture
def unpriced_only_session(seed_pricing_session):
    """One session that used a model without a catalog price only."""
    return seed_pricing_session([unpriced_model_name()])


@pytest.fixture
def insights_activity(
    assistant_factory,
    workflow_with_assistant,
    analytics_utils,
    assistant_utils,
    conversation_utils,
    workflow_utils,
):
    """Assistant chats and workflow runs whose counts and costs differ, listed by the analytics.

    One assistant is asked once and another twice, one workflow runs once and another twice.
    Every run is waited for in the per-run analytics rows, so a page opened after this fixture
    lists the activity. The assistants and workflows go with the test; the usage records stay,
    like any usage. Request this fixture before ``analytics_page``.
    """
    runs = []
    for count in INSIGHTS_SEEDED_RUN_COUNTS:
        chat = ChatRunSurface(
            analytics_utils,
            assistant_factory.create(),
            assistant_utils,
            conversation_utils,
        )
        workflow = WorkflowRunSurface(
            analytics_utils,
            workflow_with_assistant(assistant_factory.create(), WORKFLOW_TASK),
            workflow_utils,
        )
        for surface in (chat, workflow):
            runs.extend((surface, surface.start()) for _ in range(count))
    for surface, run_id in runs:
        assert surface.wait_for_row(run_id), (
            f"The analytics should list the {type(surface).__name__} run {run_id}"
        )


@pytest.fixture
def analytics_page(page) -> AnalyticsPage:
    """The Analytics page, open on its default tab."""
    return AnalyticsPage(page).navigate_to()


@pytest.fixture
def recent_insights_page(page) -> AnalyticsPage:
    """The Analytics page filtered to the last hour.

    Unfiltered Insights tables aggregate the whole platform's usage and can take minutes
    to load on a busy environment; the last hour still holds the runs ``insights_activity``
    has just made and loads in seconds.
    """
    return AnalyticsPage(page).navigate_to(time_period=INSIGHTS_TIME_PERIOD)


@pytest.fixture
def usage_attribution(analytics_page) -> UsageAttributionPage:
    """The Usage Attribution tab, open.

    The admin must be offered the tab: a missing tab fails the test.
    """
    analytics_page.should_offer_usage_attribution_tab()
    return analytics_page.open_usage_attribution()


@pytest.fixture
def user_enrichment_enabled(client):
    """Require user enrichment: the country and job title breakdown widgets are hidden without it."""
    settings = client.usage_attribution.get_settings().data
    assert "enrichment" in settings, (
        f"The settings payload should report user enrichment, it has {sorted(settings)}"
    )
    assert settings["enrichment"], (
        "User enrichment is off on this environment: "
        "the country and job title breakdown widgets need it"
    )


@pytest.fixture
def table_with_rows(usage_attribution, popup) -> UsageAttributionTable:
    """The table of a popup case with every row listed; fails where it has no rows to open."""
    table = usage_attribution.open_table(popup.table)
    table.show_all_rows()
    table.should_have_rows()
    return table
