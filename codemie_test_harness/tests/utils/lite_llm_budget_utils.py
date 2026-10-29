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

import time

import requests

from codemie_test_harness.tests import VERIFY_SSL
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager

_SPENDING_POLL_INTERVAL = 5
_SPENDING_POLL_TIMEOUT = 120
_BUDGET_ID_POLL_TIMEOUT = 10
# LiteLLM writes spend in batches (keys and customers may land in different batches),
# so waiting for a charge needs a longer window than the usual 120s spend polls.
_CHARGE_POLL_TIMEOUT = 240
_CHARGE_GRACE = 30


class LiteLLMBudgetUtils:
    def __init__(self):
        self._url = CredentialsManager.get_parameter("LITE_LLM_URL")
        self._api_key = CredentialsManager.get_parameter("LITE_LLM_KEY")

    def get_customer_info(self, email: str) -> dict | None:
        resp = requests.get(
            f"{self._url}/customer/info",
            params={"end_user_id": email},
            headers={"Authorization": f"Bearer {self._api_key}"},
            verify=VERIFY_SSL,
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def create_key(self) -> str:
        resp = requests.post(
            f"{self._url}/key/generate",
            json={},
            headers={"Authorization": f"Bearer {self._api_key}"},
            verify=VERIFY_SSL,
        )
        resp.raise_for_status()
        return resp.json()["key"]

    def delete_key(self, key: str) -> None:
        resp = requests.post(
            f"{self._url}/key/delete",
            json={"keys": [key]},
            headers={"Authorization": f"Bearer {self._api_key}"},
            verify=VERIFY_SSL,
        )
        if resp.status_code == 404:
            return
        resp.raise_for_status()

    def get_key_info(self, key: str) -> dict | None:
        resp = requests.get(
            f"{self._url}/key/info",
            params={"key": key},
            headers={"Authorization": f"Bearer {self._api_key}"},
            verify=VERIFY_SSL,
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()["info"]

    def wait_for_key_spending(self, key: str) -> dict | None:
        deadline = time.monotonic() + _SPENDING_POLL_TIMEOUT
        while time.monotonic() < deadline:
            info = self.get_key_info(key)
            if info and float(info.get("spend", 0)) > 0:
                return info
            time.sleep(_SPENDING_POLL_INTERVAL)
        return self.get_key_info(key)

    def delete_budget(self, budget_id: str) -> None:
        resp = requests.post(
            f"{self._url}/budget/delete",
            json={"id": budget_id},
            headers={"Authorization": f"Bearer {self._api_key}"},
            verify=VERIFY_SSL,
        )
        if resp.status_code == 404:
            return
        resp.raise_for_status()

    def delete_customer(self, email: str) -> None:
        resp = requests.post(
            f"{self._url}/customer/delete",
            json={"user_ids": [email]},
            headers={"Authorization": f"Bearer {self._api_key}"},
            verify=VERIFY_SSL,
        )
        if resp.status_code == 404:
            return
        resp.raise_for_status()

    def wait_for_customer_budget_id(
        self, customer_id: str, expected_budget_id: str | None
    ) -> dict | None:
        deadline = time.monotonic() + _BUDGET_ID_POLL_TIMEOUT
        while time.monotonic() < deadline:
            customer = self.get_customer_info(customer_id)
            if customer is not None:
                table = customer.get("litellm_budget_table")
                actual = table["budget_id"] if table else None
                if actual == expected_budget_id:
                    return customer
            time.sleep(_SPENDING_POLL_INTERVAL)
        return self.get_customer_info(customer_id)

    def wait_for_spending(self, email: str) -> dict | None:
        deadline = time.monotonic() + _SPENDING_POLL_TIMEOUT
        while time.monotonic() < deadline:
            customer = self.get_customer_info(email)
            if customer and float(customer.get("spend", 0)) > 0:
                return customer
            time.sleep(_SPENDING_POLL_INTERVAL)
        return self.get_customer_info(email)

    def wait_for_spending_above(self, email: str, threshold: float) -> dict | None:
        deadline = time.monotonic() + _SPENDING_POLL_TIMEOUT
        while time.monotonic() < deadline:
            customer = self.get_customer_info(email)
            if customer and float(customer.get("spend", 0)) > threshold:
                return customer
            time.sleep(_SPENDING_POLL_INTERVAL)
        return self.get_customer_info(email)

    def _find_key_token_by_alias(self, alias: str) -> str | None:
        resp = requests.get(
            f"{self._url}/key/list",
            params={"key_alias": alias, "size": 1, "return_full_object": "false"},
            headers={"Authorization": f"Bearer {self._api_key}"},
            verify=VERIFY_SSL,
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        keys = resp.json().get("keys", [])
        if not keys:
            return None
        return keys[0]

    def get_key_info_by_alias(self, alias: str) -> dict | None:
        token = self._find_key_token_by_alias(alias)
        if token is None:
            return None
        return self.get_key_info(token)

    def get_key_spend_by_alias(self, alias: str) -> float:
        """Spend of the key with this alias; 0.0 when no such key exists."""
        info = self.get_key_info_by_alias(alias)
        return float(info.get("spend", 0)) if info else 0.0

    def delete_key_by_alias(self, alias: str) -> None:
        token = self._find_key_token_by_alias(alias)
        if token is None:
            return
        self.delete_key(token)

    def wait_for_key_alias(self, alias: str) -> dict | None:
        deadline = time.monotonic() + _SPENDING_POLL_TIMEOUT
        while time.monotonic() < deadline:
            info = self.get_key_info_by_alias(alias)
            if info is not None:
                return info
            time.sleep(_SPENDING_POLL_INTERVAL)
        return self.get_key_info_by_alias(alias)

    def wait_for_key_alias_spending(self, alias: str) -> dict | None:
        deadline = time.monotonic() + _SPENDING_POLL_TIMEOUT
        while time.monotonic() < deadline:
            info = self.get_key_info_by_alias(alias)
            if info and float(info.get("spend", 0)) > 0:
                return info
            time.sleep(_SPENDING_POLL_INTERVAL)
        return self.get_key_info_by_alias(alias)

    def wait_for_key_alias_max_budget(
        self,
        alias: str,
        expected_max_budget: float,
        timeout: int = _SPENDING_POLL_TIMEOUT,
    ) -> dict | None:
        """Poll until the project key's max_budget equals expected_max_budget."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            info = self.get_key_info_by_alias(alias)
            if info is not None:
                actual = info.get("max_budget")
                if actual is not None and float(actual) == expected_max_budget:
                    return info
            time.sleep(_SPENDING_POLL_INTERVAL)
        return self.get_key_info_by_alias(alias)

    def get_budget_info(self, budget_id: str) -> dict | None:
        resp = requests.post(
            f"{self._url}/budget/info",
            json={"budgets": [budget_id]},
            headers={"Authorization": f"Bearer {self._api_key}"},
            verify=VERIFY_SSL,
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        items = resp.json()
        if isinstance(items, list):
            return items[0] if items else None
        return items

    def wait_for_budget_max_budget(
        self,
        budget_id: str,
        expected_max_budget: float,
        timeout: int = _SPENDING_POLL_TIMEOUT,
    ) -> dict | None:
        """Poll until the LiteLLM budget object's max_budget equals expected_max_budget."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            info = self.get_budget_info(budget_id)
            if info is not None:
                actual = info.get("max_budget")
                if actual is not None and float(actual) == expected_max_budget:
                    return info
            time.sleep(_SPENDING_POLL_INTERVAL)
        return self.get_budget_info(budget_id)

    def wait_for_key_alias_spending_above(
        self, alias: str, threshold: float
    ) -> dict | None:
        deadline = time.monotonic() + _SPENDING_POLL_TIMEOUT
        while time.monotonic() < deadline:
            info = self.get_key_info_by_alias(alias)
            if info and float(info.get("spend", 0)) > threshold:
                return info
            time.sleep(_SPENDING_POLL_INTERVAL)
        return self.get_key_info_by_alias(alias)

    def wait_for_customer_max_budget(
        self,
        customer_id: str,
        expected_max_budget: float,
        timeout: int = _SPENDING_POLL_TIMEOUT,
    ) -> dict | None:
        """Poll until the customer's litellm_budget_table.max_budget equals expected_max_budget."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            customer = self.get_customer_info(customer_id)
            if customer is not None:
                table = customer.get("litellm_budget_table") or {}
                if table.get("max_budget") == expected_max_budget:
                    return customer
            time.sleep(_SPENDING_POLL_INTERVAL)
        return self.get_customer_info(customer_id)

    def wait_for_customer(self, customer_id: str) -> dict | None:
        deadline = time.monotonic() + _SPENDING_POLL_TIMEOUT
        while time.monotonic() < deadline:
            customer = self.get_customer_info(customer_id)
            if customer is not None:
                return customer
            time.sleep(_SPENDING_POLL_INTERVAL)
        return self.get_customer_info(customer_id)

    def delete_project_budget_objects(
        self, budget_id: str, user_id: str | None = None
    ) -> None:
        self.delete_budget(f"{budget_id}:shared")
        if user_id:
            self.delete_budget(f"{budget_id}:user:{user_id}")

    def update_budget_reset_at(self, budget_id: str, reset_at: str) -> None:
        resp = requests.post(
            f"{self._url}/budget/update",
            json={"budget_id": budget_id, "budget_reset_at": reset_at},
            headers={"Authorization": f"Bearer {self._api_key}"},
            verify=VERIFY_SSL,
        )
        resp.raise_for_status()

    def update_key_reset_at_by_alias(self, alias: str, reset_at: str) -> None:
        token = self._find_key_token_by_alias(alias)
        if token is None:
            raise ValueError(f"Key with alias {alias!r} not found")
        resp = requests.post(
            f"{self._url}/key/update",
            json={"key": token, "budget_reset_at": reset_at},
            headers={"Authorization": f"Bearer {self._api_key}"},
            verify=VERIFY_SSL,
        )
        resp.raise_for_status()

    def wait_for_customer_budget_period_reset(
        self,
        customer_id: str,
        old_reset_at: str,
        timeout: int = _SPENDING_POLL_TIMEOUT,
    ) -> dict | None:
        """Poll until customer's litellm_budget_table.budget_reset_at is no longer old_reset_at."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            customer = self.get_customer_info(customer_id)
            if customer:
                table = customer.get("litellm_budget_table") or {}
                if table.get("budget_reset_at") != old_reset_at:
                    return customer
            time.sleep(_SPENDING_POLL_INTERVAL)
        return self.get_customer_info(customer_id)

    def delete_override_customers_for_project(
        self,
        project_name: str,
        user_id: str,
        categories: tuple[str, ...] = ("platform", "cli", "premium_models"),
    ) -> None:
        for category in categories:
            self.delete_customer(
                f"codemie:project:{project_name}:category:{category}:user:{user_id}"
            )

    def get_spends(
        self, key_aliases: dict[str, str], customers: dict[str, str]
    ) -> dict[str, float]:
        """Current spend per label: LiteLLM keys looked up by alias, customers by id."""
        spends = {}
        for label, alias in key_aliases.items():
            info = self.get_key_info_by_alias(alias)
            spends[label] = float(info.get("spend", 0)) if info else 0.0
        for label, customer_id in customers.items():
            info = self.get_customer_info(customer_id)
            spends[label] = float(info.get("spend", 0)) if info else 0.0
        return spends

    def wait_for_charged_sources(
        self,
        before: dict[str, float],
        key_aliases: dict[str, str],
        customers: dict[str, str],
    ) -> set[str]:
        """Labels whose spend grew since ``before``.

        Waits for the first growth, then a grace period so that a request wrongly charged
        to a second source is still noticed. Raises TimeoutError if nothing grew in time,
        so a timeout is never mistaken for "nothing was charged".
        """
        deadline = time.monotonic() + _CHARGE_POLL_TIMEOUT
        while time.monotonic() < deadline:
            if self._grown(before, self.get_spends(key_aliases, customers)):
                time.sleep(_CHARGE_GRACE)
                return self._grown(before, self.get_spends(key_aliases, customers))
            time.sleep(_SPENDING_POLL_INTERVAL)
        raise TimeoutError(
            f"No spend growth within {_CHARGE_POLL_TIMEOUT}s for "
            f"{sorted({*key_aliases, *customers})}"
        )

    @staticmethod
    def _grown(before: dict[str, float], now: dict[str, float]) -> set[str]:
        return {
            label
            for label, value in now.items()
            if value > before.get(label, 0.0) + 1e-9
        }
