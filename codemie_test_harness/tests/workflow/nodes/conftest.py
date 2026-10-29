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

"""Pytest fixtures for workflow nodes tests."""

import logging

import pytest

from codemie_test_harness.tests.utils.yaml_utils import AssistantModel

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def item_processor(default_llm):
    """Fixture to create assistants that process individual items."""

    def _model(assistant_id: str) -> AssistantModel:
        return AssistantModel(
            id=assistant_id,
            model=default_llm.base_name,
            system_prompt=(
                "You are a helpful assistant that processes items. "
                "Process the input data and return results in the requested format."
            ),
        )

    return _model


@pytest.fixture(scope="module")
def result_aggregator(default_llm):
    """Fixture to create assistants that aggregate results from iterations."""

    def _model(assistant_id: str) -> AssistantModel:
        return AssistantModel(
            id=assistant_id,
            model=default_llm.base_name,
            system_prompt=(
                "You are a helpful assistant that aggregates and summarizes results. "
                "Analyze the conversation history and context to provide comprehensive summaries."
            ),
        )

    return _model


@pytest.fixture(scope="module")
def data_validator(default_llm):
    """Fixture to create assistants that validate data."""

    def _model(assistant_id: str) -> AssistantModel:
        return AssistantModel(
            id=assistant_id,
            model=default_llm.base_name,
            system_prompt=(
                "You are a helpful assistant that validates data. "
                "Check if the provided information matches expectations and confirm or deny."
            ),
        )

    return _model


@pytest.fixture(scope="module")
def data_generator(default_llm):
    """Fixture to create assistants that generate structured data."""

    def _model(assistant_id: str) -> AssistantModel:
        return AssistantModel(
            id=assistant_id,
            model=default_llm.base_name,
            system_prompt=(
                "You are a helpful assistant that generates structured data. "
                "Output exactly dictionary requested in JSON format without any additional text."
                "Do not use any additional formatting like markdown!"
            ),
        )

    return _model


@pytest.fixture(scope="module")
def result_handler(default_llm):
    """Fixture to create assistants that handle conditional results."""

    def _model(assistant_id: str) -> AssistantModel:
        return AssistantModel(
            id=assistant_id,
            model=default_llm.base_name,
            system_prompt="You are a helpful assistant that handles conditional results.",
        )

    return _model


@pytest.fixture
def workflow_cleanup(workflow_utils):
    """Yield a list for registering created Workflow objects; deletes all on
    teardown. Node tests create workflows directly via
    workflow_utils.create_workflow() with no factory fixture of their own,
    so this is the only thing that tears them down.
    """
    created = []
    yield created
    for wf in created:
        try:
            workflow_utils.delete_workflow(wf)
        except Exception as e:
            logger.warning(f"Failed to delete workflow {wf.id}: {e}")
