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

import logging
import time
from typing import Optional

import requests
from reportportal_client import RPClient
from reportportal_client.helpers import timestamp

from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.report_portal_seed import (
    SEED_DASHBOARD_DESCRIPTION,
    SEED_DASHBOARD_NAME,
    SEED_FAILED_ITEM_NAME,
    SEED_FILTER_NAME,
    SEED_LAUNCH_ATTRIBUTE_FILTER,
    SEED_LAUNCH_ATTRIBUTES,
    SEED_LAUNCH_DESCRIPTION,
    SEED_LAUNCH_NAME,
    SEED_LOG_MESSAGE,
    SEED_PASSED_ITEM_NAME,
    SEED_SKIPPED_ITEM_NAME,
    SEED_WIDGET_DESCRIPTION,
    SEED_WIDGET_HEIGHT,
    SEED_WIDGET_NAME,
    SEED_WIDGET_POSITION,
    SEED_WIDGET_TYPE,
    SEED_WIDGET_WIDTH,
    SeedDashboard,
    SeedLaunch,
    find_seed_dashboard,
    find_seed_item,
    find_seed_launch,
)

logger = logging.getLogger(__name__)

API_V1 = "/api/v1"
SEED_INDEX_TIMEOUT_SECONDS = 60
SEED_INDEX_POLL_SECONDS = 2
# Launch statistics fields shown by the seed widget.
SEED_WIDGET_CONTENT_FIELDS = [
    "statistics$executions$total",
    "statistics$executions$passed",
    "statistics$executions$failed",
    "statistics$executions$skipped",
]


class ReportPortalUtils:
    """Utility class for interacting with the Report Portal REST API.

    Reads go through plain ``requests`` (the v1 API the CodeMie Report Portal
    tool itself calls). Creating the seed launch goes through the official
    ``reportportal-client`` SDK instead, since starting/finishing launches
    and test items is a stateful v2-API protocol the SDK already implements.
    """

    def __init__(self):
        self.rp_url = CredentialsManager.get_parameter("REPORT_PORTAL_URL").rstrip("/")
        self.project = CredentialsManager.get_parameter("REPORT_PORTAL_PROJECT")
        self.api_key = CredentialsManager.get_parameter("REPORT_PORTAL_API_KEY")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs):
        response = requests.request(
            method,
            f"{self.rp_url}{API_V1}/{self.project}{path}",
            headers=self.headers,
            timeout=60,
            **kwargs,
        )
        response.raise_for_status()
        return response

    def get_user(self, username: str) -> dict:
        # User profiles live outside the project-scoped v1 API.
        response = requests.get(
            f"{self.rp_url}/api/users/{username}",
            headers=self.headers,
            timeout=60,
        )
        response.raise_for_status()
        return response.json()

    def find_launches_by_name(self, name: str) -> list[dict]:
        response = self._request(
            "GET",
            "/launch",
            params={
                "filter.eq.name": name,
                "page.size": 50,
                "page.sort": "number,DESC",
            },
        )
        return response.json().get("content", [])

    def count_seed_attribute_launches(self) -> int:
        response = self._request(
            "GET",
            "/launch",
            params={
                "filter.has.compositeAttribute": SEED_LAUNCH_ATTRIBUTE_FILTER,
                "page.size": 1,
            },
        )
        return response.json()["page"]["totalElements"]

    def get_launch(self, launch_id: int) -> dict:
        return self._request("GET", f"/launch/{launch_id}").json()

    def get_items_for_launch(self, launch_id: int) -> list[dict]:
        response = self._request(
            "GET",
            "/item",
            params={"filter.eq.launchId": launch_id, "page.size": 50},
        )
        return response.json().get("content", [])

    def find_seed_launch(self) -> Optional[dict]:
        return find_seed_launch(self.find_launches_by_name(SEED_LAUNCH_NAME))

    def _create_seed_launch(self) -> dict:
        """Start a launch with one passed, one failed and one skipped item.

        That fixed composition is the whole point: total/passed/failed/skipped
        and duration can then be read back from the live launch and are never
        hardcoded, yet never drift the way a real pytest run's launch does.
        """
        client = RPClient(
            endpoint=self.rp_url,
            project=self.project,
            api_key=self.api_key,
            is_skipped_an_issue=False,
        )
        client.start_launch(
            name=SEED_LAUNCH_NAME,
            start_time=timestamp(),
            description=SEED_LAUNCH_DESCRIPTION,
            attributes=SEED_LAUNCH_ATTRIBUTES,
        )

        def _run_item(name: str, status: str) -> None:
            item_id = client.start_test_item(
                name=name,
                start_time=timestamp(),
                item_type="STEP",
                code_ref=name,
            )
            if status == "PASSED":
                client.log(
                    time=timestamp(),
                    message=SEED_LOG_MESSAGE,
                    level="INFO",
                    item_id=item_id,
                )
            client.finish_test_item(
                item_id=item_id, end_time=timestamp(), status=status
            )

        _run_item(SEED_PASSED_ITEM_NAME, "PASSED")
        _run_item(SEED_FAILED_ITEM_NAME, "FAILED")
        _run_item(SEED_SKIPPED_ITEM_NAME, "SKIPPED")

        client.finish_launch(end_time=timestamp())
        client.close()
        logger.info(
            f"Created Report Portal seed launch '{SEED_LAUNCH_NAME}' "
            f"in project {self.project}"
        )

        # The search index lags behind writes.
        deadline = time.monotonic() + SEED_INDEX_TIMEOUT_SECONDS
        launch = self.find_seed_launch()
        while launch is None:
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"Report Portal seed launch '{SEED_LAUNCH_NAME}' not "
                    f"searchable after {SEED_INDEX_TIMEOUT_SECONDS}s"
                )
            time.sleep(SEED_INDEX_POLL_SECONDS)
            launch = self.find_seed_launch()
        return launch

    def ensure_seed_launch(self) -> SeedLaunch:
        """Find or create the seed launch and return its current stats and item ids."""
        launch = self.find_seed_launch() or self._create_seed_launch()
        # Re-fetch by id: the search result is a summary, this is authoritative.
        launch = self.get_launch(launch["id"])

        items = self.get_items_for_launch(launch["id"])
        passed_item = find_seed_item(items, SEED_PASSED_ITEM_NAME)
        failed_item = find_seed_item(items, SEED_FAILED_ITEM_NAME)
        skipped_item = find_seed_item(items, SEED_SKIPPED_ITEM_NAME)
        if not (passed_item and failed_item and skipped_item):
            raise RuntimeError(
                f"Report Portal seed launch {launch['id']} ('{SEED_LAUNCH_NAME}') "
                f"is missing one of its seed test items; delete it in Report "
                f"Portal and rerun so the harness can recreate it"
            )

        owner = self.get_user(launch["owner"])
        executions = launch.get("statistics", {}).get("executions", {})
        return SeedLaunch(
            id=launch["id"],
            uuid=launch["uuid"],
            name=launch["name"],
            number=launch["number"],
            owner=launch["owner"],
            start_time=launch["startTime"],
            end_time=launch["endTime"],
            status=launch["status"],
            mode=launch.get("mode", "DEFAULT"),
            approximate_duration=launch.get("approximateDuration", 0.0),
            total=executions.get("total", 0),
            passed=executions.get("passed", 0),
            failed=executions.get("failed", 0),
            skipped=executions.get("skipped", 0),
            passed_item_id=passed_item["id"],
            passed_item_name=passed_item["name"],
            passed_item_code_ref=passed_item.get("codeRef", SEED_PASSED_ITEM_NAME),
            passed_item_unique_id=passed_item.get("uniqueId", ""),
            failed_item_id=failed_item["id"],
            failed_item_name=failed_item["name"],
            skipped_item_id=skipped_item["id"],
            skipped_item_name=skipped_item["name"],
            attribute_launch_count=self.count_seed_attribute_launches(),
            owner_uuid=owner["uuid"],
            owner_user_id=owner["id"],
            owner_full_name=owner["fullName"],
            owner_email=owner["email"],
            owner_account_type=owner["accountType"],
            owner_role=owner["userRole"],
        )

    def _create_seed_dashboard(self) -> dict:
        """Create the seed filter, widget and dashboard entirely through the API.

        Order matters: the widget references the filter, and the dashboard only
        shows widgets once they are added to it.
        """
        filter_id = self._request(
            "POST",
            "/filter",
            json={
                "name": SEED_FILTER_NAME,
                "type": "launch",
                "conditions": [
                    {
                        "filteringField": "name",
                        "condition": "eq",
                        "value": SEED_LAUNCH_NAME,
                    }
                ],
                "orders": [{"sortingColumn": "startTime", "isAsc": False}],
            },
        ).json()["id"]

        widget_id = self._request(
            "POST",
            "/widget",
            json={
                "name": SEED_WIDGET_NAME,
                "description": SEED_WIDGET_DESCRIPTION,
                "widgetType": SEED_WIDGET_TYPE,
                "contentParameters": {
                    "contentFields": SEED_WIDGET_CONTENT_FIELDS,
                    "itemsCount": 1,
                    "widgetOptions": {},
                },
                "filterIds": [filter_id],
            },
        ).json()["id"]

        dashboard_id = self._request(
            "POST",
            "/dashboard",
            json={
                "name": SEED_DASHBOARD_NAME,
                "description": SEED_DASHBOARD_DESCRIPTION,
            },
        ).json()["id"]

        position_x, position_y = SEED_WIDGET_POSITION
        self._request(
            "PUT",
            f"/dashboard/{dashboard_id}/add",
            json={
                "addWidget": {
                    "widgetName": SEED_WIDGET_NAME,
                    "widgetId": widget_id,
                    "widgetType": SEED_WIDGET_TYPE,
                    "widgetSize": {
                        "width": SEED_WIDGET_WIDTH,
                        "height": SEED_WIDGET_HEIGHT,
                    },
                    "widgetPosition": {
                        "positionX": position_x,
                        "positionY": position_y,
                    },
                    "widgetOptions": {},
                }
            },
        )
        logger.info(
            f"Created Report Portal seed dashboard '{SEED_DASHBOARD_NAME}' "
            f"(id {dashboard_id}) in project {self.project}"
        )
        return self.get_dashboard(dashboard_id)

    def get_dashboard(self, dashboard_id: int) -> dict:
        return self._request("GET", f"/dashboard/{dashboard_id}").json()

    def find_seed_dashboard(self) -> Optional[dict]:
        dashboards = self._request(
            "GET", "/dashboard", params={"page.size": 100}
        ).json()["content"]
        return find_seed_dashboard(dashboards)

    def ensure_seed_dashboard(self) -> SeedDashboard:
        """Find or create the seed dashboard and return its live definition."""
        dashboard = self.find_seed_dashboard() or self._create_seed_dashboard()

        widgets = dashboard.get("widgets") or []
        widget = next((w for w in widgets if w["widgetName"] == SEED_WIDGET_NAME), None)
        if widget is None:
            raise RuntimeError(
                f"Report Portal seed dashboard {dashboard['id']} "
                f"('{SEED_DASHBOARD_NAME}') has no seed widget; delete it in "
                f"Report Portal and rerun so the harness can recreate it"
            )

        return SeedDashboard(
            id=dashboard["id"],
            name=dashboard["name"],
            description=dashboard.get("description", ""),
            owner=dashboard["owner"],
            widget_id=widget["widgetId"],
            widget_name=widget["widgetName"],
            widget_type=widget["widgetType"],
            widget_width=widget["widgetSize"]["width"],
            widget_height=widget["widgetSize"]["height"],
            widget_position_x=widget["widgetPosition"]["positionX"],
            widget_position_y=widget["widgetPosition"]["positionY"],
        )
