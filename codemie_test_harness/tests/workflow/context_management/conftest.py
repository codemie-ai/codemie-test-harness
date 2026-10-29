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

"""Pytest fixtures for context management tests."""

import pytest
from codemie_sdk.models.workflow import WorkflowMode

from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.yaml_utils import (
    AssistantModel,
    StateModel,
    WorkflowYamlModel,
    prepare_yaml_content,
)
from codemie_test_harness.tests.workflow.context_management import (
    SYSTEM_PROMPTS,
    TEST_DATA,
)


@pytest.fixture(scope="module")
def data_extractor(default_llm):
    """Context Management fixture to create data extraction assistants."""

    def _model(assistant_id: str) -> AssistantModel:
        return AssistantModel(
            id=assistant_id,
            model=default_llm.base_name,
            system_prompt=SYSTEM_PROMPTS["data_extractor"],
        )

    return _model


@pytest.fixture(scope="module")
def data_processor(default_llm):
    """Context Management fixture to create data processing assistants."""

    def _model(assistant_id: str) -> AssistantModel:
        return AssistantModel(
            id=assistant_id,
            model=default_llm.base_name,
            system_prompt=SYSTEM_PROMPTS["data_processor"],
        )

    return _model


@pytest.fixture(scope="module")
def information_provider(default_llm):
    """Context Management fixture to create information provider assistants."""

    def _model(assistant_id: str) -> AssistantModel:
        return AssistantModel(
            id=assistant_id,
            model=default_llm.base_name,
            system_prompt=SYSTEM_PROMPTS["information_provider"],
        )

    return _model


@pytest.fixture(scope="module")
def information_validator(default_llm):
    """Context Management fixture to create information validator assistants."""

    def _model(assistant_id: str) -> AssistantModel:
        return AssistantModel(
            id=assistant_id,
            model=default_llm.base_name,
            system_prompt=SYSTEM_PROMPTS["information_validator"],
        )

    return _model


@pytest.fixture
def reset_keys_workflow(data_extractor, data_processor, workflow_utils):
    """Create the reset_keys_in_context_store test workflow and delete it after the test.

    Yields the created workflow object. Teardown calls delete_workflow even if the
    test body raises an assertion error, satisfying the project no-inline-cleanup rule.
    """
    _reset_state_status = "reset done"
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        assistants=[
            data_extractor("data_gen"),
            data_processor("verifier"),
        ],
        states=[
            StateModel(
                id="seed_context",
                assistant_id="data_gen",
                task=(
                    f"Output JSON with exactly two fields: "
                    f'{{"user_id": "{TEST_DATA["user_id"]}", "secret_code": "{TEST_DATA["secret_code"]}"}}'
                ),
                output_schema='{"user_id": "string", "secret_code": "string"}',
                next={
                    "state_id": "reset_state",
                    "reset_keys_in_context_store": ["user_id"],
                    "include_in_llm_history": False,
                },
            ),
            StateModel(
                id="reset_state",
                assistant_id="data_gen",
                task=f'Output JSON: {{"status": "{_reset_state_status}"}}',
                output_schema='{"status": "string"}',
                next={
                    "state_id": "verify_context",
                    "include_in_llm_history": False,
                },
            ),
            StateModel(
                id="verify_context",
                assistant_id="verifier",
                task="Confirm the workflow reached this state.",
                next={"state_id": "end"},
            ),
        ],
    )

    yaml_content = prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))
    created_workflow = workflow_utils.create_workflow(
        workflow_name=workflow_name,
        workflow_type=WorkflowMode.SEQUENTIAL,
        workflow_yaml=yaml_content,
    )

    yield created_workflow

    workflow_utils.delete_workflow(created_workflow)


@pytest.fixture(scope="module")
def propagated_headers_workflow(data_extractor, workflow_utils):
    """Minimal single-state SEQUENTIAL workflow for header propagation tests.

    Created once per module; each test function creates its own execution on
    this workflow and identifies it via the returned execution_id so that
    parallel-safe state inspection is possible.
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        assistants=[data_extractor("data_gen")],
        states=[
            StateModel(
                id="verify_state",
                assistant_id="data_gen",
                task='Reply with: {"status": "done"}',
                output_schema='{"status": "string"}',
                next={"state_id": "end"},
            ),
        ],
    )

    yaml_content = prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))
    created_workflow = workflow_utils.create_workflow(
        workflow_name=workflow_name,
        workflow_type=WorkflowMode.SEQUENTIAL,
        workflow_yaml=yaml_content,
    )

    yield created_workflow

    workflow_utils.delete_workflow(created_workflow)
