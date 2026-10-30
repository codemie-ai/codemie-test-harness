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

"""TC-001 — Description is visible and read-only on Workflow details page.

Covers:
    AC-1  The Workflow Description field is displayed on the Workflow details page.
    AC-2  Description is shown in a readable manner and is not editable outside configuration mode.
    AC-4  Applies to every workflow where a description exists.
    AC-3  No regression of description display in the configuration sidebar (bonus assertion).
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.workflows.workflow_details_page import (
    WorkflowDetailsPage,
)


@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.prod_regression
def test_workflow_description_visible_and_read_only(
    page, test_workflow_with_description
):
    """TC-001: Verify workflow description is visible and read-only in the configuration sidebar.

    Preconditions:
        A workflow with a unique description is created via API.

    Steps:
        1. Navigate to the Workflow details page.
        2. Open the Configuration sidebar.
        3. Assert description text is visible (AC-1, AC-4).
        4. Assert description element is not editable (AC-2).
        5. Assert configuration sidebar contains the description text (AC-3 regression guard).
    """
    workflow, description_text = test_workflow_with_description
    details_page = WorkflowDetailsPage(page)
    details_page.navigate_to(workflow.id)
    details_page.should_be_on_workflow_details_page()

    # Open the configuration sidebar — description lives inside it.
    details_page.click_configuration()
    details_page.should_have_configuration_sidebar_open()

    # AC-1 / AC-4: Description text is visible on the details page.
    details_page.should_have_description_visible(description_text)

    # AC-2: Description is read-only — rendered as <p>, no contenteditable attribute.
    details_page.should_have_description_not_editable()

    # AC-3 regression guard: sidebar still contains description text.
    details_page.should_have_description_in_configuration_sidebar(description_text)
