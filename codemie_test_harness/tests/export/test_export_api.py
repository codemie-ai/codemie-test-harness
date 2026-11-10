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

"""API tests for the public export endpoint: GET /v1/export/{kind}/{id}.

Covers the canonical export document (version/meta/spec), credential redaction to `env:`
references across every credential-bearing surface, reference-by-name resolution, the
negative paths (unknown kind, missing entity, inaccessible reference, name clash, credential
collision, unsupported datasource type, refused-rather-than-redacted MCP surfaces) and the
export -> update-request -> submit round trip for assistant, workflow, datasource, skill,
integration and category.
"""

import copy
import uuid

import pytest
import yaml
from hamcrest import assert_that, contains_string, equal_to, has_key, is_not, not_none
from requests import HTTPError

from codemie_sdk.models.assistant import (
    AssistantUpdateRequest,
    MCPServerConfig,
    MCPServerDetails,
    PromptVariable,
)
from codemie_sdk.models.datasource import UpdateGitFaqDataSourceRequest
from codemie_sdk.models.integration import (
    CredentialTypes,
    CredentialValues,
    Integration,
    IntegrationTestRequest,
    IntegrationTestResponse,
    IntegrationType,
)
from codemie_sdk.models.mcp_config import MCPConfigCreateRequest, MCPServerConfigData
from codemie_sdk.models.skill import SkillCompanionFilePayload, SkillVisibility
from codemie_sdk.models.workflow import WorkflowMode

from codemie_test_harness.tests.enums.tools import AgentWorkspaceTool
from codemie_test_harness.tests.test_data.export_test_data import (
    CREDENTIAL_MASK,
    ENV_REF_PREFIX,
    LITERAL_DATASOURCE_URL_PASSWORD,
    LITERAL_INTEGRATION_TOKEN,
    LITERAL_MCP_COMMAND,
    LITERAL_MCP_CONNECT_AUTH_TOKEN,
    LITERAL_MCP_ENV_SECRET,
    TRANSFORM_NODE_CONFIG,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.workflow_utils import WorkflowUtils
from codemie_test_harness.tests.utils.yaml_utils import (
    AssistantModel,
    CustomNodeModel,
    StateModel,
    ToolModel,
    WorkflowYamlModel,
    prepare_yaml_content,
)

# A random id of a kind/entity that never exists, for the "missing entity" negative case.
_MISSING_ASSISTANT_ID = str(uuid.uuid4())


def _contains_key_recursively(value, key: str) -> bool:
    """Whether ``key`` appears as a dict key anywhere in ``value`` (nested dicts/lists)."""
    if isinstance(value, dict):
        if key in value:
            return True
        return any(_contains_key_recursively(v, key) for v in value.values())
    if isinstance(value, list):
        return any(_contains_key_recursively(v, key) for v in value)
    return False


def _workflow_definition_to_yaml_config(
    definition: dict, assistant_ids: dict[str, str] | None = None
) -> str:
    """The exported `workflow` definition (envelope shape: `assistants` keyed by id) back into
    the stored list-based yaml_config text — the API-reachable equivalent of the backend's
    internal `workflow_converter.render()`, which this harness cannot call directly.

    ``assistant_ids`` maps a catalog assistant's exported name back to its id, for an entry
    whose `assistant_id` is a name reference; omit it when every assistant is a plain virtual
    one (no catalog reference to resolve back).
    """
    assistant_ids = assistant_ids or {}
    assistants = []
    for key, value in definition["assistants"].items():
        entry = {"id": key, **value}
        if entry.get("assistant_id"):
            entry["assistant_id"] = assistant_ids[entry["assistant_id"]]
        assistants.append(entry)
    sections = {
        "assistants": assistants,
        "tools": definition.get("tools", []),
        "custom_nodes": definition.get("custom_nodes", []),
        "states": definition.get("states", []),
    }
    return yaml.safe_dump({k: v for k, v in sections.items() if v}, sort_keys=False)


# ---------------------------------------------------------------------------------------------
# AC-1 / AC-6: the canonical document
# ---------------------------------------------------------------------------------------------


@pytest.mark.export
@pytest.mark.api
def test_export_produces_document_sufficient_to_recreate_entity(
    client, assistant_utils
):
    """@case public-export-rest-endpoint_TC_001"""
    created = assistant_utils.create_assistant(
        system_prompt="Act as a careful reviewer", temperature=0.4
    )
    # create_assistant()'s own return is the minimal list projection (name/id/description
    # only); re-fetch the full assistant for project/llm_model_type.
    assistant = assistant_utils.get_assistant_by_id(created.id)

    document = client.export.export("assistant", assistant.id)

    assert_that(document["version"], not_none())
    assert_that(
        document["meta"], equal_to({"kind": "assistant", "name": assistant.name})
    )
    assert_that(document["meta"], is_not(has_key("id")))
    spec = document["spec"]
    assert_that(spec["name"], equal_to(assistant.name))
    assert_that(spec["system_prompt"], equal_to("Act as a careful reviewer"))
    assert_that(spec["project"], equal_to(assistant.project))
    assert_that(spec["llm_model_type"], equal_to(assistant.llm_model_type))
    assert_that(spec["temperature"], equal_to(0.4))


@pytest.mark.export
@pytest.mark.api
def test_export_document_has_no_platform_id_and_no_mask_placeholder(
    client, assistant_utils
):
    """@case public-export-rest-endpoint_TC_007"""
    assistant = assistant_utils.create_assistant()

    document = client.export.export("assistant", assistant.id)

    assert_that(
        _contains_key_recursively(document, "id"),
        equal_to(False),
        "exported document carries a platform id",
    )
    assert_that(
        CREDENTIAL_MASK in str(document),
        equal_to(False),
        "exported document carries the mask placeholder",
    )
    assert_that(assistant.id not in str(document), equal_to(True))


# ---------------------------------------------------------------------------------------------
# AC-2: credential-bearing surfaces redacted to env: references
# ---------------------------------------------------------------------------------------------


@pytest.mark.export
@pytest.mark.api
def test_export_redacts_integration_credential_to_env_reference(
    client, integration_utils
):
    """@case public-export-rest-endpoint_TC_002 (surface: integration credential)"""
    integration = integration_utils.create_project_integration(
        credential_type=CredentialTypes.GIT,
        credentials=[CredentialValues(key="token", value=LITERAL_INTEGRATION_TOKEN)],
    )

    document = client.export.export("integration", integration.id)

    refs = {c["key"]: c["ref"] for c in document["spec"]["credential_values"]}
    assert_that(refs["token"].startswith(ENV_REF_PREFIX), equal_to(True))
    assert_that(LITERAL_INTEGRATION_TOKEN in str(document), equal_to(False))


@pytest.mark.export
@pytest.mark.api
def test_export_redacts_datasource_inline_credential_to_env_reference(
    client, datasource_utils, integration_utils
):
    """@case public-export-rest-endpoint_TC_002 (surface: datasource inline credential)"""
    # A real git integration as setting_id: creation validates it has credentials (a cheap
    # DB lookup) rather than probing the link's reachability, so a fake host with a literal
    # credential embedded in it (what this test needs to exercise redact_link) is accepted.
    integration = integration_utils.create_project_integration(
        credential_type=CredentialTypes.GIT,
        credentials=[
            CredentialValues(key="url", value="https://git.example.com"),
            CredentialValues(key="token", value="integration-token-placeholder"),
        ],
    )
    link = f"https://cred-user:{LITERAL_DATASOURCE_URL_PASSWORD}@git.example.com/wiki"
    datasource = (
        datasource_utils.create_git_faq_datasource_without_waiting_for_indexing(
            link=link, branch="main", setting_id=integration.id
        )
    )

    document = client.export.export("datasource", datasource.id)

    assert_that(document["spec"]["link"].startswith(ENV_REF_PREFIX), equal_to(True))
    assert_that(LITERAL_DATASOURCE_URL_PASSWORD in str(document), equal_to(False))


@pytest.mark.export
@pytest.mark.api
def test_export_redacts_mcp_tool_settings_command_to_env_reference(
    client, assistant_utils
):
    """@case public-export-rest-endpoint_TC_002 (surface: tool settings — MCP config.command)"""
    # The command must be one of the backend's permitted MCP launchers ("uvx" is); redaction
    # of config.command is positional (redact_positional), so even this ordinary, non-secret
    # value is still always replaced by an env: reference rather than left literal.
    assistant = assistant_utils.create_assistant(
        mcp_servers=[
            MCPServerDetails(
                name="mcp-tool-settings",
                description=None,
                enabled=True,
                use_custom_config=True,
                config=MCPServerConfig(command=LITERAL_MCP_COMMAND),
            )
        ]
    )

    document = client.export.export("assistant", assistant.id)

    server = document["spec"]["mcp_servers"][0]
    assert_that(server["config"]["command"].startswith(ENV_REF_PREFIX), equal_to(True))
    assert_that(LITERAL_MCP_COMMAND in str(document), equal_to(False))


@pytest.mark.export
@pytest.mark.api
def test_export_redacts_mcp_toolkit_settings_env_map_to_env_reference(
    client, assistant_utils
):
    """@case public-export-rest-endpoint_TC_002 (surface: toolkit settings — MCP config.env)"""
    assistant = assistant_utils.create_assistant(
        mcp_servers=[
            MCPServerDetails(
                name="mcp-toolkit-settings",
                description=None,
                enabled=True,
                use_custom_config=True,
                config=MCPServerConfig(
                    command="uvx", env={"TOOLKIT_SETTING": LITERAL_MCP_ENV_SECRET}
                ),
            )
        ]
    )

    document = client.export.export("assistant", assistant.id)

    server = document["spec"]["mcp_servers"][0]
    assert_that(
        server["config"]["env"]["TOOLKIT_SETTING"].startswith(ENV_REF_PREFIX),
        equal_to(True),
    )
    assert_that(LITERAL_MCP_ENV_SECRET in str(document), equal_to(False))


@pytest.mark.export
@pytest.mark.api
def test_export_redacts_mcp_connect_auth_token_to_env_reference(
    client, assistant_utils
):
    """@case public-export-rest-endpoint_TC_002 (surface: MCP connect auth token)"""
    assistant = assistant_utils.create_assistant(
        mcp_servers=[
            MCPServerDetails(
                name="mcp-connect",
                description=None,
                enabled=True,
                use_custom_config=True,
                config=MCPServerConfig(
                    command="uvx", auth_token=LITERAL_MCP_CONNECT_AUTH_TOKEN
                ),
            )
        ]
    )

    document = client.export.export("assistant", assistant.id)

    server = document["spec"]["mcp_servers"][0]
    assert_that(
        server["config"]["auth_token"].startswith(ENV_REF_PREFIX), equal_to(True)
    )
    assert_that(LITERAL_MCP_CONNECT_AUTH_TOKEN in str(document), equal_to(False))


@pytest.mark.export
@pytest.mark.api
def test_export_sensitive_prompt_variable_value_is_empty(client, assistant_utils):
    """@case public-export-rest-endpoint_TC_003"""
    assistant = assistant_utils.create_assistant(
        prompt_variables=[
            PromptVariable(
                key="api_secret",
                description="A secret prompt variable",
                default_value="literal-sensitive-default",
                is_sensitive=True,
            )
        ]
    )

    document = client.export.export("assistant", assistant.id)

    variable = next(
        v for v in document["spec"]["prompt_variables"] if v["key"] == "api_secret"
    )
    assert_that(variable["default_value"], equal_to(""))
    assert_that(variable["default_value"].startswith(ENV_REF_PREFIX), equal_to(False))
    assert_that("literal-sensitive-default" in str(document), equal_to(False))


# ---------------------------------------------------------------------------------------------
# AC-4: negative paths naming the problem
# ---------------------------------------------------------------------------------------------


@pytest.mark.export
@pytest.mark.api
@pytest.mark.parametrize(
    "kind, entity_id, expected_message_fragment",
    [
        ("bogus", "abc", "bogus"),
        ("assistant", _MISSING_ASSISTANT_ID, "not found"),
    ],
    ids=["unknown-kind", "missing-entity"],
)
def test_export_fails_naming_the_problem(
    client, kind, entity_id, expected_message_fragment
):
    """@case public-export-rest-endpoint_TC_005"""
    with pytest.raises(HTTPError) as exc_info:
        client.export.export(kind, entity_id)

    response = exc_info.value.response
    assert_that(response.status_code, equal_to(404))
    body = response.json()
    assert_that(body["error"]["message"], contains_string(expected_message_fragment))
    assert_that(body, is_not(has_key("meta")))
    assert_that(body, is_not(has_key("spec")))


@pytest.mark.export
@pytest.mark.api
def test_export_fails_for_referenced_entity_the_caller_cannot_access(
    regular_client, client, assistant_utils, default_llm
):
    """@case public-export-rest-endpoint_TC_005 (inaccessible referenced entity)"""
    # Workflow creation itself validates that every referenced assistant is visible to the
    # creating user, so the workflow must be built while the assistant is still shared, then
    # access revoked afterwards — exactly the real scenario AC-4 protects against (sharing
    # later revoked on an assistant a workflow already references).
    created = assistant_utils.create_assistant(shared=True)
    shared_assistant = assistant_utils.get_assistant_by_id(created.id)
    regular_workflow_utils = WorkflowUtils(regular_client)
    workflow_yaml = WorkflowYamlModel(
        assistants=[
            AssistantModel(
                id="referencing",
                model=default_llm.base_name,
                assistant_id=shared_assistant.id,
            )
        ],
        states=[StateModel(id="referencing", assistant_id="referencing")],
    )
    workflow = regular_workflow_utils.create_workflow(
        workflow_type=WorkflowMode.SEQUENTIAL,
        workflow_yaml=prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True)),
    )
    client.assistants.update(
        shared_assistant.id,
        AssistantUpdateRequest(
            name=shared_assistant.name,
            description=shared_assistant.description,
            system_prompt=shared_assistant.system_prompt,
            project=shared_assistant.project,
            llm_model_type=shared_assistant.llm_model_type,
            slug=shared_assistant.slug,
            shared=False,
        ),
    )

    try:
        with pytest.raises(HTTPError) as exc_info:
            regular_client.export.export("workflow", workflow.id)

        response = exc_info.value.response
        assert_that(response.status_code, equal_to(403))
        assert_that(
            response.json()["error"]["message"], contains_string("not accessible")
        )
    finally:
        regular_workflow_utils.delete_workflow(workflow)
        assistant_utils.delete_assistant_by_id(shared_assistant.id)


# ---------------------------------------------------------------------------------------------
# AC-5: deterministic canonical serialisation
# ---------------------------------------------------------------------------------------------


@pytest.mark.export
@pytest.mark.api
def test_export_twice_in_a_row_is_byte_identical(client, assistant_utils):
    """@case public-export-rest-endpoint_TC_006"""
    assistant = assistant_utils.create_assistant()

    first = client.export.export_raw("assistant", assistant.id)
    second = client.export.export_raw("assistant", assistant.id)

    assert_that(first, equal_to(second))


# ---------------------------------------------------------------------------------------------
# AC-7: references rendered by name
# ---------------------------------------------------------------------------------------------


@pytest.mark.export
@pytest.mark.api
def test_export_renders_reference_by_name_not_id(
    client, assistant_utils, workflow_with_assistant
):
    """@case public-export-rest-endpoint_TC_008"""
    assistant = assistant_utils.create_assistant()
    workflow = workflow_with_assistant(assistant, "Run the referenced assistant")

    document = client.export.export("workflow", workflow.id)

    entry = next(iter(document["spec"]["workflow"]["assistants"].values()))
    assert_that(entry["assistant_id"], equal_to(assistant.name))
    assert_that(entry["assistant_id"], is_not(equal_to(assistant.id)))


# ---------------------------------------------------------------------------------------------
# AC-8: exported spec covers every update-accepted field
# ---------------------------------------------------------------------------------------------

# Deliberately non-exportable assistant fields (grounded in ASSISTANT_NOT_EXPORTED, the
# change-analysis fact at test_export_roundtrip.py:657), plus platform-managed fields the SDK's
# request model inherits structurally from the read model but the update endpoint never accepts
# as caller-supplied (an id and audit metadata — correctly absent per AC-6).
_ASSISTANT_NOT_EXPORTED = {
    "guardrail_assignments",
    "skip_integration_validation",
    "source_assistant_id",
    "type",
    "bedrock",
    "bedrock_agentcore_runtime",
    "agent_card",
    "plan_prompt",
    "agent_mode",
    "image_generation_model",
    "smart_tool_selection_enabled",
    "custom_metadata",
    "hide_tool_outputs",
    "id",
    "created_by",
}

# codemie_tools ships a built-in hedgeable tool ("example_hedge_tool", auto-discovered via
# HedgingToolkit/DiscoverableToolkit — codemie_tools/hedging/toolkit.py) on every deployment,
# with no external integration or customer config needed; used to populate hedging_config.
_BUILTIN_HEDGE_TOOL_NAME = "example_hedge_tool"


@pytest.mark.export
@pytest.mark.api
def test_export_assistant_spec_covers_every_update_field(client, assistant_utils):
    """@case public-export-rest-endpoint_TC_009"""
    from codemie_sdk.models.assistant import (
        HedgingConfig,
        HedgingToolDetails,
        ToolPermissionsConfig,
    )

    hedging_config = HedgingConfig(
        tool=HedgingToolDetails(name=_BUILTIN_HEDGE_TOOL_NAME)
    )
    created = assistant_utils.create_assistant(
        temperature=0.3,
        top_p=0.8,
        enabled_builtin_subagents=[],
        tool_permissions=ToolPermissionsConfig(),
    )
    # create_assistant()'s own return is the minimal list projection; re-fetch the full
    # assistant so system_prompt/project/llm_model_type/slug/shared are actually present.
    assistant = assistant_utils.get_assistant_by_id(created.id)
    # Fields AssistantCreateRequest/assistant_utils.create_assistant does not expose; set them
    # through a follow-up update so every None-defaulted field becomes non-null before export.
    client.assistants.update(
        assistant.id,
        AssistantUpdateRequest(
            name=assistant.name,
            description=assistant.description,
            icon_url="https://your-host.example.com/icon.png",
            system_prompt=assistant.system_prompt,
            project=assistant.project,
            llm_model_type=assistant.llm_model_type,
            slug=assistant.slug,
            shared=assistant.shared,
            temperature=0.3,
            top_p=0.8,
            tools_tokens_size_limit=2000,
            enabled_builtin_subagents=[],
            tool_permissions=ToolPermissionsConfig(),
            hedging_config=hedging_config,
            interactive_enabled=False,
            enable_image_generation=False,
            file_attachment_enabled=False,
        ),
    )

    document = client.export.export("assistant", assistant.id)

    spec_keys = set(document["spec"])
    accepted = set(AssistantUpdateRequest.model_fields) - _ASSISTANT_NOT_EXPORTED
    missing = accepted - spec_keys
    assert_that(missing, equal_to(set()))
    assert_that(
        document["spec"]["hedging_config"]["tool"]["name"],
        equal_to(_BUILTIN_HEDGE_TOOL_NAME),
    )


# ---------------------------------------------------------------------------------------------
# AC-9: export -> update-request -> submit round trip leaves the entity unchanged
# ---------------------------------------------------------------------------------------------


@pytest.mark.export
@pytest.mark.api
def test_export_round_trip_leaves_assistant_unchanged(client, assistant_utils):
    """@case public-export-rest-endpoint_TC_010 (kind: assistant)"""
    assistant = assistant_utils.create_assistant(
        system_prompt="Round trip me", temperature=0.6
    )

    before = client.export.export("assistant", assistant.id)
    update_fields = {
        k: v
        for k, v in before["spec"].items()
        if k in AssistantUpdateRequest.model_fields
    }
    client.assistants.update(assistant.id, AssistantUpdateRequest(**update_fields))
    after = client.export.export("assistant", assistant.id)

    assert_that(after["spec"], equal_to(before["spec"]))


@pytest.mark.export
@pytest.mark.api
def test_export_round_trip_leaves_workflow_unchanged(
    client, workflow_utils, default_llm
):
    """@case public-export-rest-endpoint_TC_010 (kind: workflow)"""
    workflow_yaml = WorkflowYamlModel(
        assistants=[
            AssistantModel(
                id="round_trip_assistant",
                model=default_llm.base_name,
                system_prompt="Round trip this workflow",
            )
        ],
        states=[
            StateModel(id="round_trip_assistant", assistant_id="round_trip_assistant")
        ],
    )
    workflow = workflow_utils.create_workflow(
        workflow_type=WorkflowMode.SEQUENTIAL,
        workflow_yaml=prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True)),
    )

    try:
        before = client.export.export("workflow", workflow.id)
        new_yaml_config = _workflow_definition_to_yaml_config(
            before["spec"]["workflow"]
        )
        workflow_utils.update_workflow(
            workflow, yaml_config=new_yaml_config, mode=WorkflowMode.SEQUENTIAL
        )
        after = client.export.export("workflow", workflow.id)

        assert_that(after["spec"], equal_to(before["spec"]))
    finally:
        workflow_utils.delete_workflow(workflow)


@pytest.mark.export
@pytest.mark.api
def test_export_round_trip_leaves_datasource_unchanged(client, datasource_utils):
    """@case public-export-rest-endpoint_TC_010 (kind: datasource)"""
    # A real, publicly-reachable repo: creation synchronously probes a git_faq link with no
    # setting_id (git ls-remote), so a fake host fails before the datasource even exists.
    datasource = (
        datasource_utils.create_git_faq_datasource_without_waiting_for_indexing(
            link=CredentialsManager.get_parameter("GITHUB_PUBLIC_PROJECT"),
            branch="main",
        )
    )
    # Settle the datasource's own initial indexing before the first export: otherwise a
    # field that only fills in once indexing completes could still change on its own, with
    # nothing to do with the update below, and flip between the two snapshots.
    datasource_utils.wait_for_indexing(datasource.id)

    try:
        before = client.export.export("datasource", datasource.id)
        spec = before["spec"]
        client.datasources.update(
            datasource.id,
            UpdateGitFaqDataSourceRequest(
                name=spec["name"],
                project_name=spec["project_name"],
                description=spec["description"],
                project_space_visible=spec["shared_with_project"],
                setting_id=spec.get("setting_id"),
                link=spec["link"],
                branch=spec["branch"],
                files_filter=spec.get("files_filter"),
                # Source fields (link/branch/files_filter) require this flag whenever present
                # in the body at all, even unchanged — the real repo link means the resulting
                # background reindex is harmless.
                full_reindex=True,
            ),
        )
        # Wait for that reindex to settle before taking the second snapshot: a fake,
        # unreachable link would let the request skip straight to the comparison, but this
        # one is real and the reindex it starts is real and asynchronous.
        datasource_utils.wait_for_indexing(datasource.id)
        after = client.export.export("datasource", datasource.id)

        assert_that(after["spec"], equal_to(before["spec"]))
    finally:
        datasource_utils.delete_datasource(datasource)


@pytest.mark.export
@pytest.mark.api
def test_export_round_trip_leaves_skill_unchanged(client, skill_utils):
    """@case public-export-rest-endpoint_TC_010 (kind: skill)"""
    skill = skill_utils.create_skill()

    before = client.export.export("skill", skill.id)
    spec = before["spec"]
    skill_utils.update_skill(
        skill.id,
        name=spec["name"],
        description=spec["description"],
        content=spec["content"],
        visibility=SkillVisibility(spec["visibility"]),
        categories=spec["categories"],
        enabled_builtin_subagents=spec["enabled_builtin_subagents"],
    )
    after = client.export.export("skill", skill.id)

    assert_that(after["spec"], equal_to(before["spec"]))


# ---------------------------------------------------------------------------------------------
# AC-10: workflow structured definition with named references
# ---------------------------------------------------------------------------------------------


@pytest.mark.export
@pytest.mark.api
def test_export_workflow_structured_definition_with_named_references(
    client, workflow_utils, assistant_utils, default_llm
):
    """@case public-export-rest-endpoint_TC_011

    Covers the structured definition (assistant, mcp_server, tool, custom_node, state,
    next/condition/switch, retry_policy), name-based assistant reference, and — since
    `workflow_converter.render()` itself has no API surface — its claim indirectly: submitting
    the definition converted back into yaml_config (names resolved back to ids) through the
    real update endpoint, then re-exporting, reproduces the identical document.
    """
    catalog_assistant = assistant_utils.create_assistant()
    retry_policy = {
        "initial_interval": 1.0,
        "backoff_factor": 2.0,
        "max_interval": 10.0,
        "max_attempts": 2,
    }
    # A real, deployment-reachable MCP server (same package the existing MCP workflow tests
    # use), since workflow creation synchronously connects to every custom-config MCP server.
    mcp_command = "uvx"
    mcp_args = ["--with", "mcp<2.0.0", "mcp-server-time"]
    workflow_yaml = WorkflowYamlModel(
        assistants=[
            AssistantModel(
                id="wf_assistant",
                model=default_llm.base_name,
                assistant_id=catalog_assistant.id,
                mcp_servers=[
                    MCPServerDetails(
                        name="wf_mcp",
                        description=None,
                        enabled=True,
                        use_custom_config=True,
                        config=MCPServerConfig(command=mcp_command, args=mcp_args),
                    )
                ],
            )
        ],
        tools=[
            ToolModel(id="wf_tool", tool=AgentWorkspaceTool.LIST_WORKSPACE_FILES.value)
        ],
        custom_nodes=[
            CustomNodeModel(
                id="wf_custom",
                custom_node_id="transform_node",
                name="Transform",
                config=TRANSFORM_NODE_CONFIG,
            )
        ],
        states=[
            StateModel(
                id="wf_assistant",
                assistant_id="wf_assistant",
                task="List files then continue",
                next={"state_id": "wf_tool"},
                retry_policy=retry_policy,
            ),
            StateModel(id="wf_tool", tool_id="wf_tool", next={"state_id": "wf_custom"}),
            StateModel(
                id="wf_custom",
                custom_node_id="wf_custom",
                next={
                    "switch": {
                        "cases": [{"condition": "true", "state_id": "end"}],
                        "default": "end",
                    }
                },
            ),
        ],
    )
    workflow = workflow_utils.create_workflow(
        workflow_type=WorkflowMode.SEQUENTIAL,
        workflow_yaml=prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True)),
    )

    try:
        document = client.export.export("workflow", workflow.id)
        definition = document["spec"]["workflow"]

        assert_that(isinstance(definition["assistants"], dict), equal_to(True))
        wf_assistant_entry = definition["assistants"]["wf_assistant"]
        assert_that(
            wf_assistant_entry["assistant_id"], equal_to(catalog_assistant.name)
        )
        assert_that(wf_assistant_entry["mcp_servers"][0]["name"], equal_to("wf_mcp"))

        assert_that(definition["tools"][0]["tool"], equal_to("list_workspace_files"))
        assert_that(
            definition["custom_nodes"][0]["custom_node_id"], equal_to("transform_node")
        )

        wf_state = next(s for s in definition["states"] if s["id"] == "wf_assistant")
        assert_that(wf_state["retry_policy"], equal_to(retry_policy))

        custom_state = next(s for s in definition["states"] if s["id"] == "wf_custom")
        assert_that(custom_state["next"]["switch"]["default"], equal_to("end"))
        assert_that(
            custom_state["next"]["switch"]["cases"][0]["condition"], equal_to("true")
        )

        # render()'s claim, verified indirectly: convert the definition back into yaml_config
        # (the catalog assistant's name resolved back to its id, and the MCP server's env:
        # command/args references resolved back to the real values — exactly what a real
        # apply tool does by reading them from the environment) and submit it as a real
        # update; re-exporting must reproduce the identical document.
        definition_for_update = copy.deepcopy(definition)
        mcp_config = definition_for_update["assistants"]["wf_assistant"]["mcp_servers"][
            0
        ]["config"]
        mcp_config["command"] = mcp_command
        mcp_config["args"] = mcp_args
        rendered_yaml_config = _workflow_definition_to_yaml_config(
            definition_for_update,
            assistant_ids={catalog_assistant.name: catalog_assistant.id},
        )
        workflow_utils.update_workflow(
            workflow, yaml_config=rendered_yaml_config, mode=WorkflowMode.SEQUENTIAL
        )
        after_document = client.export.export("workflow", workflow.id)
        assert_that(after_document["spec"]["workflow"], equal_to(definition))
    finally:
        workflow_utils.delete_workflow(workflow)


# ---------------------------------------------------------------------------------------------
# AC-11: skill update built from the export document leaves companion files unchanged
# ---------------------------------------------------------------------------------------------


@pytest.mark.export
@pytest.mark.api
def test_export_skill_update_round_trip_keeps_companion_files_unchanged(
    client, skill_utils
):
    """@case public-export-rest-endpoint_TC_012"""
    companion_content = f"companion notes {get_random_name()}"
    created = skill_utils.create_skill_with_files(
        files=[
            SkillCompanionFilePayload(
                path="notes.txt",
                content=companion_content,
                mime_type="text/plain",
                encoding="text",
            )
        ]
    )

    document = client.export.export("skill", created.id)
    spec = document["spec"]
    skill_utils.update_skill(
        created.id,
        name=spec["name"],
        description=spec["description"],
        content=spec["content"],
        visibility=SkillVisibility(spec["visibility"]),
        categories=spec["categories"],
        enabled_builtin_subagents=spec["enabled_builtin_subagents"],
    )

    companion_after = client.skills.get_companion_file(created.id, "notes.txt")
    assert_that(companion_after.content, equal_to(companion_content))


# ---------------------------------------------------------------------------------------------
# AC-12: export of an unsupported datasource type fails naming the type
# ---------------------------------------------------------------------------------------------


@pytest.mark.export
@pytest.mark.api
def test_export_unsupported_datasource_type_fails_naming_type(client, file_datasource):
    """@case public-export-rest-endpoint_TC_013"""
    with pytest.raises(HTTPError) as exc_info:
        client.export.export("datasource", file_datasource.id)

    response = exc_info.value.response
    assert_that(response.status_code, equal_to(422))
    body = response.json()
    assert_that(body["error"]["message"], contains_string("knowledge_base_file"))
    assert_that(body, is_not(has_key("meta")))
    assert_that(body, is_not(has_key("spec")))


# ---------------------------------------------------------------------------------------------
# AC-13: export fails naming a clashing referenced name
# ---------------------------------------------------------------------------------------------


@pytest.mark.export
@pytest.mark.api
def test_export_fails_naming_clashing_referenced_name(client, assistant_utils):
    """@case public-export-rest-endpoint_TC_014"""
    # shared=True puts both siblings in the ambiguity scope's peer query
    # (Assistant.shared.is_(True)); a private (default) sibling with the same creator was
    # confirmed live not to be matched by that query's creator-owned branch.
    shared_name = get_random_name()
    sibling_a = assistant_utils.create_assistant(
        assistant_name=shared_name, slug=f"{shared_name}-a", shared=True
    )
    sibling_b = assistant_utils.create_assistant(
        assistant_name=shared_name, slug=f"{shared_name}-b", shared=True
    )
    referencer = assistant_utils.create_assistant(assistant_ids=[sibling_b.id])
    # sibling_a only needs to exist to create the name clash in scope.
    assert_that(sibling_a.name, equal_to(shared_name))

    with pytest.raises(HTTPError) as exc_info:
        client.export.export("assistant", referencer.id)

    response = exc_info.value.response
    assert_that(response.status_code, equal_to(422))
    message = response.json()["error"]["message"]
    assert_that(message, contains_string("Assistant"))
    assert_that(message, contains_string(shared_name))


# ---------------------------------------------------------------------------------------------
# mr-diff: two credentials colliding on the same derived env: reference name
# ---------------------------------------------------------------------------------------------


@pytest.mark.export
@pytest.mark.api
def test_export_fails_when_two_credentials_collide_on_env_reference(
    client, assistant_utils
):
    """@case public-export-rest-endpoint_TC_015"""
    assistant = assistant_utils.create_assistant(
        mcp_servers=[
            MCPServerDetails(
                name="server-1", description=None, enabled=True, command="npx"
            ),
            MCPServerDetails(
                name="server_1", description=None, enabled=True, command="npx"
            ),
        ]
    )

    with pytest.raises(HTTPError) as exc_info:
        client.export.export("assistant", assistant.id)

    response = exc_info.value.response
    assert_that(response.status_code, equal_to(422))
    assert_that(
        response.json()["error"]["message"],
        contains_string("Credential references collide"),
    )


# ---------------------------------------------------------------------------------------------
# mr-diff: a reference resolved outside the target project is refused
# ---------------------------------------------------------------------------------------------


@pytest.fixture
def second_project(project_utils):
    name = get_random_name()
    project_utils.create_project(name=name)
    yield name
    try:
        project_utils.delete_project_with_all_members(name)
    except Exception:
        pass


@pytest.mark.export
@pytest.mark.api
def test_export_refuses_cross_project_reference(
    client, assistant_utils, second_project, workflow_with_assistant
):
    """@case public-export-rest-endpoint_TC_017"""
    other_project_assistant = assistant_utils.create_assistant(
        project_name=second_project
    )
    workflow = workflow_with_assistant(
        other_project_assistant, "Run the cross-project assistant"
    )

    with pytest.raises(HTTPError) as exc_info:
        client.export.export("workflow", workflow.id)

    response = exc_info.value.response
    assert_that(response.status_code, equal_to(422))
    assert_that(
        response.json()["error"]["message"], contains_string("outside target project")
    )


# ---------------------------------------------------------------------------------------------
# mr-diff: a tool-level MCP server holding a credential is refused, not redacted
# ---------------------------------------------------------------------------------------------


@pytest.mark.export
@pytest.mark.api
def test_export_refuses_tool_level_mcp_credential(client, workflow_utils, default_llm):
    """@case public-export-rest-endpoint_TC_018"""
    workflow_yaml = WorkflowYamlModel(
        assistants=[
            AssistantModel(
                id="entry", model=default_llm.base_name, system_prompt="Entry step"
            )
        ],
        tools=[
            ToolModel(
                id="leaky_tool",
                # A real, deployment-reachable MCP server exposing a real tool name: workflow
                # creation synchronously connects to a tool-level MCP server and validates the
                # tool exists on it, so a fake command/tool name would fail at creation, before
                # the export behaviour under test ever runs.
                tool="get_current_time",
                mcp_server={
                    "name": "leaky_mcp",
                    "enabled": True,
                    "config": {
                        "command": "uvx",
                        "args": ["--with", "mcp<2.0.0", "mcp-server-time"],
                        "env": {"API_TOKEN": "literal-tool-secret"},
                    },
                },
            )
        ],
        states=[
            StateModel(
                id="entry", assistant_id="entry", next={"state_id": "leaky_tool"}
            ),
            StateModel(id="leaky_tool", tool_id="leaky_tool"),
        ],
    )
    workflow = workflow_utils.create_workflow(
        workflow_type=WorkflowMode.SEQUENTIAL,
        workflow_yaml=prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True)),
    )

    try:
        with pytest.raises(HTTPError) as exc_info:
            client.export.export("workflow", workflow.id)

        response = exc_info.value.response
        assert_that(response.status_code, equal_to(422))
        message = response.json()["error"]["message"]
        assert_that(message, contains_string("holds a credential"))
        assert_that(message, contains_string("config.env"))
    finally:
        workflow_utils.delete_workflow(workflow)


# ---------------------------------------------------------------------------------------------
# mr-diff: two MCP servers of one workflow owner sharing a name fails the export
# ---------------------------------------------------------------------------------------------


@pytest.mark.export
@pytest.mark.api
def test_export_fails_when_workflow_mcp_servers_share_a_name(
    client, workflow_with_virtual_assistant
):
    """@case public-export-rest-endpoint_TC_019"""
    name = get_random_name()
    workflow = workflow_with_virtual_assistant(
        name,
        mcp_servers=[
            MCPServerDetails(name="dup", description=None, enabled=True, command="npx"),
            MCPServerDetails(name="dup", description=None, enabled=True, command="npx"),
        ],
    )

    with pytest.raises(HTTPError) as exc_info:
        client.export.export("workflow", workflow.id)

    response = exc_info.value.response
    assert_that(response.status_code, equal_to(422))
    message = response.json()["error"]["message"]
    assert_that(message, contains_string("more than one MCP server named"))
    assert_that(message, contains_string("dup"))


# ---------------------------------------------------------------------------------------------
# mr-diff: a bare MCP catalog link cannot be exported
# ---------------------------------------------------------------------------------------------


@pytest.fixture
def global_mcp_config(client):
    response = client.mcp_configs.create(
        MCPConfigCreateRequest(
            name=get_random_name(),
            config=MCPServerConfigData(command="npx", args=["-y", "mcp-server-time"]),
            is_public=True,
        )
    )
    yield response
    try:
        client.mcp_configs.delete(response.id)
    except Exception:
        pass


@pytest.mark.export
@pytest.mark.api
def test_export_refuses_bare_mcp_catalog_link(
    client, global_mcp_config, workflow_with_virtual_assistant
):
    """@case public-export-rest-endpoint_TC_020"""
    name = get_random_name()
    workflow = workflow_with_virtual_assistant(
        name,
        mcp_servers=[
            MCPServerDetails(
                name="bare_catalog_link",
                description=None,
                enabled=True,
                mcp_config_id=global_mcp_config.id,
            )
        ],
    )

    with pytest.raises(HTTPError) as exc_info:
        client.export.export("workflow", workflow.id)

    response = exc_info.value.response
    assert_that(response.status_code, equal_to(422))
    message = response.json()["error"]["message"]
    assert_that(message, contains_string("catalog link"))
    assert_that(message, contains_string("bare_catalog_link"))


# ---------------------------------------------------------------------------------------------
# AC-9: integration and category round trips
# ---------------------------------------------------------------------------------------------


def _testable_github_credentials():
    """GitHub credentials that the ``/v1/settings/test/`` endpoint can actually verify.

    ``CredentialsManager.github_credentials()`` points ``url`` at the bare GitHub host (used
    for tool-config-style GIT integrations elsewhere in the suite), which the test-connection
    endpoint rejects with 400 ("Testing the connection requires the full repository URL") --
    confirmed against the live environment. Pointing ``url`` at a real repository's clone URL
    (``GITHUB_PROJECT`` + ``.git``, the same repo already relied on by the datasource tests,
    e.g. datasource_utils.py) is what the endpoint expects. Mirrors
    ``test_settings_transfer.py``'s ``_testable_gitlab_credentials``.
    """
    return [
        CredentialValues(
            key="url",
            value=f"{CredentialsManager.get_parameter('GITHUB_PROJECT')}.git",
        ),
        CredentialValues(key="auth_type", value="pat"),
        CredentialValues(key="name", value=""),
        CredentialValues(
            key="token", value=CredentialsManager.get_parameter("GITHUB_TOKEN")
        ),
    ]


@pytest.mark.export
@pytest.mark.github
@pytest.mark.api
@pytest.mark.parametrize(
    "scope", ["project", "user"], ids=["project-scope", "user-scope"]
)
def test_export_integration_round_trip_leaves_entity_unchanged(
    client, integration_utils, scope
):
    """@case public-export-rest-endpoint_TC_022"""
    # Real, working GitHub credentials, not a placeholder: the round trip below sends
    # CREDENTIAL_MASK for the secret ("token") only (export never reveals the stored value),
    # and the only way to prove the update didn't clobber the real secret with that mask
    # literal is to use the credential for real afterwards. The non-secret keys (auth_type,
    # name, url) must travel as real values: the backend's mask placeholder means "keep the
    # stored secret" for sensitive fields only, and the GIT request validator rejects a
    # non-"pat"/"github_app"/"oauth" auth_type outright, so masking it would 422 before the
    # mask is ever considered.
    credentials = _testable_github_credentials()
    credential_lookup = {cred.key: cred.value for cred in credentials}
    if scope == "project":
        integration = integration_utils.create_project_integration(
            credential_type=CredentialTypes.GIT, credentials=credentials
        )
    else:
        integration = integration_utils.create_user_integration(
            credential_type=CredentialTypes.GIT, credentials=credentials
        )

    try:
        before = client.export.export("integration", integration.id)
        spec = before["spec"]
        updated = Integration(
            id=integration.id,
            project_name=spec["project_name"],
            alias=spec["alias"],
            credential_type=CredentialTypes(spec["credential_type"]),
            credential_values=[
                CredentialValues(
                    key=e["key"],
                    value=CREDENTIAL_MASK
                    if e["key"] == "token"
                    else credential_lookup[e["key"]],
                )
                for e in spec["credential_values"]
            ],
            setting_type=IntegrationType(spec["setting_type"]),
            is_global=spec["is_global"],
        )
        integration_utils.update_integration(updated)
        after = client.export.export("integration", integration.id)

        assert_that(after["spec"]["alias"], equal_to(before["spec"]["alias"]))
        assert_that(
            after["spec"]["project_name"], equal_to(before["spec"]["project_name"])
        )
        assert_that(
            after["spec"]["credential_type"],
            equal_to(before["spec"]["credential_type"]),
        )
        assert_that(
            after["spec"]["setting_type"], equal_to(before["spec"]["setting_type"])
        )
        assert_that(after["spec"]["is_global"], equal_to(before["spec"]["is_global"]))
        after_keys = sorted(e["key"] for e in after["spec"]["credential_values"])
        before_keys = sorted(e["key"] for e in before["spec"]["credential_values"])
        assert_that(after_keys, equal_to(before_keys))

        test_response = integration_utils.test_integration(
            IntegrationTestRequest(
                credential_type=CredentialTypes.GIT, setting_id=integration.id
            ),
            IntegrationTestResponse,
        )
        assert_that(
            test_response,
            equal_to(IntegrationTestResponse(message="", success=True)),
            "stored credential no longer works after the round trip",
        )
    finally:
        setting_type = (
            IntegrationType.PROJECT if scope == "project" else IntegrationType.USER
        )
        integration_utils.delete_integration_by_id(integration.id, setting_type)


@pytest.mark.export
@pytest.mark.api
def test_export_category_round_trip_leaves_entity_unchanged(client, categories_utils):
    """@case public-export-rest-endpoint_TC_023"""
    category = categories_utils.create_category()

    try:
        before = client.export.export("category", category.id)
        spec = before["spec"]
        categories_utils.update_category(
            category.id, name=spec["name"], description=spec["description"]
        )
        after = client.export.export("category", category.id)

        assert_that(after["spec"], equal_to(before["spec"]))
    finally:
        categories_utils.delete_category(category.id)
