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

"""API tests for activity events access control.

Covers:
    TC-010  Non-maintainer client receives HTTP 403 on activity events endpoints
"""

import pytest
from hamcrest import assert_that, equal_to

from codemie_test_harness.tests.utils.activity_utils import ActivityUtils


# ---------------------------------------------------------------------------
# TC-010: Non-maintainer client receives HTTP 403
# ---------------------------------------------------------------------------


@pytest.mark.activity
@pytest.mark.api
def test_non_maintainer_receives_403_on_activity_endpoints(disposable_user):
    """TC-010: A non-maintainer user gets HTTP 403 on both activity endpoints."""
    _, _, user_client = disposable_user

    non_maintainer_utils = ActivityUtils(user_client)

    list_status = non_maintainer_utils.list_events_status_code()
    assert_that(
        list_status,
        equal_to(403),
        "Non-maintainer should receive HTTP 403 from GET /v1/admin/activity-events",
    )

    filter_status = non_maintainer_utils.get_filter_options_status_code()
    assert_that(
        filter_status,
        equal_to(403),
        "Non-maintainer should receive HTTP 403 from GET /v1/admin/activity-events/filter-options",
    )
