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

"""Arithmetic invariants between the Usage Attribution tiles, categories and Who Pays splits.

The invariants hold on any data, so the tests compare amounts with each other, never with fixed money.
"""

import pytest
from hamcrest import (
    assert_that,
    close_to,
    contains_exactly,
    equal_to,
    less_than_or_equal_to,
)

from codemie_test_harness.tests.test_data.usage_attribution_test_data import (
    CATEGORIES,
    MONEY_TOLERANCE,
)
from codemie_test_harness.tests.utils.usage_attribution_utils import (
    category_row,
    period_params,
)

CHANNELS = ("web", "cli")


@pytest.fixture(scope="module")
def cli_summary(usage_attribution_utils):
    """The CLI summary of the last 30 days: tiles, Who Pays and categories."""
    return usage_attribution_utils.get_cli_summary(period_params())


@pytest.fixture(scope="module")
def totals(usage_attribution_utils):
    """The fast totals of the last 30 days."""
    return usage_attribution_utils.get_totals(period_params()).data


@pytest.mark.analytics
@pytest.mark.api
def test_total_spend_is_web_platform_plus_cli(cli_summary):
    # @case usage-attribution-analytics-who-pays_TC_008
    tiles = cli_summary.data["tiles"]

    assert_that(
        tiles["total"],
        close_to(tiles["web"] + tiles["cli"], MONEY_TOLERANCE),
        "Total Spend = Web Platform + CLI",
    )


@pytest.mark.analytics
@pytest.mark.api
def test_categories_sum_to_cli_spend(cli_summary):
    # @case usage-attribution-analytics-who-pays_TC_008
    categories = cli_summary.data["categories"]

    assert_that(
        [row["category"] for row in categories],
        contains_exactly(*CATEGORIES),
        "the six categories, in order",
    )
    assert_that(
        sum(row["spend"] for row in categories),
        close_to(cli_summary.data["tiles"]["cli"], MONEY_TOLERANCE),
        "the six categories add up to CLI spend, which is the total row",
    )


@pytest.mark.analytics
@pytest.mark.api
def test_production_experiments_and_unclassified_sum_to_cli_spend(cli_summary):
    # @case usage-attribution-analytics-who-pays_TC_008
    tiles = cli_summary.data["tiles"]

    assert_that(
        tiles["prod"] + tiles["exp"] + tiles["uncl"],
        close_to(tiles["cli"], MONEY_TOLERANCE),
        "CLI Production + CLI Experiments + CLI Unclassified = CLI",
    )


@pytest.mark.parametrize("channel", CHANNELS)
@pytest.mark.analytics
@pytest.mark.api
def test_who_pays_split_sums_to_its_amount(cli_summary, channel):
    # @case usage-attribution-analytics-who-pays_TC_008
    split = cli_summary.data["who_pays"][channel]

    assert_that(
        sum(split.values()),
        close_to(cli_summary.data["tiles"][channel], MONEY_TOLERANCE),
        f"charged back + shared + personal = {channel} spend",
    )


@pytest.mark.parametrize("category", CATEGORIES)
@pytest.mark.analytics
@pytest.mark.api
def test_category_who_pays_split_sums_to_category_spend(cli_summary, category):
    # @case usage-attribution-analytics-who-pays_TC_008
    row = category_row(cli_summary, category)

    assert_that(row["category"], equal_to(category), "row of the category")
    assert_that(
        row["cb"] + row["sh"] + row["pe"],
        close_to(row["spend"], MONEY_TOLERANCE),
        f"{category}: who pays adds up to the category spend",
    )


@pytest.mark.analytics
@pytest.mark.api
def test_chargeback_potential_is_the_sum_of_its_parts(cli_summary):
    # @case usage-attribution-analytics-who-pays_TC_008
    tiles = cli_summary.data["tiles"]

    assert_that(
        tiles["ncb"],
        close_to(
            tiles["ncb_web"] + tiles["ncb_cli_shared"] + tiles["ncb_cli_personal"],
            MONEY_TOLERANCE,
        ),
        "Chargeback Potential = shared-project Web Platform + shared-project CLI + personal production CLI",
    )


@pytest.mark.analytics
@pytest.mark.api
def test_unclassified_reasons_do_not_exceed_cli_unclassified(cli_summary):
    # @case usage-attribution-analytics-who-pays_TC_008
    tiles = cli_summary.data["tiles"]

    assert_that(
        sum(tiles["uncl_parts"].values()),
        less_than_or_equal_to(tiles["uncl"] + MONEY_TOLERANCE),
        "the reasons shown for CLI Unclassified are a part of it",
    )


@pytest.mark.analytics
@pytest.mark.api
def test_totals_split_into_web_platform_and_cli(totals):
    # @case usage-attribution-analytics-who-pays_TC_008
    assert_that(
        totals["total"],
        close_to(totals["web"]["total"] + totals["cli"]["total"], MONEY_TOLERANCE),
        "total = Web Platform + CLI",
    )


@pytest.mark.parametrize("channel", CHANNELS)
@pytest.mark.analytics
@pytest.mark.api
def test_totals_who_pays_split_sums_to_its_amount(totals, channel):
    # @case usage-attribution-analytics-who-pays_TC_008
    assert_that(
        sum(totals["who_pays"][channel].values()),
        close_to(totals[channel]["total"], MONEY_TOLERANCE),
        f"charged back + shared + personal = {channel} total",
    )


@pytest.mark.analytics
@pytest.mark.api
def test_totals_charged_back_is_what_both_channels_charged(totals):
    # @case usage-attribution-analytics-who-pays_TC_008
    who_pays = totals["who_pays"]

    assert_that(
        totals["charged_back"],
        close_to(
            who_pays["web"]["charged"] + who_pays["cli"]["charged"], MONEY_TOLERANCE
        ),
        "Charged Back = Web Platform charged + CLI charged",
    )
