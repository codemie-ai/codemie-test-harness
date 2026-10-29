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

from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.workflows.base_workflow_form_page import (
    BaseWorkflowFormPage,
)


class EditWorkflowPage(BaseWorkflowFormPage):
    """Page object for the Edit Workflow page.

    The Edit Workflow page uses the same visual editor as Create Workflow page.
    All form fields, toolbar buttons, canvas, and nodes are inherited from BaseWorkflowFormPage.
    """

    page_url = "/workflows"

    def __init__(self, page):
        super().__init__(page)

    # ====================
    # PROPERTIES
    # ====================

    @property
    def page_title(self) -> Locator:
        """Page title 'Edit Workflow'."""
        return self.page.get_by_role("heading", name="Edit Workflow")

    # ====================
    # NAVIGATION METHODS
    # ====================

    @step
    def navigate_to(self, workflow_id: str):
        """Navigate to the Edit Workflow page with workflow ID."""
        url = f"{self.page_url}/{workflow_id}/edit"
        self.page.goto(url)
        # Wait for the visual editor canvas to finish loading before returning
        self.wait_for_page_load()

    # ====================
    # VERIFICATION METHODS
    # ====================

    @step
    def should_be_on_edit_workflow_page(self):
        """Verify that we are on the Edit Workflow page."""
        expect(self.page_title).to_be_visible()
        expect(self.save_button).to_be_visible()
        expect(self.cancel_button).to_be_visible()
        expect(self.canvas).to_be_visible()
        return self
