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

import json

import pytest

from codemie_test_harness.tests.enums.tools import NotificationTool
from codemie_test_harness.tests.test_data.notification_tools_test_data import (
    EMAIL_SUBJECT,
    EMAIL_BODY,
    CHAT_ID,
    TELEGRAM_BODY,
    email_response,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver

GMAIL_USER_EMAIL = CredentialsManager.get_parameter("GMAIL_USER_EMAIL")

notification_tools_test_data = [
    pytest.param(
        NotificationTool.EMAIL,
        {
            "recipient_emails": [GMAIL_USER_EMAIL],
            "subject": f"{EMAIL_SUBJECT}",
            "body": f"{EMAIL_BODY}",
        },
        email_response(GMAIL_USER_EMAIL),
        marks=[
            pytest.mark.email,
            pytest.mark.skipif(
                EnvironmentResolver.is_localhost(),
                reason="Skipping this test on local environment",
            ),
            pytest.mark.xfail(reason="EPAM blocks gmail smtp now", strict=False),
        ],
        id=NotificationTool.EMAIL,
    ),
    pytest.param(
        NotificationTool.TELEGRAM,
        {
            "method": "POST",
            "relative_url": "sendMessage",
            "params": json.dumps({"chat_id": CHAT_ID, "text": TELEGRAM_BODY}),
        },
        {
            "ok": "true",
            "result": {
                "from": {"is_bot": "true"},
                "chat": {"id": CHAT_ID},
                "text": TELEGRAM_BODY,
            },
        },
        marks=pytest.mark.telegram,
        id=NotificationTool.TELEGRAM,
    ),
]
