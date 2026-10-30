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

"""Marketplace management admin utilities.

The published ``codemie-sdk-python`` has no client for
``/v1/marketplace-management``; until it does, this wrapper is the single place
that calls the route directly (the same raw-request approach as the feedback
tests). Replace the body with a ``client.<service>`` call once the SDK ships one.
"""

import requests

from codemie_test_harness.tests.utils.base_utils import BaseUtils
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager

_BASE_PATH = "/v1/marketplace-management/entities"


class MarketplaceManagementUtils(BaseUtils):
    """Raw-HTTP access to the marketplace management admin API."""

    def bulk_unpublish(
        self, entity_ids: list[str], kind: str = "assistants"
    ) -> requests.Response:
        """POST ``/entities/{kind}/bulk-unpublish`` and return the raw response.

        The response is returned without raising so a test can assert both the
        200 body (``unpublished``, ``failed``) and rejection statuses (422).

        Args:
            entity_ids: Ids to unpublish (the API accepts 1-500).
            kind: Entity kind path segment; only ``assistants`` is implemented.
        """
        api_domain = CredentialsManager.get_parameter("CODEMIE_API_DOMAIN").rstrip("/")
        verify_ssl = (
            CredentialsManager.get_parameter("VERIFY_SSL", "false").lower() == "true"
        )
        return requests.post(
            f"{api_domain}{_BASE_PATH}/{kind}/bulk-unpublish",
            json={"entity_ids": entity_ids},
            headers={"Authorization": f"Bearer {self.client.token}"},
            verify=verify_ssl,
        )
