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

"""Tests for workflow description displayed in workflow chat intro area.

TC-001: A workflow with a configured description shows that description in the
workflow chat intro/welcome area before any message is sent.

Acceptance criteria covered:
- AC-1: Workflow chat displays the workflow description when configured.
- AC-2: Description appears in the same intro area used by assistant chat.
- AC-3 (inline): No empty placeholder / broken-layout element is present.
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.chats.chat_page import ChatPage
from codemie_test_harness.tests.ui.pageobject.workflows import WorkflowDetailsPage


@pytest.mark.sanity
@pytest.mark.workflow
@pytest.mark.ui
def test_workflow_chat_displays_description(page, test_workflow_with_description):
    """Workflow with a configured description shows it in the workflow chat intro area.

    Steps:
    1. Arrange  — fixture creates a workflow whose ``description`` field is set to a
                  unique per-run string.
    2. Act      — navigate to workflow details, click Run Chat; browser lands on
                  /chats/<id>.
    3. Assert   — AC-1: description text is visible in the chat intro area.
                  AC-2: text is scoped inside the ChatPromptStarters intro container.
                  AC-3 (inline): no empty description placeholder element is present.
    """
    workflow, description_text = test_workflow_with_description

    # Act: open the workflow details page and start a chat session
    details_page = WorkflowDetailsPage(page)
    details_page.navigate_to(workflow.id)
    details_page.click_run_chat()

    chat_page = ChatPage(page)

    # Wait for the chat input to confirm the page has fully loaded
    chat_page.should_have_chat_input_visible()

    # Assert AC-1 & AC-2: description is visible in the intro/welcome area
    chat_page.should_show_chat_description(description_text)

    # Assert AC-3 (inline negative path): no empty description placeholder in DOM
    chat_page.should_not_show_empty_description_placeholder()
