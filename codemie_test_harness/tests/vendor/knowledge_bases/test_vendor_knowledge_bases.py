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

"""Integration tests for vendor knowledge bases with CodeMie assistants."""

import pytest
from hamcrest import assert_that, is_not, none, is_

from codemie_test_harness.tests.test_data.vendor_knowledge_base_test_data import (
    vendor_knowledge_base_test_data,
    vendor_assistant_with_kb_test_data,
)


@pytest.mark.vendor
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials,prompt,expected_response",
    vendor_knowledge_base_test_data,
)
def test_codemie_assistant_with_vendor_knowledgebase(
    vendor_knowledge_base_utils,
    integration,
    assistant,
    assistant_utils,
    similarity_check,
    kb_context,
    client,
    vendor_type,
    credential_type,
    credentials,
    prompt,
    expected_response,
):
    """Test CodeMie assistant with vendor knowledge base integration."""
    _integration = integration(credential_type, credentials)

    setting = vendor_knowledge_base_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))
    assert_that(setting.invalid or False, is_(False))

    codemie_kb_id = vendor_knowledge_base_utils.install_first_available_knowledge_base(
        vendor=vendor_type,
        setting_id=setting.setting_id,
    )
    assert_that(codemie_kb_id, is_not(none()))

    datasource = client.datasources.get(codemie_kb_id)
    assert_that(datasource, is_not(none()))

    created_assistant = assistant(
        context=kb_context(datasource),
        system_prompt="You are a helpful assistant. Use the knowledge base to answer questions.",
    )

    response = assistant_utils.ask_assistant(
        assistant=created_assistant,
        user_prompt=prompt,
        minimal_response=True,
    )

    similarity_check.check_similarity(response, expected_response)

    uninstall_response = vendor_knowledge_base_utils.uninstall_knowledgebase(
        vendor=vendor_type,
        codemie_id=codemie_kb_id,
    )
    assert_that(uninstall_response.success, is_(True))


@pytest.mark.vendor
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials,assistant_name,prompt,expected_response",
    vendor_assistant_with_kb_test_data,
)
def test_vendor_assistant_with_knowledgebase(
    vendor_assistant_utils,
    integration,
    assistant_utils,
    similarity_check,
    vendor_type,
    credential_type,
    credentials,
    assistant_name,
    prompt,
    expected_response,
):
    """Test vendor assistant with knowledge base already attached."""
    _integration = integration(credential_type, credentials)

    setting = vendor_assistant_utils.find_setting_for_integration(
        vendor=vendor_type,
        integration_id=_integration.id,
    )
    assert_that(setting, is_not(none()))
    assert_that(setting.invalid or False, is_(False))

    codemie_id = vendor_assistant_utils.install_assistant_by_name(
        vendor=vendor_type,
        setting_id=setting.setting_id,
        assistant_name=assistant_name,
    )
    assert_that(codemie_id, is_not(none()))

    class AssistantIdWrapper:
        def __init__(self, assistant_id):
            self.id = assistant_id

    assistant_wrapper = AssistantIdWrapper(codemie_id)
    response = assistant_utils.ask_assistant(
        assistant=assistant_wrapper,
        user_prompt=prompt,
        minimal_response=True,
    )

    similarity_check.check_similarity(response, expected_response)

    uninstall_response = vendor_assistant_utils.uninstall_assistant(
        vendor=vendor_type,
        codemie_id=codemie_id,
    )
    assert_that(uninstall_response.success, is_(True))
