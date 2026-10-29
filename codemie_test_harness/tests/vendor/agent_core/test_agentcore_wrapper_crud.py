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

"""E2E tests for AgentCore wrapper CRUD."""

import uuid

import pytest
from hamcrest import assert_that, is_not, none, is_, instance_of, equal_to
from pydantic import ValidationError
from requests import HTTPError

from codemie_sdk.models.vendor_runtime import (
    VendorRuntimeInstallRequest,
    VendorRuntimeInstallSummary,
    VendorRuntimeUninstallResponse,
)
from codemie_test_harness.tests.test_data.vendor_endpoint_test_data import (
    vendor_endpoint_test_data,
    NON_STREAMING_CONFIG,
    STREAMING_CONFIG,
    EXTRA_PAYLOAD_CONFIG,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.vendor.agent_core.helpers import (
    get_prepared_env as _get_prepared_env,
)


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_install_ready_endpoint_returns_ai_run_id(
    vendor_runtime_utils,
    install_endpoint,
    integration,
    vendor_type,
    credential_type,
    credentials,
):
    """install returns valid UUID aiRunId matching runtime and endpoint."""
    setting, runtime, endpoints_response = _get_prepared_env(
        vendor_runtime_utils, integration, vendor_type, credential_type, credentials
    )
    unimported = vendor_runtime_utils.find_first_unimported_endpoint(
        endpoints_response.data
    )
    assert_that(unimported, is_not(none()))

    summary = install_endpoint(
        vendor_type,
        runtime_id=runtime.id,
        endpoint_name=unimported.name,
        setting_id=setting.setting_id,
        name=get_random_name(),
        description="Happy path install test",
        **NON_STREAMING_CONFIG,
    )

    assert_that(summary, instance_of(VendorRuntimeInstallSummary))
    assert_that(summary.aiRunId, is_not(none()))
    uuid.UUID(summary.aiRunId)  # raises ValueError if not a valid UUID
    assert_that(summary.runtimeId, is_(runtime.id))
    assert_that(summary.endpointName, is_(unimported.name))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_install_nonexistent_endpoint_returns_error(
    vendor_runtime_utils, integration, vendor_type, credential_type, credentials
):
    """bogus endpoint name → 404, no assistant created."""
    setting, runtime, _ = _get_prepared_env(
        vendor_runtime_utils, integration, vendor_type, credential_type, credentials
    )
    with pytest.raises((HTTPError, ValidationError)) as exc_info:
        vendor_runtime_utils.install_endpoint_with_config(
            vendor=vendor_type,
            runtime_id=runtime.id,
            endpoint_name=f"nonexistent-ep-{uuid.uuid4()}",
            setting_id=setting.setting_id,
            **NON_STREAMING_CONFIG,
        )
    assert_that(
        exc_info.type,
        equal_to(HTTPError),
        "Backend returned HTTP 200 instead of 404 for a nonexistent endpoint — "
        "response body failed schema validation (aiRunId missing). Backend defect.",
    )
    assert_that(exc_info.value.response.status_code, is_(404))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_install_with_non_streaming_config_stored(
    vendor_runtime_utils,
    install_endpoint,
    integration,
    vendor_type,
    credential_type,
    credentials,
):
    """non-streaming structured config accepted and aiRunId returned."""
    setting, runtime, endpoints_response = _get_prepared_env(
        vendor_runtime_utils, integration, vendor_type, credential_type, credentials
    )
    unimported = vendor_runtime_utils.find_first_unimported_endpoint(
        endpoints_response.data
    )
    assert_that(unimported, is_not(none()))

    summary = install_endpoint(
        vendor_type,
        runtime_id=runtime.id,
        endpoint_name=unimported.name,
        setting_id=setting.setting_id,
        name=get_random_name(),
        description="Non-streaming config validation test",
        message_path="inputText",
        streaming=False,
        text_path="output.text",
    )
    assert_that(summary.aiRunId, is_not(none()))
    uuid.UUID(summary.aiRunId)


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_install_with_streaming_config_stored(
    vendor_runtime_utils,
    install_endpoint,
    integration,
    vendor_type,
    credential_type,
    credentials,
):
    """streaming structured config accepted and aiRunId returned."""
    setting, runtime, endpoints_response = _get_prepared_env(
        vendor_runtime_utils, integration, vendor_type, credential_type, credentials
    )
    unimported = vendor_runtime_utils.find_first_unimported_endpoint(
        endpoints_response.data
    )
    assert_that(unimported, is_not(none()))

    summary = install_endpoint(
        vendor_type,
        runtime_id=runtime.id,
        endpoint_name=unimported.name,
        setting_id=setting.setting_id,
        name=get_random_name(),
        description="Streaming config validation test",
        **STREAMING_CONFIG,
    )
    assert_that(summary.aiRunId, is_not(none()))
    uuid.UUID(summary.aiRunId)


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_install_with_extra_payload_accepted(
    vendor_runtime_utils,
    install_endpoint,
    integration,
    vendor_type,
    credential_type,
    credentials,
):
    """extra_payload in config accepted, aiRunId returned."""
    setting, runtime, endpoints_response = _get_prepared_env(
        vendor_runtime_utils, integration, vendor_type, credential_type, credentials
    )
    unimported = vendor_runtime_utils.find_first_unimported_endpoint(
        endpoints_response.data
    )
    assert_that(unimported, is_not(none()))

    summary = install_endpoint(
        vendor_type,
        runtime_id=runtime.id,
        endpoint_name=unimported.name,
        setting_id=setting.setting_id,
        name=get_random_name(),
        description="Extra payload config test",
        **EXTRA_PAYLOAD_CONFIG,
    )
    assert_that(summary.aiRunId, is_not(none()))
    uuid.UUID(summary.aiRunId)


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_install_with_invalid_configuration_json_returns_error(
    vendor_runtime_utils, integration, vendor_type, credential_type, credentials
):
    """malformed configuration_json string returns 400 from backend."""
    setting, runtime, endpoints_response = _get_prepared_env(
        vendor_runtime_utils, integration, vendor_type, credential_type, credentials
    )
    prepared = vendor_runtime_utils.get_prepared_endpoint(endpoints_response.data)
    assert_that(prepared, is_not(none()))

    # Bypass install_endpoint_with_config — pass malformed JSON directly via SDK model
    # (Pydantic validates model fields but does not inspect the string contents of configuration_json)
    invalid_request = VendorRuntimeInstallRequest(
        id=runtime.id,
        agentcoreRuntimeEndpointName=prepared.name,
        setting_id=setting.setting_id,
        configuration_json="not-valid-json{",
    )
    with pytest.raises((HTTPError, ValidationError)) as exc_info:
        vendor_runtime_utils.vendor_runtime_service.install_endpoints(
            vendor=vendor_type, endpoints=[invalid_request]
        )
    assert_that(
        exc_info.type,
        equal_to(HTTPError),
        "Backend returned HTTP 200 instead of 400 for malformed configuration_json — "
        "response body failed schema validation (aiRunId missing). Backend defect.",
    )
    assert_that(exc_info.value.response.status_code, is_(400))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_reinstall_same_endpoint_returns_same_ai_run_id(
    vendor_runtime_utils,
    install_endpoint,
    integration,
    vendor_type,
    credential_type,
    credentials,
):
    """reinstalling same endpoint returns same aiRunId, no duplicate."""
    setting, runtime, endpoints_response = _get_prepared_env(
        vendor_runtime_utils, integration, vendor_type, credential_type, credentials
    )
    unimported = vendor_runtime_utils.find_first_unimported_endpoint(
        endpoints_response.data
    )
    assert_that(unimported, is_not(none()))

    first = install_endpoint(
        vendor_type,
        runtime_id=runtime.id,
        endpoint_name=unimported.name,
        setting_id=setting.setting_id,
        name=get_random_name(),
        description="Idempotency test",
        **NON_STREAMING_CONFIG,
    )

    second = vendor_runtime_utils.install_endpoint_with_config(
        vendor=vendor_type,
        runtime_id=runtime.id,
        endpoint_name=unimported.name,
        setting_id=setting.setting_id,
        name=get_random_name(),
        description="Idempotency test reinstall",
        **NON_STREAMING_CONFIG,
    )

    assert_that(second.aiRunId, is_(first.aiRunId))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_reinstall_updates_configuration(
    vendor_runtime_utils,
    install_endpoint,
    integration,
    vendor_type,
    credential_type,
    credentials,
):
    """reinstall with different message_path updates config, keeps same aiRunId."""
    setting, runtime, endpoints_response = _get_prepared_env(
        vendor_runtime_utils, integration, vendor_type, credential_type, credentials
    )
    unimported = vendor_runtime_utils.find_first_unimported_endpoint(
        endpoints_response.data
    )
    assert_that(unimported, is_not(none()))

    first = install_endpoint(
        vendor_type,
        runtime_id=runtime.id,
        endpoint_name=unimported.name,
        setting_id=setting.setting_id,
        name=get_random_name(),
        description="Config update test",
        message_path="message",
        streaming=False,
        text_path="text",
    )

    second = vendor_runtime_utils.install_endpoint_with_config(
        vendor=vendor_type,
        runtime_id=runtime.id,
        endpoint_name=unimported.name,
        setting_id=setting.setting_id,
        name=get_random_name(),
        description="Config update test",
        message_path="inputText",
        streaming=False,
        text_path="text",
    )

    assert_that(second.aiRunId, is_(first.aiRunId))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_reinstall_updates_name_and_description(
    vendor_runtime_utils,
    assistant_utils,
    install_endpoint,
    integration,
    vendor_type,
    credential_type,
    credentials,
):
    """reinstall with new name/description updates assistant, keeps same aiRunId."""
    setting, runtime, endpoints_response = _get_prepared_env(
        vendor_runtime_utils, integration, vendor_type, credential_type, credentials
    )
    unimported = vendor_runtime_utils.find_first_unimported_endpoint(
        endpoints_response.data
    )
    assert_that(unimported, is_not(none()))

    first = install_endpoint(
        vendor_type,
        runtime_id=runtime.id,
        endpoint_name=unimported.name,
        setting_id=setting.setting_id,
        name=get_random_name(),
        description="Original description",
        **NON_STREAMING_CONFIG,
    )

    updated_name = get_random_name()
    second = vendor_runtime_utils.install_endpoint_with_config(
        vendor=vendor_type,
        runtime_id=runtime.id,
        endpoint_name=unimported.name,
        setting_id=setting.setting_id,
        name=updated_name,
        description="Updated description",
        **NON_STREAMING_CONFIG,
    )

    assert_that(second.aiRunId, is_(first.aiRunId))

    assistant = assistant_utils.get_assistant_by_id(first.aiRunId)
    assert_that(assistant.name, is_(updated_name))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_uninstall_removes_assistant(
    vendor_runtime_utils,
    assistant_utils,
    install_endpoint,
    integration,
    vendor_type,
    credential_type,
    credentials,
):
    """uninstall returns success and assistant no longer accessible."""
    setting, runtime, endpoints_response = _get_prepared_env(
        vendor_runtime_utils, integration, vendor_type, credential_type, credentials
    )
    unimported = vendor_runtime_utils.find_first_unimported_endpoint(
        endpoints_response.data
    )
    assert_that(unimported, is_not(none()))

    summary = install_endpoint(
        vendor_type,
        runtime_id=runtime.id,
        endpoint_name=unimported.name,
        setting_id=setting.setting_id,
        name=get_random_name(),
        description="Uninstall test",
        **NON_STREAMING_CONFIG,
    )

    uninstall_response = vendor_runtime_utils.uninstall_endpoint(
        vendor=vendor_type, ai_run_id=summary.aiRunId
    )

    assert_that(uninstall_response, instance_of(VendorRuntimeUninstallResponse))
    assert_that(uninstall_response.success, is_(True))

    with pytest.raises(HTTPError) as exc_info:
        assistant_utils.get_assistant_by_id(summary.aiRunId)
    assert_that(exc_info.value.response.status_code, is_(404))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_uninstall_endpoint_returns_to_importable_state(
    vendor_runtime_utils,
    install_endpoint,
    integration,
    vendor_type,
    credential_type,
    credentials,
):
    """after uninstall the endpoint shows aiRunId=None in endpoint list."""
    setting, runtime, endpoints_response = _get_prepared_env(
        vendor_runtime_utils, integration, vendor_type, credential_type, credentials
    )
    unimported = vendor_runtime_utils.find_first_unimported_endpoint(
        endpoints_response.data
    )
    assert_that(unimported, is_not(none()))

    summary = install_endpoint(
        vendor_type,
        runtime_id=runtime.id,
        endpoint_name=unimported.name,
        setting_id=setting.setting_id,
        name=get_random_name(),
        description="Post-uninstall importable state test",
        **NON_STREAMING_CONFIG,
    )
    vendor_runtime_utils.uninstall_endpoint(
        vendor=vendor_type, ai_run_id=summary.aiRunId
    )

    refreshed = vendor_runtime_utils.get_endpoints(
        vendor=vendor_type, runtime_id=runtime.id, setting_id=setting.setting_id
    )
    target = next((e for e in refreshed.data if e.name == unimported.name), None)
    assert_that(target, is_not(none()))
    assert_that(target.aiRunId, is_(none()))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_uninstall_unauthorized_returns_error(
    vendor_runtime_utils, integration, vendor_type, credential_type, credentials
):
    """DELETE with bogus aiRunId returns 404."""
    integration(credential_type, credentials)
    with pytest.raises(HTTPError) as exc_info:
        vendor_runtime_utils.uninstall_endpoint(
            vendor=vendor_type, ai_run_id=str(uuid.uuid4())
        )
    assert_that(exc_info.value.response.status_code, equal_to(404))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_endpoint_accessible_via_api_after_uninstall(
    vendor_runtime_utils,
    install_endpoint,
    integration,
    vendor_type,
    credential_type,
    credentials,
):
    """AWS endpoint detail still resolves after CodeMie uninstall (AWS untouched)."""
    setting, runtime, endpoints_response = _get_prepared_env(
        vendor_runtime_utils, integration, vendor_type, credential_type, credentials
    )
    unimported = vendor_runtime_utils.find_first_unimported_endpoint(
        endpoints_response.data
    )
    assert_that(unimported, is_not(none()))

    summary = install_endpoint(
        vendor_type,
        runtime_id=runtime.id,
        endpoint_name=unimported.name,
        setting_id=setting.setting_id,
        name=get_random_name(),
        description="AWS side-effect proxy test",
        **NON_STREAMING_CONFIG,
    )
    vendor_runtime_utils.uninstall_endpoint(
        vendor=vendor_type, ai_run_id=summary.aiRunId
    )

    endpoint_detail = vendor_runtime_utils.get_endpoint(
        vendor=vendor_type,
        runtime_id=runtime.id,
        endpoint_name=unimported.name,
        setting_id=setting.setting_id,
    )
    assert_that(endpoint_detail, is_not(none()))
    assert_that(endpoint_detail.name, is_(unimported.name))
