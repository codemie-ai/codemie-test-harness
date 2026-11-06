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

"""Provisioning API: adjusting a project budget (PATCH /v1/provisioning/projects/{name}/budget)."""

import pytest
from hamcrest import assert_that, close_to, contains_string, equal_to, has_entries
from requests import HTTPError

from codemie_test_harness.cli.constants import KEY_PROVISIONING_FULL_TOKEN
from codemie_test_harness.tests.test_data.budget_test_data import (
    PLATFORM_BUDGET_CATEGORIES,
)
from codemie_test_harness.tests.test_data.provisioning_test_data import (
    PLATFORM_MUST_BE_POSITIVE,
    TWO_CATEGORIES,
    budget_request,
    change_reference,
)
from codemie_test_harness.tests.utils.user_utils import UserUtils

AMOUNT_TOLERANCE = 0.01


@pytest.mark.budget
@pytest.mark.requires_setting(KEY_PROVISIONING_FULL_TOKEN)
@pytest.mark.api
def test_adjust_budget_changes_only_the_named_category_and_zero_removes_it(
    provisioning_full, provisioning_utils
):
    # @case provisioning-api-for-third-party_TC_003
    project_name = provisioning_utils.create_project(TWO_CATEGORIES)
    platform_before = provisioning_utils.category_budgets(project_name)["platform"]

    changed = provisioning_full.adjust_budget(
        project_name, change_reference(), budget_request({"cli": 80.0})
    )

    assert_that(changed.status_code, equal_to(200), "adjust always answers 200")
    assert_that(
        provisioning_utils.category_budgets(project_name),
        has_entries(
            platform=close_to(platform_before, AMOUNT_TOLERANCE),
            cli=close_to(80.0, AMOUNT_TOLERANCE),
        ),
    )

    removed = provisioning_full.adjust_budget(
        project_name, change_reference(), budget_request({"cli": 0.0})
    )

    assert_that(removed.status_code, equal_to(200))
    categories = provisioning_utils.category_budgets(project_name)
    assert_that(list(categories), equal_to(["platform"]), "zero removes the category")
    assert_that(categories["platform"], close_to(platform_before, AMOUNT_TOLERANCE))


@pytest.mark.budget
@pytest.mark.requires_setting(KEY_PROVISIONING_FULL_TOKEN)
@pytest.mark.api
def test_adjust_budget_rejects_platform_left_at_zero_and_changes_nothing(
    provisioning_full, provisioning_utils
):
    # @case provisioning-api-for-third-party_TC_004
    project_name = provisioning_utils.create_project(PLATFORM_BUDGET_CATEGORIES)
    state_before = provisioning_utils.state(project_name)

    with pytest.raises(HTTPError) as error:
        provisioning_full.adjust_budget(
            project_name, change_reference(), budget_request({"platform": 0.0})
        )

    assert_that(error.value.response.status_code, equal_to(400))
    assert_that(
        UserUtils.error_text(error.value), contains_string(PLATFORM_MUST_BE_POSITIVE)
    )
    assert_that(
        provisioning_utils.state(project_name),
        equal_to(state_before),
        "the rejected call left the budget unchanged",
    )
