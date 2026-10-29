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

"""Shared setup helpers for AgentCore vendor tests."""

from hamcrest import assert_that, is_not, none


def get_prepared_env(
    vendor_runtime_utils, integration, vendor_type, credential_type, credentials
):
    """Shared setup: returns (setting, runtime, endpoints_response)."""
    _integration = integration(credential_type, credentials)
    setting = vendor_runtime_utils.find_setting_for_integration(
        vendor=vendor_type, integration_id=_integration.id
    )
    assert_that(setting, is_not(none()))
    runtimes_response = vendor_runtime_utils.get_runtimes(
        vendor=vendor_type, setting_id=setting.setting_id
    )
    _runtime = vendor_runtime_utils.get_prepared_runtime(runtimes_response.data)
    assert_that(_runtime, is_not(none()))
    endpoints_response = vendor_runtime_utils.get_endpoints(
        vendor=vendor_type, runtime_id=_runtime.id, setting_id=setting.setting_id
    )
    return setting, _runtime, endpoints_response
