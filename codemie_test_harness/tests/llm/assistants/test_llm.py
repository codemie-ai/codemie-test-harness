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

import uuid
from typing import Sequence

import pytest
from codemie_sdk.models.assistant import ToolKitDetails, ToolDetails
from hamcrest import assert_that, has_item, greater_than

from codemie_test_harness.tests.enums.model_types import ModelTypes
from codemie_test_harness.tests.enums.tools import Toolkit, FileManagementTool, Default
from codemie_test_harness.tests.test_data.file_test_data import file_test_data
from codemie_test_harness.tests.test_data.llm_test_data import (
    MODEL_RESPONSES,
    SKIP_TEMPERATURE_MODELS,
    SKIP_TOP_P_MODELS,
)
from codemie_test_harness.tests.utils.base_utils import (
    assert_tool_triggered,
)
from codemie_test_harness.tests.utils.constants import FILES_PATH
from codemie_test_harness.tests.utils.env_resolver import get_environment

SIMPLE_GREETING_PROMPT = "Just say one word: 'Hello'"


def get_model_names(llm_utils) -> Sequence[str]:
    """Get list of available model names."""
    return [row.base_name for row in llm_utils.list_llm_models()]


_TOP_P_TEST = "test_assistant_with_different_models_with_top_p_parameter"
_TEMPERATURE_TEST = "test_assistant_with_different_models_with_temperature_parameter"


def pytest_generate_tests(metafunc):
    if "model_type" in metafunc.fixturenames:
        test_data = []
        env = get_environment()
        test_name = metafunc.function.__name__
        for model_data in MODEL_RESPONSES:
            marks = [
                pytest.mark.skipif(
                    env not in model_data.environments,
                    reason=f"Skip on non {'/'.join(str(env) for env in model_data.environments[:-1])} envs",
                )
            ]
            if test_name == _TOP_P_TEST and model_data.model_type in SKIP_TOP_P_MODELS:
                marks.append(
                    pytest.mark.skip(reason="top_p not supported for this model")
                )
            if (
                test_name == _TEMPERATURE_TEST
                and model_data.model_type in SKIP_TEMPERATURE_MODELS
            ):
                marks.append(
                    pytest.mark.skip(reason="temperature not supported for this model")
                )
            test_data.append(pytest.param(model_data.model_type, marks=marks))

        metafunc.parametrize("model_type", test_data)


@pytest.mark.assistant
@pytest.mark.llm
@pytest.mark.api
@pytest.mark.production_check
def test_assistant_with_different_models(
    llm_utils,
    assistant_factory,
    assistant_utils,
    model_type,
    similarity_check,
    filesystem_integration,
):
    assert_that(
        get_model_names(llm_utils),
        has_item(model_type),
        f"{model_type} is missing in backend response",
    )

    tool = ToolKitDetails(
        toolkit=Toolkit.FILE_MANAGEMENT,
        tools=[
            ToolDetails(
                name=FileManagementTool.GENERATE_IMAGE, settings=filesystem_integration
            )
        ],
        settings=filesystem_integration,
    )

    _assistant = assistant_factory.create(model_type, toolkits=[tool])
    response = assistant_utils.ask_assistant(_assistant, SIMPLE_GREETING_PROMPT)

    if model_type == ModelTypes.DEEPSEEK_V4_PRO:
        response = "\n".join(response.split("\n")[-3:])
        response = response.replace("</think>\n\n", "")
    similarity_check.check_similarity(response, "Hello")


@pytest.mark.assistant
@pytest.mark.llm
@pytest.mark.top_p
@pytest.mark.api
@pytest.mark.production_check
def test_assistant_with_different_models_with_top_p_parameter(
    llm_utils, assistant_factory, assistant_utils, model_type, similarity_check
):
    assert_that(
        get_model_names(llm_utils),
        has_item(model_type),
        f"{model_type} is missing in backend response",
    )
    _assistant = assistant_factory.create(model_type, top_p=0.5)
    response = assistant_utils.ask_assistant(_assistant, SIMPLE_GREETING_PROMPT)

    if model_type == ModelTypes.DEEPSEEK_V4_PRO:
        response = "\n".join(response.split("\n")[-3:])
        response = response.replace("</think>\n\n", "")
    similarity_check.check_similarity(response, "Hello")


@pytest.mark.assistant
@pytest.mark.llm
@pytest.mark.temperature
@pytest.mark.api
@pytest.mark.production_check
def test_assistant_with_different_models_with_temperature_parameter(
    llm_utils, assistant_factory, assistant_utils, model_type, similarity_check
):
    assert_that(
        get_model_names(llm_utils),
        has_item(model_type),
        f"{model_type} is missing in backend response",
    )
    _assistant = assistant_factory.create(model_type, temperature=0.5)
    response = assistant_utils.ask_assistant(_assistant, SIMPLE_GREETING_PROMPT)

    if model_type == ModelTypes.DEEPSEEK_V4_PRO:
        response = "\n".join(response.split("\n")[-3:])
        response = response.replace("</think>\n\n", "")
    similarity_check.check_similarity(response, "Hello")


@pytest.mark.requires_capability("retrieval")
@pytest.mark.assistant
@pytest.mark.llm
@pytest.mark.api
@pytest.mark.production_check
def test_assistant_with_different_models_with_datasource_attached(
    llm_utils,
    assistant_factory,
    assistant_utils,
    model_type,
    similarity_check,
    datasource_utils,
    default_embedding_llm,
    kb_context,
    file_datasource,
):
    assert_that(
        get_model_names(llm_utils),
        has_item(model_type),
        f"{model_type} is missing in backend response",
    )

    _assistant = assistant_factory.create(
        model_type, context=[kb_context(file_datasource)]
    )

    prompt = "Show KB context. Return all information available in the context. Query may be 'Show content of the KB'"
    response, triggered_tools = assistant_utils.ask_assistant(
        _assistant, prompt, minimal_response=False
    )
    assert_tool_triggered(Default.SEARCH_KB, triggered_tools)

    similarity_check.check_similarity(response, file_test_data[2][1])


@pytest.mark.assistant
@pytest.mark.llm
@pytest.mark.sub_assistant
@pytest.mark.api
@pytest.mark.production_check
def test_assistant_with_different_models_with_sub_assistant(
    llm_utils, assistant_factory, assistant_utils, model_type, similarity_check
):
    assert_that(
        get_model_names(llm_utils),
        has_item(model_type),
        f"{model_type} is missing in backend response",
    )

    # Create sub-assistant with default model
    sub_assistant = assistant_factory.create(
        system_prompt=f"Assistant for answering {SIMPLE_GREETING_PROMPT}",
    )

    # Create parent assistant with the parametrized model that delegates to sub-assistant
    parent_assistant = assistant_factory.create(
        llm_model_type=model_type,
        system_prompt="You are a coordinator assistant.",
        assistant_ids=[sub_assistant.id],
    )

    # Test parent assistant that should delegate to sub-assistant
    response = assistant_utils.ask_assistant(
        parent_assistant,
        f"Invoke Sub-Assistant to {SIMPLE_GREETING_PROMPT}. Answer the only what Sub-Assistant returned",
    )

    if model_type == ModelTypes.DEEPSEEK_V4_PRO:
        response = "\n".join(response.split("\n")[-3:])
        response = response.replace("</think>\n\n", "")
    similarity_check.check_similarity(response, "Hello")


@pytest.mark.assistant
@pytest.mark.llm
@pytest.mark.api
@pytest.mark.production_check
def test_chatting_with_different_models_in_stream_mode(
    llm_utils,
    assistant_factory,
    assistant_utils,
    model_type,
    similarity_check,
    filesystem_integration,
):
    assert_that(
        get_model_names(llm_utils),
        has_item(model_type),
        f"{model_type} is missing in backend response",
    )

    tool = ToolKitDetails(
        toolkit=Toolkit.FILE_MANAGEMENT,
        tools=[
            ToolDetails(
                name=FileManagementTool.GENERATE_IMAGE, settings=filesystem_integration
            )
        ],
        settings=filesystem_integration,
    )

    _assistant = assistant_factory.create(model_type, toolkits=[tool])

    is_o_model = model_type in [
        ModelTypes.O1,
        ModelTypes.O3_MINI,
        ModelTypes.O3_2025_04_16,
        ModelTypes.O4_MINI_2025_04_16,
    ]

    if not is_o_model:
        streaming_prompt = (
            "Write a short paragraph (20 sentences) about the importance of testing. "
            "Make sure to mention unit tests, integration tests, and end-to-end tests."
        )

        response_metadata = assistant_utils.ask_assistant(
            _assistant, streaming_prompt, stream=True, return_stream_metadata=True
        )

        chunk_count = response_metadata["chunk_count"]
        thought_count = response_metadata["thought_count"]

        assert_that(
            chunk_count,
            greater_than(5),
            f"Expected true streaming with many chunks, got only {chunk_count} (thoughts: {thought_count})",
        )

        assert_that(
            thought_count,
            greater_than(3),
            f"Expected multiple incremental thought chunks, got only {thought_count} (total chunks: {chunk_count})",
        )

    simple_response = assistant_utils.ask_assistant(
        _assistant, SIMPLE_GREETING_PROMPT, stream=True
    )

    if model_type == ModelTypes.DEEPSEEK_V4_PRO:
        simple_response = "\n".join(simple_response.split("\n")[-3:])
    similarity_check.check_similarity(simple_response, "Hello")


@pytest.mark.assistant
@pytest.mark.llm
@pytest.mark.api
@pytest.mark.production_check
def test_assistant_with_different_models_with_file_attached(
    llm_utils,
    assistant_factory,
    assistant_utils,
    model_type,
    similarity_check,
    datasource_utils,
    default_embedding_llm,
):
    assert_that(
        get_model_names(llm_utils),
        has_item(model_type),
        f"{model_type} is missing in backend response",
    )

    _assistant = assistant_factory.create(model_type)

    uploaded_file = assistant_utils.upload_file_to_chat(
        FILES_PATH / file_test_data[10][0]
    )
    file_url = uploaded_file.get("file_url")

    conversation_id = str(uuid.uuid4())

    prompt = (
        f"Run {file_test_data[10][2]} tool with the following input:"
        f"{{'query': 'Extract the raw text content from the {file_test_data[10][0]} file.'}}"
    )

    response, triggered_tools = assistant_utils.ask_assistant(
        _assistant,
        prompt,
        file_urls=[file_url],
        conversation_id=conversation_id,
        minimal_response=False,
    )
    assert_tool_triggered(file_test_data[2][2], triggered_tools)
    similarity_check.check_similarity(response, file_test_data[10][1])
