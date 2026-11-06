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

"""UI tests for the owner's side of sharing an assistant: the grant-access
('Share assistant') popup's Remove control, and the Assistant Details
'SHARED WITH' section reflecting live grants and revocations.

Logged in as the default owner (A, tests/ui/conftest.py's autouse `login`).
Grants/revokes are seeded through the API so each test exercises only the UI
surface named by its case.
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.assistants.assistants_page import (
    AssistantsPage,
)


@pytest.mark.assistant
@pytest.mark.ui
def test_owner_removes_access_from_share_popup_immediately_and_persists(
    assistant_factory, client, regular_client, page
):
    """@case share-an-assistant-with-selected_TC_005"""
    assistant = assistant_factory.create()
    grantee = regular_client.users.about_me()
    client.assistants.share(assistant.id, [grantee.user_id])

    assistants_page = AssistantsPage(page)
    assistants_page.search_assistants(assistant.name)
    popup = assistants_page.open_share_popup(assistant.name)
    popup.should_be_open()
    popup.should_list_user(grantee.name)

    popup.remove_user(grantee.name)
    popup.should_not_list_user(grantee.name)

    page.reload()
    assistants_page = AssistantsPage(page)
    assistants_page.search_assistants(assistant.name)
    reopened_popup = assistants_page.open_share_popup(assistant.name)
    reopened_popup.should_not_list_user(grantee.name)


@pytest.mark.assistant
@pytest.mark.ui
def test_shared_with_section_reflects_grant_and_revoke(
    assistant_factory, client, regular_client, page
):
    """@case share-an-assistant-with-selected_TC_010"""
    assistant = assistant_factory.create()
    grantee = regular_client.users.about_me()

    client.assistants.share(assistant.id, [grantee.user_id])

    assistants_page = AssistantsPage(page)
    assistants_page.search_assistants(assistant.name)
    details_page = assistants_page.open_assistant_details(assistant.name)
    details_page.should_list_shared_with(grantee.name)

    client.assistants.revoke_share(assistant.id, [grantee.user_id])

    page.reload()
    details_page.should_have_no_shared_with_section()
