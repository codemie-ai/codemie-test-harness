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

"""
Response-ready signal: tab title prefix, screen-reader live region and the
browser notification raised when a chat reply finishes while the tab is hidden.

A headless run cannot switch tabs or see an OS notification, so this page object
drives the two inputs the frontend reads: ``document.hidden`` (replaced by an init
script that the test flips) and the ``Notification`` constructor (replaced by a
recorder that keeps every call). Both scripts must be installed before the page
is navigated, because an init script only applies to documents loaded afterwards.
"""

import json
import re
from typing import Callable, Optional

from hamcrest import assert_that, empty, equal_to, has_length, not_, starts_with
from playwright.sync_api import expect, Locator
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.test_data.response_ready_test_data import (
    RESPONSE_READY_ANNOUNCER_TEXT,
    RESPONSE_READY_TITLE_PREFIX,
)

# Request the chat UI sends to start a generation (same pattern ChatPage uses to
# capture the model request).
_MODEL_REQUEST_URL = re.compile(r"/assistants/(?:virtual|[^/]+)/model(?:\?.*)?$")

_VISIBILITY_CONTROL_SCRIPT = """
(() => {
  let hidden = false;
  Object.defineProperty(document, 'hidden', { configurable: true, get: () => hidden });
  Object.defineProperty(document, 'visibilityState', {
    configurable: true,
    get: () => (hidden ? 'hidden' : 'visible'),
  });
  window.__setPageHidden = (value) => {
    hidden = value;
    document.dispatchEvent(new Event('visibilitychange'));
  };
})();
"""

# Placeholders: __SUPPORTED__ (true/false) and __PERMISSION__ (JSON string or null,
# null keeps the browser's own permission value).
_NOTIFICATION_RECORDER_SCRIPT = """
(() => {
  window.__notificationCalls = [];
  const supported = __SUPPORTED__;
  const permission = __PERMISSION__;
  if (!supported) {
    delete window.Notification;
    return;
  }
  const Native = window.Notification;
  function RecordingNotification(title, options) {
    window.__notificationCalls.push({ title: title, body: options ? options.body : null });
  }
  Object.defineProperty(RecordingNotification, 'permission', {
    get: () => (permission === null ? Native.permission : permission),
  });
  RecordingNotification.requestPermission = () =>
    Promise.resolve(RecordingNotification.permission);
  window.Notification = RecordingNotification;
})();
"""


class ResponseReadyTab(BasePage):
    """Observes and drives the response-ready signal of the CodeMie tab."""

    def __init__(self, page):
        super().__init__(page)
        self.plain_title = None
        self._page_errors = []

    # ==================== ELEMENTS ====================

    @property
    def announcer(self) -> Locator:
        """Polite sr-only live region at app level: 'AI response ready' while the signal is pending, empty otherwise."""
        return self.page.locator("output.sr-only")

    # ==================== SETUP (before navigation) ====================

    @step
    def install_visibility_control(self):
        """Replace document.hidden / visibilityState so the test can mark the page hidden or visible."""
        self.page.add_init_script(_VISIBILITY_CONTROL_SCRIPT)
        return self

    @step
    def record_notifications(
        self, permission: Optional[str] = None, supported: bool = True
    ):
        """Replace window.Notification with a recorder of constructor calls.

        Args:
            permission: value Notification.permission reports; None keeps the
                browser context's own value (use context.grant_permissions to grant it).
            supported: False removes window.Notification entirely.
        """
        script = _NOTIFICATION_RECORDER_SCRIPT.replace(
            "__SUPPORTED__", "true" if supported else "false"
        ).replace("__PERMISSION__", json.dumps(permission))
        self.page.add_init_script(script)
        return self

    # ==================== ACTIONS ====================

    @step
    def remember_plain_title(self):
        """Store the current tab title as the plain (unprefixed) page title."""
        title = self.page.title()
        assert_that(
            title,
            not_(starts_with(RESPONSE_READY_TITLE_PREFIX)),
            "Tab title already carries the response-ready prefix before any reply",
        )
        self.plain_title = title
        return self

    @step
    def mark_page_hidden(self):
        """Report the page as hidden and fire visibilitychange."""
        self.page.evaluate("window.__setPageHidden(true)")
        return self

    @step
    def mark_page_visible(self):
        """Report the page as visible and fire visibilitychange."""
        self.page.evaluate("window.__setPageHidden(false)")
        return self

    @step
    def start_collecting_page_errors(self):
        """Collect uncaught page errors from now on."""
        self._page_errors.clear()
        self.page.on("pageerror", lambda error: self._page_errors.append(str(error)))
        return self

    @step
    def reload_page(self):
        """Reload the page without waiting for network idle.

        The resumed reply streams over a long-lived connection, so the network
        never goes idle until the reply finishes.
        """
        self.page.reload()
        self.page.wait_for_load_state("domcontentloaded")
        return self

    @step
    def abort_model_request_during(self, action: Callable[[], object]):
        """Abort the request that starts the generation, then run ``action`` and wait for the failure."""
        self.page.route(_MODEL_REQUEST_URL, lambda route: route.abort())
        with self.page.expect_event(
            "requestfailed",
            predicate=lambda request: bool(_MODEL_REQUEST_URL.search(request.url)),
            timeout=30000,
        ):
            action()
        return self

    # ==================== VERIFICATIONS ====================

    @step
    def should_have_plain_title(self):
        """Verify the tab title is the plain page title, with no response-ready prefix."""
        expect(self.page).to_have_title(self.plain_title)
        return self

    @step
    def should_have_response_ready_title(self, timeout: int = 90000):
        """Verify the tab title is 'Response ready - <plain page title>'."""
        expect(self.page).to_have_title(
            f"{RESPONSE_READY_TITLE_PREFIX}{self.plain_title}", timeout=timeout
        )
        return self

    @step
    def should_announce_response_ready(self):
        """Verify the live region reads 'AI response ready'."""
        expect(self.announcer).to_have_text(RESPONSE_READY_ANNOUNCER_TEXT)
        return self

    @step
    def should_have_empty_announcer(self):
        """Verify the live region is empty."""
        expect(self.announcer).to_have_text("")
        return self

    @step
    def should_have_constructed_notifications(self, count: int):
        """Verify exactly ``count`` Notification objects were constructed."""
        if count > 0:
            self.page.wait_for_function(
                "expected => window.__notificationCalls.length >= expected",
                arg=count,
            )
        assert_that(
            self._notification_calls(),
            has_length(count),
            f"Expected {count} Notification constructor call(s)",
        )
        return self

    @step
    def should_have_constructed_notification(self, title: str, body: str):
        """Verify exactly one Notification was constructed, with the given title and body."""
        self.page.wait_for_function("window.__notificationCalls.length >= 1")
        assert_that(
            self._notification_calls(),
            equal_to([{"title": title, "body": body}]),
            "Notification constructor calls differ from the expected single call",
        )
        return self

    @step
    def should_have_no_page_errors(self):
        """Verify no uncaught page error was raised since collection started."""
        assert_that(self._page_errors, empty(), "Uncaught page errors were raised")
        return self

    def _notification_calls(self):
        return self.page.evaluate("window.__notificationCalls")
