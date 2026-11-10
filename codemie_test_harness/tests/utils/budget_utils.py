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

import requests

from codemie_test_harness.tests import API_DOMAIN, VERIFY_SSL
from codemie_test_harness.tests.test_data.budget_usage_project_rows_test_data import (
    CLI_ROW_SUFFIX,
    PREMIUM_ROW_SUFFIX,
)
from codemie_test_harness.tests.utils.base_utils import BaseUtils, poll_until

logger = logging.getLogger(__name__)

_POLL_INTERVAL = 10
_PROJECT_ROW_SUFFIX = {
    "platform": "",
    "cli": CLI_ROW_SUFFIX,
    "premium_models": PREMIUM_ROW_SUFFIX,
}


class BudgetUtils(BaseUtils):
    def get_budget_usage(self, user_id: str | None = None) -> list[dict]:
        resp = requests.get(
            f"{API_DOMAIN}/v1/analytics/budget_usage",
            params={"user_id": user_id} if user_id else None,
            headers={"Authorization": f"Bearer {self.client.token}"},
            verify=VERIFY_SSL,
        )
        resp.raise_for_status()
        return resp.json()["data"]["rows"]

    def get_budget_row_for_project(self, project_name: str) -> dict | None:
        rows = self.get_budget_usage()
        return next((r for r in rows if r["project_name"] == project_name), None)

    def get_budget_row_for_cli(self, email: str) -> dict | None:
        return self.get_budget_row_for_project(f"{email} (cli)")

    def get_budget_row_for_premium(self, email: str) -> dict | None:
        return self.get_budget_row_for_project(f"{email} (premium)")

    def wait_for_members_project_spending_above(
        self,
        user_ids: list[str],
        project_name: str,
        category: str,
        threshold: float,
        timeout: int = 600,
    ) -> float | None:
        """Poll until the given users' own spend in the project's budget of the category,
        added together, exceeds threshold.

        Reads the budget usage view of each user, so the caller must be allowed to view
        them (a global admin is). A user without a row yet keeps the poll going. On timeout
        it returns the latest total (None if some user never had a row).
        """
        label = f"{project_name}{_PROJECT_ROW_SUFFIX[category]}"

        def read_total() -> float | None:
            figures = []
            for user_id in user_ids:
                row = next(
                    (
                        r
                        for r in self.get_budget_usage(user_id)
                        if r["project_name"] == label
                    ),
                    None,
                )
                figures.append(None if row is None else row.get("current_spending"))
            if any(figure is None for figure in figures):
                return None
            return sum(figures)

        total = poll_until(
            read_total,
            lambda value: value is not None and value > threshold,
            timeout=timeout,
            interval=_POLL_INTERVAL,
        )
        if total is None or total <= threshold:
            logger.warning(
                "Members' spend in %r did not exceed %.6f within %ss — returning the latest total %s",
                label,
                threshold,
                timeout,
                total,
            )
        return total
