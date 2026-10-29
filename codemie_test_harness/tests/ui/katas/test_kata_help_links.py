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

"""UI Test Suite for Kata Creation Page Help Links"""

import pytest
from hamcrest import assert_that, contains_string

from codemie_test_harness.tests.ui.pageobject.katas.create_kata_page import (
    CreateKataPage,
)
from codemie_test_harness.tests.ui.test_data.links_names_test_data import (
    KatasDocUrls,
)


@pytest.mark.ui
@pytest.mark.katas
def test_kata_help_links_validation(page):
    """UI Test Suite for Kata Help Links Validation"""
    create_kata_page = CreateKataPage(page)
    create_kata_page.navigate_to()
    create_kata_page.should_be_on_create_kata_page()

    # Open help panel
    create_kata_page.click_help_button()
    create_kata_page.should_have_help_panel_visible()

    # Test "How to work with Katas" link
    with page.expect_popup() as popup_info:
        create_kata_page.help_work_with_katas_button.click()
    popup = popup_info.value
    assert_that(popup.url, contains_string(KatasDocUrls.WORK_WITH_KATAS))
    popup.close()
