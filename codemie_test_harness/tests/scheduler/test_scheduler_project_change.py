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

"""Scheduler behaviour after the target resource is moved to another project.

A scheduler skips its run when the assistant or workflow it targets no longer
belongs to the scheduler's project. Each test pairs the moved resource with a
positive control: a second scheduler with the same cron on an unmoved resource,
which must fire. Without it, "nothing happened" could also mean the scheduler
never fired at all.
"""

import pytest
from hamcrest import assert_that, equal_to, has_item

from codemie_sdk.models.workflow import WorkflowMode
from codemie_test_harness.tests import PROJECT
from codemie_test_harness.tests.test_data.project_change_trigger_test_data import (
    CONTROL_FIRE_TIMEOUT,
    MOVED_SCHEDULER_GRACE_TIMEOUT,
    shared_cron_schedule,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name, wait_for_entity
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver
from codemie_test_harness.tests.utils.yaml_utils import (
    AssistantModel,
    StateModel,
    WorkflowYamlModel,
    prepare_yaml_content,
)


@pytest.fixture
def unmoved_workflow(workflow_utils, default_llm):
    """Second workflow in the test project, the positive control of a scheduler test.

    The shared ``workflow`` fixture tracks only the last workflow it created, so a
    test needing two workflows creates the second one here, with its own cleanup.
    """
    name = get_random_name()
    workflow_yaml = WorkflowYamlModel(
        assistants=[
            AssistantModel(
                id=name,
                model=default_llm.base_name,
                system_prompt="Act as a helpful assistant",
            )
        ],
        states=[StateModel(id=name, assistant_id=name)],
    )
    created = workflow_utils.create_workflow(
        workflow_type=WorkflowMode.SEQUENTIAL,
        workflow_yaml=prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True)),
        workflow_name=name,
        shared=True,
        project_name=PROJECT,
    )
    yield created
    try:
        workflow_utils.delete_workflow(created)
    except Exception:
        pass


@pytest.mark.scheduler
@pytest.mark.project
@pytest.mark.api
@pytest.mark.skipif(
    EnvironmentResolver.is_sandbox(),
    reason="Scheduler is disabled on sandbox environments",
)
def test_scheduler_skips_assistant_moved_to_other_project(
    project,
    assistant_factory,
    assistant_utils,
    scheduler_integration,
    conversation_utils,
):
    # @case webhook-scheduler-project-change_TC_004
    other_project = project()
    moved_assistant = assistant_factory.create(project_name=PROJECT)
    control_assistant = assistant_factory.create(project_name=PROJECT)
    schedule = shared_cron_schedule()
    for target in (moved_assistant, control_assistant):
        scheduler_integration(
            alias=get_random_name(),
            resource_type="assistant",
            resource_id=target.id,
            prompt=f"Scheduler project change {target.id}",
            schedule=schedule,
            project_name=PROJECT,
        )

    stored = assistant_utils.move_assistant_to_project(
        moved_assistant.id, other_project.name
    )
    assert_that(
        stored.project, equal_to(other_project.name), "Assistant was not moved."
    )

    # Positive control: the same cron fires for the assistant that stayed.
    control_conversation = wait_for_entity(
        lambda: conversation_utils.list_conversations(),
        entity_name=f"Scheduler: {control_assistant.id}",
        timeout=CONTROL_FIRE_TIMEOUT,
    )
    assert_that(
        control_conversation.initial_assistant_id, equal_to(control_assistant.id)
    )
    assert_that(control_conversation.assistant_ids, has_item(control_assistant.id))

    # The scheduler on the moved assistant is due at the same minute: it must not run.
    with pytest.raises(TimeoutError):
        wait_for_entity(
            lambda: conversation_utils.list_conversations(),
            entity_name=f"Scheduler: {moved_assistant.id}",
            timeout=MOVED_SCHEDULER_GRACE_TIMEOUT,
        )


@pytest.mark.scheduler
@pytest.mark.project
@pytest.mark.api
@pytest.mark.skipif(
    EnvironmentResolver.is_sandbox(),
    reason="Scheduler is disabled on sandbox environments",
)
def test_scheduler_skips_workflow_moved_to_other_project(
    project,
    workflow_with_virtual_assistant,
    unmoved_workflow,
    workflow_utils,
    scheduler_integration,
):
    # @case webhook-scheduler-project-change_TC_005
    other_project = project()
    moved_workflow = workflow_with_virtual_assistant(
        get_random_name(), project_name=PROJECT
    )
    moved_prompt = f"Scheduler project change {moved_workflow.id}"
    control_prompt = f"Scheduler project change {unmoved_workflow.id}"
    schedule = shared_cron_schedule()
    for target, prompt in (
        (moved_workflow, moved_prompt),
        (unmoved_workflow, control_prompt),
    ):
        scheduler_integration(
            alias=get_random_name(),
            resource_type="workflow",
            resource_id=target.id,
            prompt=prompt,
            schedule=schedule,
            project_name=PROJECT,
        )

    workflow_utils.update_workflow(
        workflow_utils.get_workflow(moved_workflow.id), project=other_project.name
    )
    stored = workflow_utils.get_workflow(moved_workflow.id)
    assert_that(stored.project, equal_to(other_project.name), "Workflow was not moved.")

    # Positive control: the same cron runs the workflow that stayed.
    control_execution = wait_for_entity(
        lambda: workflow_utils.get_executions(unmoved_workflow),
        entity_name=control_prompt,
        timeout=CONTROL_FIRE_TIMEOUT,
    )
    assert_that(control_execution.workflow_id, equal_to(unmoved_workflow.id))

    # The scheduler on the moved workflow is due at the same minute: it must not run.
    with pytest.raises(TimeoutError):
        wait_for_entity(
            lambda: workflow_utils.get_executions(moved_workflow),
            entity_name=moved_prompt,
            timeout=MOVED_SCHEDULER_GRACE_TIMEOUT,
        )
