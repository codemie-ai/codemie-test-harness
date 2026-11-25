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

"""UI coverage for the table widgets of Analytics > Insights: row order and the totals footer."""

import pytest

from codemie_test_harness.tests.ui.pageobject.analytics.insights_table_widget import (
    InsightsTableWidget,
)
from codemie_test_harness.tests.ui.test_data.analytics_test_data import (
    ASSISTANTS_CHATS_TABLE,
    TOP_ASSISTANTS_USAGE_TABLE,
    TOP_WORKFLOW_USAGE_TABLE,
    WORKFLOWS_TABLE,
)


@pytest.mark.analytics
@pytest.mark.ui
@pytest.mark.prod_regression
def test_insights_assistants_chats_rows_ordered_by_total_cost(
    insights_activity, recent_insights_page
):
    """Assistants Chats rows are ordered by Total Cost ($) descending, equal costs in any order."""
    # @case insights-page-fix-sorting-and_TC_001
    widget = InsightsTableWidget(
        recent_insights_page.page, ASSISTANTS_CHATS_TABLE
    ).open()

    widget.should_list_rows_with_different_costs()
    widget.should_order_rows_by_cost_descending()


@pytest.mark.analytics
@pytest.mark.ui
@pytest.mark.prod_regression
def test_insights_workflows_rows_ordered_by_total_cost(
    insights_activity, recent_insights_page
):
    """Workflows rows are ordered by Total Cost ($) descending, rows without a cost left out."""
    # @case insights-page-change-sorting_TC_002
    widget = InsightsTableWidget(recent_insights_page.page, WORKFLOWS_TABLE).open()

    widget.should_list_rows_with_different_costs()
    widget.should_order_rows_by_cost_descending()


@pytest.mark.analytics
@pytest.mark.parametrize(
    "table",
    [TOP_ASSISTANTS_USAGE_TABLE, TOP_WORKFLOW_USAGE_TABLE],
    ids=["top_assistants_usage", "top_workflow_usage"],
)
@pytest.mark.ui
@pytest.mark.prod_regression
def test_insights_top_usage_rows_ordered_by_invocations_then_name(
    insights_activity, recent_insights_page, table
):
    """Top usage rows are ordered by Invocations descending, then by name ascending."""
    # @case insights-page-change-sorting_TC_001
    widget = InsightsTableWidget(recent_insights_page.page, table).open()

    widget.should_list_rows_with_different_counts()
    widget.should_order_rows_by_count_then_name()


@pytest.mark.analytics
@pytest.mark.parametrize(
    "table",
    [ASSISTANTS_CHATS_TABLE, WORKFLOWS_TABLE],
    ids=["assistants_chats", "workflows"],
)
@pytest.mark.ui
@pytest.mark.prod_regression
def test_insights_table_footer_shows_labelled_aligned_totals(
    insights_activity, recent_insights_page, table
):
    """The totals footer reads Total, sits in the table columns and shows its numbers on one line."""
    # @case insights-page-fix-sorting-and_TC_003
    widget = InsightsTableWidget(recent_insights_page.page, table).open()

    widget.should_label_footer_total()
    widget.should_align_footer_with_columns()
    widget.should_show_numeric_totals_on_one_line()
