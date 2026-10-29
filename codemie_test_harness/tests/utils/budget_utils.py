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

import requests

from codemie_test_harness.tests import API_DOMAIN, VERIFY_SSL
from codemie_test_harness.tests.utils.base_utils import BaseUtils


class BudgetUtils(BaseUtils):
    def get_budget_usage(self) -> list[dict]:
        resp = requests.get(
            f"{API_DOMAIN}/v1/analytics/budget_usage",
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
