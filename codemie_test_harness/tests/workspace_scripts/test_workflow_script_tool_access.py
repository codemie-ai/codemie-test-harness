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

"""Scope of a script step's tool_access list.

A script step may call only the tools listed in its tool_access. An absent or empty list
refuses every call; a tool the catalog has but the list does not is refused too. A listed
tool with a pinned integration alias runs under that integration in a non-global workflow,
and a pinned alias the running user does not hold stops the step before the script runs. In
a *global* (marketplace-published) workflow, a pinned alias instead always resolves to the
creator's own integration, regardless of who runs it, and that pinned alias is surfaced in
the marketplace publish-validation credential review; an unaliased entry is unaffected by
``is_global`` and keeps using the running user's own automatic lookup. Saving a list that the
validator rejects is refused with 'Invalid tool access'.

A workflow is published to the marketplace (``is_global=True``) only through the publish
endpoint — see ``publish_workflow_as_global`` in ``conftest.py``.
"""

import pytest
from codemie_sdk.models.integration import CredentialTypes
from codemie_sdk.models.workflow import WorkflowCreateRequest
from codemie_sdk.models.workflow_state import WorkflowExecutionStatusEnum
from hamcrest import (
    assert_that,
    contains_string,
    has_entries,
    has_item,
    has_key,
    is_not,
    none,
    not_,
)

from codemie_test_harness.tests import PROJECT
from codemie_test_harness.tests.enums.tools import AgentWorkspaceTool
from codemie_test_harness.tests.test_data.workspace_script_test_data import (
    CODE_TOOL_UNAVAILABLE,
    CONFLUENCE_SPACE_ARGS,
    CONFLUENCE_TOOL,
    DENY_MARKER,
    INVALID_TOOL_ACCESS_MESSAGE,
    JIRA_MYSELF_ARGS,
    JIRA_TOOL,
    WHOAMI_MARKER,
    WHOAMI_SCRIPT,
    render_deny_probe,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
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
from codemie_test_harness.tests.utils.yaml_utils import (
    ToolModel,
    WorkflowYamlModel,
    prepare_yaml_content,
)

EXECUTE_SCRIPT = AgentWorkspaceTool.EXECUTE_WORKSPACE_SCRIPT.value

# (tool_access of the script step, tool the script calls)
DENY_VARIANTS = [
    pytest.param(None, JIRA_TOOL, JIRA_MYSELF_ARGS, id="tool-access-absent"),
    pytest.param([], JIRA_TOOL, JIRA_MYSELF_ARGS, id="tool-access-empty"),
    pytest.param(
        allow_tools(JIRA_TOOL),
        CONFLUENCE_TOOL,
        CONFLUENCE_SPACE_ARGS,
        id="cataloged-tool-not-listed",
    ),
]


@pytest.mark.workflow
@pytest.mark.workspace
@pytest.mark.api
@pytest.mark.integration
@pytest.mark.parametrize("tool_access, called_tool, args", DENY_VARIANTS)
def test_script_call_is_refused_without_a_matching_tool_access_entry(
    workflow_utils,
    create_script_workflow,
    upload_script,
    tool_access,
    called_tool,
    args,
):
    """No tool_access, an empty one, or one that does not list the called tool: the call is refused."""
    script_name, file_url = upload_script(
        render_deny_probe(called_tool, args), prefix="deny"
    )
    run_tool, run_state = tool_state(
        "run_script",
        EXECUTE_SCRIPT,
        {"script_path": script_name},
        tool_access=tool_access,
    )
    workflow = create_script_workflow([run_tool], [run_state])

    execution = workflow_utils.create_workflow_execution(
        workflow.id, file_names=[file_url], timeout=SCRIPT_WORKFLOW_EXECUTION_TIMEOUT
    )
    step_output = workflow_utils.get_state_outputs(workflow.id, execution.execution_id)[
        "run_script"
    ]

    outcome = extract_marked_json(
        parse_script_result(step_output)["output"], DENY_MARKER
    )
    assert_that(outcome, is_not(has_key("status")))
    assert_that(outcome["error"], has_entries(code=CODE_TOOL_UNAVAILABLE))


@pytest.mark.jira
@pytest.mark.workflow
@pytest.mark.workspace
@pytest.mark.api
@pytest.mark.integration
def test_listed_tool_with_pinned_alias_runs_under_the_running_users_integration(
    workflow_utils,
    create_script_workflow,
    upload_script,
    jira_user_integration,
):
    """A non-global workflow with a pinned alias: the running user's own integration serves the call."""
    script_name, file_url = upload_script(WHOAMI_SCRIPT, prefix="pinned")
    run_tool, run_state = tool_state(
        "whoami",
        EXECUTE_SCRIPT,
        {"script_path": script_name},
        tool_access=[
            ToolModel(name=JIRA_TOOL, integration_alias=jira_user_integration.alias)
        ],
    )
    workflow = create_script_workflow([run_tool], [run_state])

    execution = workflow_utils.create_workflow_execution(
        workflow.id, file_names=[file_url], timeout=SCRIPT_WORKFLOW_EXECUTION_TIMEOUT
    )
    step_output = workflow_utils.get_state_outputs(workflow.id, execution.execution_id)[
        "whoami"
    ]

    outcome = extract_marked_json(
        parse_script_result(step_output)["output"], WHOAMI_MARKER
    )
    assert_that(outcome, has_entries(status=200))


@pytest.mark.jira
@pytest.mark.workflow
@pytest.mark.workspace
@pytest.mark.api
@pytest.mark.integration
def test_pinned_alias_missing_for_running_user_fails_step_before_script_runs(
    regular_client,
    create_script_workflow,
    jira_user_integration,
):
    """The creator holds the pinned alias, the runner does not: the step fails at start and the script never runs."""
    script_name = unique_script_name("missing_alias")
    run_tool, run_state = tool_state(
        "whoami",
        EXECUTE_SCRIPT,
        {"script_path": script_name},
        tool_access=[
            ToolModel(name=JIRA_TOOL, integration_alias=jira_user_integration.alias)
        ],
    )
    workflow = create_script_workflow([run_tool], [run_state])
    runner_utils = WorkflowUtils(regular_client)
    file_url = upload_text_file(regular_client, script_name, WHOAMI_SCRIPT)

    execution_id = runner_utils.start_run(workflow.id, file_names=[file_url])
    failure = runner_utils.wait_for_state_status(
        workflow.id,
        execution_id,
        "whoami",
        WorkflowExecutionStatusEnum.FAILED,
    )

    assert_that(failure, not_(contains_string(f"{WHOAMI_MARKER}=")))


def save_refusal(workflow_utils, tools, states):
    """Try to save a workflow with these tools and states; return the refusal the API sends back."""
    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        tools=tools,
        assistants=[],
        states=states,
    )
    request = WorkflowCreateRequest(
        name=get_random_name(),
        description="Test Workflow",
        project=PROJECT,
        yaml_config=prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True)),
    )
    return workflow_utils.send_request_to_create_workflow_endpoint(request)


@pytest.mark.workflow
@pytest.mark.workspace
@pytest.mark.api
@pytest.mark.integration
def test_save_refuses_tool_access_on_a_step_whose_tool_takes_no_tool_access(
    workflow_utils,
):
    """A Jira tool step (not the script tool) carrying a tool_access list is refused on save."""
    tool, state = tool_state(
        "jira_step",
        JIRA_TOOL,
        JIRA_MYSELF_ARGS,
        tool_access=allow_tools(JIRA_TOOL),
    )

    response = save_refusal(workflow_utils, [tool], [state])

    assert_that(response.get("error"), not_(none()))
    assert_that(
        response["error"].get("details"), contains_string(INVALID_TOOL_ACCESS_MESSAGE)
    )


@pytest.mark.workflow
@pytest.mark.workspace
@pytest.mark.api
@pytest.mark.integration
def test_save_refuses_tool_access_naming_a_tool_that_is_not_script_callable(
    workflow_utils,
):
    """A tool that exists but is not callable from a script is refused on save with 'Invalid tool access'."""
    tool, state = tool_state(
        "run_script",
        EXECUTE_SCRIPT,
        {"script_path": unique_script_name("save")},
        tool_access=allow_tools(AgentWorkspaceTool.READ_WORKSPACE_FILE.value),
    )

    response = save_refusal(workflow_utils, [tool], [state])

    assert_that(response.get("error"), not_(none()))
    assert_that(
        response["error"].get("details"), contains_string(INVALID_TOOL_ACCESS_MESSAGE)
    )


# ---- global (marketplace-published) workflow: AC-4, AC-8 ------------------------------------


@pytest.fixture
def runner_invalid_jira_integration(regular_client):
    """The runner's own Jira integration, with credentials that do not work.

    So a successful call in a global-workflow pinned-alias test can only be explained by the
    creator's own pinned integration — never by the runner's own automatic-lookup fallback.
    """
    integration_utils = IntegrationUtils(regular_client)
    integration = integration_utils.create_user_integration(
        CredentialTypes.JIRA, CredentialsManager.invalid_jira_credentials()
    )
    yield integration
    integration_utils.delete_integration(integration)


@pytest.mark.jira
@pytest.mark.workflow
@pytest.mark.workspace
@pytest.mark.api
@pytest.mark.integration
def test_global_workflow_pinned_alias_runs_under_creators_integration_regardless_of_runner(
    regular_client,
    create_script_workflow,
    publish_workflow_as_global,
    jira_user_integration,
    runner_invalid_jira_integration,
):
    """A global workflow's pinned alias always serves the creator's integration, even when a
    different user — whose own integration for the same tool is broken — runs it."""
    script_name = unique_script_name("global_pinned")
    run_tool, run_state = tool_state(
        "whoami",
        EXECUTE_SCRIPT,
        {"script_path": script_name},
        tool_access=[
            ToolModel(name=JIRA_TOOL, integration_alias=jira_user_integration.alias)
        ],
    )
    workflow = create_script_workflow([run_tool], [run_state])
    publish_workflow_as_global(workflow.id)

    runner_utils = WorkflowUtils(regular_client)
    file_url = upload_text_file(regular_client, script_name, WHOAMI_SCRIPT)
    execution = runner_utils.create_workflow_execution(
        workflow.id, file_names=[file_url], timeout=SCRIPT_WORKFLOW_EXECUTION_TIMEOUT
    )
    step_output = runner_utils.get_state_outputs(workflow.id, execution.execution_id)[
        "whoami"
    ]

    outcome = extract_marked_json(
        parse_script_result(step_output)["output"], WHOAMI_MARKER
    )
    assert_that(outcome, has_entries(status=200))


@pytest.mark.jira
@pytest.mark.workflow
@pytest.mark.workspace
@pytest.mark.api
@pytest.mark.integration
def test_global_workflow_unaliased_entry_still_uses_runners_automatic_lookup(
    regular_client,
    create_script_workflow,
    publish_workflow_as_global,
    jira_user_integration_runner,
):
    """A global workflow's unaliased tool_access entry is gated only by list membership: the
    runner's own project-level automatic lookup still serves the call, exactly as it would on
    a non-global workflow — ``is_global`` neither narrows nor widens that boundary."""
    script_name = unique_script_name("global_unaliased")
    run_tool, run_state = tool_state(
        "whoami",
        EXECUTE_SCRIPT,
        {"script_path": script_name},
        tool_access=allow_tools(JIRA_TOOL),
    )
    workflow = create_script_workflow([run_tool], [run_state])
    publish_workflow_as_global(workflow.id)

    runner_utils = WorkflowUtils(regular_client)
    file_url = upload_text_file(regular_client, script_name, WHOAMI_SCRIPT)
    execution = runner_utils.create_workflow_execution(
        workflow.id, file_names=[file_url], timeout=SCRIPT_WORKFLOW_EXECUTION_TIMEOUT
    )
    step_output = runner_utils.get_state_outputs(workflow.id, execution.execution_id)[
        "whoami"
    ]

    outcome = extract_marked_json(
        parse_script_result(step_output)["output"], WHOAMI_MARKER
    )
    assert_that(outcome, has_entries(status=200))


@pytest.mark.jira
@pytest.mark.workflow
@pytest.mark.workspace
@pytest.mark.api
@pytest.mark.integration
def test_publishing_global_workflow_surfaces_pinned_alias_in_credential_review(
    workflow_utils,
    create_script_workflow,
    publish_workflow_as_global,
    jira_user_integration,
):
    """Publishing a workflow with a pinned alias must not let the shared credential slip past
    review unnoticed: the publish-validation response's inline credentials name the tool and
    the pinned alias."""
    run_tool, run_state = tool_state(
        "whoami",
        EXECUTE_SCRIPT,
        {"script_path": unique_script_name("publish_review")},
        tool_access=[
            ToolModel(name=JIRA_TOOL, integration_alias=jira_user_integration.alias)
        ],
    )
    workflow = create_script_workflow([run_tool], [run_state])
    publish_workflow_as_global(workflow.id)

    response = workflow_utils.validate_workflow_marketplace_publish(workflow.id)

    assert_that(
        response["inline_credentials"],
        has_item(
            has_entries(tool=JIRA_TOOL, integration_alias=jira_user_integration.alias)
        ),
    )
