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

"""Test data for the project activity history modal UI tests."""

from datetime import datetime, timedelta, timezone

import pytest

# Browser login of each acting role: (username key, password key) in the settings.
# The maintainer is the default login of the UI tests; the project admin is the
# preconfigured persona that is made administrator of the project under test.
ROLE_CREDENTIAL_KEYS = {
    "maintainer": ("AUTH_USERNAME", "AUTH_PASSWORD"),
    "project_admin": ("AUTH_USERNAME_PROJECT", "AUTH_PASSWORD_PROJECT"),
}

# Marks a test whose browser signs in as the project administrator persona.
AS_PROJECT_ADMIN = pytest.mark.parametrize(
    "acting_credentials", ["project_admin"], indirect=True
)

HISTORY_COLUMNS = ["When", "Event", "Entity", "Actor"]
HISTORY_FILTER_LABELS = [
    "Category",
    "From",
    "To",
    "Domain",
    "Event type",
    "Actor",
    "Sort",
]
ALL_CATEGORIES_PLACEHOLDER = "All categories"
ALL_DOMAINS_PLACEHOLDER = "All domains"
ALL_EVENTS_PLACEHOLDER = "All events"
ACTOR_FILTER_PLACEHOLDER = "Filter by actor"
NEWEST_FIRST = "Newest first"
OLDEST_FIRST = "Oldest first"

SETTINGS_CATEGORY = "Settings"
BUDGET_CATEGORY = "Budget"

# The modal lists 50 events per page until a size is chosen; the per-page selector renders
# only while the list spans several pages, so the trail must outgrow the default size.
SMALLEST_PAGE_SIZE = 10
DEFAULT_PAGE_SIZE = 50
# Events by which the trail exceeds the default page size, so a stray extra event
# or two cannot bring it back to a single page.
PAGE_OVERFLOW_MARGIN = 5

# Budget limits the project budget is raised to (it is created with 100.00 / 50.00).
RAISED_MAX_BUDGET = 1234.56
RAISED_SOFT_BUDGET = 600.25
PREVIOUS_MAX_BUDGET_TEXT = "$100.00"
RAISED_MAX_BUDGET_TEXT = "$1,234.56"
MAX_BUDGET_INCREASE_TEXT = "+$1,134.56"
SOFT_BUDGET_INCREASE_TEXT = "+$550.25"
PROJECT_BUDGET_UPDATED_LABEL = "Project Budget Updated"

EMPTY_STATE_TEXT = "No activity events for this project generation."
NO_DETAIL_TEXT = "No additional detail"

# Years ahead of today used as a date with no events.
FUTURE_YEARS = 10


def role_credential_keys(role: str) -> tuple[str, str]:
    """Settings keys of the username and password the browser signs in with."""
    return ROLE_CREDENTIAL_KEYS[role]


def local_midnight(days_from_today: int) -> datetime:
    """Local midnight `days_from_today` days from today, timezone-aware."""
    today = (
        datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
    )
    return today + timedelta(days=days_from_today)


def ui_date(moment: datetime) -> str:
    """The MM/DD/YYYY text a date field of the modal accepts and shows."""
    return moment.strftime("%m/%d/%Y")


def api_timestamp(moment: datetime) -> str:
    """ISO 8601 UTC timestamp the activity events API takes as a time bound."""
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def far_future_date() -> str:
    """A date, in the modal's input format, on which no event can exist."""
    today = datetime.now()
    return ui_date(today.replace(year=today.year + FUTURE_YEARS))


def total_events_text(total: int) -> str:
    """The total line of the modal: singular for exactly one event."""
    return f"{total} total event{'' if total == 1 else 's'}"


def event_label(event) -> str:
    """The Event cell text: the backend label, else the humanized event type."""
    label = (event.label or "").strip()
    if label:
        return label
    words = event.event_type.replace("_", " ").strip()
    return words[:1].upper() + words[1:]


def event_actor_text(event) -> str:
    """The Actor cell text of an event: '<name> (<email>)', either part, else 'system'."""
    if event.actor_name and event.actor_email:
        return f"{event.actor_name} ({event.actor_email})"
    return event.actor_name or event.actor_email or "system"
