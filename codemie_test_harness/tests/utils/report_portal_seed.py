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

"""Seed data for Report Portal tests: harness-managed launch, owner and dashboard.

Pure logic only (no HTTP); ReportPortalUtils performs the requests. Report
Portal tests used to assert on launch 5563 -- a launch produced by a real
pytest run of this project -- plus other live data (the launch count, the
owner's profile, dashboard 2). Rerunning the project replaces that launch and
changes the counts, so every assertion broke over time. The seed objects are
created once per Report Portal project with a fixed, known composition and
reused by every later run. Tests derive their expected values from them
instead of hardcoding anything.
"""

from dataclasses import asdict, dataclass
from typing import Optional

SEED_LAUNCH_NAME = "CodeMie Test Harness Seed Launch"
SEED_LAUNCH_DESCRIPTION = (
    "Seed launch used by codemie-test-harness Report Portal tests. "
    "Do not delete or edit."
)
SEED_LAUNCH_ATTRIBUTES = {"seed": "true"}
# Composite attribute filter that matches only seed launches.
SEED_LAUNCH_ATTRIBUTE_FILTER = "seed:true"

SEED_PASSED_ITEM_NAME = "codemie_test_harness/seed::test_seed_passed"
SEED_FAILED_ITEM_NAME = "codemie_test_harness/seed::test_seed_failed"
SEED_SKIPPED_ITEM_NAME = "codemie_test_harness/seed::test_seed_skipped"
SEED_LOG_MESSAGE = "codemie-test-harness seed log entry"

SEED_FILTER_NAME = "CodeMie Test Harness Seed Filter"
SEED_WIDGET_NAME = "CodeMie Test Harness Seed Widget"
SEED_WIDGET_DESCRIPTION = (
    "Seed widget used by codemie-test-harness Report Portal tests."
)
SEED_WIDGET_TYPE = "launchStatistics"
SEED_WIDGET_WIDTH = 6
SEED_WIDGET_HEIGHT = 7
SEED_WIDGET_POSITION = (0, 0)
SEED_DASHBOARD_NAME = "CodeMie Test Harness Seed Dashboard"
SEED_DASHBOARD_DESCRIPTION = (
    "Seed dashboard used by codemie-test-harness Report Portal tests. "
    "Do not delete or edit."
)

REPORT_PORTAL_SEED = "report_portal_seed_launch"
REPORT_PORTAL_SEED_DASHBOARD = "report_portal_seed_dashboard"


@dataclass(frozen=True)
class SeedLaunch:
    id: int
    uuid: str
    name: str
    number: int
    owner: str
    start_time: str
    end_time: str
    status: str
    mode: str
    approximate_duration: float
    total: int
    passed: int
    failed: int
    skipped: int
    passed_item_id: int
    passed_item_name: str
    passed_item_code_ref: str
    passed_item_unique_id: str
    failed_item_id: int
    failed_item_name: str
    skipped_item_id: int
    skipped_item_name: str
    attribute_launch_count: int
    owner_uuid: str
    owner_user_id: int
    owner_full_name: str
    owner_email: str
    owner_account_type: str
    owner_role: str
    log_message: str = SEED_LOG_MESSAGE

    @property
    def duration_seconds(self) -> int:
        """Whole-second duration, derived from the live launch, never hardcoded."""
        return round(self.approximate_duration)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SeedLaunch":
        return cls(**data)


@dataclass(frozen=True)
class SeedDashboard:
    id: int
    name: str
    description: str
    owner: str
    widget_id: int
    widget_name: str
    widget_type: str
    widget_width: int
    widget_height: int
    widget_position_x: int
    widget_position_y: int

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SeedDashboard":
        return cls(**data)


def find_seed_launch(
    launches: list[dict], name: str = SEED_LAUNCH_NAME
) -> Optional[dict]:
    """The oldest finished launch whose name equals ``name`` exactly."""
    matches = [
        launch
        for launch in launches
        if launch.get("name") == name and launch.get("status") != "IN_PROGRESS"
    ]
    if not matches:
        return None
    return min(matches, key=lambda launch: launch["id"])


def find_seed_item(items: list[dict], name: str) -> Optional[dict]:
    """The oldest item under the seed launch whose name equals ``name`` exactly."""
    matches = [item for item in items if item.get("name") == name]
    if not matches:
        return None
    return min(matches, key=lambda item: item["id"])


def find_seed_dashboard(
    dashboards: list[dict], name: str = SEED_DASHBOARD_NAME
) -> Optional[dict]:
    """The oldest dashboard whose name equals ``name`` exactly."""
    matches = [dashboard for dashboard in dashboards if dashboard.get("name") == name]
    if not matches:
        return None
    return min(matches, key=lambda dashboard: dashboard["id"])
