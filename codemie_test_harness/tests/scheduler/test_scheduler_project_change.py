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

Every resource is created in fixtures. The test body then computes the cron
minute, creates the two schedulers in the original project and moves the target,
in that order: the guard under test runs when the scheduler fires, so the move
must come after the scheduler exists, and nothing else may eat into the cron lead.
"""

import pytest
from hamcrest import assert_that, equal_to, has_item

from codemie_test_harness.tests import PROJECT
from codemie_test_harness.tests.test_data.project_change_trigger_test_data import (
    CONTROL_FIRE_TIMEOUT,
    MOVED_SCHEDULER_GRACE_TIMEOUT,
    SCHEDULER_TEST_TIMEOUT,
    assert_cron_minute_still_ahead,
    shared_cron_schedule,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name, wait_for_entity
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver


@pytest.fixture
def other_project(project):
    """Project the target resource is moved to."""
    return project()


@pytest.fixture
def create_scheduler(scheduler_integration):
    """Create a scheduler in the test project on the shared cron, in its timezone."""

    def _create(resource_type, resource_id, prompt, cron):
        return scheduler_integration(
            alias=get_random_name(),
            resource_type=resource_type,
            resource_id=resource_id,
            prompt=prompt,
            schedule=cron.expression,
            timezone=cron.timezone,
            project_name=PROJECT,
        )

    return _create


@pytest.fixture
def moved_assistant(assistant_factory):
    return assistant_factory.create(project_name=PROJECT)


@pytest.fixture
def control_assistant(assistant_factory):
    return assistant_factory.create(project_name=PROJECT)


@pytest.fixture
def moved_workflow(workflow_with_virtual_assistant):
    return workflow_with_virtual_assistant(get_random_name(), project_name=PROJECT)


@pytest.fixture
def control_workflow(workflow_with_virtual_assistant):
    return workflow_with_virtual_assistant(get_random_name(), project_name=PROJECT)


@pytest.mark.scheduler
@pytest.mark.project
@pytest.mark.api
@pytest.mark.timeout(SCHEDULER_TEST_TIMEOUT)
@pytest.mark.skipif(
    EnvironmentResolver.is_sandbox(),
    reason="Scheduler is disabled on sandbox environments",
)
def test_scheduler_skips_assistant_moved_to_other_project(
    other_project,
    moved_assistant,
    control_assistant,
    assistant_utils,
    create_scheduler,
    conversation_utils,
):
    # @case webhook-scheduler-project-change_TC_004
    # Compute the cron only now: from here to the control wait, only the two
    # scheduler creations and the move may spend the lead.
    cron = shared_cron_schedule()
    create_scheduler(
        "assistant",
        moved_assistant.id,
        f"Scheduler project change {moved_assistant.id}",
        cron,
    )
    create_scheduler(
        "assistant",
        control_assistant.id,
        f"Scheduler project change {control_assistant.id}",
        cron,
    )

    stored = assistant_utils.move_assistant_to_project(
        moved_assistant.id, other_project.name
    )
    assert_that(
        stored.project, equal_to(other_project.name), "Assistant was not moved."
    )
    assert_cron_minute_still_ahead(cron)

    # Positive control: the same cron fires for the assistant that stayed.
    control_conversation = wait_for_entity(
        lambda: conversation_utils.list_conversations(),
        entity_name=f"Scheduler: {control_assistant.id}",
        timeout=CONTROL_FIRE_TIMEOUT,
    )
    assert_that(
        control_conversation.initial_assistant_id,
        equal_to(control_assistant.id),
        "The control scheduler's conversation must start with the unmoved assistant.",
    )
    assert_that(
        control_conversation.assistant_ids,
        has_item(control_assistant.id),
        "The control scheduler's conversation must include the unmoved assistant.",
    )

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
@pytest.mark.timeout(SCHEDULER_TEST_TIMEOUT)
@pytest.mark.skipif(
    EnvironmentResolver.is_sandbox(),
    reason="Scheduler is disabled on sandbox environments",
)
def test_scheduler_skips_workflow_moved_to_other_project(
    other_project,
    moved_workflow,
    control_workflow,
    workflow_utils,
    create_scheduler,
):
    # @case webhook-scheduler-project-change_TC_005
    moved_prompt = f"Scheduler project change {moved_workflow.id}"
    control_prompt = f"Scheduler project change {control_workflow.id}"

    # Compute the cron only now: from here to the control wait, only the two
    # scheduler creations and the move may spend the lead.
    cron = shared_cron_schedule()
    create_scheduler("workflow", moved_workflow.id, moved_prompt, cron)
    create_scheduler("workflow", control_workflow.id, control_prompt, cron)

    stored = workflow_utils.move_workflow_to_project(
        moved_workflow.id, other_project.name
    )
    assert_that(stored.project, equal_to(other_project.name), "Workflow was not moved.")
    assert_cron_minute_still_ahead(cron)

    # Positive control: the same cron runs the workflow that stayed.
    control_execution = wait_for_entity(
        lambda: workflow_utils.get_executions(control_workflow),
        entity_name=control_prompt,
        timeout=CONTROL_FIRE_TIMEOUT,
    )
    assert_that(
        control_execution.workflow_id,
        equal_to(control_workflow.id),
        "The control scheduler's execution must belong to the unmoved workflow.",
    )

    # The scheduler on the moved workflow is due at the same minute: it must not run.
    with pytest.raises(TimeoutError):
        wait_for_entity(
            lambda: workflow_utils.get_executions(moved_workflow),
            entity_name=moved_prompt,
            timeout=MOVED_SCHEDULER_GRACE_TIMEOUT,
        )
