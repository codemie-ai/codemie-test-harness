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

"""Tests covering how the preconfigured azure-devops-work-item-fields Skill
reaches a workflow's virtual assistant, mirroring the chat-path behaviour."""

import pytest
from hamcrest import assert_that, contains_string, is_in

from codemie_test_harness.tests.enums.tools import AzureDevOpsWorkItemTool
from codemie_test_harness.tests.utils.base_utils import get_random_name

ADO_FIELD_REFERENCE_PROMPT = (
    "What is the REST API attribute name for the Acceptance Criteria field "
    "on an Azure DevOps work item?"
)
ACCEPTANCE_CRITERIA_REST_NAME = "Microsoft.VSTS.Common.AcceptanceCriteria"


@pytest.mark.workflow
@pytest.mark.virtual_workflow
@pytest.mark.skill
@pytest.mark.ado
@pytest.mark.api
def test_workflow_with_ado_skill_returns_field_reference_on_demand(
    ado_integration,
    workflow_with_virtual_assistant,
    workflow_utils,
    ado_field_reference_skill,
):
    """Covers extend-context-for-ado-tools_TC_004: a workflow's virtual
    assistant with the Azure DevOps Work Item toolkit enabled and the
    preconfigured Skill attached (skill_ids) returns the field reference
    on demand, the same as the chat path in TC-003.
    """
    # @case extend-context-for-ado-tools_TC_004
    assistant_and_state_name = get_random_name()

    test_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name,
        AzureDevOpsWorkItemTool.GET_WORK_ITEM,
        integration=ado_integration,
        skill_ids=[ado_field_reference_skill.id],
    )

    output = workflow_utils.execute_workflow(
        test_workflow.id, assistant_and_state_name, ADO_FIELD_REFERENCE_PROMPT
    )
    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        test_workflow
    )

    assert_that("skill", is_in(triggered_tools))
    assert_that(output, contains_string(ACCEPTANCE_CRITERIA_REST_NAME))
