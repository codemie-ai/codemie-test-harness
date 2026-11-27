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

"""UI coverage of incomplete pricing in the CLI Analytics cost values: a total that leaves out
a model without a catalog price is marked, a complete one is not."""

import pytest

from codemie_test_harness.tests.ui.pageobject.analytics.cli_analytics_cost_page import (
    CLIAnalyticsCostPage,
)
from codemie_test_harness.tests.ui.test_data.analytics_test_data import (
    CLIAnalyticsSection,
)


@pytest.mark.cli_analytics
@pytest.mark.ui
def test_cli_analytics_cost_totals_marked_partial_when_a_model_has_no_price(
    page, mixed_pricing_session
):
    # @case cli-analytics-cost-pricing-notice_TC_001
    """Overview, Cost, Users and Repositories mark the priced total as a partial estimate and
    name the model without a price; Cost by Model shows that model's cost as unknown."""
    session = mixed_pricing_session
    cli_analytics = CLIAnalyticsCostPage(page).navigate_to()
    cli_analytics.filter_by_window(session.window_start, session.window_end)
    cli_analytics.filter_by_project(session.project)

    cli_analytics.should_show_overview_est_cost(
        session.priced_cost
    )  # repro:precondition
    cli_analytics.should_mark_overview_est_cost_partial(
        session.priced_cost, session.unpriced_model
    )  # repro:symptom

    cli_analytics.open_section(CLIAnalyticsSection.COST)
    cli_analytics.should_mark_cost_est_cost_partial(
        session.priced_cost, session.unpriced_model
    )  # repro:symptom
    cli_analytics.should_mark_cost_by_model_unknown(
        session.unpriced_model
    )  # repro:symptom
    cli_analytics.should_not_mark_cost_by_model(
        session.priced_model, session.priced_cost
    )

    cli_analytics.open_section(CLIAnalyticsSection.USERS)
    cli_analytics.should_mark_user_cost_partial(
        session.priced_cost, session.unpriced_model
    )  # repro:symptom

    cli_analytics.open_section(CLIAnalyticsSection.REPOSITORIES)
    cli_analytics.should_mark_project_cost_partial(
        session.project, session.priced_cost, session.unpriced_model
    )  # repro:symptom


@pytest.mark.cli_analytics
@pytest.mark.ui
def test_cli_analytics_cost_totals_unmarked_when_pricing_is_complete(
    page, fully_priced_session
):
    # @case cli-analytics-cost-pricing-notice_TC_002
    """Overview, Cost, Users and Repositories show the cost of a fully priced selection
    without any incomplete-pricing marker."""
    session = fully_priced_session
    cli_analytics = CLIAnalyticsCostPage(page).navigate_to()
    cli_analytics.filter_by_window(session.window_start, session.window_end)
    cli_analytics.filter_by_project(session.project)

    cli_analytics.should_show_overview_est_cost(
        session.priced_cost
    )  # repro:precondition
    cli_analytics.should_not_mark_overview_est_cost(
        session.priced_cost
    )  # repro:symptom

    cli_analytics.open_section(CLIAnalyticsSection.COST)
    cli_analytics.should_not_mark_cost_est_cost(session.priced_cost)  # repro:symptom
    cli_analytics.should_not_mark_cost_by_model(
        session.priced_model, session.priced_cost
    )

    cli_analytics.open_section(CLIAnalyticsSection.USERS)
    cli_analytics.should_not_mark_user_cost(session.priced_cost)  # repro:symptom

    cli_analytics.open_section(CLIAnalyticsSection.REPOSITORIES)
    cli_analytics.should_not_mark_project_cost(
        session.project, session.priced_cost
    )  # repro:symptom


@pytest.mark.cli_analytics
@pytest.mark.ui
def test_cli_analytics_cost_totals_unknown_when_no_model_has_a_price(
    page, unpriced_only_session
):
    # @case cli-analytics-cost-pricing-notice_TC_003
    """Overview, Cost, Users and Repositories show the cost of a selection that no model prices
    as unknown (a dash with a marker naming the model), not as $0.00."""
    session = unpriced_only_session
    cli_analytics = CLIAnalyticsCostPage(page).navigate_to()
    cli_analytics.filter_by_window(session.window_start, session.window_end)
    cli_analytics.filter_by_project(session.project)

    cli_analytics.should_show_overview_sessions(1)  # repro:precondition
    cli_analytics.should_mark_overview_est_cost_unknown(
        session.unpriced_model
    )  # repro:symptom

    cli_analytics.open_section(CLIAnalyticsSection.COST)
    cli_analytics.should_mark_cost_est_cost_unknown(
        session.unpriced_model
    )  # repro:symptom

    cli_analytics.open_section(CLIAnalyticsSection.USERS)
    cli_analytics.should_mark_user_cost_unknown(session.unpriced_model)  # repro:symptom

    cli_analytics.open_section(CLIAnalyticsSection.REPOSITORIES)
    cli_analytics.should_mark_project_cost_unknown(
        session.project, session.unpriced_model
    )  # repro:symptom
