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

"""UI tests for a workflow execution history item linked to a conversation.

Covers the case: while a workflow execution is still linked to a live
conversation, the "Remove" action in the execution history sidebar must be
blocked (disabled with an explanatory tooltip). Once the conversation is
deleted, the execution is removed automatically and no longer lingers as an
orphaned, permanently-blocked history entry.
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.workflows import WorkflowExecutionsPage
from codemie_test_harness.tests.ui.test_data.workflows_test_data import (
    EXECUTION_REMOVE_BLOCKED_TOOLTIP_TEXT,
)


@pytest.mark.workflow
@pytest.mark.workflow_execution
@pytest.mark.ui
@pytest.mark.not_for_parallel_run
@pytest.mark.prod_regression
def test_execution_remove_blocked_while_conversation_exists_then_removed_after_deletion(
    page, test_workflow, conversation_linked_execution, conversation_utils
):
    """A conversation-linked execution shows a disabled 'Remove' option with a
    blocking tooltip while the conversation exists; once the conversation is
    deleted, the execution disappears from the history sidebar."""
    conversation_id, execution = conversation_linked_execution

    executions_page = WorkflowExecutionsPage(page)
    executions_page.navigate_to(test_workflow.id, execution.execution_id)

    history_item = executions_page.get_first_execution_history_item()
    history_item.should_show_remove_blocked_tooltip(
        EXECUTION_REMOVE_BLOCKED_TOOLTIP_TEXT
    )

    conversation_utils.delete_conversation(conversation_id)
    executions_page.refresh_page()

    history_item = executions_page.get_first_execution_history_item()
    history_item.should_not_be_visible()
