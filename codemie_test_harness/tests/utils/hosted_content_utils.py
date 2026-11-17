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

"""Open a hosted application the way the browser does, without a browser.

The content of an application is served from its own origin, not from the CodeMie API, so the
SDK has no call for it. A viewing session is a launch ticket from the API, posted as a form to the
content origin, which answers with a cookie; every later content request carries that cookie.
These requests are the raw HTTP pattern for content hosts; the management API stays on the SDK.
"""

from typing import Optional
from urllib.parse import urlparse

import requests
from codemie_sdk.models.hosted_application import HostedApplicationLaunch
from hamcrest import assert_that, contains_string, empty, equal_to, is_not

from codemie_test_harness.tests import VERIFY_SSL
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager

REQUEST_TIMEOUT_SECONDS = 60
PAGE_ACCEPT = "text/html,application/xhtml+xml"


def ui_origin() -> str:
    """Scheme and host of the CodeMie web application, the origin a launch must come from."""
    parsed = urlparse(CredentialsManager.get_required_parameter("FRONTEND_URL"))
    return f"{parsed.scheme}://{parsed.netloc}"


class HostedContentSession:
    """A viewing session of one user on one version of an application.

    ``embedded`` is how the web application opens it, inside a frame; the cookie it gets works
    for every later request of the session.
    """

    def __init__(self, launch: HostedApplicationLaunch, embedded: bool = True):
        self.launch = launch
        self.origin = launch.content_origin.rstrip("/")
        self._cookie = self._redeem(launch, embedded)

    @classmethod
    def open(
        cls,
        service,
        app_id: str,
        purpose: str = "published_view",
        path: Optional[str] = None,
    ) -> "HostedContentSession":
        """Launch the application as the user behind ``service`` and redeem the ticket."""
        return cls(service.launch(app_id, purpose, path=path))

    @staticmethod
    def _redeem(launch: HostedApplicationLaunch, embedded: bool) -> str:
        response = requests.post(
            launch.action,
            data={"ticket": launch.ticket},
            headers={
                "Origin": ui_origin(),
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Dest": "iframe" if embedded else "document",
                "Sec-Fetch-Site": "cross-site",
            },
            allow_redirects=False,
            verify=VERIFY_SSL,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        assert_that(
            response.status_code,
            equal_to(303),
            "redeeming the launch ticket redirects to the viewing session",
        )
        # One header per cookie: read the list, never the comma-joined value (an Expires date holds a comma).
        cookies = response.raw.headers.getlist("Set-Cookie")
        assert_that(
            cookies,
            is_not(empty()),
            "redeeming the launch ticket sets the viewing-session cookie",
        )
        pair = cookies[0].split(";", 1)[0].strip()
        assert_that(
            pair,
            contains_string("="),
            "the viewing-session cookie carries a name and a value",
        )
        return pair

    def request(
        self,
        path: str = "/",
        method: str = "GET",
        dest: str = "iframe",
        page: bool = True,
        cookie: bool = True,
    ) -> requests.Response:
        """One content request. ``page`` asks like a frame navigation, ``dest`` sets the fetch destination."""
        headers = {
            "Sec-Fetch-Dest": dest,
            "Sec-Fetch-Mode": "navigate" if page else "no-cors",
            "Sec-Fetch-Site": "cross-site",
        }
        if page:
            headers["Accept"] = PAGE_ACCEPT
        if cookie:
            headers["Cookie"] = self._cookie
        return requests.request(
            method,
            self.origin + path,
            headers=headers,
            allow_redirects=False,
            verify=VERIFY_SSL,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

    def page(self, path: str = "/") -> requests.Response:
        return self.request(path)

    def asset(self, path: str) -> requests.Response:
        return self.request(path, page=False)

    def document_navigation(self, path: str = "/") -> requests.Response:
        """The version URL opened as a top-level document, which the content host hands to the viewer."""
        return self.request(path, dest="document")

    def should_serve(self, marker: str, path: str = "/") -> None:
        response = self.page(path)
        assert_that(response.status_code, equal_to(200), f"'{path}' is served")
        assert_that(
            response.text,
            contains_string(marker),
            f"the page of the application holds '{marker}'",
        )
