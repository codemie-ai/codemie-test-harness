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

import datetime
import threading
import time

import requests

from codemie_test_harness.tests import API_DOMAIN, VERIFY_SSL
from codemie_test_harness.tests.utils.base_utils import BaseUtils


class AdminSpendTrackingUtils(BaseUtils):
    def __init__(self, client):
        super().__init__(client)
        self._headers = {
            "Authorization": f"Bearer {client.token}",
            "Content-Type": "application/json",
        }

    def collect_spends(self, timeout: int = 120, poll_interval: int = 5) -> dict | None:
        """Trigger a collect; give up quietly on persistent 409 (another collect is
        already running elsewhere) instead of failing — that other collect run covers
        our pending spend too, so callers should rely on wait_for_project_spends next."""
        deadline = time.monotonic() + timeout
        while True:
            resp = requests.post(
                f"{API_DOMAIN}/v1/admin/spend-tracking/collect",
                headers=self._headers,
                verify=VERIFY_SSL,
            )
            if resp.status_code != 409:
                resp.raise_for_status()
                return resp.json()
            if time.monotonic() + poll_interval > deadline:
                return None
            time.sleep(poll_interval)

    def collect_spends_nowait(self) -> None:
        """Fire the collect endpoint in a daemon thread without blocking."""
        threading.Thread(target=self.collect_spends, daemon=True).start()

    def get_project_spends(
        self,
        project_name: str,
        period_from: datetime.date,
        period_to: datetime.date,
        budget_category: str | None = None,
        spend_subject_type: str | None = None,
    ) -> dict:
        params = {
            "period_from": period_from.isoformat(),
            "period_to": period_to.isoformat(),
        }
        if budget_category is not None:
            params["budget_category"] = budget_category
        if spend_subject_type is not None:
            params["spend_subject_type"] = spend_subject_type
        resp = requests.get(
            f"{API_DOMAIN}/v1/projects/{project_name}/spends",
            params=params,
            headers=self._headers,
            verify=VERIFY_SSL,
        )
        resp.raise_for_status()
        return resp.json()

    def wait_for_project_spends(
        self,
        project_name: str,
        period_from: datetime.date,
        period_to: datetime.date,
        budget_category: str | None = None,
        spend_subject_type: str | None = None,
        timeout: int = 300,
        poll_interval: int = 5,
    ) -> dict:
        """Poll get_project_spends until total_spend > 0, then return the result."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            spends = self.get_project_spends(
                project_name,
                period_from,
                period_to,
                budget_category,
                spend_subject_type,
            )
            if spends["total_spend"] > 0:
                return spends
            time.sleep(poll_interval)
        raise TimeoutError(
            f"project_spend_tracking never populated within {timeout}s "
            f"(project={project_name}, category={budget_category}, subject_type={spend_subject_type})"
        )
