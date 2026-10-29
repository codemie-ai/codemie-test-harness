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
from urllib.parse import quote
from xml.sax.saxutils import escape

import requests

from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.xwiki_seed import (
    SEED_CONTENT,
    SEED_PAGE_NAME,
    SEED_TITLE,
    XWikiSeedPage,
)

logger = logging.getLogger(__name__)

REST_PATH = "/rest/wikis/xwiki"


class XWikiUtils:
    """Utility class for writing to the xWiki REST API."""

    def __init__(self):
        self.xwiki_url = CredentialsManager.get_parameter("XWIKI_URL").rstrip("/")
        # XWIKI_TOKEN is the bare token (used as the Basic-auth password for the
        # CodeMie integration); the seed write goes straight to xWiki's REST API,
        # which needs it as a Bearer token instead.
        self.authorization = f"Bearer {CredentialsManager.get_parameter('XWIKI_TOKEN')}"
        self.space = CredentialsManager.xwiki_space()

        if not self.space:
            raise ValueError("XWIKI_SPACE is not set; a xWiki space is required")

    def _page_endpoint(self, space: str, page: str) -> str:
        return (
            f"{self.xwiki_url}{REST_PATH}/spaces/{quote(space, safe='')}"
            f"/pages/{quote(page, safe='')}"
        )

    def ensure_seed_page(self) -> XWikiSeedPage:
        """Create or update the seed page with the known token.

        PUT on a fixed page name is an upsert: the first run creates the page,
        later runs rewrite the same page, so no duplicates are ever created.
        """
        body = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<page xmlns="http://www.xwiki.org">'
            f"<title>{escape(SEED_TITLE)}</title>"
            f"<content>{escape(SEED_CONTENT)}</content>"
            "</page>"
        )
        response = requests.put(
            url=self._page_endpoint(self.space, SEED_PAGE_NAME),
            headers={
                "Authorization": self.authorization,
                "Content-Type": "application/xml",
            },
            data=body.encode("utf-8"),
            verify=True,
            timeout=60,
        )
        response.raise_for_status()
        logger.info(
            f"Ensured xWiki seed page {SEED_PAGE_NAME} in space {self.space} "
            f"(HTTP {response.status_code})"
        )
        return XWikiSeedPage(space=self.space)
