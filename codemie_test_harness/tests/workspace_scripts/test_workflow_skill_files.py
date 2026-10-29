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

"""Skill bundle files in the workspace of a workflow run.

The workspace of a run is addressed by the execution id. Two assistant nodes that attach the same skill
share the run's workspace, so the skill's files must be there once. The assistants only have to answer;
the files are placed before they do.
"""

import pytest
from codemie_sdk.models.workflow import ExecutionStatus
from hamcrest import assert_that, contains_inanyorder, equal_to

from codemie_test_harness.tests.enums.tools import AgentWorkspaceTool
from codemie_test_harness.tests.test_data.skill_workspace_test_data import (
    SEED_PROMPT,
    two_file_bundle,
)
from codemie_test_harness.tests.utils.skill_workspace_utils import (
    folder_paths,
    list_paths,
)
from codemie_test_harness.tests.utils.workspace_script_utils import (
    SCRIPT_WORKFLOW_EXECUTION_TIMEOUT,
)
from codemie_test_harness.tests.utils.yaml_utils import (
    AssistantModel,
    StateModel,
    ToolModel,
)

SYSTEM_PROMPT = "Answer briefly and never call a tool unless asked."


@pytest.mark.workflow
@pytest.mark.skill
@pytest.mark.workspace
@pytest.mark.api
def test_workflow_run_places_skill_files_once_across_its_assistants(
    client,
    workflow_utils,
    create_script_workflow,
    create_skill_with_bundle,
    default_llm,
):
    """Two assistant nodes with the same skill: the run's workspace holds one folder with each file once."""
    bundle = two_file_bundle()
    skill = create_skill_with_bundle(bundle)
    assistants = [
        AssistantModel(
            id=f"skill_assistant_{position}",
            model=default_llm.base_name,
            system_prompt=SYSTEM_PROMPT,
            skill_ids=[skill.id],
            tools=[ToolModel(name=AgentWorkspaceTool.EXECUTE_WORKSPACE_SCRIPT.value)],
        )
        for position in (1, 2)
    ]
    states = [
        StateModel(
            id="first_step",
            assistant_id="skill_assistant_1",
            task=SEED_PROMPT,
            next={"state_id": "second_step"},
        ),
        StateModel(
            id="second_step",
            assistant_id="skill_assistant_2",
            task=SEED_PROMPT,
        ),
    ]
    workflow = create_script_workflow([], states, assistants=assistants)

    execution = workflow_utils.create_workflow_execution(
        workflow.id, timeout=SCRIPT_WORKFLOW_EXECUTION_TIMEOUT
    )

    assert_that(execution.status, equal_to(ExecutionStatus.SUCCEEDED))
    workspace = client.workspaces.get_by_conversation(execution.execution_id)
    assert_that(
        list_paths(client, workspace.id),
        contains_inanyorder(*folder_paths(skill, bundle)),
        "the skill folder holds each bundle file exactly once",
    )
