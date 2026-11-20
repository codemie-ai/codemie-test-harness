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

"""Page object for the Model management administration page.

URL: /settings/administration/models ("Global model management")

The page lists every platform model with its provider, capabilities, cost and status.
A status is changed in the row select (``#model-status-<base_name>``) or, for selected
rows, with the Bulk Actions menu; both only stage a change, and nothing is stored until
"Apply changes" is clicked.

Locators follow the live walks of the page and of its list filters (recon of 2026-11-16).
"""

import re
from typing import Iterable

from hamcrest import assert_that, empty
from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.test_data.model_management_test_data import (
    MODELS_MANAGEMENT_HEADING,
    MODELS_MANAGEMENT_PATH,
    SETTINGS_UPDATED_TOAST,
)

_LOAD_TIMEOUT_MS = 30000


class ModelsManagementPage(BasePage):
    """Settings → Administration → Model management."""

    # ── Locators ──────────────────────────────────────────────────────────────

    @property
    def page_heading(self) -> Locator:
        """Page heading 'Global model management'."""
        return self.page.get_by_role("heading", name=MODELS_MANAGEMENT_HEADING)

    @property
    def apply_changes_button(self) -> Locator:
        """'Apply changes' button; enabled only while a change is staged."""
        return self.page.get_by_role("button", name="Apply changes")

    @property
    def summary(self) -> Locator:
        """Summary line '<n> of <m> models · <p> premium · <d> disabled · <x> deprecated'."""
        return self.page.get_by_text(re.compile(r"\d+ of \d+ models"))

    @property
    def search_input(self) -> Locator:
        """'Search models' text box of the list filters."""
        return self.page.get_by_placeholder("Search models")

    @property
    def provider_filter(self) -> Locator:
        """Provider text box of the list filters, showing 'All providers' by default."""
        return self.page.get_by_role("textbox", name="Provider")

    @property
    def provider_dropdown(self) -> Locator:
        """Clickable root of the Provider dropdown; its text box is hidden and opens nothing."""
        return self.provider_filter.locator(
            'xpath=ancestor::*[@data-pc-name="dropdown"][1]'
        )

    @property
    def provider_options(self) -> Locator:
        """Open list of providers."""
        return self.page.get_by_role("listbox", name="Option List")

    @property
    def status_filter(self) -> Locator:
        """Status multi-select of the list filters, showing 'All statuses' by default."""
        return self.page.get_by_role("combobox", name="Status")

    @property
    def status_filter_control(self) -> Locator:
        """Clickable root of the Status multi-select; its label covers the combobox input."""
        return self.status_filter.locator(
            'xpath=ancestor::*[@data-pc-name="multiselect"][1]'
        )

    def _status_filter_option(self, label: str) -> Locator:
        """Option (with a checkbox) of the open Status filter."""
        return self.page.get_by_role("listbox").get_by_role(
            "option", name=label, exact=True
        )

    @property
    def bulk_actions_button(self) -> Locator:
        """'Bulk Actions' button of the selection bar (shown once a row is selected)."""
        return self.page.get_by_role("button", name="Bulk Actions")

    @property
    def model_table(self) -> Locator:
        """The model table."""
        return self.page.get_by_role("table")

    @property
    def data_rows(self) -> Locator:
        """Model rows of the table, without the header row."""
        return self.model_table.get_by_role("row").filter(
            has=self.page.get_by_role("cell")
        )

    def column_header(self, name: str) -> Locator:
        """Column header whose title contains `name` (the cost title continues with "(in / out)")."""
        return self.model_table.get_by_role("columnheader", name=name)

    def row_for_model(self, base_name: str) -> Locator:
        """Row of the model; every row shows its base name under the label."""
        return self.data_rows.filter(has=self.page.get_by_text(base_name, exact=True))

    def status_select(self, base_name: str) -> Locator:
        """Status select of the model row (attribute selector: base names contain dots)."""
        return self.page.locator(f'[id="model-status-{base_name}"]')

    def _status_option(self, label: str) -> Locator:
        """Option of the open status select.

        Scoped to the open list: every row also holds a hidden native select with the
        same option names.
        """
        return self.page.get_by_role("listbox", name="Option List").get_by_role(
            "option", name=label, exact=True
        )

    def _bulk_action_item(self, label: str) -> Locator:
        """Item of the open Bulk Actions menu."""
        return self.page.get_by_role("menuitem", name=label, exact=True)

    @property
    def settings_updated_toast(self) -> Locator:
        """Toast that confirms the stored change."""
        return self.page.locator(".codemie-toast").filter(
            has_text=SETTINGS_UPDATED_TOAST
        )

    # ── Navigation and actions ────────────────────────────────────────────────

    @step
    def navigate_to(self):
        """Open the page by URL and wait for the model rows."""
        self.page.goto(MODELS_MANAGEMENT_PATH)
        expect(self.page_heading).to_be_visible(timeout=_LOAD_TIMEOUT_MS)
        expect(self.data_rows.first).to_be_visible(timeout=_LOAD_TIMEOUT_MS)
        return self

    @step
    def open_status_select(self, base_name: str):
        """Open the status select of a model row."""
        self.status_select(base_name).click()
        return self

    @step
    def choose_status(self, label: str):
        """Pick a status in the open status select."""
        self._status_option(label).click()
        return self

    @step
    def select_model_row(self, base_name: str):
        """Tick the checkbox of a model row."""
        self.row_for_model(base_name).get_by_role("checkbox").click()
        return self

    @step
    def open_bulk_actions(self):
        """Open the Bulk Actions menu."""
        self.bulk_actions_button.click()
        return self

    @step
    def choose_bulk_action(self, label: str):
        """Pick an item of the open Bulk Actions menu."""
        self._bulk_action_item(label).click()
        return self

    @step
    def apply_changes(self):
        """Store the staged changes."""
        self.apply_changes_button.click()
        return self

    @step
    def search_models(self, text: str):
        """Filter the list by a search text."""
        self.search_input.fill(text)
        return self

    @step
    def select_provider(self, provider_label: str):
        """Filter the list by a provider, named as the filter spells it."""
        self.provider_dropdown.click()
        self.provider_options.get_by_role(
            "option", name=provider_label, exact=True
        ).click()
        return self

    @step
    def select_provider_of_model(self, base_name: str):
        """Filter the list by the provider a model row shows, spelled as the filter spells it."""
        row = self.row_for_model(base_name)
        expect(row).to_be_visible(timeout=_LOAD_TIMEOUT_MS)
        headers = self.model_table.get_by_role("columnheader").all_inner_texts()
        provider_column = next(
            index for index, header in enumerate(headers) if "Provider" in header
        )
        provider_label = row.get_by_role("cell").nth(provider_column).inner_text()
        return self.select_provider(provider_label.strip())

    @step
    def toggle_status_filter_option(self, label: str):
        """Check or uncheck a status in the Status filter, then close the list."""
        self.status_filter_control.click()
        self._status_filter_option(label).click()
        self.page.keyboard.press("Escape")
        return self

    # ── Verifications ─────────────────────────────────────────────────────────

    @step
    def should_be_on_models_management_page(self):
        """Assert the URL and the page heading of Model management."""
        expect(self.page).to_have_url(
            re.compile(rf"{re.escape(MODELS_MANAGEMENT_PATH)}$"),
            timeout=_LOAD_TIMEOUT_MS,
        )
        expect(self.page_heading).to_be_visible(timeout=_LOAD_TIMEOUT_MS)
        return self

    @step
    def should_show_columns(self, names: Iterable[str]):
        """Assert each column header is shown."""
        for name in names:
            expect(self.column_header(name)).to_be_visible()
        return self

    @step
    def should_list_exactly_models(self, base_names: list[str]):
        """Assert the table has one row per given base name and no other row."""
        expect(self.data_rows).to_have_count(len(base_names), timeout=15000)
        texts = self.data_rows.all_inner_texts()
        missing = [
            base_name
            for base_name in base_names
            if not any(
                re.search(rf"(^|\s){re.escape(base_name)}(\s|$)", text)
                for text in texts
            )
        ]
        assert_that(missing, empty(), "models of the list that have no row")
        return self

    @step
    def should_offer_status_options(self, labels: Iterable[str]):
        """Assert the open status select offers each status."""
        for label in labels:
            expect(self._status_option(label)).to_be_visible()
        return self

    @step
    def should_offer_bulk_actions(self, labels: Iterable[str]):
        """Assert the open Bulk Actions menu offers each action."""
        for label in labels:
            expect(self._bulk_action_item(label)).to_be_visible()
        return self

    @step
    def should_show_settings_updated_toast(self):
        """Assert the 'Model settings updated' toast is shown."""
        expect(self.settings_updated_toast.first).to_be_visible(timeout=10000)
        return self

    @step
    def should_show_row_status(self, base_name: str, label: str):
        """Assert the status select of a model row shows the status."""
        expect(self.status_select(base_name)).to_contain_text(label)
        return self

    @step
    def should_show_summary(self, expected: str):
        """Assert the summary line contains the expected counts."""
        expect(self.summary.first).to_contain_text(expected)
        return self

    @step
    def should_show_status_filter_value(self, text: str):
        """Assert the Status filter reads `text` ('All statuses' or the checked labels)."""
        expect(self.status_filter_control).to_contain_text(text)
        return self
