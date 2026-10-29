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

"""Tests for vendor workflow SDK endpoints.

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
from codemie_sdk.models.vendor_workflow import (
    VendorWorkflowSettingsResponse,
    VendorWorkflowsResponse,
    VendorWorkflow,
    VendorWorkflowAliasesResponse,
    VendorWorkflowInstallRequest,
    VendorWorkflowInstallResponse,
    VendorWorkflowUninstallResponse,
    VendorWorkflowStatus,
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
def test_get_workflow_settings(
    vendor_workflow_utils, integration, vendor_type, credential_type, credentials
):
    """Test GET /v1/vendors/{vendor}/workflows/settings endpoint."""
    _integration = integration(credential_type, credentials)

    settings_response = vendor_workflow_utils.get_workflow_settings(vendor=vendor_type)

    assert_that(settings_response, instance_of(VendorWorkflowSettingsResponse))
    assert_that(settings_response.data, is_not(none()))
    assert_that(settings_response.pagination, is_not(none()))
    assert_that(settings_response.data, is_not(empty()))
    assert_that(settings_response.pagination.total, greater_than(0))

    created_setting = vendor_workflow_utils.find_setting_for_integration(
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
def test_get_workflows(
    vendor_workflow_utils, integration, vendor_type, credential_type, credentials
):
    """Test GET /v1/vendors/{vendor}/workflows endpoint."""
    _integration = integration(credential_type, credentials)

    setting = vendor_workflow_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    workflows_response = vendor_workflow_utils.get_workflows(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )

    assert_that(workflows_response, instance_of(VendorWorkflowsResponse))
    assert_that(workflows_response.data, is_not(none()))
    assert_that(workflows_response.pagination, is_not(none()))
    assert_that(workflows_response.data, is_not(empty()))

    _workflow = vendor_workflow_utils.get_prepared_workflow(workflows_response.data)

    assert_that(_workflow.id, is_not(none()))
    assert_that(_workflow.name, is_not(none()))
    assert_that(_workflow.status, is_(VendorWorkflowStatus.PREPARED))
    assert_that(_workflow.description, is_not(none()))
    assert_that(_workflow.version, is_not(none()))
    assert_that(_workflow.createdAt, is_not(none()))
    assert_that(_workflow.updatedAt, is_not(none()))


@pytest.mark.vendor
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_get_workflow(
    vendor_workflow_utils, integration, vendor_type, credential_type, credentials
):
    """Test GET /v1/vendors/{vendor}/workflows/{workflow_id} endpoint."""
    _integration = integration(credential_type, credentials)

    setting = vendor_workflow_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    workflows_response = vendor_workflow_utils.get_workflows(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )
    assert_that(workflows_response.data, is_not(empty()))

    first_workflow = vendor_workflow_utils.get_prepared_workflow(
        workflows_response.data
    )

    _workflow = vendor_workflow_utils.get_workflow(
        vendor=vendor_type,
        workflow_id=first_workflow.id,
        setting_id=setting.setting_id,
    )

    assert_that(_workflow, instance_of(VendorWorkflow))
    assert_that(_workflow.id, is_(first_workflow.id))
    assert_that(_workflow.name, is_not(none()))
    assert_that(_workflow.status, is_(VendorWorkflowStatus.PREPARED))
    assert_that(_workflow.description, is_not(none()))
    assert_that(_workflow.version, is_not(none()))
    assert_that(_workflow.createdAt, is_not(none()))
    assert_that(_workflow.updatedAt, is_not(none()))


@pytest.mark.vendor
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_get_workflow_aliases(
    vendor_workflow_utils, integration, vendor_type, credential_type, credentials
):
    """Test GET /v1/vendors/{vendor}/workflows/{workflow_id}/aliases endpoint."""
    _integration = integration(credential_type, credentials)

    setting = vendor_workflow_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    workflows_response = vendor_workflow_utils.get_workflows(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )
    assert_that(workflows_response.data, is_not(empty()))

    first_workflow = vendor_workflow_utils.get_prepared_workflow(
        workflows_response.data
    )

    aliases_response = vendor_workflow_utils.get_workflow_aliases(
        vendor=vendor_type,
        workflow_id=first_workflow.id,
        setting_id=setting.setting_id,
    )

    assert_that(aliases_response, instance_of(VendorWorkflowAliasesResponse))
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
def test_install_workflows(
    vendor_workflow_utils, integration, vendor_type, credential_type, credentials
):
    """Test POST /v1/vendors/{vendor}/workflows endpoint."""
    _integration = integration(credential_type, credentials)

    setting = vendor_workflow_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    result = vendor_workflow_utils.find_first_available_workflow(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )
    assert_that(result, is_not(none()))

    _workflow, alias_id = result

    install_request = VendorWorkflowInstallRequest(
        id=_workflow.id,
        flowAliasId=alias_id,
        setting_id=setting.setting_id,
    )

    install_response = vendor_workflow_utils.install_workflows(
        vendor=vendor_type,
        workflows=[install_request],
    )

    assert_that(install_response, instance_of(VendorWorkflowInstallResponse))
    assert_that(install_response.summary, is_not(empty()))
    assert_that(install_response.summary, has_length(1))

    installed = install_response.summary[0]
    assert_that(installed.flowId, is_(_workflow.id))
    assert_that(installed.flowAliasId, is_(alias_id))
    assert_that(installed.aiRunId, is_not(none()))


@pytest.mark.vendor
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_uninstall_workflow(
    vendor_workflow_utils, integration, vendor_type, credential_type, credentials
):
    """Test DELETE /v1/vendors/{vendor}/workflows/{ai_run_id} endpoint."""
    _integration = integration(credential_type, credentials)

    setting = vendor_workflow_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    codemie_id = vendor_workflow_utils.install_first_available_workflow(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )
    assert_that(codemie_id, is_not(none()))

    uninstall_response = vendor_workflow_utils.uninstall_workflow(
        vendor=vendor_type,
        codemie_id=codemie_id,
    )

    assert_that(uninstall_response, instance_of(VendorWorkflowUninstallResponse))
    assert_that(uninstall_response.success, is_(True))


@pytest.mark.vendor
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_get_workflow_settings_pagination(
    vendor_workflow_utils, integration, vendor_type, credential_type, credentials
):
    """Test pagination functionality for get_workflow_settings endpoint."""

    for _ in range(11):
        integration(credential_type, credentials, integration_alias=get_random_name())

    first_page = vendor_workflow_utils.get_workflow_settings(
        vendor=vendor_type,
        page=0,
        per_page=2,
    )

    assert_that(first_page.pagination.page, is_(0))
    assert_that(first_page.pagination.per_page, is_(2))
    assert_that(first_page.pagination.total, greater_than(0))

    if first_page.pagination.pages > 1:
        second_page = vendor_workflow_utils.get_workflow_settings(
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
def test_get_workflows_pagination(
    vendor_workflow_utils, integration, vendor_type, credential_type, credentials
):
    """Test pagination functionality for get_workflows endpoint using next_token."""
    _integration = integration(credential_type, credentials)

    setting = vendor_workflow_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    first_page = vendor_workflow_utils.get_workflows(
        vendor=vendor_type,
        setting_id=setting.setting_id,
        per_page=2,
    )

    assert_that(first_page.data, is_not(empty()))

    if first_page.pagination.next_token:
        second_page = vendor_workflow_utils.get_workflows(
            vendor=vendor_type,
            setting_id=setting.setting_id,
            per_page=2,
            next_token=first_page.pagination.next_token,
        )
        assert_that(second_page.data, is_not(empty()))
        first_page_ids = {w.id for w in first_page.data}
        second_page_ids = {w.id for w in second_page.data}
        assert_that(first_page_ids.intersection(second_page_ids), is_(set()))
