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

"""Invalid run attributes are refused with 422 and nothing runs."""

import uuid

import pytest
from hamcrest import assert_that, empty
from requests import HTTPError

from codemie_test_harness.tests.test_data.run_attributes_test_data import (
    CHAT_INVALID_ATTRIBUTES,
    CONVERSATION_NOT_FOUND,
    RUN_PROMPT,
    WORKFLOW_INVALID_ATTRIBUTES,
    WORKFLOW_TASK,
)
from codemie_test_harness.tests.utils.base_utils import assert_error_details
from codemie_test_harness.tests.utils.run_attributes_utils import (
    assert_error_message,
)


@pytest.mark.parametrize("invalid", CHAT_INVALID_ATTRIBUTES)
@pytest.mark.analytics
@pytest.mark.conversations
@pytest.mark.api
def test_chat_with_invalid_attributes_is_rejected_and_nothing_runs(
    assistant_factory, assistant_utils, conversation_utils, invalid
):
    # @case allow-callers-to-associate-custom_TC_003
    created_assistant = assistant_factory.create()
    conversation_id = str(uuid.uuid4())

    with pytest.raises(HTTPError) as rejected:
        assistant_utils.ask_assistant(
            created_assistant,
            RUN_PROMPT,
            conversation_id=conversation_id,
            attributes=invalid.attributes,
        )

    assert_error_message(rejected.value.response, 422, invalid.message)
    with pytest.raises(HTTPError) as not_found:
        conversation_utils.get_conversation_by_id(conversation_id)
    assert_error_details(
        not_found.value.response,
        404,
        CONVERSATION_NOT_FOUND.format(conversation_id=conversation_id),
    )


@pytest.mark.parametrize("invalid", WORKFLOW_INVALID_ATTRIBUTES)
@pytest.mark.analytics
@pytest.mark.workflow
@pytest.mark.api
def test_workflow_execution_with_invalid_attributes_is_rejected_and_nothing_runs(
    assistant_factory, workflow_with_assistant, workflow_utils, invalid
):
    # @case allow-callers-to-associate-custom_TC_003
    workflow = workflow_with_assistant(assistant_factory.create(), WORKFLOW_TASK)

    with pytest.raises(HTTPError) as rejected:
        workflow_utils.send_workflow_execution_request(
            workflow.id, user_input=RUN_PROMPT, attributes=invalid.attributes
        )

    assert_error_message(rejected.value.response, 422, invalid.message)
    assert_that(
        workflow_utils.get_executions(workflow),
        empty(),
        "a rejected request must not create an execution",
    )
