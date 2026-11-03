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

"""CLI Analytics delivery framework: the label a session gets from the skill that started it."""

import pytest
from hamcrest import assert_that, equal_to, has_key

from codemie_test_harness.tests.test_data.cli_analytics_test_data import (
    DELIVERY_FRAMEWORK_CASES,
    get_delivery_framework_session_seeds,
)
from codemie_test_harness.tests.utils.cli_analytics_api_utils import CliAnalyticsApi


@pytest.fixture(scope="module")
def framework_sessions(analytics_utils, cli_analytics_project):
    """Sessions that each started with one skill (or none), sent by the signed-in user
    to the module's project and rolled up; keyed by skill."""
    seeds = get_delivery_framework_session_seeds()
    for seed in seeds.values():
        analytics_utils.ingest_cli_event_hooks(
            seed.events(cli_analytics_project), project=cli_analytics_project
        )
    for seed in seeds.values():
        analytics_utils.wait_for_cli_session(seed.session_id)
    return seeds


@pytest.mark.cli_analytics
@pytest.mark.parametrize("skill, expected_label", DELIVERY_FRAMEWORK_CASES)
@pytest.mark.api
def test_session_delivery_framework_follows_starting_skill(
    analytics_utils, framework_sessions, skill, expected_label
):
    """A session started by a factory skill shows that factory's label; one with no
    factory skill stays 'Pure chat'."""
    seed = framework_sessions[skill]
    response = CliAnalyticsApi(analytics_utils.client).request(
        "GET", f"/v1/analytics/cli-analytics/sessions/{seed.session_id}"
    )
    assert_that(response.status_code, equal_to(200))
    session = response.json()["data"]
    assert_that(session, has_key("delivery_framework"))  # repro:precondition
    assert_that(  # repro:symptom
        session["delivery_framework"],
        equal_to(expected_label),
        f"framework label of the session started by {skill!r}",
    )
