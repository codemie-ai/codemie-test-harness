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


"""The currency text the Personal settings checks expect, against the panel's own rounding.

The panel formats with ``toLocaleString('en-US', {minimumFractionDigits: 2,
maximumFractionDigits: 2})``. The expected values below are that call's output in Node; they
differ from ``toFixed(2)`` where the binary value sits just below a tie (1.005 is stored as
1.00499...). No call to the stand is made.
"""

import pytest
from hamcrest import assert_that, equal_to

from codemie_test_harness.tests.ui.pageobject.budgets.personal_spending_page import (
    PersonalSpendingPage,
)


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.parametrize(
    "value, expected",
    [
        (1.005, "$1.01"),
        (0.015, "$0.02"),
        (0.285, "$0.29"),
        (2.675, "$2.68"),
        (1.255, "$1.26"),
        (0.125, "$0.13"),
        (0.0067, "$0.01"),
        (0.0017, "$0.00"),
        (0, "$0.00"),
        (1234.5, "$1,234.50"),
    ],
)
def test_format_currency_rounds_like_the_panel(value, expected):
    assert_that(PersonalSpendingPage.format_currency(value), equal_to(expected))


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.parametrize(
    "spent, limit, expected",
    [
        (8.995, 10, "$1.01"),  # 10 - 8.995 is 1.0050000000000008 in both languages
        (0.715, 1, "$0.29"),
        (12, 10, "$0.00"),
    ],
)
def test_format_available_rounds_like_the_panel(spent, limit, expected):
    assert_that(PersonalSpendingPage.format_available(spent, limit), equal_to(expected))
