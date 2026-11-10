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

"""API tests for access control of the marketplace review endpoints.

Every marketplace-management route requires the admin or maintainer role, and
the force_publish flag of the assistant publish route is limited the same way.
No distinct admin-publisher role exists, so the tests pin admin-or-maintainer.
"""

import pytest
from hamcrest import assert_that, equal_to, has_properties
from requests import HTTPError

from codemie_test_harness.tests.test_data.marketplace_approval_gate_test_data import (
    MANAGEMENT_ENDPOINT_PARAMS,
    PENDING_REVIEW,
)


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
@pytest.mark.parametrize("endpoint", MANAGEMENT_ENDPOINT_PARAMS)
def test_non_admin_is_refused_on_management_endpoints_and_force_publish(
    pending_assistant, marketplace_submitter, marketplace_management_utils, endpoint
):
    # @case marketplace-admin-approval-gate_TC_002
    submitted = pending_assistant()
    before = marketplace_management_utils.get_detail(submitted.id)

    with pytest.raises(HTTPError) as exc_info:
        marketplace_submitter.management.call_endpoint(
            endpoint,
            submitted.id,
            expected_version=before.marketplace_version,
            categories=submitted.categories,
        )

    response = exc_info.value.response
    assert_that(response.status_code, equal_to(403), response.text)
    after = marketplace_management_utils.get_detail(submitted.id)
    assert_that(
        after,
        has_properties(
            marketplace_status=PENDING_REVIEW,
            marketplace_version=before.marketplace_version,
            is_verified=False,
        ),
    )
