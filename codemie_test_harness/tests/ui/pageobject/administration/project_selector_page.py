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

"""Page object component for the ProjectSelector dropdown.

Used across multiple pages wherever a project filter/selector appears.
"""

from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


class ProjectSelectorComponent(BasePage):
    """Shared project selector dropdown — maps option labels to display_name / name fallback."""

    # ── Locators ──────────────────────────────────────────────────────────────

    @property
    def selector_root(self) -> Locator:
        """The root multi-select element for project filtering."""
        return self.page.locator(
            "[data-testid='project-selector'], .project-selector, [aria-label*='project' i]"
        ).first

    def _option_by_project_name(self, project_name: str) -> Locator:
        """A dropdown option identified by its underlying project technical name (value)."""
        return self.page.locator(
            f"[data-value='{project_name}'], li[aria-label='{project_name}']"
        )

    def _option_label_for_project(self, project_name: str) -> Locator:
        """The visible label element for a project option inside the dropdown."""
        return self.page.locator(
            f"[data-testid='option-{project_name}'], li:has([data-value='{project_name}'])"
        ).first

    # ── Actions ───────────────────────────────────────────────────────────────

    @step
    def open_selector(self):
        """Click the project selector to open the options dropdown."""
        self.selector_root.click()
        self.page.wait_for_timeout(500)
        return self

    @step
    def select_project(self, project_name: str):
        """Select a project by its technical name."""
        self.open_selector()
        self._option_by_project_name(project_name).click()
        return self

    # ── Assertions ────────────────────────────────────────────────────────────

    @step
    def should_show_display_name_as_label(self, project_name: str, display_name: str):
        """Verify the option label for project_name shows display_name (not the technical name)."""
        self.open_selector()
        option_label = self._option_label_for_project(project_name)
        expect(option_label).to_contain_text(display_name)
        return self

    @step
    def should_show_technical_name_as_label(self, project_name: str):
        """Verify that a project without display_name uses its technical name as the label."""
        self.open_selector()
        option_label = self._option_label_for_project(project_name)
        expect(option_label).to_contain_text(project_name)
        return self
