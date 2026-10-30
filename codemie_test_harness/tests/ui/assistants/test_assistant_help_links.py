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

"""UI Test Suite for Assistant Creation Page Help Links"""

import pytest
from hamcrest import assert_that, contains_string

from codemie_test_harness.tests.ui.pageobject.assistants.create_edit_assistant_page import (
    CreateEditAssistantPage,
)
from codemie_test_harness.tests.ui.test_data.links_names_test_data import (
    AssistantDocUrls,
)


@pytest.mark.ui
@pytest.mark.assistant
@pytest.mark.prod_regression
def test_assistant_help_links_validation(page):
    """UI Test Suite for Assistant Help Links Validation"""
    create_assistant_page = CreateEditAssistantPage(page)
    create_assistant_page.navigate_to()

    # Open help panel
    create_assistant_page.click_help_button()
    create_assistant_page.should_have_help_panel_visible()

    # Test "How to create Assistant" link
    with page.expect_popup() as popup_info:
        create_assistant_page.help_create_assistant_button.click()
    popup = popup_info.value
    assert_that(popup.url, contains_string(AssistantDocUrls.CREATE_ASSISTANT))
    popup.close()

    # Reopen help panel
    create_assistant_page.click_help_button()

    # Test "How to properly connect Tools" link
    with page.expect_popup() as popup_info:
        create_assistant_page.help_connect_tools_button.click()
    popup = popup_info.value
    assert_that(popup.url, contains_string(AssistantDocUrls.CONNECT_TOOLS))
    popup.close()

    # Reopen help panel
    create_assistant_page.click_help_button()

    # Test "How to properly connect Integrations" link
    with page.expect_popup() as popup_info:
        create_assistant_page.help_connect_integrations_button.click()
    popup = popup_info.value
    assert_that(popup.url, contains_string(AssistantDocUrls.CONNECT_INTEGRATIONS))
    popup.close()
