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

from typing import Optional, List

import yaml
from pydantic import BaseModel, Field, ConfigDict

from codemie_sdk.models.assistant import MCPServerDetails


def prepare_yaml_content(model_dump: str) -> str:
    yaml.add_representer(str, str_presenter)
    return yaml.dump(
        model_dump,
        sort_keys=False,
        allow_unicode=True,
    )


def str_presenter(dumper, data):
    style = None
    if "\n" in data:
        style = "|"
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


# ------------------- MODELS -------------------


class CustomNodeModel(BaseModel):
    id: str
    custom_node_id: str
    name: Optional[str] = None
    model: Optional[str] = None
    config: Optional[dict] = None


class ToolModel(BaseModel):
    id: Optional[str] = None
    tool: Optional[str] = None
    name: Optional[str] = None
    integration_alias: Optional[str] = None
    tool_args: Optional[dict] = None
    datasource_ids: Optional[List[str]] = None
    # Tools a script step may call (the workspace script tool only): a list of {name, integration_alias?}.
    tool_access: Optional[List["ToolModel"]] = None


class AssistantModel(BaseModel):
    id: str
    model: str
    assistant_id: Optional[str] = None
    system_prompt: Optional[str] = None
    datasource_ids: Optional[List[str]] = None
    skill_ids: Optional[List[str]] = None
    tools: Optional[List[ToolModel]] = None
    mcp_servers: Optional[List[MCPServerDetails]] = None


class StateModel(BaseModel):
    id: str
    assistant_id: Optional[str] = None
    custom_node_id: Optional[str] = None
    tool_id: Optional[str] = None
    workflow_id: Optional[str] = None
    task: Optional[str] = None
    next: Optional[dict] = {"state_id": "end"}
    output_schema: Optional[str] = None
    resolve_dynamic_values_in_prompt: Optional[bool] = True


class WorkflowYamlModel(BaseModel):
    max_concurrency: Optional[int] = None
    enable_summarization_node: Optional[bool] = None
    custom_nodes: List[CustomNodeModel] = Field(default_factory=list)
    tools: List[ToolModel] = Field(default_factory=list)
    assistants: List[AssistantModel] = Field(default_factory=list)
    states: List[StateModel] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")
