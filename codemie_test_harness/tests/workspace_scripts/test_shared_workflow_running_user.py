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

"""A script in a shared workflow calls tools as the user who runs it, not the creator.

The real AC8 case is a *global* (marketplace) workflow, but the public API has no way to
publish a workflow as global, so this checks the same rule on a shared workflow: the
creator's own Jira integration is invalid, the runner's is valid, and the script's call
must go through the runner's.

It must run on its own: the creator must have no other working Jira integration, which
cannot hold while other tests create valid ones.
"""

import pytest
from codemie_sdk.models.integration import CredentialTypes
from hamcrest import assert_that, equal_to, is_not

from codemie_test_harness.tests.enums.tools import AgentWorkspaceTool
from codemie_test_harness.tests.test_data.workspace_script_test_data import (
    JIRA_TOOL,
    WHOAMI_MARKER,
    WHOAMI_SCRIPT,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.integration_utils import IntegrationUtils
from codemie_test_harness.tests.utils.workflow_utils import WorkflowUtils
from codemie_test_harness.tests.utils.workspace_script_utils import (
    SCRIPT_WORKFLOW_EXECUTION_TIMEOUT,
    allow_tools,
    extract_marked_json,
    parse_script_result,
    tool_state,
    unique_script_name,
    upload_text_file,
)


@pytest.fixture
def creator_invalid_jira_integration(client):
    """The creator's own Jira integration, with credentials that do not work."""
    integration_utils = IntegrationUtils(client)
    integration = integration_utils.create_user_integration(
        CredentialTypes.JIRA, CredentialsManager.invalid_jira_credentials()
    )
    yield integration
    integration_utils.delete_integration(integration)


@pytest.fixture
def runner_valid_jira_integration(regular_client):
    """The runner's own Jira integration, with working credentials."""
    integration_utils = IntegrationUtils(regular_client)
    integration = integration_utils.create_user_integration(
        CredentialTypes.JIRA, CredentialsManager.jira_credentials()
    )
    yield integration
    integration_utils.delete_integration(integration)


def run_whoami(workflow_utils, workflow_id, file_url):
    """Run the workflow as the user behind ``workflow_utils``; return the Jira status the script reported."""
    execution = workflow_utils.create_workflow_execution(
        workflow_id, file_names=[file_url], timeout=SCRIPT_WORKFLOW_EXECUTION_TIMEOUT
    )
    step_output = workflow_utils.get_state_outputs(workflow_id, execution.execution_id)[
        "whoami"
    ]
    outcome = extract_marked_json(
        parse_script_result(step_output)["output"], WHOAMI_MARKER
    )
    return outcome["status"]


@pytest.mark.jira
@pytest.mark.workflow
@pytest.mark.workspace
@pytest.mark.api
@pytest.mark.integration
def test_script_call_uses_the_running_users_integration_not_the_creators(
    client,
    regular_client,
    workflow_utils,
    create_script_workflow,
    creator_invalid_jira_integration,
    runner_valid_jira_integration,
):
    """The runner gets Jira's answer through their own integration, the creator through theirs."""
    script_name = unique_script_name("whoami")
    tool, state = tool_state(
        "whoami",
        AgentWorkspaceTool.EXECUTE_WORKSPACE_SCRIPT.value,
        {"script_path": script_name},
        tool_access=allow_tools(JIRA_TOOL),
    )
    workflow = create_script_workflow([tool], [state])

    runner_status = run_whoami(
        WorkflowUtils(regular_client),
        workflow.id,
        upload_text_file(regular_client, script_name, WHOAMI_SCRIPT),
    )
    creator_status = run_whoami(
        workflow_utils,
        workflow.id,
        upload_text_file(client, script_name, WHOAMI_SCRIPT),
    )

    assert_that(runner_status, equal_to(200))
    assert_that(creator_status, is_not(equal_to(200)))
