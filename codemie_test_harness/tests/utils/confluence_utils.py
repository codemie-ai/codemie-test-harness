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

from codemie_test_harness.tests.utils.confluence_seed import (
    SEED_BODY,
    SEED_TITLE,
    SeedPage,
    find_seed_page_id,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager

logger = logging.getLogger(__name__)

SEED_SEARCH_TIMEOUT_SECONDS = 60
SEED_SEARCH_POLL_SECONDS = 3


class ConfluenceUtils:
    """Utility class for interacting with Confluence API."""

    def __init__(self, is_cloud: bool = False):
        """
        Initialize Confluence utilities with credentials from CredentialsManager.

        Args:
            is_cloud: Whether to use Confluence Cloud or Confluence Server credentials
        """
        self.is_cloud = is_cloud

        if is_cloud:
            self.confluence_url = CredentialsManager.get_parameter(
                "CONFLUENCE_CLOUD_URL"
            )
            self.token = CredentialsManager.get_parameter("CONFLUENCE_CLOUD_TOKEN")
            self.email = CredentialsManager.get_parameter("CONFLUENCE_CLOUD_EMAIL")
            self.auth = (self.email, self.token)
            self.headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            self.confluence_api = "/wiki/api/v2"
            self.pages_endpoint = "/pages"
            # Cloud v1 API path for search — /wiki/api/v2/pages does not support spaceKey
            self.search_api_path = "/wiki/rest/api/content"
            self.space_key = CredentialsManager.confluence_cloud_space_key()
        else:
            self.confluence_url = CredentialsManager.get_parameter("CONFLUENCE_URL")
            self.token = CredentialsManager.get_parameter("CONFLUENCE_TOKEN")
            self.email = None
            self.auth = None
            self.headers = {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            self.confluence_api = "/rest/api"
            self.pages_endpoint = "/content"
            self.search_api_path = "/rest/api/content"
            self.space_key = CredentialsManager.confluence_space_key()

        if not self.space_key:
            env_var = (
                "CONFLUENCE_CLOUD_SPACE_KEY" if is_cloud else "CONFLUENCE_SPACE_KEY"
            )
            raise ValueError(
                f"{env_var} is not set; a Confluence space key is required "
                f"(is_cloud={is_cloud})"
            )

    def delete_confluence_page(self, page_id: str):
        """
        Delete a Confluence page via Confluence API.

        Args:
            page_id: The Confluence page ID
        """
        # Construct API endpoint
        endpoint = (
            f"{self.confluence_url}{self.confluence_api}{self.pages_endpoint}/{page_id}"
        )

        try:
            logger.info(f"Deleting Confluence page: {page_id}")
            requests.delete(
                url=endpoint,
                headers=self.headers,
                auth=self.auth,
                verify=True,
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Error deleting Confluence page {page_id}: {str(e)}")

    def search_pages_in_space(
        self, space_key: str = None, limit: int = 100
    ) -> list[dict]:
        """List pages (type=page) in a Confluence space."""
        space_key = self.space_key if not space_key else space_key
        endpoint = f"{self.confluence_url}{self.search_api_path}"
        response = requests.get(
            url=endpoint,
            headers=self.headers,
            auth=self.auth,
            params={"spaceKey": space_key, "type": "page", "limit": limit},
            verify=True,
            timeout=60,
        )
        response.raise_for_status()
        return response.json().get("results", [])

    def create_page(self, title: str, body: str) -> str:
        """Create a page in this instance's configured space; returns its id."""
        endpoint = f"{self.confluence_url}{self.search_api_path}"
        payload = {
            "type": "page",
            "title": title,
            "space": {"key": self.space_key},
            "body": {"storage": {"value": body, "representation": "storage"}},
        }
        response = requests.post(
            url=endpoint,
            headers=self.headers,
            auth=self.auth,
            json=payload,
            verify=True,
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["id"]

    def find_seed_page_id(self) -> Optional[str]:
        return find_seed_page_id(self.search_pages_in_space())

    def _create_seed_page(self) -> str:
        page_id = self.create_page(SEED_TITLE, SEED_BODY)
        logger.info(
            f"Created Confluence seed page {page_id} in space {self.space_key} "
            f"(is_cloud={self.is_cloud})"
        )
        # A just-created page may not appear in the space listing immediately.
        deadline = time.monotonic() + SEED_SEARCH_TIMEOUT_SECONDS
        while self.find_seed_page_id() is None:
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"Confluence seed page {page_id} not searchable after "
                    f"{SEED_SEARCH_TIMEOUT_SECONDS}s"
                )
            time.sleep(SEED_SEARCH_POLL_SECONDS)
        # Concurrent runs may each have created a seed; all settle on the oldest.
        settled = self.find_seed_page_id()
        if settled != page_id:
            logger.warning(
                f"Duplicate Confluence seed page {page_id} exists next to "
                f"{settled}; it can be deleted"
            )
        return settled

    def ensure_seed_page(self) -> SeedPage:
        """Find or create the seed page."""
        page_id = self.find_seed_page_id() or self._create_seed_page()
        return SeedPage(id=page_id, space_key=self.space_key)

    def cleanup_confluence_space(
        self,
        title_prefix: str = None,
        title_contains: str = None,
        space_key: str = None,
    ) -> int:
        """
        Clean up Confluence pages in a space matching the given title filter.

        Args:
            title_prefix: Delete pages whose title starts with this string (session-scoped cleanup).
            title_contains: Delete pages whose title contains this string (session-agnostic cleanup).
            space_key: Override the default space key for this instance.

        Returns:
            Number of pages deleted.
        """
        space_key = self.space_key if not space_key else space_key
        label = f"is_cloud={self.is_cloud}, space={space_key}"

        try:
            # Use the v1 content API for both Server and Cloud — it supports spaceKey filtering.
            # The Cloud v2 API (/wiki/api/v2/pages) does NOT support the spaceKey query parameter.
            search_endpoint = f"{self.confluence_url}{self.search_api_path}"
            params = {
                "spaceKey": space_key,
                "type": "page",
                "limit": 100,
            }

            filter_desc = title_prefix or title_contains or "(none)"
            logger.info(
                "Searching Confluence pages in space %s (filter: '%s', %s)",
                space_key,
                filter_desc,
                label,
            )
            response = requests.get(
                url=search_endpoint,
                headers=self.headers,
                auth=self.auth,
                params=params,
                verify=True,
            )

            if response.status_code != 200:
                # Suppress errors during cleanup — space may not exist or token may be expired
                logger.debug(
                    "Could not search Confluence pages (%s). Status: %d",
                    label,
                    response.status_code,
                )
                return 0

            all_pages = response.json().get("results", [])

            if title_prefix:
                pages_to_delete = [
                    p for p in all_pages if p.get("title", "").startswith(title_prefix)
                ]
            elif title_contains:
                pages_to_delete = [
                    p for p in all_pages if title_contains in p.get("title", "")
                ]
            else:
                pages_to_delete = list(all_pages)

            # The seed page is shared by every run and must survive cleanup.
            pages_to_delete = [
                p for p in pages_to_delete if p.get("title") != SEED_TITLE
            ]

            for page in pages_to_delete:
                self.delete_confluence_page(page["id"])

            if pages_to_delete:
                logger.info(
                    "✓ Deleted %d Confluence page(s) (%s)", len(pages_to_delete), label
                )

            return len(pages_to_delete)

        except requests.exceptions.RequestException as e:
            # Suppress errors during cleanup — credentials may be expired
            logger.debug("Confluence cleanup skipped (%s): %s", label, str(e))
            return 0
