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

"""Test data for analytics date filters written without a timezone offset."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

# Endpoints that filter by start_date/end_date; the first five are the CLI Analytics
# summary endpoints, the rest cover the shared query models of the other routers.
DATE_FILTERED_ENDPOINTS = [
    "/v1/analytics/cli-summary",
    "/v1/analytics/cli-users",
    "/v1/analytics/cli-llms",
    "/v1/analytics/cli-tools",
    "/v1/analytics/cli-repositories",
    "/v1/analytics/cli-insights-weekday-pattern",
    "/v1/analytics/summaries",
    "/v1/analytics/projects-spending",
    "/v1/analytics/cli-analytics/overview",
    "/v1/analytics/cli-analytics/tools",
]

# What a correct backend may answer for a date without an offset: it is treated as UTC (200)
# or rejected with a validation error (400/422). Never a server error.
NAIVE_DATE_ACCEPTED_STATUSES = (200, 400, 422)


@dataclass(frozen=True)
class NaiveDateCase:
    """The same filter written without an offset (naive) and with one (aware)."""

    name: str
    naive: dict
    aware: dict


def get_naive_date_cases() -> list[NaiveDateCase]:
    """Past, whole-day windows, so the end is never in the future and the data is stable."""
    today = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    start = today - timedelta(days=8)
    end = today - timedelta(seconds=1)
    start_naive = start.strftime("%Y-%m-%dT%H:%M:%S")
    end_naive = end.strftime("%Y-%m-%dT%H:%M:%S")
    start_day = start.strftime("%Y-%m-%d")
    end_day = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    return [
        NaiveDateCase(
            "start-and-end",
            {"start_date": start_naive, "end_date": end_naive},
            {"start_date": f"{start_naive}Z", "end_date": f"{end_naive}Z"},
        ),
        NaiveDateCase(
            "start-only",
            {"start_date": start_naive},
            {"start_date": f"{start_naive}Z"},
        ),
        NaiveDateCase(
            "end-only",
            {"end_date": end_naive},
            {"end_date": f"{end_naive}Z"},
        ),
        NaiveDateCase(
            "date-only",
            {"start_date": start_day, "end_date": end_day},
            {
                "start_date": f"{start_day}T00:00:00Z",
                "end_date": f"{end_day}T00:00:00Z",
            },
        ),
    ]
