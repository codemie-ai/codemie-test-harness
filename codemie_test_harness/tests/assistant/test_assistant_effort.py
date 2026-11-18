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

import pytest
from hamcrest import assert_that, empty, equal_to, greater_than, has_length, none

from codemie_test_harness.tests.test_data.assistant_effort_test_data import (
    EFFORT_UPDATE_TARGETS,
    EXPECTED_GREETING,
    GREETING_PROMPT,
    chat_effort_for,
    claude_effort_models,
    effort_catalog_violations,
    effort_levels,
    models_accepting_temperature,
    models_missing_temperature_flag,
    models_with_effort,
    models_without_effort,
)


@pytest.fixture(scope="module")
def llm_models(client):
    return client.llms.list()


@pytest.fixture(scope="module")
def claude_models(llm_models):
    """Enabled Claude models that declare effort levels, read from the catalog."""
    models = claude_effort_models(llm_models)
    assert_that(
        models,
        has_length(greater_than(0)),
        "Expected at least one enabled Claude model with effort levels in the catalog",
    )
    return models


@pytest.fixture
def effort_chat_target(claude_models, model_slot, effort_role):
    """The (model, effort) pair one chat test sends, at most two models in all."""
    if model_slot >= len(claude_models):
        pytest.skip(f"Catalog has no Claude effort model in slot {model_slot}")
    model = claude_models[model_slot]
    effort = chat_effort_for(effort_levels(model), effort_role)
    if effort is None:
        pytest.skip(f"{model.base_name} declares every level, none is {effort_role}")
    return model, effort


# @case support-effort-parameter-newer-models_TC_001
@pytest.mark.assistant
@pytest.mark.llm
@pytest.mark.api
def test_llm_catalog_effort_levels_are_ascending_known_levels(llm_models):
    assert_that(
        effort_catalog_violations(llm_models),
        empty(),
        "Models whose features.effort is not an ascending subset of the known levels",
    )
    assert_that(
        models_with_effort(llm_models),
        has_length(greater_than(0)),
        "Expected at least one model with features.effort in the catalog",
    )
    assert_that(
        models_without_effort(llm_models),
        has_length(greater_than(0)),
        "Expected at least one model with features.effort null in the catalog",
    )


# @case support-effort-parameter-newer-models_TC_001
@pytest.mark.assistant
@pytest.mark.llm
@pytest.mark.api
def test_llm_catalog_exposes_temperature_support_flag(llm_models):
    assert_that(
        models_missing_temperature_flag(llm_models),
        empty(),
        "Models without a boolean features.temperature",
    )
    # The stand catalog holds no model with features.temperature false, so the
    # "false for models that reject temperature" step stays uncovered (case partial).
    assert_that(
        models_accepting_temperature(llm_models),
        has_length(greater_than(0)),
        "Expected at least one model with features.temperature true in the catalog",
    )


# @case support-effort-parameter-newer-models_TC_002
@pytest.mark.assistant
@pytest.mark.api
@pytest.mark.parametrize("effort", ["low", "medium", "high"])
def test_assistant_effort_is_echoed_on_create_and_update_and_cleared_with_null(
    assistant_factory, assistant_utils, claude_models, effort
):
    model = claude_models[0]
    new_effort = EFFORT_UPDATE_TARGETS[effort]

    created = assistant_factory.create(llm_model_type=model.base_name, effort=effort)
    assert_that(
        assistant_utils.get_assistant_by_id(created.id).effort,
        equal_to(effort),
        f"effort {effort} was not echoed after create on {model.base_name}",
    )

    assistant_utils.update_assistant_effort(created.id, new_effort)
    assert_that(
        assistant_utils.get_assistant_by_id(created.id).effort,
        equal_to(new_effort),
        f"effort was not updated from {effort} to {new_effort}",
    )

    assistant_utils.update_assistant_effort(created.id, None)
    assert_that(
        assistant_utils.get_assistant_by_id(created.id).effort,
        none(),
        "effort was not cleared by an update with null",
    )


# @case support-effort-parameter-newer-models_TC_003
@pytest.mark.assistant
@pytest.mark.llm
@pytest.mark.api
@pytest.mark.parametrize("model_slot", [0, 1], ids=["first_model", "second_model"])
@pytest.mark.parametrize(
    "effort_role", ["lowest", "highest", "above_ceiling"], ids=lambda role: role
)
def test_chat_with_effort_assistant_answers_without_provider_parameter_error(
    assistant_factory, assistant_utils, similarity_check, effort_chat_target
):
    model, effort = effort_chat_target

    created = assistant_factory.create(llm_model_type=model.base_name, effort=effort)
    assert_that(
        assistant_utils.get_assistant_by_id(created.id).effort,
        equal_to(effort),
        f"effort {effort} was not echoed after create on {model.base_name}",
    )

    response = assistant_utils.ask_assistant(created, GREETING_PROMPT)
    similarity_check.check_similarity(response, EXPECTED_GREETING)
