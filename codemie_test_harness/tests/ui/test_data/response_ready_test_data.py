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

"""Test data for the "response ready" tab signal and browser notification."""

from dataclasses import dataclass
from typing import Optional

# Title prefix applied while a reply that finished in a hidden tab is pending
# (RESPONSE_READY_PREFIX in the frontend, followed by the plain page title).
RESPONSE_READY_TITLE_PREFIX = "Response ready - "

# Text of the polite sr-only live region rendered while the signal is pending.
RESPONSE_READY_ANNOUNCER_TEXT = "AI response ready"

# Browser notification constructed when the reply finishes in a hidden tab
# and notification permission is already granted.
NOTIFICATION_TITLE = "CodeMie"
NOTIFICATION_BODY = "AI response is ready"

# Prompts. The default test assistant answers within about a second; the slow
# conversation fixture is used wherever the reply must still be running.
SHORT_PROMPT = "Reply with one short greeting."
LONG_PROMPT = "Explain the history of the Roman Empire"


@dataclass
class NotificationState:
    """State of the browser Notification API the page sees.

    ``permission`` is the value ``Notification.permission`` reports; ``supported``
    False removes ``window.Notification`` altogether.
    """

    id: str
    permission: Optional[str]
    supported: bool


NOTIFICATION_STATES_WITHOUT_GRANT = [
    NotificationState(id="permission-default", permission="default", supported=True),
    NotificationState(id="permission-denied", permission="denied", supported=True),
    NotificationState(id="api-absent", permission=None, supported=False),
]
