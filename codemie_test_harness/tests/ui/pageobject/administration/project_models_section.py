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

"""Page object for the 'Models' tab (Model configuration) on the Project
Details administration page.

URL: /settings/administration/projects/{project_name}/models

Shows which platform LLM models are available in the project: a per-model
checkbox table (Model / Provider / Capabilities / Cost columns), a
"<N> of <M> models available" counter, a "Project default model" select, a
model name search box, an "All providers" filter, a "Premium only" filter,
and "Reset to global settings" / "Apply changes" buttons. Confirmed via live
inspection on 2026-10-15; the "CLI default model" select
was removed and "Reset to global settings" confirmed on 2026-10-20.
"""

import re

from playwright.sync_api import expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


class ProjectModelsSection(BasePage):
    """Project Details > Models tab."""

    # ── Locators ──────────────────────────────────────────────────────────────

    @property
    def model_configuration_heading(self):
        """'Model configuration' heading at the top of the tab."""
        return self.page.get_by_text("Model configuration", exact=True)

    @property
    def models_available_counter(self):
        """'<N> of <M> models available' label next to the heading."""
        return self.page.get_by_text("models available", exact=False).first

    @property
    def apply_changes_button(self):
        """'Apply changes' button that saves the model selection."""
        return self.page.get_by_role("button", name="Apply changes")

    @property
    def search_models_input(self):
        """'Search models' text box that filters the model table by name."""
        return self.page.get_by_placeholder("Search models")

    @property
    def premium_only_checkbox(self):
        """'Premium only' checkbox that narrows the table to premium models."""
        return self.page.get_by_role("checkbox", name="Premium only")

    @property
    def selected_only_checkbox(self):
        """'Selected only' checkbox that narrows the table to checked models."""
        return self.page.get_by_role("checkbox", name="Selected only")

    @property
    def reset_to_global_settings_button(self):
        """'Reset to global settings' button that restores the project's model
        selection and default model to the platform's global configuration.
        """
        return self.page.get_by_role("button", name="Reset to global settings")

    def model_row(self, model_name: str):
        """The table row for a given model name (first cell of each row)."""
        return self.page.get_by_role("row", name=model_name)

    # ── Assertions ────────────────────────────────────────────────────────────

    @step
    def filter_models(self, query: str):
        """Type into 'Search models' to filter the table — the model table is
        lazily rendered as it scrolls, so filtering to a single match is the
        reliable way to make an arbitrary model's row exist in the DOM.
        """
        self.search_models_input.fill(query)
        self.page.wait_for_timeout(500)
        return self

    @step
    def toggle_model(self, model_name: str):
        """Filter to `model_name` and click its row's checkbox to include/exclude it,
        then clear the filter so the rest of the table is visible again.
        """
        self.filter_models(model_name)
        self.model_row(model_name).get_by_role("checkbox").first.click()
        self.filter_models("")
        return self

    @step
    def apply_changes(self):
        """Save the model selection."""
        expect(self.apply_changes_button).to_be_enabled(timeout=5000)
        self.apply_changes_button.click()
        expect(self.apply_changes_button).to_be_disabled(timeout=15000)
        return self

    def default_model_trigger(self, field_label: str):
        """The 'Project default model' PrimeReact dropdown — the whole component
        (found via the <label for=...> id, since the dropdown itself carries no
        accessible role). Clicking anywhere on it opens the options listbox.
        """
        dropdown_id = self.page.get_by_text(field_label, exact=True).get_attribute(
            "for"
        )
        return self.page.locator(f"#{dropdown_id}")

    def current_default_model(self, field_label: str) -> str:
        """The model name currently shown (closed) in the default-model select."""
        return (
            self.default_model_trigger(field_label)
            .locator(".p-dropdown-label")
            .inner_text()
        )

    @step
    def select_default_model(self, field_label: str, model_name: str):
        """Open the default-model select and choose `model_name` from its options."""
        self.default_model_trigger(field_label).click()
        listbox = self.page.get_by_role("listbox").last
        expect(listbox).to_be_visible(timeout=5000)
        listbox.get_by_role("option", name=model_name).click()
        return self

    @step
    def reset_to_global_settings(self):
        """Click 'Reset to global settings', restoring the project's model
        selection and default model to the platform's global configuration.
        """
        self.reset_to_global_settings_button.click()
        return self

    @step
    def exclude_first_removable_model(self, candidates: list[str]) -> str:
        """Uncheck candidate models one at a time until 'Apply changes' becomes
        enabled, and return the one that registered. The UI refuses to drop a model
        that is currently a project/CLI default (Apply stays disabled), so a failed
        candidate is re-checked before the next one is tried.
        """
        for candidate in candidates:
            self.toggle_model(candidate)
            if self.apply_changes_button.is_enabled():
                return candidate
            self.toggle_model(candidate)
        raise AssertionError(
            f"No candidate could be excluded — Apply never enabled for: {candidates}"
        )

    @step
    def open_default_model_options(self, field_label: str) -> list[str]:
        """Open the 'Project default model' select and return the option texts
        from its listbox (the select is closed again afterwards).
        """
        self.default_model_trigger(field_label).click()
        listbox = self.page.get_by_role("listbox").last
        expect(listbox).to_be_visible(timeout=5000)
        options = listbox.get_by_role("option").all_inner_texts()
        self.page.keyboard.press("Escape")
        return options

    @step
    def should_offer_model_in_default_dropdown(self, field_label: str, model_name: str):
        """Verify `model_name` is one of the options in the default-model select."""
        options = self.open_default_model_options(field_label)
        assert any(model_name in option for option in options), (
            f"'{model_name}' is not offered in '{field_label}'; options: {options}"
        )
        return self

    @step
    def should_not_offer_model_in_default_dropdown(
        self, field_label: str, model_name: str
    ):
        """Verify `model_name` is NOT among the options in the default-model select."""
        options = self.open_default_model_options(field_label)
        assert not any(model_name in option for option in options), (
            f"'{model_name}' is still offered in '{field_label}'; options: {options}"
        )
        return self

    @step
    def should_be_visible(self):
        """Verify the Models tab has rendered its Model configuration table."""
        expect(self.model_configuration_heading).to_be_visible(timeout=15000)
        return self

    @step
    def scroll_to_end_of_model_list(self):
        """Scroll the model table until no more rows load, so every model is rendered
        before asserting on it (the list is lazily rendered as it scrolls).
        """
        rows = self.page.get_by_role("row")
        previous_count = -1
        while rows.count() != previous_count:
            previous_count = rows.count()
            rows.last.scroll_into_view_if_needed()
            self.page.wait_for_timeout(250)
        return self

    @step
    def should_have_default_model_selected(self, field_label: str, model_name: str):
        """Verify the closed default-model select currently shows `model_name`."""
        expect(self.default_model_trigger(field_label)).to_contain_text(
            model_name, timeout=10000
        )
        return self

    @step
    def should_have_all_models_checked(self):
        """Verify every model row's checkbox is checked (the full catalog is
        selected, as after 'Reset to global settings' is applied).
        """
        self.scroll_to_end_of_model_list()
        rows = self.page.get_by_role("row").filter(has=self.page.get_by_role("cell"))
        checkboxes = rows.get_by_role("checkbox")
        count = checkboxes.count()
        for i in range(count):
            expect(checkboxes.nth(i)).to_be_checked()
        return self

    def visible_model_rows(self):
        """Table body rows (header row excluded)."""
        return self.page.get_by_role("row").filter(has=self.page.get_by_role("cell"))

    def model_row_exact(self, model_name: str):
        """Table row whose model name is exactly `model_name` — a DIAL sibling
        such as "GPT-5.6 Sol (DIAL)" must not match "GPT-5.6 Sol".
        """
        return self.visible_model_rows().filter(
            has_text=re.compile(rf"^\s*{re.escape(model_name)}(?!\s*\()")
        )

    @step
    def set_premium_only(self, enabled: bool):
        """Check or uncheck the 'Premium only' filter."""
        if enabled:
            self.premium_only_checkbox.check()
        else:
            self.premium_only_checkbox.uncheck()
        self.page.wait_for_timeout(500)
        return self

    @step
    def set_selected_only(self, enabled: bool):
        """Check or uncheck the 'Selected only' filter."""
        if enabled:
            self.selected_only_checkbox.check()
        else:
            self.selected_only_checkbox.uncheck()
        self.page.wait_for_timeout(500)
        return self

    @step
    def should_show_only_premium_models(self) -> int:
        """Verify every visible row carries a Premium badge; return how many rows
        are visible.
        """
        self.scroll_to_end_of_model_list()
        rows = self.visible_model_rows()
        premium_badges = rows.get_by_role("status", name="Premium")
        assert rows.count() > 0, "'Premium only' filter shows no rows"
        expect(premium_badges).to_have_count(rows.count(), timeout=10000)
        return rows.count()

    @step
    def should_show_only_selected_models(self) -> int:
        """Verify every visible row's checkbox is checked; return how many rows
        are visible.
        """
        self.scroll_to_end_of_model_list()
        rows = self.visible_model_rows()
        checkboxes = rows.get_by_role("checkbox")
        assert rows.count() > 0, "'Selected only' filter shows no rows"
        for i in range(checkboxes.count()):
            expect(checkboxes.nth(i)).to_be_checked()
        return rows.count()

    @step
    def should_not_show_model(self, model_name: str):
        """Verify no visible row is the model named `model_name`."""
        self.scroll_to_end_of_model_list()
        expect(self.model_row_exact(model_name)).to_have_count(0, timeout=10000)
        return self

    @step
    def should_show_selected_count(self, expected_count: int):
        """Verify the 'N of M models available' counter reports `expected_count`
        selected models.
        """
        expect(self.models_available_counter).to_have_text(
            re.compile(rf"^{expected_count} of \d+ models available")
        )
        return self

    def selected_and_total_count(self) -> tuple[int, int]:
        """Parse the '<N> of <M> models available' counter into (N, M)."""
        text = self.models_available_counter.inner_text()
        match = re.search(r"(\d+)\s+of\s+(\d+)\s+models available", text)
        assert match, f"Could not parse models-available counter text: {text!r}"
        return int(match.group(1)), int(match.group(2))

    @step
    def should_show_model_count(self, expected_count: int):
        """Verify the model table lists exactly `expected_count` model rows (the
        header row excluded) and that the "N of M models available" counter's
        total M matches it too — i.e. every model the API returns is rendered,
        no more and no fewer.
        """
        self.scroll_to_end_of_model_list()
        rows = self.page.get_by_role("row").filter(has=self.page.get_by_role("cell"))
        expect(rows).to_have_count(expected_count, timeout=15000)
        expect(self.models_available_counter).to_have_text(
            re.compile(rf"of {expected_count} models available")
        )
        return self
