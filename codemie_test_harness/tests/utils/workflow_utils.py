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

import json
import logging
import os
import uuid
from pathlib import Path
from typing import List, Optional
import time


from codemie_sdk.exceptions import ApiError
from codemie_sdk.models.workflow import (
    WorkflowCreateRequest,
    WorkflowUpdateRequest,
    WorkflowMode,
    WorkflowExecution,
)
from codemie_sdk.models.workflow_state import (
    WorkflowExecutionState,
    WorkflowExecutionStatusEnum,
)
from codemie_sdk.services.workflow_execution import WorkflowExecutionService
from codemie_sdk.services.workflow_execution_state import WorkflowExecutionStateService

from codemie_test_harness.tests import (
    PROJECT,
    VERIFY_SSL,
    API_DOMAIN,
    CredentialsManager,
)
from codemie_test_harness.tests.utils.base_utils import (
    BaseUtils,
    get_random_name,
    wait_for_entity,
)
from codemie_test_harness.tests.utils.http_utils import RequestHandler
from time import sleep


workflow_endpoint = "/v1/workflows"

logger = logging.getLogger(__name__)


class WorkflowUtils(BaseUtils):
    def evaluate_workflow(self, workflow_id: str, request) -> dict:
        """Evaluate a workflow against a Langfuse dataset using the SDK.

        Raises ApiError on non-2xx responses — use pytest.raises in error-path tests.
        """
        return self.client.workflows.evaluate(workflow_id, request)

    def send_evaluate_workflow_request(self, workflow_id: str, payload: dict):
        """Send a raw evaluate POST, returning the requests.Response without raising.

        Use only when tests need to bypass SDK Pydantic validation (e.g. 422 boundary tests).
        """
        request_handler = RequestHandler(API_DOMAIN, self.client.token, VERIFY_SSL)
        return request_handler.post(
            f"{workflow_endpoint}/{workflow_id}/evaluate",
            stream=True,
            json_data=payload,
        )

    def send_request_to_create_workflow_endpoint(
        self, request: WorkflowCreateRequest, error_format: Optional[str] = None
    ) -> dict:
        """
        Send request to workflow creation endpoint without raising error for response status codes.

        Args:
            request: The workflow creation request containing required fields:
                    - name: Name of the workflow
                    - description: Description of the workflow
                    - project: Project identifier
                    - yaml_config: YAML configuration for the workflow
                    Optional fields with defaults:
                    - mode: WorkflowMode (defaults to SEQUENTIAL)
                    - shared: bool (defaults to False)
                    - icon_url: Optional URL for workflow icon
            error_format: Optional error format parameter ('string' or 'json')

        Returns:
            Raw response from '/v1/workflows' endpoint
        """

        request_handler = RequestHandler(API_DOMAIN, self.client.token, VERIFY_SSL)

        params = {"error_format": error_format} if error_format else None

        return request_handler.post(
            workflow_endpoint, dict, json_data=request.model_dump(), params=params
        )

    def send_create_workflow_request(
        self,
        workflow_yaml,
        workflow_type=WorkflowMode.SEQUENTIAL,
        description=None,
        workflow_name=None,
        shared=False,
        project=None,
        categories=None,
    ):
        workflow_name = get_random_name() if not workflow_name else workflow_name

        request = WorkflowCreateRequest(
            name=workflow_name,
            description=description if description else "Test Workflow",
            project=project if project else PROJECT,
            mode=workflow_type,
            yaml_config=workflow_yaml,
            shared=shared,
            categories=categories or [],
        )

        response = self.client.workflows.create_workflow(request)

        return response, workflow_name

    def create_workflow(
        self,
        workflow_type,
        workflow_yaml,
        description=None,
        workflow_name=None,
        shared=False,
        project_name=None,
        categories=None,
    ):
        """
        Sends request to workflow creation endpoint and waits for workflow created.
        """
        response = self.send_create_workflow_request(
            workflow_yaml,
            workflow_type,
            description,
            workflow_name,
            shared,
            project_name,
            categories,
        )

        return wait_for_entity(
            lambda: self.client.workflows.list(per_page=200),
            entity_name=response[1],
        )

    def execute_workflow(
        self,
        workflow,
        execution_name,
        user_input="",
        file_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        modify_prompt: bool = True,
        file_names: Optional[List[str]] = None,
    ):
        """Execute a workflow and return the output of the named state.

        Args:
            file_names: Run-start file references (several files at once).
            modify_prompt: When True (default), prepends a unique nonce to bust
                prompt caching.  Pass False when user_input is structured JSON
                that must not be prefixed — a _debug_id key is injected inside
                the JSON object instead.
        """
        if modify_prompt:
            user_input = f"{user_input}; REQUEST_UUID: {uuid.uuid4()};"
        else:
            try:
                payload = json.loads(user_input)
                payload["_debug_id"] = str(uuid.uuid4())
                user_input = json.dumps(payload)
            except (json.JSONDecodeError, TypeError):
                pass
        self.client.workflows.run(
            workflow,
            user_input=user_input,
            file_name=file_name,
            file_names=file_names,
            tags=tags,
            session_id=session_id,
        )
        executions_service = self.client.workflows.executions(workflow)

        # Wait for execution to appear (returns execution object with prompt attribute)
        execution = wait_for_entity(
            lambda: executions_service.list(),
            entity_name=user_input,
        )
        execution_id = execution.execution_id

        # Wait for state to appear
        states_service = executions_service.states(execution_id)
        state = wait_for_entity(
            lambda: states_service.list(per_page=20),
            entity_name=execution_name,
            timeout=30,
        )

        self.wait_for_completion(service=states_service, _id=state.id)
        self.wait_for_completion(service=executions_service, _id=execution_id)

        return states_service.get_output(state_id=state.id).output

    def execute_workflow_expecting_failure(
        self,
        workflow,
        user_input="",
        file_name: Optional[str] = None,
    ):
        """
        Execute workflow and wait for it to fail, then return the error response.

        This method is useful for testing scenarios where workflow execution is expected
        to fail (e.g., due to guardrails blocking harmful content).

        Args:
            workflow: Workflow ID or object
            user_input: Input prompt for the workflow
            file_name: Optional file to attach

        Returns:
            ApiError: The error raised when workflow fails

        Raises:
            TimeoutError: If workflow doesn't fail within timeout
            AssertionError: If workflow succeeds when failure was expected
        """
        user_input = f"{user_input}; REQUEST_UUID: {uuid.uuid4()};"
        self.client.workflows.run(workflow, user_input=user_input, file_name=file_name)
        executions_service = self.client.workflows.executions(workflow)

        # Wait for execution to appear
        execution = wait_for_entity(
            lambda: executions_service.list(),
            entity_name=user_input,
        )
        execution_id = execution.execution_id

        # Wait for state to appear
        states_service = executions_service.states(execution_id)
        state = wait_for_entity(
            lambda: states_service.list(),
            entity_name="AI/Run Thoughts",
        )

        error = states_service.get_output(state.id).output

        return error

    def create_workflow_execution(
        self,
        workflow_id,
        user_input: str = "",
        conversation_id: Optional[str] = None,
        file_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        modify_prompt: bool = True,
        file_names: Optional[List[str]] = None,
        timeout: Optional[int] = None,
    ):
        """
        Create a workflow execution with optional conversation context.

        This method is used for workflow chat mode where executions are linked
        to a conversation. It waits for the execution to complete and verifies
        that the LLM responded to the message.

        Args:
            workflow_id: Workflow ID
            user_input: User input prompt
            conversation_id: Optional conversation ID for chat mode
            file_name: Optional file name
            tags: Optional tags to attach to the workflow execution trace in Langfuse.
            modify_prompt: When True (default), prepends a unique nonce to bust
                prompt caching.  Pass False when user_input is structured JSON
                that must not be prefixed — a _debug_id key is injected inside
                the JSON object instead.
            file_names: Run-start file references (several files at once).
            timeout: Override the shared ``DEFAULT_TIMEOUT`` completion poll timeout
                (seconds) for this call only. Pass it for executions known to run
                long for reasons unrelated to the LLM (e.g. a script step that
                provisions a sandbox) instead of raising the timeout for every test.

        Returns:
            Completed workflow execution object with LLM response
        """
        if modify_prompt:
            user_input = f"{user_input}; REQUEST_UUID: {uuid.uuid4()};"
        else:
            try:
                payload = json.loads(user_input)
                payload["_debug_id"] = str(uuid.uuid4())
                user_input = json.dumps(payload)
            except (json.JSONDecodeError, TypeError):
                pass
        executions_service = self.client.workflows.executions(workflow_id)

        # Create execution with optional conversation_id
        executions_service.create(
            user_input=user_input,
            file_name=file_name,
            file_names=file_names,
            conversation_id=conversation_id,
            tags=tags,
        )

        # Wait for execution to appear (same technique as execute_workflow)
        execution = wait_for_entity(
            lambda: executions_service.list(),
            entity_name=user_input,
            timeout=30,
        )
        execution_id = execution.execution_id

        # Wait for execution to complete
        wait_kwargs = {"timeout": timeout} if timeout is not None else {}
        self.wait_for_completion(
            service=executions_service, _id=execution_id, **wait_kwargs
        )

        # Get the completed execution with final status
        completed_execution = executions_service.get(execution_id)

        return completed_execution

    def create_workflow_execution_no_wait(
        self,
        workflow_id,
        user_input: str = "",
        conversation_id: Optional[str] = None,
        modify_prompt: bool = True,
    ):
        """
        Create a workflow execution and return as soon as it appears, without
        waiting for it to complete.

        Used by tests that need to observe an intermediate execution status
        (e.g. IN_PROGRESS) before the run finishes. Callers are
        responsible for driving the execution to completion themselves (e.g. via
        ``wait_for_completion``) before test teardown.

        Args:
            workflow_id: Workflow ID
            user_input: User input prompt
            conversation_id: Optional conversation ID for chat mode
            modify_prompt: When True (default), prepends a unique nonce to bust
                prompt caching.

        Returns:
            Tuple of (execution, executions_service) where ``execution`` is the
            just-appeared (not necessarily completed) execution object and
            ``executions_service`` can be used for further polling/cleanup.
        """
        if modify_prompt:
            user_input = f"{user_input}; REQUEST_UUID: {uuid.uuid4()};"

        executions_service = self.client.workflows.executions(workflow_id)

        executions_service.create(
            user_input=user_input,
            conversation_id=conversation_id,
        )

        execution = wait_for_entity(
            lambda: executions_service.list(),
            entity_name=user_input,
            timeout=30,
        )

        return execution, executions_service

    def run_workflow(
        self, workflow_id, user_input="", tags: Optional[List[str]] = None
    ):
        user_input = f"{user_input}; REQUEST_UUID: {uuid.uuid4()};"
        return self.client.workflows.run(
            workflow_id=workflow_id, user_input=user_input, tags=tags
        )

    def get_workflow(self, workflow_id):
        return self.client.workflows.get(workflow_id)

    def get_workflow_execution(self, test_workflow_id, execution_id):
        return self.client.workflows.executions(test_workflow_id).get(execution_id)

    def delete_workflow_execution(self, workflow_id, execution_id):
        """Delete a single workflow execution via the SDK.

        Raises requests.exceptions.HTTPError (via response.raise_for_status()) on
        non-2xx responses, e.g. when the execution is still linked to a live
        conversation (400).
        """
        return self.client.workflows.executions(workflow_id).delete(execution_id)

    def get_workflow_executions_states(self, test_workflow_id, execution_id):
        return self.client.workflows.executions(test_workflow_id).states(execution_id)

    def send_update_workflow_request(
        self,
        workflow_id,
        request: WorkflowUpdateRequest,
    ):
        return self.client.workflows.update(workflow_id, request)

    def update_workflow(
        self,
        workflow,
        name=None,
        description=None,
        project=None,
        yaml_config=None,
        mode=None,
        shared=None,
        categories=None,
    ):
        """Update a workflow; ``categories=None`` leaves the stored categories untouched."""
        name = name if name else workflow.name
        request = WorkflowUpdateRequest(
            name=name,
            project=project if project else workflow.project,
            description=description if description else workflow.description,
            yaml_config=yaml_config if yaml_config else workflow.yaml_config,
            mode=mode if mode else workflow.mode,
            shared=shared if shared else workflow.shared,
            categories=categories,
        )
        self.send_update_workflow_request(workflow.id, request=request)

        return wait_for_entity(
            lambda: self.client.workflows.list(per_page=200),
            entity_name=name,
        )

    def get_prebuilt_workflows(self):
        return self.client.workflows.get_prebuilt()

    def publish_workflow_to_marketplace(
        self, workflow_id: str, categories: List[str]
    ) -> dict:
        """Publish a workflow to the marketplace — the only way the public API sets
        ``is_global=True``.
        """
        return self.client.workflows.publish(workflow_id, categories=categories)

    def validate_workflow_marketplace_publish(self, workflow_id: str) -> dict:
        """Surface the credential/warning review a publish attempt would show, without actually changing ``is_global``."""
        return self.client.workflows.marketplace_validate(workflow_id)

    def unpublish_workflow_from_marketplace(self, workflow_id: str) -> dict:
        """Unpublish a workflow from the marketplace, setting ``is_global`` back to False."""
        return self.client.workflows.unpublish(workflow_id)

    @staticmethod
    def open_workflow_yaml(path, yaml_file, values: dict = None):
        yaml_path = os.path.join(os.path.dirname(__file__), f"../{path}/{yaml_file}")
        assert os.path.exists(yaml_path), f"YAML file not found: {yaml_path}"

        with open(yaml_path, encoding="utf-8") as file:
            template = file.read()

        return template.format(**values) if values else template

    def delete_workflow(self, workflow):
        for conversation in self.client.conversations.list():
            if conversation.initial_assistant_id == workflow.id:
                try:
                    self.client.conversations.delete(conversation.id)
                except Exception as e:
                    logger.warning(
                        f"Failed to delete conversation {conversation.id}: {e}"
                    )
        self.client.workflows.delete(workflow.id)

    def get_executions(self, workflow):
        return self.client.workflows.executions(workflow.id).list()

    def wait_for_executions(self, workflow, timeout: int = 30, poll_interval: int = 3):
        deadline = time.time() + timeout
        while time.time() < deadline:
            executions = self.get_executions(workflow)
            if executions:
                return executions
            sleep(poll_interval)
        raise TimeoutError(
            f"No executions appeared for workflow {workflow.id} within {timeout}s"
        )

    def get_first_execution(self, workflow):
        return self.get_executions(workflow)[0]

    @staticmethod
    def poll_execution_until_status(
        executions_service: WorkflowExecutionService,
        execution_id: str,
        stop_statuses: set,
        timeout: int = 60,
        poll_interval: float = 0.5,
    ) -> Optional[WorkflowExecution]:
        """Poll an execution until its status is one of ``stop_statuses``.

        Lets a test observe a transient status (e.g. IN_PROGRESS) without a
        polling loop in the test body.

        Returns:
            The execution as soon as its status is in ``stop_statuses``, or
            None if the timeout elapses first.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            execution = executions_service.get(execution_id)
            if execution.status in stop_statuses:
                return execution
            sleep(poll_interval)
        return None

    def extract_triggered_tools_from_execution(self, workflow, execution=None):
        """
        Extract triggered tools from workflow execution thoughts.

        Args:
            workflow: Workflow object
            execution: Execution object

        Returns:
            list: List of triggered tool names in lowercase
        """

        if execution:
            execution_id = execution.execution_id
        else:
            executions = self.get_executions(workflow)
            assert len(executions) > 0, "No workflow executions found"
            first_execution = executions[0]
            execution_id = first_execution.execution_id

        triggered_tools = []

        # Get execution states to find thought IDs
        states_service = self.client.workflows.executions(workflow.id).states(
            execution_id
        )
        states = states_service.list()

        if not states:
            return triggered_tools

        # Collect all thought IDs from states
        thought_ids = []
        for state in states:
            if hasattr(state, "thoughts") and state.thoughts:
                for thought in state.thoughts:
                    thought_ids.append(thought.id)

        if not thought_ids:
            return triggered_tools

        # Get detailed thoughts information
        executions_service = self.client.workflows.executions(workflow.id)
        thoughts_data = executions_service.get_thoughts(execution_id, thought_ids)

        # Convert thoughts objects to dictionaries for processing
        thoughts_dict_data = [thought.model_dump() for thought in thoughts_data]

        # Extract triggered tools from thoughts
        triggered_tools = self._extract_tools_from_thoughts(thoughts_dict_data)

        return triggered_tools

    def execute_workflow_with_headers(
        self,
        workflow_id: str,
        execution_name: str,
        user_input: str = "",
        propagate_headers: bool = False,
        extra_headers: Optional[dict] = None,
    ) -> str:
        """Execute a workflow with optional custom HTTP headers for header propagation testing.

        Passes propagate_headers and extra_headers to client.workflows.run() so the
        backend can inject X-* request headers into the workflow context store.

        Returns:
            The execution_id of the completed execution.
        """
        user_input = f"{user_input}; REQUEST_UUID: {uuid.uuid4()};"
        self.client.workflows.run(
            workflow_id,
            user_input=user_input,
            propagate_headers=propagate_headers,
            headers=extra_headers or None,
        )
        executions_service = self.client.workflows.executions(workflow_id)

        execution = wait_for_entity(
            lambda: executions_service.list(),
            entity_name=user_input,
        )
        execution_id = execution.execution_id

        states_service = executions_service.states(execution_id)
        state = wait_for_entity(
            lambda: states_service.list(per_page=20),
            entity_name=execution_name,
            timeout=30,
        )

        self.wait_for_completion(service=states_service, _id=state.id)
        self.wait_for_completion(service=executions_service, _id=execution_id)

        return execution_id

    def get_context_store_at_state(
        self,
        workflow_id: str,
        execution_id: str,
        state_name: str,
    ) -> dict:
        """Return the workflow_context.context_store from the transition into the named state.

        Args:
            workflow_id: The workflow whose execution to inspect.
            execution_id: The execution whose states to query.
            state_name: YAML state id (e.g. "verify_state") to look up in the
                        execution-states list.

        Returns:
            The context_store dict from the transition into that state.
        """
        states_service = self.get_workflow_executions_states(workflow_id, execution_id)
        states = states_service.list(per_page=20)
        target_state = next((s for s in states if s.name == state_name), None)
        assert target_state is not None, (
            f"State '{state_name}' not found in execution states. "
            f"Available: {[s.name for s in states]}"
        )
        executions_service = self.client.workflows.executions(workflow_id)
        transition = executions_service.get_transition_to(execution_id, target_state.id)
        return transition.workflow_context.context_store

    def upload_file(self, file_path: Path):
        return self.client.files.bulk_upload([file_path])

    def start_run(
        self,
        workflow_id: str,
        file_names: Optional[List[str]] = None,
        user_input: str = "Start",
    ) -> str:
        """Start a workflow run with optional run-start files and return its execution id.

        Does not wait for the run. Use it where the test must not wait for success: a run the
        API refuses, or a step that is expected to fail (and is retried, so the run stays in
        progress). For a run that succeeds use ``create_workflow_execution``.
        """
        user_input = f"{user_input}; REQUEST_UUID: {uuid.uuid4()};"
        response = self.client.workflows.run(
            workflow_id, user_input=user_input, file_names=file_names
        )
        return response["execution_id"]

    def get_state_outputs(self, workflow_id: str, execution_id: str) -> dict:
        """Return ``{state name: output}`` for every state of the run."""
        states_service = self.client.workflows.executions(workflow_id).states(
            execution_id
        )
        return {
            state.name: states_service.get_output(state.id).output
            for state in states_service.list(per_page=50)
        }

    def wait_for_state_status(
        self,
        workflow_id: str,
        execution_id: str,
        state_name: str,
        status: WorkflowExecutionStatusEnum,
        timeout: int = 180,
        poll_interval: int = 3,
    ) -> str:
        """Wait until a state reports ``status`` and return its output.

        Use it for failure paths: a failed step is retried by the workflow, so the run
        stays in progress for a long time while the state already reports the failure.
        """
        states_service = self.client.workflows.executions(workflow_id).states(
            execution_id
        )
        deadline = time.time() + timeout
        while time.time() < deadline:
            for state in states_service.list(per_page=50):
                if state.name == state_name and state.status == status:
                    return states_service.get_output(state.id).output
            sleep(poll_interval)
        raise TimeoutError(
            f"State '{state_name}' did not reach '{status.value}' within {timeout}s"
        )

    @staticmethod
    def _extract_tools_from_thoughts(thoughts_data):
        """
        Extract tool names from thoughts data recursively.

        Args:
            thoughts_data: List of thought objects with nested children

        Returns:
            list: List of triggered tool names in lowercase
        """
        triggered_tools = []

        def process_thought(_thought):
            # Check if this thought represents a tool call
            author_name = _thought.get("author_name", "")
            author_type = _thought.get("author_type", "")

            # Filter out 'Codemie Thoughts' and non-tool entries
            if (
                author_type == "Tool"
                and author_name
                and author_name != "Codemie Thoughts"
            ):
                triggered_tools.append(author_name.lower())

            # Recursively process children
            children = _thought.get("children", [])
            for child in children:
                process_thought(child)

        # Process all top-level thoughts
        if isinstance(thoughts_data, list):
            for thought in thoughts_data:
                process_thought(thought)

        return triggered_tools

    @staticmethod
    def wait_for_completion(
        service: WorkflowExecutionStateService | WorkflowExecutionService,
        _id: str,
        timeout: int = int(CredentialsManager.get_parameter("DEFAULT_TIMEOUT", "120")),
        pool_interval: int = 3,
    ) -> WorkflowExecutionState | WorkflowExecution:
        is_workflow_execution_state_state = isinstance(
            service, WorkflowExecutionStateService
        )
        start_time = time.time()
        while time.time() - start_time < timeout:
            executions_or_states = [
                row
                for row in service.list(per_page=20)
                if row.id == _id or row.execution_id == _id
            ]
            if len(executions_or_states) == 0:
                sleep(pool_interval)
                continue
            execution_or_state = executions_or_states[0]
            if execution_or_state.status == WorkflowExecutionStatusEnum.SUCCEEDED:
                return execution_or_state
            elif execution_or_state.status == WorkflowExecutionStatusEnum.FAILED:
                if is_workflow_execution_state_state:
                    raise ApiError(f"State execution failed: {service.get_output(_id)}")
                else:
                    raise ApiError(
                        f"Execution failed. Execution id: {execution_or_state.execution_id}"
                    )
            sleep(pool_interval)
        if is_workflow_execution_state_state:
            raise TimeoutError("State was not executed within the timeout period.")
        else:
            raise TimeoutError("Workflow was not executed within the timeout period.")

    def execute_workflow_without_prompt_modification(
        self,
        workflow,
        execution_name,
        user_input="",
        file_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        session_id: Optional[str] = None,
    ):
        """Use when user_input is structured JSON that must not be prefixed.

        Delegates to execute_workflow(modify_prompt=False), which embeds a
        _debug_id key inside the JSON payload for cache-busting.
        """
        return self.execute_workflow(
            workflow,
            execution_name,
            user_input=user_input,
            file_name=file_name,
            tags=tags,
            session_id=session_id,
            modify_prompt=False,
        )

    def create_workflow_execution_without_prompt_modification(
        self,
        workflow_id,
        user_input: str = "",
        conversation_id: Optional[str] = None,
        file_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ):
        """Use when user_input is structured JSON that must not be prefixed.

        Delegates to create_workflow_execution(modify_prompt=False), which embeds
        a _debug_id key inside the JSON payload for cache-busting.
        """
        return self.create_workflow_execution(
            workflow_id,
            user_input=user_input,
            conversation_id=conversation_id,
            file_name=file_name,
            tags=tags,
            modify_prompt=False,
        )
