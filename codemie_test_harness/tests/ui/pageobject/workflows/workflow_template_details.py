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

from playwright.sync_api import expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


class WorkflowTemplateDetailsPage(BasePage):
    """Page object for the Workflow Template Details page."""

    page_url = "/workflows/templates/"

    def __init__(self, page):
        """Initialize the WorkflowTemplateDetailsPage."""
        super().__init__(page)

    # ==================== PROPERTIES ====================

    @property
    def create_workflow_button(self):
        return self.page.locator('button:has-text("Create Workflow")')

    @property
    def template_icon(self):
        return self.page.locator("img.chat-header-assistant[class*='w-[4.5rem]']")

    @property
    def yaml_config(self):
        return self.page.locator("code.language-yaml")

    @property
    def copy_code_button(self):
        return self.page.locator("button").filter(has_text="Copy")

    @property
    def download_yaml_code_button(self):
        return self.page.locator("button").filter(has_text="Download")

    @property
    def link_to_workflow_template_button(self):
        return self.page.locator(
            "//div[contains(text(), 'Link to workflow template')]/following-sibling::div//button"
        )

    @property
    def link_to_video_template_field(self):
        return self.page.locator("//div[contains(text(), 'Link to Video')]")

    @property
    def link_to_video_template_button(self):
        return self.link_to_video_template_field.locator(
            "//following-sibling::div//button"
        )

    @property
    def template_title(self):
        return self.page.locator("h4.text-2xl")

    @property
    def about_workflow(self):
        return self.page.locator(
            "div.text-text-quaternary.break-words.whitespace-pre-wrap"
        )

    # ==================== INTERACTION METHODS ====================
    @step
    def get_template_title(self) -> str:
        """Verify that user on workflow templates page can get template title."""
        return self.template_title.inner_text()

    # ==================== VERIFICATION METHODS ====================
    @step
    def should_have_template_header(self):
        """Verify workflow templates has given functionality."""
        expect(self.create_workflow_button).to_be_visible()
        expect(self.create_workflow_button).to_be_enabled()
        expect(self.back_button).to_be_visible()
        expect(self.back_button).to_be_enabled()

    @step
    def should_have_template_details(self, template_title, description, yaml_config):
        expect(self.template_title).to_have_text(template_title)
        expect(self.about_workflow).to_have_text(description)
        expect(self.template_icon).to_be_visible()
        expect(self.yaml_config).to_be_visible()
        expect(self.copy_code_button).to_be_visible()
        expect(self.copy_code_button).to_be_enabled()
        expect(self.download_yaml_code_button).to_be_visible()
        expect(self.download_yaml_code_button).to_be_enabled()

    @step
    def should_have_template_sidebar(self):
        expect(self.link_to_workflow_template_button).to_be_visible()
        expect(self.link_to_workflow_template_button).to_be_enabled()
        if self.link_to_video_template_field.is_visible():
            expect(self.link_to_video_template_button).to_be_visible()
            expect(self.link_to_video_template_button).to_be_enabled()
