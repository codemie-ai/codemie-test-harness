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

"""Tests for vendor guardrail SDK endpoints.

Architecture:
- Parametrized tests that support multiple vendors (AWS, Azure, GCP)
- Extensible design for easy addition of new vendors
- Uses integration fixture factory for consistent setup
- Each test validates a specific SDK endpoint
"""

import pytest
from hamcrest import (
    assert_that,
    is_not,
    none,
    empty,
    greater_than,
    instance_of,
    has_length,
    is_,
)
from codemie_sdk.models.vendor_guardrail import (
    VendorGuardrailSettingsResponse,
    VendorGuardrailsResponse,
    VendorGuardrail,
    VendorGuardrailVersion,
    VendorGuardrailVersionsResponse,
    VendorGuardrailInstallRequest,
    VendorGuardrailInstallResponse,
    VendorGuardrailUninstallResponse,
    VendorGuardrailStatus,
)
from codemie_test_harness.tests.test_data.vendor_endpoint_test_data import (
    vendor_endpoint_test_data,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name


@pytest.mark.vendor
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_get_guardrail_settings(
    vendor_guardrail_utils, integration, vendor_type, credential_type, credentials
):
    """Test GET /v1/vendors/{vendor}/guardrails/settings endpoint."""
    _integration = integration(credential_type, credentials)

    settings_response = vendor_guardrail_utils.get_guardrail_settings(
        vendor=vendor_type
    )

    assert_that(settings_response, instance_of(VendorGuardrailSettingsResponse))
    assert_that(settings_response.data, is_not(none()))
    assert_that(settings_response.pagination, is_not(none()))
    assert_that(settings_response.data, is_not(empty()))
    assert_that(settings_response.pagination.total, greater_than(0))

    created_setting = vendor_guardrail_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(created_setting, is_not(none()))


@pytest.mark.vendor
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_get_guardrails(
    vendor_guardrail_utils, integration, vendor_type, credential_type, credentials
):
    """Test GET /v1/vendors/{vendor}/guardrails endpoint."""
    _integration = integration(credential_type, credentials)

    setting = vendor_guardrail_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    guardrails_response = vendor_guardrail_utils.get_guardrails(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )

    assert_that(guardrails_response, instance_of(VendorGuardrailsResponse))
    assert_that(guardrails_response.data, is_not(none()))
    assert_that(guardrails_response.pagination, is_not(none()))
    assert_that(guardrails_response.data, is_not(empty()))

    _guardrail = vendor_guardrail_utils.get_prepared_guardrail(guardrails_response.data)

    assert_that(_guardrail.id, is_not(none()))
    assert_that(_guardrail.name, is_not(none()))
    assert_that(_guardrail.status, is_(VendorGuardrailStatus.PREPARED))
    assert_that(_guardrail.version, is_not(none()))
    assert_that(_guardrail.createdAt, is_not(none()))
    assert_that(_guardrail.updatedAt, is_not(none()))


@pytest.mark.vendor
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_get_guardrail(
    vendor_guardrail_utils, integration, vendor_type, credential_type, credentials
):
    """Test GET /v1/vendors/{vendor}/guardrails/{guardrail_id} endpoint."""
    _integration = integration(credential_type, credentials)

    setting = vendor_guardrail_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    guardrails_response = vendor_guardrail_utils.get_guardrails(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )
    assert_that(guardrails_response.data, is_not(empty()))

    first_guardrail = vendor_guardrail_utils.get_prepared_guardrail(
        guardrails_response.data
    )

    _guardrail = vendor_guardrail_utils.get_guardrail(
        vendor=vendor_type,
        guardrail_id=first_guardrail.id,
        setting_id=setting.setting_id,
    )

    assert_that(_guardrail, instance_of(VendorGuardrail))
    assert_that(_guardrail.id, is_(first_guardrail.id))
    assert_that(_guardrail.name, is_not(none()))
    assert_that(_guardrail.status, is_(VendorGuardrailStatus.PREPARED))
    assert_that(_guardrail.version, is_not(none()))
    assert_that(_guardrail.createdAt, is_not(none()))
    assert_that(_guardrail.updatedAt, is_not(none()))


@pytest.mark.vendor
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_get_guardrail_version(
    vendor_guardrail_utils, integration, vendor_type, credential_type, credentials
):
    """Test GET /v1/vendors/{vendor}/guardrails/{guardrail_id}/{version} endpoint."""
    _integration = integration(credential_type, credentials)

    setting = vendor_guardrail_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    guardrails_response = vendor_guardrail_utils.get_guardrails(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )
    assert_that(guardrails_response.data, is_not(empty()))

    first_guardrail = vendor_guardrail_utils.get_prepared_guardrail(
        guardrails_response.data
    )
    versions_response = vendor_guardrail_utils.get_guardrail_versions(
        vendor=vendor_type,
        guardrail_id=first_guardrail.id,
        setting_id=setting.setting_id,
    )
    assert_that(versions_response.data, is_not(empty()))

    first_version = vendor_guardrail_utils.get_non_draft_version(versions_response.data)

    guardrail_version = (
        vendor_guardrail_utils.vendor_guardrail_service.get_guardrail_version(
            vendor=vendor_type,
            guardrail_id=first_guardrail.id,
            version=first_version.version,
            setting_id=setting.setting_id,
        )
    )

    assert_that(guardrail_version, instance_of(VendorGuardrailVersion))
    assert_that(guardrail_version.id, is_(first_guardrail.id))
    assert_that(guardrail_version.name, is_not(none()))
    assert_that(guardrail_version.status, is_not(none()))
    assert_that(guardrail_version.version, is_(first_version.version))
    assert_that(guardrail_version.createdAt, is_not(none()))
    assert_that(guardrail_version.updatedAt, is_not(none()))


@pytest.mark.vendor
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_get_guardrail_versions(
    vendor_guardrail_utils, integration, vendor_type, credential_type, credentials
):
    """Test GET /v1/vendors/{vendor}/guardrails/{guardrail_id}/versions endpoint."""
    _integration = integration(credential_type, credentials)

    setting = vendor_guardrail_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    guardrails_response = vendor_guardrail_utils.get_guardrails(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )
    assert_that(guardrails_response.data, is_not(empty()))

    first_guardrail = vendor_guardrail_utils.get_prepared_guardrail(
        guardrails_response.data
    )

    versions_response = vendor_guardrail_utils.get_guardrail_versions(
        vendor=vendor_type,
        guardrail_id=first_guardrail.id,
        setting_id=setting.setting_id,
    )

    assert_that(versions_response, instance_of(VendorGuardrailVersionsResponse))
    assert_that(versions_response.data, is_not(none()))
    assert_that(versions_response.pagination, is_not(none()))
    assert_that(versions_response.data, is_not(empty()))

    first_version = versions_response.data[0]
    assert_that(first_version.id, is_not(none()))
    assert_that(first_version.name, is_not(none()))
    assert_that(first_version.status, is_not(none()))
    assert_that(first_version.version, is_not(none()))
    assert_that(first_version.createdAt, is_not(none()))
    assert_that(first_version.updatedAt, is_not(none()))


@pytest.mark.vendor
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_install_guardrails(
    vendor_guardrail_utils, integration, vendor_type, credential_type, credentials
):
    """Test POST /v1/vendors/{vendor}/guardrails endpoint."""
    _integration = integration(credential_type, credentials)

    setting = vendor_guardrail_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    result = vendor_guardrail_utils.find_first_available_guardrail(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )
    assert_that(result, is_not(none()))

    _guardrail, version = result

    install_request = VendorGuardrailInstallRequest(
        id=_guardrail.id,
        version=version,
        setting_id=setting.setting_id,
    )

    install_response = vendor_guardrail_utils.install_guardrails(
        vendor=vendor_type,
        guardrails=[install_request],
    )

    assert_that(install_response, instance_of(VendorGuardrailInstallResponse))
    assert_that(install_response.summary, is_not(empty()))
    assert_that(install_response.summary, has_length(1))

    installed = install_response.summary[0]
    assert_that(installed.guardrailId, is_(_guardrail.id))
    assert_that(installed.version, is_(version))
    assert_that(installed.aiRunId, is_not(none()))


@pytest.mark.vendor
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_uninstall_guardrail(
    vendor_guardrail_utils, integration, vendor_type, credential_type, credentials
):
    """Test DELETE /v1/vendors/{vendor}/guardrails/{ai_run_id} endpoint."""
    _integration = integration(credential_type, credentials)

    setting = vendor_guardrail_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    ai_run_id = vendor_guardrail_utils.install_first_available_guardrail(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )
    assert_that(ai_run_id, is_not(none()))

    uninstall_response = vendor_guardrail_utils.uninstall_guardrail(
        vendor=vendor_type,
        ai_run_id=ai_run_id,
    )

    assert_that(uninstall_response, instance_of(VendorGuardrailUninstallResponse))
    assert_that(uninstall_response.success, is_(True))


@pytest.mark.vendor
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_get_guardrail_settings_pagination(
    vendor_guardrail_utils, integration, vendor_type, credential_type, credentials
):
    """Test pagination functionality for get_guardrail_settings endpoint."""

    for _ in range(11):
        integration(credential_type, credentials, integration_alias=get_random_name())

    first_page = vendor_guardrail_utils.get_guardrail_settings(
        vendor=vendor_type,
        page=0,
        per_page=2,
    )

    assert_that(first_page.pagination.page, is_(0))
    assert_that(first_page.pagination.per_page, is_(2))
    assert_that(first_page.pagination.total, greater_than(0))

    if first_page.pagination.pages > 1:
        second_page = vendor_guardrail_utils.get_guardrail_settings(
            vendor=vendor_type,
            page=1,
            per_page=2,
        )
        assert_that(second_page.pagination.page, is_(1))
        assert_that(second_page.data, is_not(empty()))


@pytest.mark.vendor
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_get_guardrails_pagination(
    vendor_guardrail_utils, integration, vendor_type, credential_type, credentials
):
    """Test pagination functionality for get_guardrails endpoint using next_token."""
    _integration = integration(credential_type, credentials)

    setting = vendor_guardrail_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    first_page = vendor_guardrail_utils.get_guardrails(
        vendor=vendor_type,
        setting_id=setting.setting_id,
        per_page=2,
    )

    assert_that(first_page.data, is_not(empty()))

    if first_page.pagination.next_token:
        second_page = vendor_guardrail_utils.get_guardrails(
            vendor=vendor_type,
            setting_id=setting.setting_id,
            per_page=2,
            next_token=first_page.pagination.next_token,
        )
        assert_that(second_page.data, is_not(empty()))
        first_page_ids = {g.id for g in first_page.data}
        second_page_ids = {g.id for g in second_page.data}
        assert_that(first_page_ids.intersection(second_page_ids), is_(set()))


@pytest.mark.vendor
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_get_guardrail_versions_pagination(
    vendor_guardrail_utils, integration, vendor_type, credential_type, credentials
):
    """Test pagination functionality for get_guardrail_versions endpoint using next_token."""
    _integration = integration(credential_type, credentials)

    setting = vendor_guardrail_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    guardrails_response = vendor_guardrail_utils.get_guardrails(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )
    assert_that(guardrails_response.data, is_not(empty()))

    first_guardrail = vendor_guardrail_utils.get_prepared_guardrail(
        guardrails_response.data
    )

    first_page = vendor_guardrail_utils.get_guardrail_versions(
        vendor=vendor_type,
        guardrail_id=first_guardrail.id,
        setting_id=setting.setting_id,
        per_page=2,
    )

    assert_that(first_page.data, is_not(empty()))

    if first_page.pagination.next_token:
        second_page = vendor_guardrail_utils.get_guardrail_versions(
            vendor=vendor_type,
            guardrail_id=first_guardrail.id,
            setting_id=setting.setting_id,
            per_page=2,
            next_token=first_page.pagination.next_token,
        )
        assert_that(second_page.data, is_not(empty()))
        first_page_versions = {v.version for v in first_page.data}
        second_page_versions = {v.version for v in second_page.data}
        assert_that(first_page_versions.intersection(second_page_versions), is_(set()))
