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

"""API tests for the POST /v1/settings/test/ authorization fix.

Before this fix, any authenticated user could test a *stored* USER setting they
did not own -- by supplying its ``setting_id`` -- causing that owner's
credential to be decrypted and executed on the caller's behalf (IDOR). The fix
adds an ownership/read-ability check (``Ability(user).can(Action.READ, ...)``)
before ``SettingsTester`` is ever constructed. See
backend/src/codemie/rest_api/routers/user_settings.py:284-286 and
backend/tests/codemie/rest_api/routers/test_user_settings.py:242,261.

This suite exercises the fix as a black-box HTTP client (no access to the
backend's internal ``SettingsTester`` object), so "SettingsTester never ran" is
verified indirectly: ``raise_forbidden("test")`` emits a distinctive 403 body
that only occurs on the router's own authorization-gate path
(backend/src/codemie/rest_api/routers/utils.py:63-69) -- SettingsTester
running (success or failure) always produces a different status/body. That
in-repo backend suite already asserts the mock/spy call-count directly;
covering the exact same claim by mocking is out of scope for this black-box
harness.

Covers TC_001 and TC_002.
"""

import pytest
from hamcrest import assert_that, equal_to
from requests import HTTPError

from codemie_sdk.models.integration import (
    CredentialTypes,
    IntegrationTestRequest,
    IntegrationTestResponse,
    IntegrationType,
)
from codemie_test_harness.tests.utils.base_utils import (
    assert_error_details,
    get_random_name,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager

# raise_forbidden("test")'s exact "details" text --
# backend/src/codemie/rest_api/routers/utils.py:63-69. Unique to the router's own
# authorization gate: SettingsTester never runs on this path, so this exact string
# (rather than SettingsTester's own "Integration test failed" / "Cannot test
# specified setting" messages) is the black-box proof that no decryption or
# outbound credential test occurred.
FORBIDDEN_TEST_DETAILS = (
    "You do not have the necessary permissions to test this entity."
)


@pytest.mark.integration
@pytest.mark.user_integration
@pytest.mark.jira
@pytest.mark.project_management
@pytest.mark.api
def test_owner_can_test_own_user_setting(general_integration, integration_utils):
    """
    The owner of a stored USER Jira setting can test it via
    POST /v1/settings/test/ (setting_id=<owned setting>). The request must
    succeed with a real (unmocked) Jira credential -- that only happens if
    SettingsTester actually ran the owner's decrypted credential through a
    live healthcheck (backend/tests/.../test_user_settings.py:261:
    test_test_setting_owner_allowed -> 200, SettingsTester.test() called
    once).
    """
    integration_alias = get_random_name()
    owned_setting = general_integration(
        integration_type=IntegrationType.USER,
        credential_type=CredentialTypes.JIRA,
        credential_values=CredentialsManager.jira_credentials(),
        integration_alias=integration_alias,
    )

    test_response = integration_utils.test_integration(
        IntegrationTestRequest(
            credential_type=owned_setting.credential_type,
            setting_id=owned_setting.id,
        ),
        IntegrationTestResponse,
    )

    # response is 200 with a genuine successful healthcheck. A mocked or
    # never-invoked SettingsTester cannot produce this exact success body,
    # so this is the black-box equivalent of "SettingsTester.test() was
    # called once with the owner's decrypted credential".
    assert_that(
        test_response,
        equal_to(IntegrationTestResponse(message="", success=True)),
        "Owner testing their own USER setting did not succeed.",
    )


@pytest.mark.integration
@pytest.mark.user_integration
@pytest.mark.jira
@pytest.mark.project_management
@pytest.mark.api
def test_non_owner_denied_testing_others_user_setting(
    general_integration, non_admin_integration_utils
):
    """
    A different authenticated user (non-owner) is denied with 403 when
    attempting to test another user's stored USER setting via
    POST /v1/settings/test/ (setting_id=<someone else's setting>). This is
    the exact IDOR the ticket fixes (backend/tests/.../test_user_settings.py:242:
    test_test_setting_foreign_user_setting_denied -> 403, SettingsTester.test
    asserted not called).

    The 403 body must carry the router's own raise_forbidden("test") message
    -- SettingsTester running (success or failure) would surface a different
    status/body entirely, so this is the black-box proof that no decryption,
    client construction, healthcheck, or outbound request occurred.
    """
    integration_alias = get_random_name()
    owned_setting = general_integration(
        integration_type=IntegrationType.USER,
        credential_type=CredentialTypes.JIRA,
        credential_values=CredentialsManager.jira_credentials(),
        integration_alias=integration_alias,
    )

    try:
        non_admin_integration_utils.test_integration(
            IntegrationTestRequest(
                credential_type=owned_setting.credential_type,
                setting_id=owned_setting.id,
            )
        )
        raise AssertionError(
            "Non-owner testing another user's USER setting did not raise the "
            "expected 403 Forbidden."
        )
    except HTTPError as e:
        assert_error_details(e.response, 403, FORBIDDEN_TEST_DETAILS)
