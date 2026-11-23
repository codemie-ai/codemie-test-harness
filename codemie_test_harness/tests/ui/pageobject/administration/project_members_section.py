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

"""Page object for the Members tab of the Project Details administration page.

URL: /settings/administration/projects/{project_name}

The tab lists the members in the order the backend returns them (A to Z by name) and loads
them with GET /v1/admin/users, without sort_by / sort_order query params.
"""

from typing import List
from urllib.parse import parse_qs, urlparse

from hamcrest import assert_that, empty, is_not
from playwright.sync_api import expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage

USER_LIST_PATH = "/v1/admin/users"
SORT_PARAMS = ("sort_by", "sort_order")


class ProjectMembersSection(BasePage):
    """Members tab of the Project Details page, ordering aspect."""

    def __init__(self, page):
        super().__init__(page)
        self._user_list_urls: List[str] = []

    # ── Locators ──────────────────────────────────────────────────────────────

    def member_rows(self, search_token: str):
        """Members table rows whose text holds the token (the e-mails of the members under test)."""
        return self.page.get_by_role("row").filter(has_text=search_token)

    # ── Actions ───────────────────────────────────────────────────────────────

    @step
    def capture_user_list_requests(self):
        """Record every GET /v1/admin/users request the page makes from now on.

        Call before navigating, so the tab's first load is captured.
        """
        self.page.on("request", self._record_user_list_request)
        return self

    def _record_user_list_request(self, request):
        if request.method == "GET" and urlparse(request.url).path.rstrip("/").endswith(
            USER_LIST_PATH
        ):
            self._user_list_urls.append(request.url)

    # ── Assertions ────────────────────────────────────────────────────────────

    @step
    def should_list_members_in_order(self, search_token: str, emails: List[str]):
        """Verify the members whose e-mail holds the token are listed in exactly this order."""
        expect(self.member_rows(search_token)).to_contain_text(emails, timeout=30000)
        return self

    @step
    def should_have_loaded_members_without_sort_params(self):
        """Verify the tab requested the user list and no request carried sort_by / sort_order.

        Call after the members are rendered, so the load has certainly happened.
        """
        assert_that(
            self._user_list_urls,
            is_not(empty()),
            "The Members tab must request GET /v1/admin/users",
        )
        sorted_requests = [
            url
            for url in self._user_list_urls
            if any(param in parse_qs(urlparse(url).query) for param in SORT_PARAMS)
        ]
        assert_that(
            sorted_requests,
            empty(),
            "No Members tab request may carry sort_by or sort_order",
        )
        return self
