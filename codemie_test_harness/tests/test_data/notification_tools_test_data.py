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

import pytest

from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager

CHAT_ID = CredentialsManager.get_parameter("TELEGRAM_CHAT_ID")

EMAIL_SUBJECT = "Test email"

EMAIL_BODY = "This is a test email"

TELEGRAM_BODY = "CodeMie Test Message"

GMAIL_USER_EMAIL = CredentialsManager.get_parameter("GMAIL_USER_EMAIL")


def email_tool_prompt(email_address: str = GMAIL_USER_EMAIL) -> str:
    """Generate email tool prompt for given email address."""
    return f"""
    Write an email to the '{email_address}' with the following information:
        - Subject: '{EMAIL_SUBJECT}'
        - Body: '{EMAIL_BODY}'
"""


def email_response(email_address: str) -> str:
    """Generate expected email response for given email address."""
    return f"The email has been sent successfully to {email_address} with the subject '{EMAIL_SUBJECT}' and the body '{EMAIL_BODY}'."


TELEGRAM_TOOL_PROMPT = f"Send message to chat_id {CHAT_ID} with text '{TELEGRAM_BODY}'"

TELEGRAM_RESPONSE = (
    f"The message '{TELEGRAM_BODY}' has been successfully sent to chat_id {CHAT_ID}."
)

# Email test parametrize data for Gmail and Azure email integrations
EMAIL_INTEGRATION_PARAMS = [
    pytest.param(
        "email_integration",
        "gmail_message_operator",
        CredentialsManager.get_parameter("GMAIL_USER_EMAIL"),
        id="gmail",
        marks=pytest.mark.xfail(reason="EPAM blocks gmail smtp now", strict=False),
    ),
    pytest.param(
        "azure_email_integration",
        "azure_message_operator",
        CredentialsManager.get_parameter("AZURE_EMAIL_USER_EMAIL"),
        id="azure_email",
    ),
]
