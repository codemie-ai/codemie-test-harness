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

import copy
import json

import pytest

from codemie_test_harness.tests import CredentialsManager
from codemie_test_harness.tests.enums.tools import CodeExplorationTools

DEFAULT_EXCLUDE_FILES_VALUE = "*.log, tests/, **/build/**"
DEFAULT_INCLUDE_FILES_VALUE = "*.py, **/*.js"

PROVIDER_DEFAULT_BRANCH = "main"
PROVIDER_DEFAULT_DATASOURCE_ROOT = "/"


def default_repositories_json() -> str:
    """The `repositories` value pointing at the real GitLab
    project the suite already indexes, shared by every fixture that needs the
    AICE provider to actually complete indexing.
    """
    return json.dumps(
        {
            "repo": {
                "repo_url": CredentialsManager.get_parameter("GITLAB_PROJECT"),
                "token": CredentialsManager.get_parameter("GITLAB_TOKEN"),
                "branch": PROVIDER_DEFAULT_BRANCH,
            }
        }
    )


# AICE combined-provider (CodeExplorationToolkit) default-value fields
DEFAULT_REPOSITORIES_VALUE = (
    '{"repo": {"repo_url": '
    '"https://git.example.com/autotests/default-repo", '
    '"branch": "develop"}}'
)
DEFAULT_GRAPHDB_USERNAME_VALUE = "default-graphdb-username"
DEFAULT_GRAPHDB_PASSWORD_VALUE = "default-graphdb-password"
# Matches the schema's own documented example (neo4j://localhost:7687) — the
# API accepts this scheme fine (test_update_provider_schema_field_default_value,
# test_provider_schema_fields_default_values pass with it).
DEFAULT_GRAPHDB_TENANT_URL_VALUE = "neo4j://default-tenant:7687"
# The Create/Edit Data Source form rejects neo4j:// and bolt:// (client-side
# URL validation) while indexing rejects https:// — no value passes both, so the
# UI default-value test leaves graphdb_tenant_url unset. Frontend bug, file separately.


def provider_payload_with_default_value(
    base_payload: dict, parameter_name: str, default_value, *, tool_name: str = None
):
    """Return a deep copy of a provider request payload with `default_value`
    set (or removed, when `default_value` is None) on a named schema
    parameter of the provider's first provided toolkit.

    - `tool_name=None` (default): targets a provider-level config field at
      `toolkit_config.parameters[parameter_name]` (e.g. 'branch', 'api_url',
      'access_token').
    - `tool_name=<name>`: targets a per-tool argument at the matching entry
      in `provided_tools[<tool_name>].args_schema[parameter_name]` (e.g.
      'exclude_files' / 'include_files' / 'datasource_root' on the
      'create_datasource' tool).
    """
    payload = copy.deepcopy(base_payload)
    toolkit = payload["provided_toolkits"][0]
    if tool_name is None:
        target = toolkit["toolkit_config"]["parameters"][parameter_name]
    else:
        tool = next(
            (t for t in toolkit["provided_tools"] if t["name"] == tool_name), None
        )
        assert tool is not None, f"Tool [{tool_name}] not found in provided_tools"
        target = tool["args_schema"][parameter_name]
    if default_value is None:
        target.pop("default_value", None)
    else:
        target["default_value"] = default_value
    return payload


default_value_field_test_data = [
    pytest.param(
        "repositories",
        None,
        DEFAULT_REPOSITORIES_VALUE,
        id="repositories_with_default",
    ),
    pytest.param("repositories", None, None, id="repositories_without_default"),
    pytest.param(
        "graphdb_username",
        None,
        DEFAULT_GRAPHDB_USERNAME_VALUE,
        id="graphdb_username_with_default",
    ),
    pytest.param("graphdb_username", None, None, id="graphdb_username_without_default"),
    pytest.param(
        "graphdb_password",
        None,
        DEFAULT_GRAPHDB_PASSWORD_VALUE,
        id="graphdb_password_with_default",
    ),
    pytest.param("graphdb_password", None, None, id="graphdb_password_without_default"),
    pytest.param(
        "graphdb_tenant_url",
        None,
        DEFAULT_GRAPHDB_TENANT_URL_VALUE,
        id="graphdb_tenant_url_with_default",
    ),
    pytest.param(
        "graphdb_tenant_url", None, None, id="graphdb_tenant_url_without_default"
    ),
]

_PLACEHOLDER_NODE_ID = "d865ccff-bb1d-4d1a-a34e-87b679308034"

code_exploration_toolkit_test_data = [
    pytest.param(
        "Call the knowledge_graph_search_semantic tool directly (not via "
        "knowledge_graph_run_python) to find code related to user "
        "authentication and login logic",
        CodeExplorationTools.SEARCH_SEMANTIC,
        id="search_semantic",
    ),
    pytest.param(
        "Call the knowledge_graph_search_keyword tool directly (not via "
        "knowledge_graph_run_python) to search the codebase for the keyword TODO",
        CodeExplorationTools.SEARCH_KEYWORD,
        id="search_keyword",
    ),
    pytest.param(
        "Call the knowledge_graph_search_nodes_by_name tool directly (not via "
        "knowledge_graph_run_python) to find nodes named Controller",
        CodeExplorationTools.SEARCH_NODES_BY_NAME,
        id="search_nodes_by_name",
    ),
    pytest.param(
        "Show the directory tree structure starting from the root",
        CodeExplorationTools.BROWSE_HIERARCHY,
        id="browse_hierarchy",
    ),
    pytest.param(
        f"Show me the full content of node {_PLACEHOLDER_NODE_ID}",
        CodeExplorationTools.READ_NODE_CONTENT,
        id="read_node_content",
    ),
    pytest.param(
        f"Show me a summary of node {_PLACEHOLDER_NODE_ID}",
        CodeExplorationTools.READ_NODE_SUMMARY,
        id="read_node_summary",
    ),
    pytest.param(
        f"Show me metadata (name, file path, labels) for node {_PLACEHOLDER_NODE_ID}",
        CodeExplorationTools.DESCRIBE_NODE,
        id="describe_node",
    ),
    pytest.param(
        "Give me an overview of this workspace",
        CodeExplorationTools.DESCRIBE_WORKSPACE,
        id="describe_workspace",
    ),
    pytest.param(
        "Describe the graph database structure and data model",
        CodeExplorationTools.DESCRIBE_DATA_MODEL,
        id="describe_data_model",
    ),
    pytest.param(
        f"Show me what functions or methods are called starting from node {_PLACEHOLDER_NODE_ID}",
        CodeExplorationTools.TRACE_CALLS,
        id="trace_calls",
    ),
    pytest.param(
        f"Show me what node {_PLACEHOLDER_NODE_ID} depends on",
        CodeExplorationTools.TRACE_DEPENDENCIES,
        id="trace_dependencies",
    ),
    pytest.param(
        "Run this Cypher query against the graph: MATCH (n) RETURN n.name AS name LIMIT 5",
        CodeExplorationTools.RUN_CYPHER,
        id="run_cypher",
    ),
    pytest.param(
        "Use the knowledge_graph_run_python tool to run a Python script that "
        "computes 123 * 456 and prints the result",
        CodeExplorationTools.RUN_PYTHON,
        id="run_python",
    ),
    pytest.param(
        "Call the read_resource tool directly to read the 'aice://info' resource",
        CodeExplorationTools.READ_RESOURCE,
        id="read_resource",
    ),
]
