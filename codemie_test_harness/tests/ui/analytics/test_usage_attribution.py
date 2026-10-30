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

"""UI coverage for the Analytics > Usage Attribution tab.

The tab needs features:usageAttribution on and an admin, maintainer or auditor login; the tests fail where it is not offered.
"""

import pytest

from codemie_test_harness.tests.ui.test_data.usage_attribution_test_data import (
    POPUPS,
    TABLES,
)


@pytest.mark.analytics
@pytest.mark.ui
def test_usage_attribution_tab_has_sub_tabs_and_period_only_filters(
    analytics_page, usage_attribution
):
    # @case usage-attribution-analytics-who-pays_TC_001
    analytics_page.should_list_usage_attribution_tab_after_existing_tabs()
    usage_attribution.should_have_sub_tabs()
    analytics_page.should_show_only_period_filters_with_note()


@pytest.mark.analytics
@pytest.mark.ui
def test_overview_shows_summary_tiles_and_money_widgets(usage_attribution):
    # @case usage-attribution-analytics-who-pays_TC_009
    usage_attribution.should_show_summary_tiles()
    usage_attribution.should_show_summary_amounts()
    usage_attribution.should_show_money_widgets()


@pytest.mark.analytics
@pytest.mark.ui
def test_overview_shows_country_and_job_title_breakdown_widgets(
    usage_attribution, user_enrichment_enabled
):
    # @case usage-attribution-analytics-who-pays_TC_009
    usage_attribution.should_show_breakdown_widgets()


@pytest.mark.parametrize("table_spec", TABLES)
@pytest.mark.analytics
@pytest.mark.ui
def test_table_shows_shipped_columns_and_controls(usage_attribution, table_spec):
    # @case usage-attribution-analytics-who-pays_TC_010
    table = usage_attribution.open_table(table_spec)

    table.should_have_columns()
    table.should_have_search_box()
    table.should_offer_options()


@pytest.mark.parametrize("popup", POPUPS)
@pytest.mark.analytics
@pytest.mark.ui
def test_first_row_popup_opens_with_its_tiles_and_sections(table_with_rows, popup):
    # @case usage-attribution-analytics-who-pays_TC_013
    row_popup = table_with_rows.open_first_row(popup.header_prefix)

    row_popup.should_be_visible()
    row_popup.should_have_tiles(popup.tiles)
    row_popup.should_have_sections(popup.sections)

    row_popup.close()
    row_popup.should_be_closed()


@pytest.mark.analytics
@pytest.mark.ui
def test_how_it_works_shows_analysis_tiles_sections_and_computed_time(
    usage_attribution,
):
    # @case usage-attribution-analytics-who-pays_TC_018
    usage_attribution.should_show_how_it_works()
