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

"""UI test for the recipient's (grantee's) side of a shared assistant.

tests/ui/conftest.py's autouse `login` always authenticates as the primary
owner account (AUTH_USERNAME). This module overrides it for its one test so
the browser session is the shared-with recipient (B) instead — the same
override pattern as tests/ui/budgets/conftest.py and tests/ui/auditor/conftest.py,
scoped to this file only.
"""

import os

import pytest

from codemie_test_harness.tests.ui.pageobject.assistants.assistants_page import (
    AssistantsPage,
)
from codemie_test_harness.tests.ui.pageobject.login_page import LoginPage
from codemie_test_harness.tests.ui.test_data.chat_test_data import (
    get_simple_test_message,
)
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager


@pytest.fixture(autouse=True)
def login(page):
    """Override tests/ui/conftest.py login — authenticate as the shared-with recipient (B)."""
    username = CredentialsManager.get_parameter(
        "AUTH_USERNAME_DEFAULT", CredentialsManager.get_parameter("AUTH_USERNAME")
    )
    password = CredentialsManager.get_parameter(
        "AUTH_PASSWORD_DEFAULT", CredentialsManager.get_parameter("AUTH_PASSWORD")
    )
    user = get_client(username=username, password=password).users.about_me()
    frontend_url = os.getenv("FRONTEND_URL", "")
    LoginPage(page).login_suppressing_popups(
        username, password, user.user_id, frontend_url
    )


@pytest.mark.assistant
@pytest.mark.ui
def test_shared_recipient_can_chat_but_sees_no_edit_controls(
    assistant_factory, client, regular_client, page
):
    """@case share-an-assistant-with-selected_TC_003"""
    assistant = assistant_factory.create()
    grantee_id = regular_client.users.about_me().user_id
    client.assistants.share(assistant.id, [grantee_id])

    assistants_page = AssistantsPage(page)
    assistants_page.search_assistants(assistant.name)
    details_page = assistants_page.open_assistant_details(assistant.name)

    details_page.should_see_chat_now_button()
    details_page.should_not_see_edit_button()

    chat_page = details_page.click_chat_now()
    test_message = get_simple_test_message()
    chat_page.send_message(test_message.content)
    chat_page.should_have_message_sent(test_message.content)
    chat_page.wait_for_assistant_response()
    chat_page.should_have_assistant_response()
