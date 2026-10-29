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

import uuid

import pytest
from hamcrest import (
    assert_that,
    is_not,
    none,
    empty,
    greater_than,
    instance_of,
    is_,
    is_in,
)
from requests import HTTPError

from codemie_sdk.models.vendor_runtime import (
    VendorRuntimeSettingsResponse,
    VendorRuntimesResponse,
    VendorRuntime,
    VendorRuntimeStatus,
    VendorRuntimeEndpointsResponse,
    VendorRuntimeEndpointStatus,
    VendorRuntimeEndpointDetail,
    VendorRuntimeInstallSummary,
    VendorRuntimeUninstallResponse,
)
from codemie_test_harness.tests.test_data.vendor_endpoint_test_data import (
    vendor_endpoint_test_data,
    NON_STREAMING_CONFIG,
    RUNTIME_CHAT_PROMPT,
    RUNTIME_CHAT_EXPECTED,
)


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_get_runtime_settings(
    vendor_runtime_utils, integration, vendor_type, credential_type, credentials
):
    """Test GET /v1/vendors/{vendor}/runtimes/settings endpoint."""
    _integration = integration(credential_type, credentials)

    settings_response = vendor_runtime_utils.get_runtime_settings(vendor=vendor_type)

    assert_that(settings_response, instance_of(VendorRuntimeSettingsResponse))
    assert_that(settings_response.data, is_not(none()))
    assert_that(settings_response.pagination, is_not(none()))
    assert_that(settings_response.data, is_not(empty()))
    assert_that(settings_response.pagination.total, greater_than(0))

    created_setting = vendor_runtime_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(created_setting, is_not(none()))
    assert_that(created_setting.setting_id, is_not(none()))
    assert_that(created_setting.setting_name, is_not(none()))
    assert_that(created_setting.project, is_not(none()))
    assert_that(created_setting.entities, instance_of(list))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_get_runtimes(
    vendor_runtime_utils, integration, vendor_type, credential_type, credentials
):
    """Test GET /v1/vendors/{vendor}/runtimes — AC1: canonical fields and status mapping."""
    _integration = integration(credential_type, credentials)

    setting = vendor_runtime_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    runtimes_response = vendor_runtime_utils.get_runtimes(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )

    assert_that(runtimes_response, instance_of(VendorRuntimesResponse))
    assert_that(runtimes_response.data, is_not(none()))
    assert_that(runtimes_response.pagination, is_not(none()))
    assert_that(runtimes_response.data, is_not(empty()))

    _runtime = vendor_runtime_utils.get_prepared_runtime(runtimes_response.data)

    assert_that(_runtime.id, is_not(none()))
    assert_that(_runtime.name, is_not(none()))
    assert_that(_runtime.status, is_(VendorRuntimeStatus.PREPARED))
    assert_that(_runtime.description, is_not(none()))
    assert_that(_runtime.version, is_not(none()))
    assert_that(_runtime.updatedAt, is_not(none()))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_get_runtime(
    vendor_runtime_utils, integration, vendor_type, credential_type, credentials
):
    """Test GET /v1/vendors/{vendor}/runtimes/{runtime_id} — canonical fields match list response."""
    _integration = integration(credential_type, credentials)

    setting = vendor_runtime_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    runtimes_response = vendor_runtime_utils.get_runtimes(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )
    assert_that(runtimes_response.data, is_not(empty()))

    list_runtime = vendor_runtime_utils.get_prepared_runtime(runtimes_response.data)

    _runtime = vendor_runtime_utils.get_runtime(
        vendor=vendor_type,
        runtime_id=list_runtime.id,
        setting_id=setting.setting_id,
    )

    assert_that(_runtime, instance_of(VendorRuntime))
    assert_that(_runtime.id, is_(list_runtime.id))
    assert_that(_runtime.name, is_not(none()))
    assert_that(_runtime.status, is_(VendorRuntimeStatus.PREPARED))
    assert_that(_runtime.description, is_not(none()))
    assert_that(_runtime.version, is_not(none()))
    assert_that(_runtime.updatedAt, is_not(none()))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_get_runtimes_pagination_next_token(
    vendor_runtime_utils, integration, vendor_type, credential_type, credentials
):
    """Test next_token pagination for GET /v1/vendors/{vendor}/runtimes — AC2: no dropped/duplicated results."""
    _integration = integration(credential_type, credentials)

    setting = vendor_runtime_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    first_page = vendor_runtime_utils.get_runtimes(
        vendor=vendor_type,
        setting_id=setting.setting_id,
        per_page=2,
    )
    assert_that(first_page.data, is_not(empty()))

    if not first_page.pagination.next_token:
        pytest.skip("Only one page of runtimes available — next_token not present")

    second_page = vendor_runtime_utils.get_runtimes(
        vendor=vendor_type,
        setting_id=setting.setting_id,
        per_page=2,
        next_token=first_page.pagination.next_token,
    )
    assert_that(second_page.data, is_not(empty()))
    first_page_ids = {r.id for r in first_page.data}
    second_page_ids = {r.id for r in second_page.data}
    assert_that(first_page_ids.intersection(second_page_ids), is_(set()))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_get_runtime_settings_pagination(
    vendor_runtime_utils, integration, vendor_type, credential_type, credentials
):
    """Test offset pagination for GET /v1/vendors/{vendor}/runtimes/settings — page/per_page/total consistency."""
    _integration = integration(credential_type, credentials)

    first_page = vendor_runtime_utils.get_runtime_settings(
        vendor=vendor_type,
        page=0,
        per_page=2,
    )
    assert_that(first_page.pagination.page, is_(0))
    assert_that(first_page.pagination.per_page, is_(2))
    assert_that(first_page.pagination.total, greater_than(0))

    if first_page.pagination.pages <= 1:
        pytest.skip("Only one page of settings available — second page not testable")

    second_page = vendor_runtime_utils.get_runtime_settings(
        vendor=vendor_type,
        page=1,
        per_page=2,
    )
    assert_that(second_page.pagination.page, is_(1))
    assert_that(second_page.data, is_not(empty()))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_get_runtime_not_found(
    vendor_runtime_utils, integration, vendor_type, credential_type, credentials
):
    """Test GET /v1/vendors/{vendor}/runtimes/{runtime_id} — AC2: 403 for non-existent runtime_id."""
    _integration = integration(credential_type, credentials)

    setting = vendor_runtime_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    with pytest.raises(HTTPError) as exc_info:
        vendor_runtime_utils.get_runtime(
            vendor=vendor_type,
            runtime_id=str(uuid.uuid4()),
            setting_id=setting.setting_id,
        )

    assert_that(exc_info.value.response.status_code, is_(403))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_get_runtimes_unauthorized_integration(
    vendor_runtime_utils, integration, vendor_type, credential_type, credentials
):
    """Test that a non-existent/unauthorized integration_id is rejected before any AWS call — AC4."""
    with pytest.raises(HTTPError) as exc_info:
        vendor_runtime_utils.get_runtimes(
            vendor=vendor_type,
            setting_id=str(uuid.uuid4()),
        )

    assert_that(exc_info.value.response.status_code, is_(404))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_get_runtime_endpoints(
    vendor_runtime_utils, integration, vendor_type, credential_type, credentials
):
    """Test GET /v1/vendors/{vendor}/runtimes/{runtime_id}/endpoints — AC1: canonical fields."""
    _integration = integration(credential_type, credentials)

    setting = vendor_runtime_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    runtimes_response = vendor_runtime_utils.get_runtimes(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )
    _runtime = vendor_runtime_utils.get_prepared_runtime(runtimes_response.data)
    assert_that(_runtime, is_not(none()))

    endpoints_response = vendor_runtime_utils.get_endpoints(
        vendor=vendor_type,
        runtime_id=_runtime.id,
        setting_id=setting.setting_id,
    )

    assert_that(endpoints_response, instance_of(VendorRuntimeEndpointsResponse))
    assert_that(endpoints_response.data, is_not(none()))
    assert_that(endpoints_response.data, is_not(empty()))
    assert_that(endpoints_response.pagination, is_not(none()))

    endpoint = vendor_runtime_utils.get_prepared_endpoint(endpoints_response.data)
    assert_that(endpoint.id, is_not(none()))
    assert_that(endpoint.name, is_not(none()))
    assert_that(endpoint.status, instance_of(VendorRuntimeEndpointStatus))
    assert_that(endpoint.status, is_(VendorRuntimeEndpointStatus.PREPARED))
    assert_that(endpoint.createdAt, is_not(none()))
    assert_that(endpoint.updatedAt, is_not(none()))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_get_runtime_endpoints_pagination_next_token(
    vendor_runtime_utils, integration, vendor_type, credential_type, credentials
):
    """Test next_token pagination for GET endpoints — AC2: no dropped/duplicated results."""
    _integration = integration(credential_type, credentials)

    setting = vendor_runtime_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    runtimes_response = vendor_runtime_utils.get_runtimes(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )
    _runtime = vendor_runtime_utils.get_prepared_runtime(runtimes_response.data)
    assert_that(_runtime, is_not(none()))

    first_page = vendor_runtime_utils.get_endpoints(
        vendor=vendor_type,
        runtime_id=_runtime.id,
        setting_id=setting.setting_id,
        per_page=2,
    )
    assert_that(first_page.data, is_not(empty()))

    if not first_page.pagination.next_token:
        pytest.skip("Only one page of endpoints available — next_token not present")

    second_page = vendor_runtime_utils.get_endpoints(
        vendor=vendor_type,
        runtime_id=_runtime.id,
        setting_id=setting.setting_id,
        per_page=2,
        next_token=first_page.pagination.next_token,
    )
    assert_that(second_page.data, is_not(empty()))
    first_ids = {e.id for e in first_page.data}
    second_ids = {e.id for e in second_page.data}
    assert_that(first_ids.intersection(second_ids), is_(set()))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_get_runtime_endpoint_imported_state(
    vendor_runtime_utils, integration, vendor_type, credential_type, credentials
):
    """Test that already-imported endpoints expose aiRunId — AC3."""
    _integration = integration(credential_type, credentials)

    setting = vendor_runtime_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    runtimes_response = vendor_runtime_utils.get_runtimes(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )
    _runtime = vendor_runtime_utils.get_prepared_runtime(runtimes_response.data)
    assert_that(_runtime, is_not(none()))

    endpoints_response = vendor_runtime_utils.get_endpoints(
        vendor=vendor_type,
        runtime_id=_runtime.id,
        setting_id=setting.setting_id,
    )

    imported = vendor_runtime_utils.get_imported_endpoint(endpoints_response.data)
    if imported is None:
        pytest.skip(
            "No imported endpoints found in this runtime — skipping AC3 assertion"
        )

    assert_that(imported.aiRunId, is_not(none()))
    assert_that(imported.aiRunId, instance_of(str))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_get_runtime_endpoints_unauthorized_setting(
    vendor_runtime_utils, integration, vendor_type, credential_type, credentials
):
    """Test that a bogus setting_id is rejected before any AWS call."""
    with pytest.raises(HTTPError) as exc_info:
        vendor_runtime_utils.get_endpoints(
            vendor=vendor_type,
            runtime_id=str(uuid.uuid4()),
            setting_id=str(uuid.uuid4()),
        )

    assert_that(exc_info.value.response.status_code, is_(404))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_get_runtime_endpoint_detail(
    vendor_runtime_utils, integration, vendor_type, credential_type, credentials
):
    """Test GET /v1/vendors/{vendor}/runtimes/{runtime_id}/endpoints/{name} — AC1: detail fields."""
    _integration = integration(credential_type, credentials)

    setting = vendor_runtime_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    runtimes_response = vendor_runtime_utils.get_runtimes(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )
    _runtime = vendor_runtime_utils.get_prepared_runtime(runtimes_response.data)
    assert_that(_runtime, is_not(none()))

    endpoints_response = vendor_runtime_utils.get_endpoints(
        vendor=vendor_type,
        runtime_id=_runtime.id,
        setting_id=setting.setting_id,
    )
    assert_that(endpoints_response.data, is_not(empty()))

    list_endpoint = vendor_runtime_utils.get_prepared_endpoint(endpoints_response.data)

    endpoint_detail = vendor_runtime_utils.get_endpoint(
        vendor=vendor_type,
        runtime_id=_runtime.id,
        endpoint_name=list_endpoint.name,
        setting_id=setting.setting_id,
    )

    assert_that(endpoint_detail, instance_of(VendorRuntimeEndpointDetail))
    assert_that(endpoint_detail.id, is_(list_endpoint.id))
    assert_that(endpoint_detail.name, is_(list_endpoint.name))
    assert_that(endpoint_detail.status, instance_of(VendorRuntimeEndpointStatus))
    assert_that(endpoint_detail.createdAt, is_not(none()))
    assert_that(endpoint_detail.updatedAt, is_not(none()))
    assert_that(endpoint_detail.arn, is_not(none()))
    assert_that(endpoint_detail.arn, instance_of(str))
    assert_that(endpoint_detail.runtimeArn, is_not(none()))
    assert_that(endpoint_detail.runtimeArn, instance_of(str))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_get_runtime_endpoint_detail_not_found(
    vendor_runtime_utils, integration, vendor_type, credential_type, credentials
):
    """Test GET .../endpoints/{name} with a non-existent name — AC2: no silent empty success."""
    _integration = integration(credential_type, credentials)

    setting = vendor_runtime_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    runtimes_response = vendor_runtime_utils.get_runtimes(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )
    _runtime = vendor_runtime_utils.get_prepared_runtime(runtimes_response.data)
    assert_that(_runtime, is_not(none()))

    with pytest.raises(HTTPError) as exc_info:
        vendor_runtime_utils.get_endpoint(
            vendor=vendor_type,
            runtime_id=_runtime.id,
            endpoint_name=f"nonexistent-endpoint-{uuid.uuid4()}",
            setting_id=setting.setting_id,
        )

    assert_that(exc_info.value.response.status_code, is_in([404, 403]))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_get_runtime_endpoint_detail_unauthorized_setting(
    vendor_runtime_utils, integration, vendor_type, credential_type, credentials
):
    """Test GET .../endpoints/{name} with a bogus setting_id — AC2: access failure is actionable."""
    _integration = integration(credential_type, credentials)

    setting = vendor_runtime_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    runtimes_response = vendor_runtime_utils.get_runtimes(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )
    _runtime = vendor_runtime_utils.get_prepared_runtime(runtimes_response.data)
    assert_that(_runtime, is_not(none()))

    endpoints_response = vendor_runtime_utils.get_endpoints(
        vendor=vendor_type,
        runtime_id=_runtime.id,
        setting_id=setting.setting_id,
    )
    list_endpoint = vendor_runtime_utils.get_prepared_endpoint(endpoints_response.data)

    with pytest.raises(HTTPError) as exc_info:
        vendor_runtime_utils.get_endpoint(
            vendor=vendor_type,
            runtime_id=_runtime.id,
            endpoint_name=list_endpoint.name,
            setting_id=str(uuid.uuid4()),
        )

    assert_that(exc_info.value.response.status_code, is_(404))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_get_runtime_endpoint_detail_failure_reason(
    vendor_runtime_utils, integration, vendor_type, credential_type, credentials
):
    """Test that a NOT_PREPARED endpoint exposes failureReason in detail — AC1 detail fields."""
    _integration = integration(credential_type, credentials)

    setting = vendor_runtime_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    runtimes_response = vendor_runtime_utils.get_runtimes(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )
    _runtime = vendor_runtime_utils.get_prepared_runtime(runtimes_response.data)
    assert_that(_runtime, is_not(none()))

    endpoints_response = vendor_runtime_utils.get_endpoints(
        vendor=vendor_type,
        runtime_id=_runtime.id,
        setting_id=setting.setting_id,
    )

    not_prepared = next(
        (
            e
            for e in endpoints_response.data
            if e.status == VendorRuntimeEndpointStatus.NOT_PREPARED
        ),
        None,
    )
    if not_prepared is None:
        pytest.skip(
            "No NOT_PREPARED endpoint in this environment — skipping failureReason assertion"
        )

    endpoint_detail = vendor_runtime_utils.get_endpoint(
        vendor=vendor_type,
        runtime_id=_runtime.id,
        endpoint_name=not_prepared.name,
        setting_id=setting.setting_id,
    )

    assert_that(endpoint_detail.status, is_(VendorRuntimeEndpointStatus.NOT_PREPARED))
    assert_that(endpoint_detail.failureReason, is_not(none()))
    assert_that(endpoint_detail.failureReason, instance_of(str))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_install_and_uninstall_runtime_endpoint(
    vendor_runtime_utils, integration, vendor_type, credential_type, credentials
):
    """Test POST and DELETE /v1/vendors/{vendor}/agentcore-runtimes — install then uninstall."""
    _integration = integration(credential_type, credentials)

    setting = vendor_runtime_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    runtimes_response = vendor_runtime_utils.get_runtimes(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )
    _runtime = vendor_runtime_utils.get_prepared_runtime(runtimes_response.data)
    assert_that(_runtime, is_not(none()))

    endpoints_response = vendor_runtime_utils.get_endpoints(
        vendor=vendor_type,
        runtime_id=_runtime.id,
        setting_id=setting.setting_id,
    )
    unimported = vendor_runtime_utils.find_first_unimported_endpoint(
        endpoints_response.data
    )
    if unimported is None:
        pytest.skip("No unimported PREPARED endpoint available — skipping install test")

    install_summary = vendor_runtime_utils.install_endpoint_with_config(
        vendor=vendor_type,
        runtime_id=_runtime.id,
        endpoint_name=unimported.name,
        setting_id=setting.setting_id,
        **NON_STREAMING_CONFIG,
    )

    assert_that(install_summary, instance_of(VendorRuntimeInstallSummary))
    assert_that(install_summary.aiRunId, is_not(none()))
    assert_that(install_summary.aiRunId, instance_of(str))
    assert_that(install_summary.runtimeId, is_(_runtime.id))
    assert_that(install_summary.endpointName, is_(unimported.name))

    uninstall_response = vendor_runtime_utils.uninstall_endpoint(
        vendor=vendor_type,
        ai_run_id=install_summary.aiRunId,
    )

    assert_that(uninstall_response, instance_of(VendorRuntimeUninstallResponse))
    assert_that(uninstall_response.success, is_(True))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_chat_with_installed_runtime_endpoint(
    vendor_runtime_utils,
    integration,
    assistant_utils,
    conversation_utils,
    similarity_check,
    vendor_type,
    credential_type,
    credentials,
):
    """Test that an installed runtime endpoint is usable as a CodeMie assistant."""
    _integration = integration(credential_type, credentials)

    setting = vendor_runtime_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))

    runtimes_response = vendor_runtime_utils.get_runtimes(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )
    _runtime = vendor_runtime_utils.get_prepared_runtime(runtimes_response.data)
    assert_that(_runtime, is_not(none()))

    endpoints_response = vendor_runtime_utils.get_endpoints(
        vendor=vendor_type,
        runtime_id=_runtime.id,
        setting_id=setting.setting_id,
    )
    unimported = vendor_runtime_utils.find_first_unimported_endpoint(
        endpoints_response.data
    )
    if unimported is None:
        pytest.skip("No unimported PREPARED endpoint available — skipping chat test")

    install_summary = vendor_runtime_utils.install_endpoint_with_config(
        vendor=vendor_type,
        runtime_id=_runtime.id,
        endpoint_name=unimported.name,
        setting_id=setting.setting_id,
        **NON_STREAMING_CONFIG,
    )
    assert_that(install_summary.aiRunId, is_not(none()))

    conversation = conversation_utils.create_conversation(
        initial_assistant_id=install_summary.aiRunId,
    )
    conversation_id = conversation["id"]

    class _AssistantRef:
        def __init__(self, ai_run_id):
            self.id = ai_run_id

    response = assistant_utils.ask_assistant(
        assistant=_AssistantRef(install_summary.aiRunId),
        user_prompt=RUNTIME_CHAT_PROMPT,
        minimal_response=True,
        conversation_id=conversation_id,
    )

    similarity_check.check_similarity(response, RUNTIME_CHAT_EXPECTED)

    conversation_utils.delete_conversation(conversation_id)

    uninstall_response = vendor_runtime_utils.uninstall_endpoint(
        vendor=vendor_type,
        ai_run_id=install_summary.aiRunId,
    )
    assert_that(uninstall_response.success, is_(True))
