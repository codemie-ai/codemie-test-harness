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
from hamcrest import assert_that, equal_to

from codemie_test_harness.tests.enums.tools import Toolkit, NotificationTool
from codemie_test_harness.tests.test_data.notification_tools_test_data import (
    email_tool_prompt,
    email_response,
    EMAIL_SUBJECT,
    EMAIL_BODY,
    EMAIL_INTEGRATION_PARAMS,
    TELEGRAM_TOOL_PROMPT,
    TELEGRAM_RESPONSE,
)
from codemie_test_harness.tests.utils.base_utils import assert_tool_triggered
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver


@pytest.mark.workflow
@pytest.mark.workflow_with_assistant
@pytest.mark.notification
@pytest.mark.email
@pytest.mark.api
@pytest.mark.skipif(
    EnvironmentResolver.is_localhost(),
    reason="Skipping this test on local environment",
)
@pytest.mark.parametrize(
    "integration_fixture, message_operator_fixture, recipient_email",
    EMAIL_INTEGRATION_PARAMS,
)
def test_workflow_with_email_tool(
    assistant,
    similarity_check,
    workflow_utils,
    workflow_with_assistant,
    request,
    integration_fixture,
    message_operator_fixture,
    recipient_email,
):
    # Get the appropriate fixtures
    integration = request.getfixturevalue(integration_fixture)
    message_operator = request.getfixturevalue(message_operator_fixture)

    assistant_instance = assistant(
        Toolkit.NOTIFICATION, NotificationTool.EMAIL, settings=integration
    )

    workflow_with_assistant_instance = workflow_with_assistant(
        assistant_instance, email_tool_prompt(recipient_email)
    )
    response = workflow_utils.execute_workflow(
        workflow_with_assistant_instance.id, assistant_instance.name
    )

    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        workflow_with_assistant_instance
    )
    assert_tool_triggered(NotificationTool.EMAIL, triggered_tools)

    similarity_check.check_similarity(response, email_response(recipient_email))

    message_data = message_operator.get_messages_list()
    latest_message_id = message_data["messages"][-1]["id"]
    message_content = message_operator.get_specific_message_content(latest_message_id)

    message_body = message_content["snippet"]
    message_title = next(
        (
            header["value"]
            for header in message_content["payload"]["headers"]
            if header["name"].lower() == "subject"
        )
    )

    assert_that(message_body, equal_to(EMAIL_BODY))
    assert_that(message_title, equal_to(EMAIL_SUBJECT))


@pytest.mark.workflow
@pytest.mark.workflow_with_assistant
@pytest.mark.notification
@pytest.mark.telegram
@pytest.mark.api
def test_workflow_with_telegram_tool(
    assistant,
    similarity_check,
    workflow_utils,
    workflow_with_assistant,
    telegram_integration,
):
    assistant_instance = assistant(
        Toolkit.NOTIFICATION, NotificationTool.TELEGRAM, settings=telegram_integration
    )
    workflow_with_assistant_instance = workflow_with_assistant(
        assistant_instance, TELEGRAM_TOOL_PROMPT
    )
    response = workflow_utils.execute_workflow(
        workflow_with_assistant_instance.id, assistant_instance.name
    )

    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        workflow_with_assistant_instance
    )
    assert_tool_triggered(NotificationTool.TELEGRAM, triggered_tools)

    similarity_check.check_similarity(response, TELEGRAM_RESPONSE)
