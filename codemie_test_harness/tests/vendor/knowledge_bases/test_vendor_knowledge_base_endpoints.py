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

"""Tests for vendor knowledge base SDK endpoints.

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
from codemie_sdk.models.vendor_knowledgebase import (
    VendorKnowledgeBaseSettingsResponse,
    VendorKnowledgeBasesResponse,
    VendorKnowledgeBaseDetail,
    VendorKnowledgeBaseInstallRequest,
    VendorKnowledgeBaseInstallResponse,
    VendorKnowledgeBaseUninstallResponse,
    VendorKnowledgeBaseStatus,
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
def test_get_knowledgebase_settings(
    vendor_knowledge_base_utils, integration, vendor_type, credential_type, credentials
):
    """Test GET /v1/vendors/{vendor}/knowledge-bases/settings endpoint."""
    _integration = integration(credential_type, credentials)

    settings_response = vendor_knowledge_base_utils.get_knowledgebase_settings(
        vendor=vendor_type
    )

    assert_that(settings_response, instance_of(VendorKnowledgeBaseSettingsResponse))
    assert_that(settings_response.data, is_not(none()))
    assert_that(settings_response.pagination, is_not(none()))
    assert_that(settings_response.data, is_not(empty()))
    assert_that(settings_response.pagination.total, greater_than(0))

    created_setting = vendor_knowledge_base_utils.find_setting_for_integration(
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
def test_get_knowledgebases(
    vendor_knowledge_base_utils, integration, vendor_type, credential_type, credentials
):
    """Test GET /v1/vendors/{vendor}/knowledge-bases endpoint."""
    _integration = integration(credential_type, credentials)

    setting = vendor_knowledge_base_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    kbs_response = vendor_knowledge_base_utils.get_knowledgebases(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )

    assert_that(kbs_response, instance_of(VendorKnowledgeBasesResponse))
    assert_that(kbs_response.data, is_not(none()))
    assert_that(kbs_response.pagination, is_not(none()))
    assert_that(kbs_response.data, is_not(empty()))

    _kb = vendor_knowledge_base_utils.get_available_knowledge_base(kbs_response.data)

    assert_that(_kb.id, is_not(none()))
    assert_that(_kb.name, is_not(none()))
    assert_that(_kb.status, is_(VendorKnowledgeBaseStatus.PREPARED))
    assert_that(_kb.description, is_not(none()))
    assert_that(_kb.updatedAt, is_not(none()))


@pytest.mark.vendor
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_get_knowledgebase(
    vendor_knowledge_base_utils, integration, vendor_type, credential_type, credentials
):
    """Test GET /v1/vendors/{vendor}/knowledge-bases/{knowledgebase_id} endpoint."""
    _integration = integration(credential_type, credentials)

    setting = vendor_knowledge_base_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    kbs_response = vendor_knowledge_base_utils.get_knowledgebases(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )
    assert_that(kbs_response.data, is_not(empty()))

    first_kb = vendor_knowledge_base_utils.get_available_knowledge_base(
        kbs_response.data
    )

    _kb = vendor_knowledge_base_utils.get_knowledgebase(
        vendor=vendor_type,
        knowledgebase_id=first_kb.id,
        setting_id=setting.setting_id,
    )

    assert_that(_kb, instance_of(VendorKnowledgeBaseDetail))
    assert_that(_kb.id, is_(first_kb.id))
    assert_that(_kb.name, is_not(none()))
    assert_that(_kb.status, is_(VendorKnowledgeBaseStatus.PREPARED))
    assert_that(_kb.description, is_not(none()))
    assert_that(_kb.updatedAt, is_not(none()))


@pytest.mark.vendor
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_install_knowledgebases(
    vendor_knowledge_base_utils, integration, vendor_type, credential_type, credentials
):
    """Test POST /v1/vendors/{vendor}/knowledge-bases endpoint."""
    _integration = integration(credential_type, credentials)

    setting = vendor_knowledge_base_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    kb = vendor_knowledge_base_utils.find_first_available_knowledge_base(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )
    assert_that(kb, is_not(none()))

    install_request = VendorKnowledgeBaseInstallRequest(
        id=kb.id,
        setting_id=setting.setting_id,
    )

    install_response = vendor_knowledge_base_utils.install_knowledgebases(
        vendor=vendor_type,
        knowledgebases=[install_request],
    )

    assert_that(install_response, instance_of(VendorKnowledgeBaseInstallResponse))
    assert_that(install_response.summary, is_not(empty()))
    assert_that(install_response.summary, has_length(1))

    installed = install_response.summary[0]
    assert_that(installed.knowledgeBaseId, is_(kb.id))
    assert_that(installed.aiRunId, is_not(none()))


@pytest.mark.vendor
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_uninstall_knowledgebase(
    vendor_knowledge_base_utils, integration, vendor_type, credential_type, credentials
):
    """Test DELETE /v1/vendors/{vendor}/knowledge-bases/{ai_run_id} endpoint."""
    _integration = integration(credential_type, credentials)

    setting = vendor_knowledge_base_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    codemie_id = vendor_knowledge_base_utils.install_first_available_knowledge_base(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )
    assert_that(codemie_id, is_not(none()))

    uninstall_response = vendor_knowledge_base_utils.uninstall_knowledgebase(
        vendor=vendor_type,
        codemie_id=codemie_id,
    )

    assert_that(uninstall_response, instance_of(VendorKnowledgeBaseUninstallResponse))
    assert_that(uninstall_response.success, is_(True))


@pytest.mark.vendor
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_get_knowledgebase_settings_pagination(
    vendor_knowledge_base_utils, integration, vendor_type, credential_type, credentials
):
    """Test pagination functionality for get_knowledgebase_settings endpoint."""

    for _ in range(11):
        integration(credential_type, credentials, integration_alias=get_random_name())

    first_page = vendor_knowledge_base_utils.get_knowledgebase_settings(
        vendor=vendor_type,
        page=0,
        per_page=2,
    )

    assert_that(first_page.pagination.page, is_(0))
    assert_that(first_page.pagination.per_page, is_(2))
    assert_that(first_page.pagination.total, greater_than(0))

    if first_page.pagination.pages > 1:
        second_page = vendor_knowledge_base_utils.get_knowledgebase_settings(
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
def test_get_knowledgebases_pagination(
    vendor_knowledge_base_utils, integration, vendor_type, credential_type, credentials
):
    """Test pagination functionality for get_knowledgebases endpoint using next_token."""
    _integration = integration(credential_type, credentials)

    setting = vendor_knowledge_base_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    first_page = vendor_knowledge_base_utils.get_knowledgebases(
        vendor=vendor_type,
        setting_id=setting.setting_id,
        per_page=2,
    )

    assert_that(first_page.data, is_not(empty()))

    if first_page.pagination.next_token:
        second_page = vendor_knowledge_base_utils.get_knowledgebases(
            vendor=vendor_type,
            setting_id=setting.setting_id,
            per_page=2,
            next_token=first_page.pagination.next_token,
        )
        assert_that(second_page.data, is_not(empty()))
        first_page_ids = {kb.id for kb in first_page.data}
        second_page_ids = {kb.id for kb in second_page.data}
        assert_that(first_page_ids.intersection(second_page_ids), is_(set()))
