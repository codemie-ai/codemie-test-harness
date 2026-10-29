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

import pytest
from hamcrest import assert_that, is_not, none, is_

from codemie_test_harness.tests.test_data.vendor_workflow_test_data import (
    vendor_workflow_test_data,
)


@pytest.mark.vendor
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials,workflow_name,user_input,expected_response",
    vendor_workflow_test_data,
)
def test_vendor_workflow_installation_and_execution(
    vendor_workflow_utils,
    integration,
    workflow_utils,
    similarity_check,
    vendor_type,
    credential_type,
    credentials,
    workflow_name,
    user_input,
    expected_response,
):
    """Test vendor workflow installation and execution functionality."""
    _integration = integration(credential_type, credentials)

    setting = vendor_workflow_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))
    assert_that(setting.invalid or False, is_(False))

    codemie_id = vendor_workflow_utils.install_workflow_by_name(
        vendor=vendor_type,
        setting_id=setting.setting_id,
        workflow_name=workflow_name,
    )
    assert_that(codemie_id, is_not(none()))

    class WorkflowIdWrapper:
        def __init__(self, workflow_id):
            self.id = workflow_id

    workflow_wrapper = WorkflowIdWrapper(codemie_id)

    response = workflow_utils.execute_workflow_without_prompt_modification(
        workflow=workflow_wrapper.id,
        execution_name="bedrock_flow_1",
        user_input=user_input,
    )

    similarity_check.check_similarity(response, expected_response, similarity_rank=50)

    uninstall_response = vendor_workflow_utils.uninstall_workflow(
        vendor=vendor_type,
        codemie_id=codemie_id,
    )
    assert_that(uninstall_response.success, is_(True))
