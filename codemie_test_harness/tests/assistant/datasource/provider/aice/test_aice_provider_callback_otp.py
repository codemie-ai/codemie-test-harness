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

"""
API tests for the provider callback of an AICE provider datasource.

The callback route is anonymous: the external provider proves itself with the
one-time password it was given. Once a datasource has completed, that password
is reset, so the route must still reject every request that does not carry a
valid one.
"""

import pytest
from hamcrest import assert_that, equal_to

from codemie_test_harness.tests.test_data.provider_callback_test_data import (
    PROVIDER_CALLBACK_COMPLETED_PAYLOAD,
    provider_callback_rejected_otp_test_data,
)
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver


# @case strip-datasource-credentials_TC_003
@pytest.mark.datasource
@pytest.mark.provider
@pytest.mark.aice
@pytest.mark.api
@pytest.mark.parametrize("otp", provider_callback_rejected_otp_test_data)
@pytest.mark.skipif(
    EnvironmentResolver.is_sandbox(),
    reason="AICE is not configured for sandbox environments",
)
def test_provider_callback_rejects_invalid_otp_for_completed_datasource(
    client,
    datasource_utils,
    code_exploration_datasource,
    otp,
):
    """A callback for a completed provider datasource is rejected with 403
    when the one-time password header is missing, empty or wrong, and the
    datasource keeps its status and error message.
    """
    datasource_before = datasource_utils.get_datasource(code_exploration_datasource.id)

    response = client.datasources.send_provider_callback(
        code_exploration_datasource.id,
        PROVIDER_CALLBACK_COMPLETED_PAYLOAD,
        otp=otp,
    )

    assert_that(
        response.status_code,
        equal_to(403),
        f"Callback with OTP [{otp}] should be forbidden: {response.text}",
    )
    assert_that(
        response.json().get("detail"),
        equal_to("Invalid or expired OTP"),
        "Rejected callback must carry the OTP error detail",
    )

    datasource_after = datasource_utils.get_datasource(code_exploration_datasource.id)
    assert_that(
        datasource_after.status,
        equal_to(datasource_before.status),
        "A rejected callback must not change the datasource status",
    )
    assert_that(
        datasource_after.error_message,
        equal_to(datasource_before.error_message),
        "A rejected callback must not set an error on the datasource",
    )
