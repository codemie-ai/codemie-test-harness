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

import re

from hamcrest import assert_that, equal_to
from playwright.sync_api import expect, Locator
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


class AvailableModelsPage(BasePage):
    page_url = "/help/models"

    # ==================== PAGE ELEMENTS ====================

    @property
    def available_models_heading(self) -> Locator:
        """Main page heading 'Available models'."""
        return self.page.locator("h1").filter(has_text="Available models")

    @property
    def text_filter(self) -> Locator:
        """Search text filter input."""
        return self.page.get_by_role("textbox", name="Search models")

    @property
    def _filter_dropdowns(self) -> Locator:
        """Filter dropdowns in toolbar order: provider first, model type second."""
        return self.page.locator("[data-pc-name='dropdown']")

    @property
    def provider_filter(self) -> Locator:
        """Provider filter dropdown ('All providers' by default)."""
        return self._filter_dropdowns.nth(0)

    @property
    def model_type_filter(self) -> Locator:
        """Model type filter dropdown ('All models' / 'Premium only')."""
        return self._filter_dropdowns.nth(1)

    def _select_dropdown_option(self, dropdown: Locator, option_name: str):
        dropdown.click()
        self.page.get_by_role("option", name=option_name, exact=True).click()

    @property
    def model_table(self) -> Locator:
        """The models table element."""
        return self.page.get_by_role("table")

    @property
    def all_premium_marks(self) -> Locator:
        """All visible premium status badges inside the model table."""
        return self.model_table.get_by_role("status", name="Premium")

    def _row_name_pattern(self, model_name: str) -> re.Pattern:
        """Row-text pattern matching exactly one model by name.

        A plain ``has_text=model_name`` substring filter is ambiguous once
        the environment has both a base model and its "(DIAL)"-suffixed
        sibling (e.g. "GPT-5.6 Sol" and "GPT-5.6 Sol (DIAL)") — the base
        name is a literal text prefix of the DIAL variant's row, so it
        matches both. The negative lookahead rejects any row whose text
        continues the matched name with a parenthetical suffix, keeping
        only the row for the exact model asked for.
        """
        return re.compile(rf"^{re.escape(model_name)}(?!\s*\()")

    def premium_mark_for_model(self, model_name: str) -> Locator:
        """Premium status badge in the table row matching a model name."""
        return self.row_for_model(model_name).get_by_role("status", name="Premium")

    def row_for_model(self, model_name: str) -> Locator:
        """Table row matching a given model name."""
        return self.model_table.get_by_role("row").filter(
            has_text=self._row_name_pattern(model_name)
        )

    # ==================== NAVIGATION METHODS ====================

    @step
    def navigate_to(self):
        """Navigate to the Available Models page."""
        self.page.goto(self.page_url)
        self.wait_for_page_load()
        return self

    # ==================== INTERACTION METHODS ====================

    @step
    def enable_premium_only_filter(self):
        """Pick 'Premium only' in the model type filter dropdown."""
        self._select_dropdown_option(self.model_type_filter, "Premium only")
        return self

    @step
    def fill_text_filter(self, text: str):
        """Type in the text search filter."""
        self.text_filter.fill(text)
        return self

    @step
    def select_provider(self, provider_name: str):
        """Select a provider from the provider filter dropdown."""
        self._select_dropdown_option(self.provider_filter, provider_name)
        return self

    # ==================== VERIFICATION METHODS ====================

    @step
    def should_show_available_models_heading(self):
        """Assert the 'Available models' heading is visible."""
        expect(self.available_models_heading).to_be_visible(timeout=10000)
        return self

    @step
    def should_show_filter_controls(self):
        """Assert all three filter controls are visible."""
        expect(self.text_filter).to_be_visible()
        expect(self.provider_filter).to_be_visible()
        expect(self.model_type_filter).to_be_visible()
        return self

    @step
    def should_show_model_table(self):
        """Assert the model table is visible."""
        expect(self.model_table).to_be_visible()
        return self

    @step
    def should_show_model_with_premium_mark(self, model_name: str):
        """Assert a specific model row carries a premium mark."""
        expect(self.premium_mark_for_model(model_name)).to_be_visible()
        return self

    @step
    def should_show_at_least_one_premium_model(self):
        """Assert at least one premium mark is visible in the table."""
        expect(self.all_premium_marks.first).to_be_visible()
        return self

    @step
    def should_not_show_model(self, model_name: str):
        """Assert a specific model name does not appear in the visible table."""
        expect(self.row_for_model(model_name)).to_have_count(0)
        return self

    @step
    def should_show_only_premium_models(self):
        """Assert all visible data rows in the table carry a premium mark.

        This method counts data rows (excluding header) and premium marks.
        After enabling the premium-only filter, both counts must match.
        """
        # Wait for table to be visible first
        expect(self.model_table).to_be_visible(timeout=5000)
        # At least one premium mark must be visible
        expect(self.all_premium_marks.first).to_be_visible()
        premium_mark_count = self.all_premium_marks.count()
        rows = self.model_table.get_by_role("row")
        total_row_count = rows.count()
        # Subtract 1 for the header row
        data_row_count = total_row_count - 1 if total_row_count > 0 else 0
        assert_that(
            premium_mark_count,
            equal_to(data_row_count),
            f"Expected all {data_row_count} data rows to have premium marks, "
            f"but found only {premium_mark_count}",
        )
        return self
