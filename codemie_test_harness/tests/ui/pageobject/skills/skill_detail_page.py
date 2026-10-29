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

"""Page object for the Skill detail view.

Reached by navigating to /skills and clicking "View Details" from a skill card menu.
URL pattern: /skills/{skill_id}
"""

from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


class SkillDetailPage(BasePage):
    """Skill detail view — read-only page showing skill metadata and overview."""

    # ── Locators ──────────────────────────────────────────────────────────────

    @property
    def _overview_block(self) -> Locator:
        """The OVERVIEW sidebar block containing project, visibility, and skill ID."""
        return self.page.get_by_role("heading", name="OVERVIEW", level=3).locator(
            "xpath=.."
        )

    @property
    def overview_project(self) -> Locator:
        """The project value in the OVERVIEW block (p.text-wrap.break-words after 'Project:')."""
        return self._overview_block.locator(
            "div.flex:has(p.text-text-quaternary:text('Project:')) > p:not(.text-text-quaternary)"
        )

    # ── Assertions ────────────────────────────────────────────────────────────

    @step
    def should_show_project_display_name(self, display_name: str):
        """Verify the OVERVIEW Project field shows technical name with display_name as hover tooltip."""
        self.overview_project.hover()
        self.page.wait_for_timeout(300)
        expect(self.page.locator('[role="tooltip"]')).to_contain_text(display_name)
        return self
