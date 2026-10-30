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

import logging
import uuid
from pathlib import Path
from typing import Optional

from pydantic import Field

from codemie_sdk.models.assistant import (
    AssistantChatRequest,
    AssistantCreateRequest,
    AssistantUpdateRequest,
    BuiltinSubagent,
    EnvVars,
    ExportAssistantPayload,
    ReactionRequest,
    ToolPermissionsConfig,
)
from codemie_test_harness.tests import (
    API_DOMAIN,
    LANGFUSE_TRACES_ENABLED,
    PROJECT,
    VERIFY_SSL,
)
from codemie_test_harness.tests.utils.base_utils import (
    BaseUtils,
    get_random_name,
    wait_for_entity,
)
from codemie_test_harness.tests.utils.http_utils import RequestHandler


class _CloneAssistantRequest(AssistantCreateRequest):
    """AssistantCreateRequest extended with source_assistant_id for clone tracking.

    AssistantCreateRequest (via AssistantRequestBase) uses ConfigDict(extra="ignore"),
    so new fields must be declared explicitly in a subclass. Pydantic v2 model_dump()
    on a subclass instance includes all parent fields plus the new field, making
    source_assistant_id appear in the serialised POST /v1/assistants payload.
    """

    source_assistant_id: Optional[str] = Field(default=None)


logger = logging.getLogger(__name__)


class AssistantUtils(BaseUtils):
    def send_create_assistant_request(
        self,
        llm_model_type=None,
        toolkits=(),
        context=(),
        mcp_servers=(),
        slug=None,
        description=None,
        system_prompt="",
        assistant_name=None,
        shared=False,
        project_name=None,
        top_p=None,
        temperature=None,
        assistant_ids=(),
        categories=(),
        conversation_starters=(),
        enabled_builtin_subagents=None,
        tool_permissions: ToolPermissionsConfig | None = None,
    ):
        # Generate a random name if assistant_name is not provided
        assistant_name = assistant_name if assistant_name else get_random_name()
        # Use the first available LLM model if llm_model_type is not provided
        llm_model_type = (
            llm_model_type
            if llm_model_type
            else [row for row in self.client.llms.list() if row.default][0].base_name
        )
        request = AssistantCreateRequest(
            name=assistant_name,
            slug=slug if slug else assistant_name,
            description=description if description else "Integration test assistant",
            shared=shared,
            system_prompt=system_prompt,
            project=project_name if project_name else PROJECT,
            llm_model_type=llm_model_type,
            toolkits=toolkits,
            context=context,
            mcp_servers=mcp_servers,
            top_p=top_p,
            temperature=temperature,
            assistant_ids=list(assistant_ids) if assistant_ids else [],
            categories=list(categories) if categories else [],
            conversation_starters=list(conversation_starters)
            if conversation_starters
            else [],
            enabled_builtin_subagents=enabled_builtin_subagents,
            tool_permissions=tool_permissions,
        )

        response = self.client.assistants.create(request)

        return response, assistant_name

    def create_assistant(
        self,
        llm_model_type=None,
        toolkits=(),
        context=(),
        mcp_servers=(),
        system_prompt="Act as a helpful assistant",
        assistant_name=None,
        slug=None,
        shared=False,
        project_name=None,
        top_p=None,
        temperature=None,
        description=None,
        assistant_ids=(),
        categories=(),
        conversation_starters=(),
        enabled_builtin_subagents=None,
        tool_permissions: ToolPermissionsConfig | None = None,
    ):
        # Generate a random name if assistant_name is not provided
        assistant_name = assistant_name if assistant_name else get_random_name()
        # Use the first available LLM model if llm_model_type is not provided
        llm_model_type = (
            llm_model_type
            if llm_model_type
            else [row for row in self.client.llms.list() if row.default][0].base_name
        )
        slug = slug if slug else assistant_name
        response = self.send_create_assistant_request(
            llm_model_type=llm_model_type,
            toolkits=toolkits,
            context=context,
            mcp_servers=mcp_servers,
            system_prompt=system_prompt,
            assistant_name=assistant_name,
            slug=slug,
            shared=shared,
            project_name=project_name,
            top_p=top_p,
            temperature=temperature,
            description=description,
            assistant_ids=assistant_ids,
            categories=categories,
            conversation_starters=conversation_starters,
            enabled_builtin_subagents=enabled_builtin_subagents,
            tool_permissions=tool_permissions,
        )

        return wait_for_entity(
            lambda: self.client.assistants.list(per_page=200),
            entity_name=response[1],
        )

    def ask_assistant(
        self,
        assistant,
        user_prompt,
        minimal_response=True,
        stream=False,
        tools_config=None,
        file_urls=(),
        conversation_id=None,
        history=(),
        output_schema=None,
        extract_failed_tools=False,
        return_stream_metadata=False,
    ):
        user_prompt = f"{user_prompt}; REQUEST_UUID: {uuid.uuid4()};"
        chat_request = AssistantChatRequest(
            content_raw=f"<p>{user_prompt}</p>",
            text=user_prompt,
            conversation_id=conversation_id,
            stream=stream,
            tools_config=tools_config,
            file_names=file_urls,
            history=history,
            output_schema=output_schema,
            metadata={"langfuse_traces_enabled": LANGFUSE_TRACES_ENABLED},
        )

        response = self.client.assistants.chat(
            assistant_id=assistant.id, request=chat_request
        )

        if stream:
            # Parse streaming response with optional chunk count and output schema
            if return_stream_metadata:
                generated_text, thoughts, chunk_count = self._parse_streaming_response(
                    response, return_chunk_count=True, output_schema=output_schema
                )
            else:
                generated_text, thoughts = self._parse_streaming_response(
                    response, output_schema=output_schema
                )
                chunk_count = None

            if minimal_response:
                if return_stream_metadata:
                    return {
                        "generated": generated_text,
                        "chunk_count": chunk_count,
                        "thought_count": len(thoughts),
                    }
                return generated_text
            else:

                class StreamResponse:
                    def __init__(self, _thoughts):
                        self.thoughts = _thoughts

                stream_response = StreamResponse(thoughts)
                triggered_tools = self._extract_triggered_tools(
                    stream_response, extract_failed_tools
                )
                if return_stream_metadata:
                    return {
                        "generated": generated_text,
                        "triggered_tools": triggered_tools,
                        "chunk_count": chunk_count,
                        "thought_count": len(thoughts),
                    }
                return generated_text, triggered_tools

        # Non-streaming response handling
        if minimal_response:
            return response.generated
        else:
            # Extract triggered tools from response thoughts
            triggered_tools = self._extract_triggered_tools(
                response, extract_failed_tools
            )
            return response.generated, triggered_tools

    def _parse_streaming_response(
        self, response, return_chunk_count=False, output_schema=None
    ):
        """
        Parse streaming response and extract generated text and thoughts.

        The streaming response contains concatenated JSON objects without delimiters.
        Each JSON object has the structure:
        {
            "time_elapsed": float | null,
            "generated_chunk": str | null,
            "generated": str | null,
            "thought": dict | null,
            "last": bool,
            ...
        }

        Args:
            response: requests.Response object with streaming content
            return_chunk_count: If True, returns the total number of chunks parsed
            output_schema: Optional Pydantic model or JSON schema to parse structured output

        Returns:
            tuple: (generated_text: str, thoughts: list[dict], chunk_count: int) if return_chunk_count=True
                   (generated_text: str, thoughts: list[dict]) otherwise
        """
        import json
        import inspect
        from pydantic import BaseModel

        generated_text = ""
        thoughts = []
        chunk_count = 0

        # Parse the streaming response as concatenated JSON objects
        # Each chunk in the stream is a complete JSON object, but there's no delimiter
        # We need to use a JSON decoder that can handle multiple objects
        decoder = json.JSONDecoder()
        buffer = ""

        # Read the entire response content and decode bytes to string
        for chunk in response.iter_content(chunk_size=None):
            if not chunk:
                continue
            # Decode bytes to string
            if isinstance(chunk, bytes):
                chunk = chunk.decode("utf-8")
            buffer += chunk

        # Parse multiple JSON objects from the buffer
        idx = 0
        while idx < len(buffer):
            buffer = buffer[idx:].lstrip()
            if not buffer:
                break
            try:
                chunk_data, end_idx = decoder.raw_decode(buffer)
                idx = end_idx
                chunk_count += 1

                if chunk_data.get("thought"):
                    thoughts.append(chunk_data["thought"])

                if chunk_data.get("last") and chunk_data.get("generated"):
                    generated_text = chunk_data["generated"]

            except json.JSONDecodeError:
                # If we can't parse, we've reached the end of valid JSON
                break

        # Parse structured output if schema provided
        if output_schema and generated_text:
            try:
                # Check if it's a Pydantic model
                if inspect.isclass(output_schema) and issubclass(
                    output_schema, BaseModel
                ):
                    # Parse JSON string and validate with Pydantic model
                    parsed_data = json.loads(generated_text)
                    generated_text = output_schema.model_validate(parsed_data)
                else:
                    # It's a JSON schema dict, just parse the JSON string
                    generated_text = json.loads(generated_text)
            except (json.JSONDecodeError, ValueError):
                # If parsing fails, keep the original string
                pass

        if return_chunk_count:
            return generated_text, thoughts, chunk_count
        return generated_text, thoughts

    def _extract_triggered_tools(self, response, extract_failed_tools):
        """
        Extract triggered tools from response thoughts.

        Filters out 'Codemie Thoughts' entries and optionally error entries,
        returning a list of tool names in lowercase.

        Args:
            response: The assistant response containing thoughts
            extract_failed_tools: If True, include tools that failed with errors

        Returns:
            list: List of triggered tool names in lowercase
        """
        triggered_tools = []

        # Check if response has thoughts attribute
        if not (hasattr(response, "thoughts") and response.thoughts):
            return triggered_tools

        for thought in response.thoughts:
            author_name = thought.get("author_name", "")

            # Skip if no author name or if it's 'Codemie Thoughts'
            if not author_name or author_name == "Codemie Thoughts":
                continue

            # If not extracting failed tools, skip error entries
            if not extract_failed_tools and thought.get("error", False):
                continue

            triggered_tools.append(author_name.lower())

        return triggered_tools

    def send_chat_request(
        self,
        assistant,
        request: AssistantChatRequest,
    ):
        return self.client.assistants.chat(assistant_id=assistant.id, request=request)

    def upload_file_to_chat(self, file_path: Path):
        return self.client.assistants.upload_file_to_chat(file_path)

    def get_prebuilt_assistant(self):
        return self.client.assistants.get_prebuilt()

    def get_assistant_context(self, project_name: str):
        return self.client.assistants.get_context(project_name)

    def get_assistant_tools(self):
        return self.client.assistants.get_tools()

    def get_tool_details(self, toolkit: str, tool_name: str):
        """ToolDetails of ``tool_name`` inside the available ``toolkit``."""
        toolkit_details = next(
            (kit for kit in self.get_assistant_tools() if kit.toolkit == toolkit), None
        )
        assert toolkit_details is not None, f"Toolkit '{toolkit}' is not available"
        tool_details = next(
            (tool for tool in toolkit_details.tools if tool.name == tool_name), None
        )
        assert tool_details is not None, (
            f"Tool '{tool_name}' is not in toolkit '{toolkit}'"
        )
        return tool_details

    def get_assistants(
        self,
        minimal_response=True,
        filters=None,
        scope="visible_to_user",
        page=0,
        per_page=12,
        sort_by=None,
        sort_order="desc",
    ):
        return self.client.assistants.list(
            minimal_response=minimal_response,
            filters=filters,
            scope=scope,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    def get_all_assistants(
        self,
        minimal_response=True,
        filters=None,
        scope="visible_to_user",
        per_page=100,
        sort_by=None,
        sort_order="desc",
    ):
        """Fetch assistants across all pages for the given scope/filters.

        Use only when a test must confirm presence/absence across the full
        result set (e.g. marketplace membership) rather than a single page.
        """
        all_assistants = []
        page = 0
        while True:
            page_assistants = self.get_assistants(
                minimal_response=minimal_response,
                filters=filters,
                scope=scope,
                page=page,
                per_page=per_page,
                sort_by=sort_by,
                sort_order=sort_order,
            )
            if not page_assistants:
                break
            all_assistants.extend(page_assistants)
            if len(page_assistants) < per_page:
                break
            page += 1
        return all_assistants

    def get_tasks(self, task_id):
        return self.client.tasks.get(task_id)

    def get_assistant_by_id(self, assistant_id: str):
        return self.client.assistants.get(assistant_id)

    def get_assistant_by_name(self, assistant_name: str, scope="visible_to_user"):
        return self.client.assistants.list(
            per_page=10,
            minimal_response=False,
            filters={"search": assistant_name},
            scope=scope,
        )[0]

    def get_assistant_by_slug(self, slug: str):
        return self.client.assistants.get_by_slug(slug)

    def get_assistant_by_slug_response(self, slug: str, project: Optional[str] = None):
        """Raw ``GET /v1/assistants/slug/{slug}[?project=...]`` response.

        Unlike ``get_assistant_by_slug`` this never raises on 4xx, so a test can
        assert the status code and error body of an ambiguous / unknown slug.
        """
        params = {"project": project} if project else None
        return self._raw_api().get(f"/v1/assistants/slug/{slug}", params=params)

    def _raw_api(self) -> RequestHandler:
        return RequestHandler(API_DOMAIN, self.client.token, VERIFY_SSL)

    def get_prebuilt_assistant_by_slug(self, slug: str):
        return self.client.assistants.get_prebuilt_by_slug(slug)

    def update_assistant(
        self, assistant_id: str, update_request: AssistantUpdateRequest
    ):
        return self.client.assistants.update(
            assistant_id=assistant_id, request=update_request
        )

    def delete_assistant(self, assistant):
        response = self.client.assistants.delete(assistant.id)
        for conversation in self.client.conversations.list_by_assistant_id(
            assistant.id
        ):
            try:
                self.client.conversations.delete(conversation.id)
            except Exception as e:
                logger.warning(f"Failed to delete conversation {conversation.id}: {e}")
        return response

    def delete_assistant_by_id(self, assistant_id: str):
        return self.client.assistants.delete(assistant_id)

    def get_builtin_subagents(self) -> list[BuiltinSubagent]:
        return self.client.assistants.get_builtin_subagents()

    def send_chat_request_by_id(self, assistant_id: str, request: AssistantChatRequest):
        return self.client.assistants.chat(assistant_id=assistant_id, request=request)

    def export_assistant(self, assistant_id: str):
        env_vars = EnvVars(
            azure_openai_url="https://ai-proxy.example.com",
            azure_openai_api_key="RANDOM_KEY",
            openai_api_type="azure",
            openai_api_version="2024-02-15-preview",
            models_env="dial",
        )
        payload = ExportAssistantPayload(env_vars=env_vars)
        return self.client.assistants.export(assistant_id, payload)

    def send_evaluate_assistant_request(self, assistant_id: str, evaluation_request):
        return self.client.assistants.evaluate(assistant_id, evaluation_request)

    def publish_assistant_to_marketplace(
        self, assistant_id: str, categories=None, ignore_recommendations=False
    ):
        return self.client.assistants.publish(
            assistant_id,
            categories=categories,
            ignore_recommendations=ignore_recommendations,
        )

    def unpublish_assistant_from_marketplace(self, assistant_id: str):
        return self.client.assistants.unpublish(assistant_id)

    def validate_assistant_for_marketplace(self, assistant_id: str):
        return self.client.assistants.marketplace_validate(assistant_id)

    def react_to_assistant(self, assistant_id: str, reaction: str):
        request = ReactionRequest(reaction=reaction)
        return self.client.assistants.react(assistant_id, request)

    def remove_reactions_from_assistant(self, assistant_id: str):
        return self.client.assistants.remove_reactions(assistant_id)

    def clone_assistant_api(self, source_assistant_id: str):
        """Clone an assistant by POSTing to /v1/assistants with source_assistant_id set.

        This triggers backend clone tracking: a clone event is logged against the source
        assistant and its clone_count is incremented on the marketplace assistant record.

        Args:
            source_assistant_id: ID of the assistant to clone.

        Returns:
            The newly created (cloned) assistant object (AssistantCreateResponse).
        """
        llm_model_type = [row for row in self.client.llms.list() if row.default][
            0
        ].base_name
        name = get_random_name()
        request = _CloneAssistantRequest(
            name=name,
            slug=name,
            description="Cloned assistant for E2E test",
            system_prompt="Act as a helpful assistant",
            project=PROJECT,
            llm_model_type=llm_model_type,
            source_assistant_id=source_assistant_id,
        )
        return self.client.assistants.create(request)
