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

"""Page object for the Cost Centers management list.

URL: /settings/administration/cost-centers

The list needs the `features:costCenters` flag on the target environment. Each row's
'Projects' cell holds a badge: an anchor with the accessible name 'Projects', the project
count as its text and a link to Project Management filtered to that cost center
(`?cost_center_ids=<id>`).
"""

import re

from playwright.sync_api import expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


class CostCentersManagementPage(BasePage):
    """Administration > Cost centers management list."""

    PATH = "/settings/administration/cost-centers"

    # ── Locators ──────────────────────────────────────────────────────────────

    @property
    def page_heading(self):
        """'Cost centers management' page heading."""
        return self.page.get_by_role("heading", name="Cost centers management", level=1)

    def _cost_center_row(self, name: str):
        """The table row of a cost center: the row holding its name button."""
        return self.page.get_by_role("row").filter(
            has=self.page.get_by_role("button", name=name, exact=True)
        )

    def project_count_badge(self, name: str):
        """The project-count badge of a cost center row, as a link named 'Projects'."""
        return self._cost_center_row(name).get_by_role(
            "link", name="Projects", exact=True
        )

    # ── Actions ───────────────────────────────────────────────────────────────

    @step
    def navigate_to(self):
        """Open the Cost centers management list directly and wait for it to render."""
        self.page.goto(self.PATH)
        self.page.wait_for_load_state("networkidle", timeout=30000)
        expect(self.page_heading).to_be_visible(timeout=15000)
        return self

    @step
    def click_project_count_badge(self, name: str):
        """Click the project-count badge of a cost center row (opens Project Management)."""
        badge = self.project_count_badge(name)
        expect(badge).to_be_visible(timeout=15000)
        badge.click()
        return self

    # ── Assertions ────────────────────────────────────────────────────────────

    @step
    def should_show_project_count_link(
        self, name: str, project_count: int, cost_center_id
    ):
        """Verify the row's badge is a link named 'Projects' with the project count as its
        text and a target filtered to the cost center."""
        badge = self.project_count_badge(name)
        expect(badge).to_have_count(1, timeout=15000)
        expect(badge).to_have_text(str(project_count))
        expect(badge).to_have_attribute(
            "href",
            re.compile(rf"[?&]cost_center_ids={re.escape(str(cost_center_id))}(&|$)"),
        )
        return self
