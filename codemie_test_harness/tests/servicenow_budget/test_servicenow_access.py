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

"""API tests for who may call the ServiceNow integration, and what that caller may reach."""

import pytest
from hamcrest import assert_that, equal_to
from requests import HTTPError

from codemie_test_harness.tests.test_data.servicenow_project_budget_test_data import (
    ACCESS_DENIED_MESSAGE,
    INTEGRATION_REQUESTS,
    INTEGRATION_ROUTE_GUARD_DETAILS,
    OUT_OF_SCOPE_REQUESTS,
    SERVICE_ACCOUNT_SCOPE_DETAILS,
)
from codemie_test_harness.tests.utils.servicenow_budget_utils import error_body


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.parametrize("request_method", OUT_OF_SCOPE_REQUESTS)
def test_service_account_is_denied_endpoints_outside_the_integration(
    servicenow_account, request_method
):
    # @case servicenow-project-budget-integration-api_TC_012
    with pytest.raises(HTTPError) as exc_info:
        getattr(servicenow_account, request_method)()

    assert_that(
        exc_info.value.response.status_code,
        equal_to(403),
        "The service account must be refused outside the integration endpoints",
    )
    assert_that(
        error_body(exc_info)["message"],
        equal_to(ACCESS_DENIED_MESSAGE),
        "The refusal must be an access denied error",
    )
    assert_that(
        error_body(exc_info)["details"],
        equal_to(SERVICE_ACCOUNT_SCOPE_DETAILS),
        "The refusal must explain the service account is limited to the integration",
    )


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.parametrize("send_request", INTEGRATION_REQUESTS)
def test_non_service_account_callers_are_denied_the_integration_endpoints(
    non_service_account_client, send_request
):
    # @case servicenow-project-budget-integration-api_TC_013
    with pytest.raises(HTTPError) as exc_info:
        send_request(non_service_account_client.servicenow_integration)

    assert_that(
        exc_info.value.response.status_code,
        equal_to(403),
        "Only the ServiceNow service account may call the integration endpoints",
    )
    assert_that(
        error_body(exc_info)["message"],
        equal_to(ACCESS_DENIED_MESSAGE),
        "The refusal must be an access denied error",
    )
    assert_that(
        error_body(exc_info)["details"],
        equal_to(INTEGRATION_ROUTE_GUARD_DETAILS),
        "The refusal must say the endpoint is reserved for the service account",
    )
