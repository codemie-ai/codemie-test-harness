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

"""Regression coverage for workflow chat should not fire assistant endpoint requests with workflow ID.

Related: parent issue (false 'Assistant not found' toast)
"""

import re

import pytest
from hamcrest import assert_that, empty, greater_than

from codemie_test_harness.tests.ui.pageobject.chats.chat_page import ChatPage
from codemie_test_harness.tests.ui.pageobject.workflows import WorkflowDetailsPage


@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.prod_regression
def test_workflow_chat_send_message_no_assistant_endpoint_request(page, test_workflow):
    """Regression: workflow chat should not call /assistants/{workflow_id} when sending a message (running workflow).

    AC1: No assistant endpoint request with workflow ID.
    AC2: Workflow execution request WAS made (positive control).
    AC3: No error toast (regression guard).
    """
    workflow = test_workflow
    details_page = WorkflowDetailsPage(page)
    details_page.navigate_to(workflow.id)
    details_page.click_run_chat()

    chat_page = ChatPage(page)
    chat_page.should_have_chat_input_visible()

    captured_requests = chat_page.capture_requests_during(
        lambda: (
            chat_page.send_message("Hello, please provide a greeting"),
            chat_page.wait_for_generation_to_start(),
        )
    )

    workflow_execution_requests = [
        r
        for r in captured_requests
        if re.search(rf"/workflows/{re.escape(workflow.id)}/executions", r.url)
    ]
    assistant_requests_with_workflow_id = [
        r
        for r in captured_requests
        if re.search(
            rf"/assistants/(?:virtual|[^/]+)/.*{re.escape(workflow.id)}", r.url
        )
    ]

    assert_that(
        assistant_requests_with_workflow_id,
        empty(),
        f"Regression: assistant requests found with workflow ID {workflow.id}. "
        f"Requests: {[r.url for r in assistant_requests_with_workflow_id]}",
    )

    assert_that(
        len(workflow_execution_requests),
        greater_than(0),
        f"No workflow execution request found for {workflow.id}. "
        "Expected POST to /workflows/{{id}}/executions.",
    )

    chat_page.should_not_have_error_toast()
