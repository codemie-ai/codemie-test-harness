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

import pytest

from codemie_test_harness.tests.test_data.projects_test_data import (
    get_project_create_data,
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
from codemie_test_harness.tests.utils.analytics_utils import CLIAnalyticsTestSession
from codemie_test_harness.tests.utils.cli_analytics_api_utils import (
    delete_projects_strict,
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


@pytest.fixture
def analytics_page(page) -> AnalyticsPage:
    """The Analytics page, open on its default tab."""
    return AnalyticsPage(page).navigate_to()


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
