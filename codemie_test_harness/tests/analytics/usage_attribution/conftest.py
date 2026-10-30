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

"""Fixtures for Usage Attribution analytics tests (/v1/analytics/usage-attribution/*)."""

import pytest
from hamcrest import assert_that, is_

from codemie_test_harness.tests.test_data.usage_attribution_test_data import (
    PERIOD_LAST_30_DAYS,
)
from codemie_test_harness.tests.utils.usage_attribution_utils import (
    UsageAttributionUtils,
    period_params,
)


@pytest.fixture(scope="session")
def usage_attribution_utils(client):
    """Usage Attribution utilities for the admin client."""
    return UsageAttributionUtils(client)


@pytest.fixture(scope="session")
def user_enrichment_enabled(usage_attribution_utils):
    """Fails where user enrichment is off: country and job title group breakdowns need it."""
    assert_that(
        usage_attribution_utils.get_settings().data["enrichment"],
        is_(True),
        "User enrichment is off on this environment: "
        "the country and job title breakdowns need it",
    )


@pytest.fixture
def member_client(default_project_member):
    """Client of a plain project member who holds no platform role."""
    return default_project_member.client


@pytest.fixture
def thirty_days():
    """Query parameters for the last 30 days."""
    return period_params(PERIOD_LAST_30_DAYS)
