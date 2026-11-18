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

"""Webhook behaviour after the target resource is moved to another project.

A webhook belongs to one project and refuses to invoke an assistant or workflow
that no longer belongs to it: HTTP 401, nothing is queued.
"""

import pytest
from hamcrest import assert_that, empty, equal_to

from codemie_test_harness.tests import PROJECT
from codemie_test_harness.tests.test_data.project_change_trigger_test_data import (
    webhook_assistant_project_mismatch_detail,
    webhook_workflow_project_mismatch_detail,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name


@pytest.mark.webhook
@pytest.mark.project
@pytest.mark.api
def test_webhook_rejects_assistant_moved_to_other_project(
    project,
    assistant,
    assistant_utils,
    webhook_integration,
    webhook_utils,
    conversation_utils,
):
    # @case webhook-scheduler-project-change_TC_001
    other_project = project()
    webhook_id = get_random_name()
    moved_assistant = assistant(project_name=PROJECT)
    webhook_integration(
        webhook_id, "assistant", moved_assistant.id, project_name=PROJECT
    )

    stored = assistant_utils.move_assistant_to_project(
        moved_assistant.id, other_project.name
    )
    assert_that(
        stored.project, equal_to(other_project.name), "Assistant was not moved."
    )

    response = webhook_utils.trigger_webhook(
        webhook_id, data=f"Test message for {webhook_id}"
    )

    assert_that(response.status_code, equal_to(401))
    assert_that(
        response.json()["detail"],
        equal_to(
            webhook_assistant_project_mismatch_detail(moved_assistant.id, PROJECT)
        ),
    )
    conversations = conversation_utils.get_conversation_by_assistant_id(
        moved_assistant.id
    )
    assert_that(
        conversations, empty(), "A rejected webhook must not create a conversation."
    )


@pytest.mark.webhook
@pytest.mark.project
@pytest.mark.api
def test_webhook_rejects_workflow_moved_to_other_project(
    project,
    workflow_with_virtual_assistant,
    workflow_utils,
    webhook_integration,
    webhook_utils,
):
    # @case webhook-scheduler-project-change_TC_002
    other_project = project()
    webhook_id = get_random_name()
    workflow = workflow_with_virtual_assistant(webhook_id, project_name=PROJECT)
    webhook_integration(webhook_id, "workflow", workflow.id, project_name=PROJECT)

    workflow_utils.update_workflow(
        workflow_utils.get_workflow(workflow.id), project=other_project.name
    )
    stored = workflow_utils.get_workflow(workflow.id)
    assert_that(stored.project, equal_to(other_project.name), "Workflow was not moved.")

    response = webhook_utils.trigger_webhook(
        webhook_id, data=f"Test message for {webhook_id}"
    )

    assert_that(response.status_code, equal_to(401))
    assert_that(
        response.json()["detail"],
        equal_to(webhook_workflow_project_mismatch_detail(workflow.id, PROJECT)),
    )
    executions = workflow_utils.get_executions(workflow)
    assert_that(executions, empty(), "A rejected webhook must not create an execution.")
