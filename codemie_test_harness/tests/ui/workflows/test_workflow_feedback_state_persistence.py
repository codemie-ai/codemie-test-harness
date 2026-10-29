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

"""Workflow chat like/dislike feedback state (with hydration limitation).

Known workflow defect: message-index mismatch prevents userMark
hydration after reload.
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.chats.chat_page import ChatPage
from codemie_test_harness.tests.ui.pageobject.workflows import WorkflowDetailsPage
from codemie_test_harness.tests.ui.test_data.chat_test_data import (
    get_simple_test_message,
)


@pytest.mark.workflow
@pytest.mark.ui
def test_workflow_chat_like_dislike_feedback_state_visible_with_hydration_limitation(
    page, test_workflow
):
    """Like/dislike state in workflow chat (xfail on reload due to hydration defect)."""
    details_page = WorkflowDetailsPage(page)
    details_page.navigate_to(test_workflow.id)
    details_page.click_run_chat()

    chat_page = ChatPage(page)
    test_message = get_simple_test_message()
    chat_page.send_message(test_message.content)
    chat_page.wait_for_assistant_response()

    chat_page.should_have_like_button_inactive()
    chat_page.click_assistant_message_like()
    chat_page.should_have_like_button_active()

    chat_page.refresh_page()
    chat_page.should_have_history_visible()

    try:
        chat_page.should_have_like_button_active()
    except AssertionError:
        pytest.xfail(
            reason="Workflow chat userMark not hydrated after reload (message index mismatch)"
        )

    chat_page.click_assistant_message_remove_like()
    chat_page.should_have_delete_feedback_dialog_visible()
    chat_page.confirm_delete_feedback()
    chat_page.should_have_like_button_inactive()

    chat_page.refresh_page()
    chat_page.should_have_history_visible()
    chat_page.should_have_like_button_inactive()

    chat_page.should_have_dislike_button_inactive()
    chat_page.click_assistant_message_dislike()
    chat_page.should_have_submit_feedback_dialog_visible()
    chat_page.select_feedback_option("Other")
    chat_page.send_feedback()
    chat_page.should_have_dislike_button_active()

    chat_page.refresh_page()
    chat_page.should_have_history_visible()

    try:
        chat_page.should_have_dislike_button_active()
    except AssertionError:
        pytest.xfail(
            reason="Workflow chat userMark not hydrated after reload (message index mismatch)"
        )

    chat_page.click_assistant_message_remove_dislike()
    chat_page.should_have_delete_feedback_dialog_visible()
    chat_page.confirm_delete_feedback()
    chat_page.should_have_dislike_button_inactive()

    chat_page.refresh_page()
    chat_page.should_have_history_visible()
    chat_page.should_have_dislike_button_inactive()
