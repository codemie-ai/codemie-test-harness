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

"""UI Test Suite for Workflow Creation Page Help Links"""

import pytest
from hamcrest import assert_that, contains_string

from codemie_test_harness.tests.ui.test_data.links_names_test_data import (
    WorkflowDocUrls,
)
from codemie_test_harness.tests.ui.pageobject.workflows.create_workflow_page import (
    CreateWorkflowPage,
)


@pytest.mark.ui
@pytest.mark.workflow
def test_workflow_help_links_validation(page):
    """UI Test Suite for Workflow Help Links Validation"""
    create_workflow_page = CreateWorkflowPage(page)
    create_workflow_page.navigate_to()
    create_workflow_page.should_be_on_create_workflow_page()

    # Open help panel
    create_workflow_page.click_help_button()
    create_workflow_page.should_have_help_panel_visible()

    # Test "How to create Workflows" link - capture popup URL
    with page.expect_popup() as popup_info:
        create_workflow_page.help_create_workflows_button.click()
    popup = popup_info.value
    assert_that(popup.url, contains_string(WorkflowDocUrls.CREATE_WORKFLOW))
    popup.close()

    # Reopen help panel
    create_workflow_page.click_help_button()

    # Test "How to work with YAML Configuration" link - capture popup URL
    with page.expect_popup() as popup_info:
        create_workflow_page.help_yaml_config_button.click()
    popup = popup_info.value
    assert_that(popup.url, contains_string(WorkflowDocUrls.YAML_CONFIGURATION))
    popup.close()
