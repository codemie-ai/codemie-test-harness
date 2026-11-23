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
from typing import Optional

import requests

from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.servicenow_seed import (
    SEED_DESCRIPTION,
    SEED_FIELDS,
    SEED_SHORT_DESCRIPTION,
    SeedIncident,
    build_seed_query,
    find_seed_incident,
    seed_incident_from_record,
)

logger = logging.getLogger(__name__)

INCIDENT_TABLE_PATH = "/api/now/table/incident"


class ServiceNowUtils:
    """Utility class for interacting with the ServiceNow Table API."""

    def __init__(self):
        """Initialize ServiceNow utilities with credentials from CredentialsManager."""
        self.base_url = CredentialsManager.get_parameter("SERVICENOW_URL").rstrip("/")
        self.headers = {
            "x-sn-apikey": CredentialsManager.get_parameter("SERVICENOW_TOKEN"),
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, **kwargs):
        response = requests.request(
            method,
            f"{self.base_url}{INCIDENT_TABLE_PATH}",
            headers=self.headers,
            timeout=60,
            **kwargs,
        )
        response.raise_for_status()
        return response

    def list_seed_candidates(self) -> list[dict]:
        response = self._request(
            "GET",
            params={
                "sysparm_query": build_seed_query(),
                "sysparm_fields": SEED_FIELDS,
                "sysparm_limit": 100,
            },
        )
        return response.json()["result"]

    def create_seed_incident(self) -> dict:
        return self._request(
            "POST",
            json={
                "short_description": SEED_SHORT_DESCRIPTION,
                "description": SEED_DESCRIPTION,
            },
        ).json()["result"]

    def find_seed_incident(self) -> Optional[dict]:
        return find_seed_incident(self.list_seed_candidates())

    def ensure_seed_incident(self) -> SeedIncident:
        """Find or create the seed incident."""
        record = self.find_seed_incident()
        if record is None:
            created = self.create_seed_incident()
            logger.info(f"Created ServiceNow seed incident {created['number']}")
            # Concurrent runs may each have created a seed; all settle on the oldest.
            record = self.find_seed_incident() or created
            if record["number"] != created["number"]:
                logger.warning(
                    f"Duplicate ServiceNow seed incident {created['number']} exists "
                    f"next to {record['number']}; it can be closed"
                )
        return seed_incident_from_record(record)
