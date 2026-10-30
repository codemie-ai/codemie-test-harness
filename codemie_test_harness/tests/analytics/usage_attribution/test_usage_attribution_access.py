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

"""Who may read the Usage Attribution data routes and its analysis settings."""

import pytest
from hamcrest import (
    assert_that,
    equal_to,
    greater_than_or_equal_to,
    has_entries,
    instance_of,
    is_,
    is_not,
    none,
    only_contains,
)
from requests import HTTPError

from codemie_sdk.models.usage_attribution import UsageAttributionResponse

from codemie_test_harness.tests.test_data.usage_attribution_test_data import (
    FORBIDDEN,
    PUBLIC_COMPONENT_FIELDS,
    ROLES_WITH_ACCESS,
    ROLES_WITHOUT_ACCESS,
    SETTINGS_BY_ROLE,
    SHIPPED_FIXED_SETTINGS,
    SHIPPED_SETTING_DEFAULTS,
    SHIPPED_TUNING,
    USAGE_ATTRIBUTION_FEATURE_ID,
)


@pytest.mark.parametrize("role_client", ROLES_WITH_ACCESS)
@pytest.mark.analytics
@pytest.mark.api
def test_totals_are_readable_by_privileged_roles(request, role_client):
    # @case usage-attribution-analytics-who-pays_TC_002
    response = request.getfixturevalue(role_client).usage_attribution.get_totals()

    assert_that(response, instance_of(UsageAttributionResponse))
    assert_that(
        response.data["total"],
        greater_than_or_equal_to(0),
        "the totals carry the total spend",
    )
    assert_that(response.range.clamped, is_(False), "the default range is not clamped")


@pytest.mark.parametrize("role_client", ROLES_WITHOUT_ACCESS)
@pytest.mark.analytics
@pytest.mark.api
def test_totals_are_forbidden_without_a_privileged_role(request, role_client):
    # @case usage-attribution-analytics-who-pays_TC_002
    denied_client = request.getfixturevalue(role_client)

    with pytest.raises(HTTPError) as error:
        denied_client.usage_attribution.get_totals()

    assert_that(error.value.response.status_code, equal_to(FORBIDDEN))


@pytest.mark.analytics
@pytest.mark.api
def test_settings_defaults_match_shipped_values(usage_attribution_utils):
    # @case usage-attribution-analytics-who-pays_TC_019
    data = usage_attribution_utils.get_settings().data

    defaults = {setting["key"]: setting["default"] for setting in data["settings"]}
    assert_that(defaults, has_entries(SHIPPED_SETTING_DEFAULTS))
    assert_that(data["fixed"], has_entries(SHIPPED_FIXED_SETTINGS))
    assert_that(data["tuning"], has_entries(SHIPPED_TUNING))


@pytest.mark.parametrize("role_client, can_tune, can_refresh", SETTINGS_BY_ROLE)
@pytest.mark.analytics
@pytest.mark.api
def test_settings_tuning_rights_follow_the_role(
    request, role_client, can_tune, can_refresh
):
    # @case usage-attribution-analytics-who-pays_TC_019
    data = request.getfixturevalue(role_client).usage_attribution.get_settings().data

    assert_that(data["can_tune"], equal_to(can_tune), "may the caller tune")
    assert_that(data["can_refresh"], equal_to(can_refresh), "may the caller refresh")


@pytest.mark.analytics
@pytest.mark.api
def test_auditor_reads_the_same_defaults_as_admin(
    usage_attribution_utils, auditor_client
):
    # @case usage-attribution-analytics-who-pays_TC_019
    admin_data = usage_attribution_utils.get_settings().data
    auditor_data = auditor_client.usage_attribution.get_settings().data

    assert_that(
        {s["key"]: s["default"] for s in auditor_data["settings"]},
        equal_to({s["key"]: s["default"] for s in admin_data["settings"]}),
        "the auditor sees the same defaults, read-only",
    )
    assert_that(auditor_data["fixed"], equal_to(admin_data["fixed"]))


@pytest.mark.analytics
@pytest.mark.api
def test_public_config_hides_usage_attribution_settings(usage_attribution_utils):
    # @case usage-attribution-analytics-who-pays_TC_019
    component = usage_attribution_utils.get_public_component()

    assert_that(
        component,
        is_not(none()),
        f"{USAGE_ATTRIBUTION_FEATURE_ID} is listed in the public config when enabled",
    )
    assert_that(
        list(component["settings"]),
        only_contains(*PUBLIC_COMPONENT_FIELDS),
        "only the public fields are served; the analysis settings are not",
    )
