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

"""Page object for the project activity history modal.

The modal opens from the 'History' button of the project details page
(ProjectDetailsPage.tsx) and is built in ProjectActivityHistoryModal.tsx of the frontend:
a title 'Activity history — <project name>', filter controls (Category, From, To, Domain,
Event type, Actor, Sort, 'Clear filters' while a filter is active), a '<N> total events'
line, a table of When / Event / Entity / Actor with an expand control per row, and a
pagination footer. The controls have no test ids; they are located by role and label.
"""

import re
from datetime import datetime

from playwright.sync_api import expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.test_data.project_history_test_data import (
    ACTOR_FILTER_PLACEHOLDER,
    ALL_CATEGORIES_PLACEHOLDER,
    ALL_DOMAINS_PLACEHOLDER,
    ALL_EVENTS_PLACEHOLDER,
    EMPTY_STATE_TEXT,
    HISTORY_COLUMNS,
    HISTORY_FILTER_LABELS,
    NEWEST_FIRST,
    NO_DETAIL_TEXT,
    event_actor_text,
    event_label,
    total_events_text,
    ui_date,
)

# 'MM/dd/yyyy, HH:mm' (DEFAULT_DATE_FORMAT of the frontend)
TIMESTAMP_PATTERN = r"\d{2}/\d{2}/\d{4},? \d{2}:\d{2}"
ISO_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")
JSON_BRACES = re.compile(r"[{}]")
# Cells of a row: expand control, When, Event, Entity, Actor
EVENT_CELL_INDEX = 2
# Request of the events list; the metadata request has no query string and is not matched.
ACTIVITY_EVENTS_LIST_URL = re.compile(r"/activity-events\?")
TOTAL_TEXT = re.compile(r"^\d+ total events?$")


class ProjectActivityHistoryModal(BasePage):
    """Modal 'Activity history — <project>' of the project details page."""

    # ── Locators ──────────────────────────────────────────────────────────────

    @property
    def dialog(self):
        """The history dialog, identified by its 'Activity history' heading."""
        return self.page.get_by_role("dialog").filter(
            has=self.page.get_by_role("heading", name=re.compile(r"^Activity history"))
        )

    @property
    def title(self):
        """Modal heading 'Activity history — <project name>'."""
        return self.dialog.get_by_role("heading", name=re.compile(r"^Activity history"))

    @property
    def total_text(self):
        """'<N> total events' line above the table."""
        return self.dialog.get_by_text(TOTAL_TEXT)

    @property
    def data_rows(self):
        """Event rows of the table: the rows that carry an expand/collapse control."""
        return self.dialog.locator("tbody tr").filter(
            has=self.page.get_by_role(
                "button", name=re.compile(r"^(Expand|Collapse) row$")
            )
        )

    @property
    def empty_state(self):
        """Table cell shown when no event matches."""
        return self.dialog.get_by_text(EMPTY_STATE_TEXT)

    @property
    def clear_filters_button(self):
        """'Clear filters' button, rendered while any filter is active."""
        return self.dialog.get_by_role("button", name="Clear filters")

    @property
    def retry_button(self):
        """'Retry' button of the load-error state."""
        return self.dialog.get_by_role("button", name="Retry")

    @property
    def close_button(self):
        """Close control of the dialog."""
        return self.dialog.get_by_role("button", name="Close")

    @property
    def next_page_button(self):
        """'Next page' control of the pagination footer."""
        return self.dialog.get_by_role("button", name="Next page")

    @property
    def per_page_select(self):
        """'Show: items per page' selector of the pagination footer."""
        return self.dialog.get_by_role("combobox", name="Show: items per page")

    @property
    def options(self):
        """Options of the dropdown panel that is open."""
        return self.page.get_by_role("listbox").get_by_role("option")

    def filter_control(self, label: str):
        """Filter control by its label: Category, From, To, Domain, Event type, Actor, Sort."""
        return self.dialog.get_by_label(label, exact=True).first

    def row_with_label(self, label: str):
        """First event row whose Event cell is `label`."""
        return self.data_rows.filter(
            has_text=re.compile(rf"{TIMESTAMP_PATTERN}\s*{re.escape(label)}")
        ).first

    @staticmethod
    def detail_of(row):
        """The row holding the expanded detail of `row`."""
        return row.locator("xpath=following-sibling::tr[1]")

    @staticmethod
    def detail_value(detail, term: str):
        """Value of the labelled attribute `term` in an expanded detail."""
        return (
            detail.get_by_role("term")
            .filter(has_text=re.compile(rf"^\s*{re.escape(term)}\s*$"))
            .first.locator("xpath=following-sibling::dd[1]")
        )

    # ── Actions ───────────────────────────────────────────────────────────────

    @step
    def close_dropdown(self):
        """Close an open dropdown panel by clicking the dialog title."""
        self.title.click()
        return self

    @step
    def select_category(self, category: str):
        """Tick `category` in the Category filter."""
        self.filter_control("Category").click()
        self.page.get_by_role("option", name=category, exact=True).click()
        return self.close_dropdown()

    @step
    def set_from(self, day: datetime):
        """Type the From date (local midnight of `day`)."""
        self.filter_control("From").fill(ui_date(day))
        return self.close_dropdown()

    @step
    def set_to(self, day: datetime):
        """Type the To date (local midnight of `day`)."""
        self.filter_control("To").fill(ui_date(day))
        return self.close_dropdown()

    @step
    def set_from_text(self, text: str):
        """Type the From date as MM/DD/YYYY text."""
        self.filter_control("From").fill(text)
        return self.close_dropdown()

    @step
    def sort_oldest_first(self):
        """Choose 'Oldest first' in the Sort filter."""
        self.filter_control("Sort").click()
        self.page.get_by_role("option", name="Oldest first", exact=True).click()
        return self

    @step
    def filter_by_actor(self, email: str):
        """Search the Actor filter for `email` and choose the matching user."""
        self.filter_control("Actor").click()
        self.page.get_by_placeholder("Search users").fill(email)
        self.page.get_by_role("option").filter(has_text=email).first.click()
        return self.close_dropdown()

    @step
    def show_per_page(self, size: int):
        """Choose '<size> items' in the page-size selector."""
        self.per_page_select.click()
        self.page.get_by_role("option", name=f"{size} items", exact=True).click()
        return self

    @step
    def go_to_next_page(self):
        """Go to the next page of events."""
        self.next_page_button.click()
        return self

    @step
    def expand_row(self, label: str):
        """Expand the first row whose Event cell is `label`."""
        self.row_with_label(label).get_by_role("button", name="Expand row").click()
        return self

    @step
    def retry(self):
        """Click 'Retry' of the load-error state."""
        self.retry_button.click()
        return self

    @step
    def fail_event_requests(self):
        """Abort every request of the events list made by the browser."""
        self.page.route(ACTIVITY_EVENTS_LIST_URL, lambda route: route.abort())
        return self

    @step
    def restore_event_requests(self):
        """Let the events list requests through again."""
        self.page.unroute(ACTIVITY_EVENTS_LIST_URL)
        return self

    @step
    def close(self):
        """Close the modal."""
        self.close_button.click()
        return self

    # ── Assertions ────────────────────────────────────────────────────────────

    @step
    def should_be_open_for(self, project_name: str):
        """The modal is open and titled for `project_name`."""
        expect(self.title).to_have_text(
            f"Activity history — {project_name}", timeout=15000
        )
        return self

    @step
    def should_be_closed(self):
        """The modal is not on the page."""
        expect(self.dialog).to_have_count(0, timeout=10000)
        return self

    @step
    def should_show_columns(self):
        """The table has the columns When, Event, Entity and Actor."""
        for column in HISTORY_COLUMNS:
            expect(
                self.dialog.get_by_role("columnheader", name=column, exact=True)
            ).to_be_visible(timeout=15000)
        return self

    @step
    def should_show_all_filter_controls(self):
        """Every filter control of the modal is on the page."""
        for label in HISTORY_FILTER_LABELS:
            expect(self.filter_control(label)).to_be_visible(timeout=15000)
        return self

    @step
    def should_show_no_active_filter(self):
        """Every filter shows its default and 'Clear filters' is not offered."""
        for placeholder in (
            ALL_CATEGORIES_PLACEHOLDER,
            ALL_DOMAINS_PLACEHOLDER,
            ALL_EVENTS_PLACEHOLDER,
            ACTOR_FILTER_PLACEHOLDER,
            NEWEST_FIRST,
        ):
            expect(self.dialog.get_by_text(placeholder, exact=True)).to_be_visible(
                timeout=15000
            )
        expect(self.filter_control("From")).to_have_value("")
        expect(self.filter_control("To")).to_have_value("")
        expect(self.clear_filters_button).to_have_count(0)
        return self

    @step
    def should_show_total(self, total: int):
        """The total line reads '<total> total events'."""
        expect(self.total_text).to_have_text(total_events_text(total), timeout=20000)
        return self

    @step
    def should_list_events(self, events):
        """The table lists exactly `events`, in this order, with their label and actor."""
        expected = [
            re.compile(
                rf"^\s*{TIMESTAMP_PATTERN}\s*{re.escape(event_label(event))}"
                rf".*{re.escape(event_actor_text(event))}\s*$",
                re.DOTALL,
            )
            for event in events
        ]
        expect(self.data_rows).to_have_text(expected, timeout=20000)
        return self

    @step
    def should_show_event_row(self, label: str):
        """A row whose Event cell is `label` is in the table."""
        expect(self.row_with_label(label)).to_be_visible(timeout=20000)
        return self

    @step
    def should_show_category_selected(self, category: str):
        """The Category filter still shows `category` as selected."""
        expect(self.dialog.get_by_text(category, exact=True).first).to_be_visible()
        return self

    @step
    def should_show_date_filters(self, start: datetime, end: datetime):
        """The From and To fields still hold the dates that were typed."""
        expect(self.filter_control("From")).to_have_value(
            re.compile(rf"^{re.escape(ui_date(start))}")
        )
        expect(self.filter_control("To")).to_have_value(
            re.compile(rf"^{re.escape(ui_date(end))}")
        )
        return self

    @step
    def should_show_active_filters(self):
        """'Clear filters' is offered, so a filter is active."""
        expect(self.clear_filters_button).to_be_visible(timeout=10000)
        return self

    @step
    def should_offer_categories(self, categories):
        """The Category dropdown offers exactly `categories`, in this order."""
        self.filter_control("Category").click()
        expect(self.options).to_have_text(list(categories), timeout=10000)
        self.close_dropdown()
        return self

    @step
    def should_show_no_events(self):
        """The explicit empty state is shown, with no table rows."""
        expect(self.empty_state).to_be_visible(timeout=20000)
        expect(self.data_rows).to_have_count(0)
        return self

    @step
    def should_show_load_error_with_retry(self):
        """A non-empty error message and a 'Retry' action replace the table."""
        expect(self.retry_button).to_be_visible(timeout=20000)
        expect(self.retry_button.locator("xpath=preceding-sibling::span")).to_have_text(
            re.compile(r"\S")
        )
        expect(self.total_text).to_have_count(0)
        return self

    @step
    def should_show_formatted_timestamps(self):
        """Every When cell reads like 'MM/DD/YYYY, HH:mm', not as an ISO timestamp."""
        expect(self.data_rows.first).to_be_visible(timeout=20000)
        expect(
            self.data_rows.filter(has_not_text=re.compile(rf"^\s*{TIMESTAMP_PATTERN}"))
        ).to_have_count(0)
        expect(self.data_rows.filter(has_text=ISO_TIMESTAMP)).to_have_count(0)
        return self

    @step
    def should_show_budget_change_detail(
        self,
        label: str,
        project_name: str,
        previous_max: str,
        new_max: str,
        max_increase: str,
        soft_increase: str,
    ):
        """The expanded `label` row names the project, formats the amounts as USD and
        shows signed increases with an up triangle, with no raw JSON."""
        detail = self.detail_of(self.row_with_label(label))
        expect(detail).to_be_visible(timeout=10000)
        expect(self.detail_value(detail, "Project name")).to_have_text(project_name)
        expect(self.detail_value(detail, "Previous max budget")).to_have_text(
            previous_max
        )
        expect(self.detail_value(detail, "New max budget")).to_have_text(new_max)
        expect(self.detail_value(detail, "Max budget change")).to_have_text(
            re.compile(rf"▲\s*{re.escape(max_increase)}")
        )
        expect(self.detail_value(detail, "Soft limit change")).to_have_text(
            re.compile(rf"▲\s*{re.escape(soft_increase)}")
        )
        expect(detail).not_to_contain_text(JSON_BRACES)
        expect(detail).not_to_contain_text(ISO_TIMESTAMP)
        return self

    @step
    def should_show_readable_detail_for_every_row(self):
        """Expand every row: each has a non-blank, humanized Event cell and a detail that
        is a list of labelled values or the fallback text, never raw JSON."""
        expect(self.data_rows.first).to_be_visible(timeout=20000)
        for row in self.data_rows.all():
            row.get_by_role("button", name="Expand row").click()
            expect(row.locator("td").nth(EVENT_CELL_INDEX)).to_have_text(
                re.compile(r"^\s*[A-Z][^._]*$")
            )
            detail = self.detail_of(row)
            expect(
                detail.get_by_role("term").or_(detail.get_by_text(NO_DETAIL_TEXT)).first
            ).to_be_visible()
            expect(detail).not_to_contain_text(JSON_BRACES)
        return self

    @step
    def should_show_actor_text(self, actor_text: str, count: int):
        """Exactly `count` Actor cells read `actor_text`."""
        expect(
            self.data_rows.locator("td").filter(
                has_text=re.compile(rf"^\s*{re.escape(actor_text)}\s*$")
            )
        ).to_have_count(count, timeout=20000)
        return self
