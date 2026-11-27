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

"""Page object for the cost values of Analytics > CLI Analytics.

Overview, Cost, Users and Repositories show an estimated cost that leaves out usage of models
without a catalog price. The UI marks such a value with a button next to it (``data-testid``
``unpriced-cost-marker``) whose accessible name starts "Partial estimate." when the value is the
priced part only, or "Cost unknown." when no usage could be priced, and names the unpriced
models. A complete value carries no marker. Locators read on preview on 2026-11-24.
"""

import re
from datetime import datetime
from zoneinfo import ZoneInfo

from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.analytics.cli_analytics_page import (
    CLIAnalyticsPage,
)
from codemie_test_harness.tests.ui.test_data.cli_analytics_pricing_test_data import (
    AVG_COST_COMPLETE_NOTE,
    AVG_COST_PARTIAL_NOTE,
    AVG_COST_UNKNOWN_NOTE,
    COST_UNKNOWN_NOTICE,
    PARTIAL_ESTIMATE_NOTICE,
    UNKNOWN_COST_VALUE,
)


class CLIAnalyticsCostPage(CLIAnalyticsPage):
    """CLI Analytics dashboard, with the cost values of its sections."""

    DATE_FORMAT = "%m/%d/%Y %H:%M"
    EST_COST = "Est. Cost"
    SESSIONS = "Sessions"
    AVG_COST = "Avg Cost / Session"

    # ── Locators ────────────────────────────────────────────────────────────────

    def date_filter_input(self, label: str) -> Locator:
        """Date and time input of the sidebar filter 'START DATE' or 'END DATE'."""
        return self.page.get_by_role("region", name=label).get_by_role("textbox")

    def summary_card_value(self, label: str) -> Locator:
        """Value of the summary card with the label (the table headers of the same name are
        not paragraphs)."""
        title = self.section_panel.locator("p").filter(
            has_text=re.compile(rf"^{re.escape(label)}$")
        )
        return title.locator("xpath=../following-sibling::p[1]")

    def summary_card_note(self, label: str) -> Locator:
        """Description under the value of the summary card with the label."""
        return self.summary_card_value(label).locator("xpath=following-sibling::p[1]")

    def cost_marker(self, scope: Locator, notice: str, model: str) -> Locator:
        """Marker button in the scope that carries the notice and names the model."""
        return scope.get_by_role("button", name=f"{notice} {model}")

    def any_cost_marker(self, scope: Locator) -> Locator:
        """Every marker button in the scope, whatever its notice."""
        return scope.get_by_test_id("unpriced-cost-marker")

    def cost_by_model_row(self, model: str) -> Locator:
        """Legend row of the model in the 'Cost by Model' widget (titled '<model>: <cost>')."""
        return self.section_panel.get_by_title(f"{model}:")

    @property
    def only_user_row(self) -> Locator:
        """The row of the only user of the selection in the 'All Users' table."""
        return self.users_data_rows.first

    def project_row(self, project: str) -> Locator:
        """Row of the project in the Repositories section."""
        return self.section_panel.get_by_role("row").filter(has_text=project)

    def est_cost_cell(self, row: Locator) -> Locator:
        """'Est. Cost' cell of a row of the open section's table (Users or Repositories).

        The position is read from the column header, as ``user_cell`` does: the cells carry no
        data-testid. The cell holds the amount and its marker.
        """
        index = self.users_header(self.EST_COST).evaluate(
            "header => Array.from(header.parentElement.children).indexOf(header)"
        )
        return row.get_by_role("cell").nth(index)

    # ── Actions ──────────────────────────────────────────────────────────────────

    def _browser_time(self, moment: datetime) -> str:
        """The moment as the date inputs take it: local time of the browser."""
        zone = self.page.evaluate("Intl.DateTimeFormat().resolvedOptions().timeZone")
        return moment.astimezone(ZoneInfo(zone)).strftime(self.DATE_FORMAT)

    @step
    def filter_by_window(self, start: datetime, end: datetime):
        """Type the start and end of the window into the sidebar and wait for Overview data."""
        for label, moment in (("START DATE", start), ("END DATE", end)):
            field = self.date_filter_input(label)
            with self.expect_section_data(self.DEFAULT_SECTION):
                field.fill(self._browser_time(moment))
                field.press("Enter")
        return self

    # ── Assertions ────────────────────────────────────────────────────────────────

    def _should_have_value_and_marker(
        self, value: Locator, text: str, notice: str, model: str
    ):
        expect(value, f"Cost value should read '{text}'").to_have_text(
            text, timeout=30000
        )
        expect(
            self.cost_marker(value, notice, model),
            f"'{text}' should carry the '{notice}' marker naming {model}",
        ).to_have_count(1, timeout=15000)

    def _should_have_value_without_marker(self, value: Locator, text: str):
        expect(value, f"Cost value should read '{text}'").to_have_text(
            text, timeout=30000
        )
        expect(
            self.any_cost_marker(value),
            f"Complete cost '{text}' should carry no marker",
        ).to_have_count(0)

    @step
    def should_show_overview_est_cost(self, amount: str):
        """Assert the Overview 'Est. Cost' reads the amount, whatever marker it carries."""
        expect(
            self.summary_card_value(self.EST_COST),
            f"Overview Est. Cost should read '{amount}'",
        ).to_have_text(amount, timeout=30000)
        return self

    @step
    def should_show_overview_sessions(self, count: int):
        """Assert the Overview 'Sessions' card counts the sessions of the selection."""
        expect(
            self.summary_card_value(self.SESSIONS),
            f"Overview should count {count} session(s)",
        ).to_have_text(str(count), timeout=30000)
        return self

    @step
    def should_mark_overview_est_cost_partial(self, amount: str, model: str):
        """Assert the Overview 'Est. Cost' is the priced amount, marked as a partial estimate."""
        self._should_have_value_and_marker(
            self.summary_card_value(self.EST_COST),
            amount,
            PARTIAL_ESTIMATE_NOTICE,
            model,
        )
        return self

    @step
    def should_not_mark_overview_est_cost(self, amount: str):
        """Assert the Overview 'Est. Cost' is the amount, with no marker."""
        self._should_have_value_without_marker(
            self.summary_card_value(self.EST_COST), amount
        )
        return self

    @step
    def should_mark_overview_est_cost_unknown(self, model: str):
        """Assert the Overview 'Est. Cost' is unknown, not $0.00, and names the model."""
        self._should_have_value_and_marker(
            self.summary_card_value(self.EST_COST),
            UNKNOWN_COST_VALUE,
            COST_UNKNOWN_NOTICE,
            model,
        )
        return self

    @step
    def should_mark_cost_est_cost_partial(self, amount: str, model: str):
        """Assert the Cost section 'Est. Cost' and 'Avg Cost / Session' are marked as partial."""
        self._should_have_value_and_marker(
            self.summary_card_value(self.EST_COST),
            amount,
            PARTIAL_ESTIMATE_NOTICE,
            model,
        )
        expect(
            self.summary_card_value(self.AVG_COST),
            f"Avg Cost / Session should read '{amount}'",
        ).to_have_text(amount)
        expect(
            self.summary_card_note(self.AVG_COST),
            "Avg Cost / Session should say it is a partial estimate",
        ).to_have_text(AVG_COST_PARTIAL_NOTE)
        return self

    @step
    def should_not_mark_cost_est_cost(self, amount: str):
        """Assert the Cost section 'Est. Cost' and 'Avg Cost / Session' are the amount, unmarked."""
        self._should_have_value_without_marker(
            self.summary_card_value(self.EST_COST), amount
        )
        expect(
            self.summary_card_value(self.AVG_COST),
            f"Avg Cost / Session should read '{amount}'",
        ).to_have_text(amount)
        expect(
            self.summary_card_note(self.AVG_COST),
            "Complete Avg Cost / Session should not say it is partial",
        ).to_have_text(AVG_COST_COMPLETE_NOTE)
        return self

    @step
    def should_mark_cost_est_cost_unknown(self, model: str):
        """Assert the Cost section 'Est. Cost' and 'Avg Cost / Session' are unknown, not $0.00."""
        self._should_have_value_and_marker(
            self.summary_card_value(self.EST_COST),
            UNKNOWN_COST_VALUE,
            COST_UNKNOWN_NOTICE,
            model,
        )
        expect(
            self.summary_card_value(self.AVG_COST),
            "Avg Cost / Session should be unknown",
        ).to_have_text(UNKNOWN_COST_VALUE)
        expect(
            self.summary_card_note(self.AVG_COST),
            "Avg Cost / Session should say the cost is unknown",
        ).to_have_text(AVG_COST_UNKNOWN_NOTE)
        return self

    @step
    def should_mark_cost_by_model_unknown(self, model: str):
        """Assert the 'Cost by Model' row of the unpriced model has no amount and says why."""
        row = self.cost_by_model_row(model)
        expect(
            row, f"Cost by Model should list {model} with no amount"
        ).to_have_attribute("title", f"{model}: {UNKNOWN_COST_VALUE}", timeout=15000)
        expect(
            self.cost_marker(row, COST_UNKNOWN_NOTICE, model),
            f"The {model} row should carry the cost unknown marker",
        ).to_have_count(1)
        return self

    @step
    def should_not_mark_cost_by_model(self, model: str, amount: str):
        """Assert the 'Cost by Model' row of the model is the amount, with no marker."""
        row = self.cost_by_model_row(model)
        expect(row, f"Cost by Model should list {model} at {amount}").to_have_attribute(
            "title", f"{model}: {amount}", timeout=15000
        )
        expect(
            self.any_cost_marker(row),
            f"The priced {model} row should carry no marker",
        ).to_have_count(0)
        return self

    def _should_list_one_user(self):
        expect(self.users_data_rows, "Users should list the one sender").to_have_count(
            1, timeout=15000
        )

    @step
    def should_mark_user_cost_partial(self, amount: str, model: str):
        """Assert the Users table row shows the priced amount, marked as a partial estimate."""
        self._should_list_one_user()
        self._should_have_value_and_marker(
            self.est_cost_cell(self.only_user_row),
            amount,
            PARTIAL_ESTIMATE_NOTICE,
            model,
        )
        return self

    @step
    def should_not_mark_user_cost(self, amount: str):
        """Assert the Users table row shows the amount with no marker."""
        self._should_list_one_user()
        self._should_have_value_without_marker(
            self.est_cost_cell(self.only_user_row), amount
        )
        return self

    @step
    def should_mark_user_cost_unknown(self, model: str):
        """Assert the Users table row shows an unknown cost, not $0.00, naming the model."""
        self._should_list_one_user()
        self._should_have_value_and_marker(
            self.est_cost_cell(self.only_user_row),
            UNKNOWN_COST_VALUE,
            COST_UNKNOWN_NOTICE,
            model,
        )
        return self

    @step
    def should_mark_project_cost_partial(self, project: str, amount: str, model: str):
        """Assert the Repositories row of the project is the priced amount, marked as partial."""
        self._should_have_value_and_marker(
            self.est_cost_cell(self.project_row(project)),
            amount,
            PARTIAL_ESTIMATE_NOTICE,
            model,
        )
        return self

    @step
    def should_not_mark_project_cost(self, project: str, amount: str):
        """Assert the Repositories row of the project is the amount, with no marker."""
        self._should_have_value_without_marker(
            self.est_cost_cell(self.project_row(project)), amount
        )
        return self

    @step
    def should_mark_project_cost_unknown(self, project: str, model: str):
        """Assert the Repositories row of the project has an unknown cost, not $0.00, naming the
        model."""
        self._should_have_value_and_marker(
            self.est_cost_cell(self.project_row(project)),
            UNKNOWN_COST_VALUE,
            COST_UNKNOWN_NOTICE,
            model,
        )
        return self
