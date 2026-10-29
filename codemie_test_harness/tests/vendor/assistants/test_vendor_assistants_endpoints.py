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

"""Tests for vendor service SDK endpoints.

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
from codemie_sdk.models.vendor_assistant import (
    VendorAssistantSettingsResponse,
    VendorAssistantsResponse,
    VendorAssistant,
    VendorAssistantVersion,
    VendorAssistantAliasesResponse,
    VendorAssistantInstallRequest,
    VendorAssistantInstallResponse,
    VendorAssistantUninstallResponse,
    VendorAssistantStatus,
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
def test_get_assistant_settings(
    vendor_assistant_utils, integration, vendor_type, credential_type, credentials
):
    """Test GET /v1/vendors/{vendor}/assistants/settings endpoint."""
    _integration = integration(credential_type, credentials)

    settings_response = vendor_assistant_utils.get_assistant_settings(
        vendor=vendor_type
    )

    assert_that(settings_response, instance_of(VendorAssistantSettingsResponse))
    assert_that(settings_response.data, is_not(none()))
    assert_that(settings_response.pagination, is_not(none()))
    assert_that(settings_response.data, is_not(empty()))
    assert_that(settings_response.pagination.total, greater_than(0))

    created_setting = vendor_assistant_utils.find_setting_for_integration(
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
def test_get_assistants(
    vendor_assistant_utils, integration, vendor_type, credential_type, credentials
):
    """Test GET /v1/vendors/{vendor}/assistants endpoint."""
    _integration = integration(credential_type, credentials)

    setting = vendor_assistant_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    assistants_response = vendor_assistant_utils.get_assistants(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )

    assert_that(assistants_response, instance_of(VendorAssistantsResponse))
    assert_that(assistants_response.data, is_not(none()))
    assert_that(assistants_response.pagination, is_not(none()))
    assert_that(assistants_response.data, is_not(empty()))

    _assistant = vendor_assistant_utils.get_prepared_assistant(assistants_response.data)

    assert_that(_assistant.id, is_not(none()))
    assert_that(_assistant.name, is_not(none()))
    assert_that(_assistant.status, is_(VendorAssistantStatus.PREPARED))
    assert_that(_assistant.description, is_not(none()))
    assert_that(_assistant.updatedAt, is_not(none()))


@pytest.mark.vendor
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_get_assistant(
    vendor_assistant_utils, integration, vendor_type, credential_type, credentials
):
    """Test GET /v1/vendors/{vendor}/assistants/{assistant_id} endpoint."""
    _integration = integration(credential_type, credentials)

    setting = vendor_assistant_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    assistants_response = vendor_assistant_utils.get_assistants(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )
    assert_that(assistants_response.data, is_not(empty()))

    first_assistant = vendor_assistant_utils.get_prepared_assistant(
        assistants_response.data
    )

    _assistant = vendor_assistant_utils.get_assistant(
        vendor=vendor_type,
        assistant_id=first_assistant.id,
        setting_id=setting.setting_id,
    )

    assert_that(_assistant, instance_of(VendorAssistant))
    assert_that(_assistant.id, is_(first_assistant.id))
    assert_that(_assistant.name, is_not(none()))
    assert_that(_assistant.status, is_(VendorAssistantStatus.PREPARED))
    assert_that(_assistant.description, is_not(none()))
    assert_that(_assistant.updatedAt, is_not(none()))


@pytest.mark.vendor
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_get_assistant_version(
    vendor_assistant_utils, integration, vendor_type, credential_type, credentials
):
    """Test GET /v1/vendors/{vendor}/assistants/{assistant_id}/{version} endpoint."""
    _integration = integration(credential_type, credentials)

    setting = vendor_assistant_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    assistants_response = vendor_assistant_utils.get_assistants(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )
    assert_that(assistants_response.data, is_not(empty()))

    first_assistant = vendor_assistant_utils.get_prepared_assistant(
        assistants_response.data
    )
    aliases_response = vendor_assistant_utils.get_assistant_aliases(
        vendor=vendor_type,
        assistant_id=first_assistant.id,
        setting_id=setting.setting_id,
    )
    assert_that(aliases_response.data, is_not(empty()))

    first_alias = vendor_assistant_utils.get_non_draft_alias(aliases_response.data)

    assistant_version = (
        vendor_assistant_utils.vendor_assistant_service.get_assistant_version(
            vendor=vendor_type,
            assistant_id=first_assistant.id,
            version=first_alias.version,
            setting_id=setting.setting_id,
        )
    )

    assert_that(assistant_version, instance_of(VendorAssistantVersion))
    assert_that(assistant_version.id, is_(first_assistant.id))
    assert_that(assistant_version.name, is_not(none()))
    assert_that(assistant_version.status, is_not(none()))
    assert_that(assistant_version.version, is_(first_alias.version))
    assert_that(assistant_version.instruction, is_not(none()))
    assert_that(assistant_version.foundationModel, is_not(none()))
    assert_that(assistant_version.createdAt, is_not(none()))
    assert_that(assistant_version.updatedAt, is_not(none()))


@pytest.mark.vendor
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_get_assistant_aliases(
    vendor_assistant_utils, integration, vendor_type, credential_type, credentials
):
    """Test GET /v1/vendors/{vendor}/assistants/{assistant_id}/aliases endpoint."""
    _integration = integration(credential_type, credentials)

    setting = vendor_assistant_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    assistants_response = vendor_assistant_utils.get_assistants(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )
    assert_that(assistants_response.data, is_not(empty()))

    first_assistant = vendor_assistant_utils.get_prepared_assistant(
        assistants_response.data
    )

    aliases_response = vendor_assistant_utils.get_assistant_aliases(
        vendor=vendor_type,
        assistant_id=first_assistant.id,
        setting_id=setting.setting_id,
    )

    assert_that(aliases_response, instance_of(VendorAssistantAliasesResponse))
    assert_that(aliases_response.data, is_not(none()))
    assert_that(aliases_response.pagination, is_not(none()))
    assert_that(aliases_response.data, is_not(empty()))

    first_alias = aliases_response.data[0]
    assert_that(first_alias.id, is_not(none()))
    assert_that(first_alias.name, is_not(none()))
    assert_that(first_alias.status, is_not(none()))
    assert_that(first_alias.description, is_not(none()))
    assert_that(first_alias.version, is_not(none()))
    assert_that(first_alias.createdAt, is_not(none()))
    assert_that(first_alias.updatedAt, is_not(none()))


@pytest.mark.vendor
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_install_assistants(
    vendor_assistant_utils, integration, vendor_type, credential_type, credentials
):
    """Test POST /v1/vendors/{vendor}/assistants endpoint."""
    _integration = integration(credential_type, credentials)

    setting = vendor_assistant_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    result = vendor_assistant_utils.find_first_available_assistant(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )
    assert_that(result, is_not(none()))

    _assistant, alias_id = result

    install_request = VendorAssistantInstallRequest(
        id=_assistant.id,
        agentAliasId=alias_id,
        setting_id=setting.setting_id,
    )

    install_response = vendor_assistant_utils.install_assistants(
        vendor=vendor_type,
        assistants=[install_request],
    )

    assert_that(install_response, instance_of(VendorAssistantInstallResponse))
    assert_that(install_response.summary, is_not(empty()))
    assert_that(install_response.summary, has_length(1))

    installed = install_response.summary[0]
    assert_that(installed.agentId, is_(_assistant.id))
    assert_that(installed.agentAliasId, is_(alias_id))
    assert_that(installed.aiRunId, is_not(none()))


@pytest.mark.vendor
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_uninstall_assistant(
    vendor_assistant_utils, integration, vendor_type, credential_type, credentials
):
    """Test DELETE /v1/vendors/{vendor}/assistants/{ai_run_id} endpoint."""
    _integration = integration(credential_type, credentials)

    setting = vendor_assistant_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    codemie_id = vendor_assistant_utils.install_first_available_assistant(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )
    assert_that(codemie_id, is_not(none()))

    uninstall_response = vendor_assistant_utils.uninstall_assistant(
        vendor=vendor_type,
        codemie_id=codemie_id,
    )

    assert_that(uninstall_response, instance_of(VendorAssistantUninstallResponse))
    assert_that(uninstall_response.success, is_(True))


@pytest.mark.vendor
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_get_assistant_settings_pagination(
    vendor_assistant_utils, integration, vendor_type, credential_type, credentials
):
    """Test pagination functionality for get_assistant_settings endpoint."""

    for _ in range(11):
        integration(credential_type, credentials, integration_alias=get_random_name())

    first_page = vendor_assistant_utils.get_assistant_settings(
        vendor=vendor_type,
        page=0,
        per_page=2,
    )

    assert_that(first_page.pagination.page, is_(0))
    assert_that(first_page.pagination.per_page, is_(2))
    assert_that(first_page.pagination.total, greater_than(0))

    if first_page.pagination.pages > 1:
        second_page = vendor_assistant_utils.get_assistant_settings(
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
def test_get_assistants_pagination(
    vendor_assistant_utils, integration, vendor_type, credential_type, credentials
):
    """Test pagination functionality for get_assistants endpoint using next_token."""
    _integration = integration(credential_type, credentials)

    setting = vendor_assistant_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    first_page = vendor_assistant_utils.get_assistants(
        vendor=vendor_type,
        setting_id=setting.setting_id,
        per_page=2,
    )

    assert_that(first_page.data, is_not(empty()))

    if first_page.pagination.next_token:
        second_page = vendor_assistant_utils.get_assistants(
            vendor=vendor_type,
            setting_id=setting.setting_id,
            per_page=2,
            next_token=first_page.pagination.next_token,
        )
        assert_that(second_page.data, is_not(empty()))
        first_page_ids = {a.id for a in first_page.data}
        second_page_ids = {a.id for a in second_page.data}
        assert_that(first_page_ids.intersection(second_page_ids), is_(set()))
