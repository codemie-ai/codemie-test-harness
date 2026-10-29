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

"""UI Test Suite for Integration Creation Page Help Links"""

import pytest
from hamcrest import assert_that, contains_string

from codemie_test_harness.tests.ui.pageobject.integrations.create_integration_page import (
    CreateIntegrationPage,
)
from codemie_test_harness.tests.ui.test_data.links_names_test_data import (
    IntegrationDocUrls,
)


@pytest.mark.ui
@pytest.mark.integration
def test_integration_help_links_validation(page):
    """UI Test Suite for Integration Help Links Validation"""
    create_integration_page = CreateIntegrationPage(page)
    create_integration_page.navigate_to_user_integration_creation()

    # Open help panel
    create_integration_page.click_help_button()
    create_integration_page.should_have_help_panel_visible()

    # Test "How to work with Integrations" link
    with page.expect_popup() as popup_info:
        create_integration_page.help_work_with_integrations_button.click()
    popup = popup_info.value
    assert_that(popup.url, contains_string(IntegrationDocUrls.WORK_WITH_INTEGRATIONS))
    popup.close()
