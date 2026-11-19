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

"""Effort parameter in the assistant edit form: levels, temperature rules, token warning."""

import pytest
from hamcrest import assert_that, equal_to, none, not_none

from codemie_test_harness.tests.enums.model_types import ModelTypes
from codemie_test_harness.tests.test_data.assistant_effort_test_data import (
    effort_levels,
    model_by_label,
)
from codemie_test_harness.tests.ui.pageobject.assistants.assistants_page import (
    AssistantsPage,
)
from codemie_test_harness.tests.ui.test_data.assistant_effort_ui_test_data import (
    CLEARING_EFFORT,
    EFFORT_MODEL_LABEL,
    EFFORT_WITH_WARNING,
    EFFORT_WITHOUT_WARNING,
    NON_EFFORT_MODEL_LABEL,
    OVER_CAP_TEMPERATURE,
    SAVED_TEMPERATURE,
    SAVED_TEMPERATURE_TEXT,
)
from codemie_test_harness.tests.ui.test_data.assistant_test_data import (
    AssistantPopUpMessages,
    AssistantValidationErrors,
)


def _catalog_model(client, label):
    model = model_by_label(client.llms.list(), label)
    assert_that(model, not_none(), f"Model '{label}' is not in the stand catalog")
    return model


@pytest.fixture(scope="module")
def effort_model(client):
    model = _catalog_model(client, EFFORT_MODEL_LABEL)
    assert_that(
        effort_levels(model),
        not_none(),
        f"Model '{EFFORT_MODEL_LABEL}' declares no effort levels in the catalog",
    )
    return model


@pytest.fixture(scope="module")
def non_effort_model(client):
    model = _catalog_model(client, NON_EFFORT_MODEL_LABEL)
    assert_that(
        effort_levels(model),
        none(),
        f"Model '{NON_EFFORT_MODEL_LABEL}' declares effort levels in the catalog",
    )
    return model


def _open_edit_page(page, assistant):
    assistants_page = AssistantsPage(page)
    assistants_page.navigate_to()
    assistants_page.search_assistants(assistant.name)
    edit_page = assistants_page.click_assistant_edit(assistant.name)
    edit_page.should_have_pinned_title(assistant.name)
    return assistants_page, edit_page


# @case support-effort-parameter-newer-models_TC_004
@pytest.mark.assistant
@pytest.mark.ui
def test_effort_select_lists_model_levels_and_hides_temperature_and_top_p(
    page, assistant_factory, effort_model
):
    created = assistant_factory.create(llm_model_type=effort_model.base_name)

    _, edit_page = _open_edit_page(page, created)

    edit_page.should_have_effort_levels(effort_levels(effort_model))
    edit_page.should_have_temperature_and_top_p_hidden()


# @case support-effort-parameter-newer-models_TC_004
@pytest.mark.assistant
@pytest.mark.ui
def test_non_effort_model_shows_temperature_and_no_effort_select(
    page, assistant_factory, non_effort_model
):
    created = assistant_factory.create(llm_model_type=non_effort_model.base_name)

    _, edit_page = _open_edit_page(page, created)

    edit_page.should_have_top_p_and_temperature()
    edit_page.should_not_have_effort_select()


# @case support-effort-parameter-newer-models_TC_004
@pytest.mark.assistant
@pytest.mark.ui
def test_effort_model_with_saved_temperature_keeps_it_until_effort_is_chosen(
    page, assistant_factory, effort_model
):
    created = assistant_factory.create(
        llm_model_type=effort_model.base_name, temperature=SAVED_TEMPERATURE
    )

    _, edit_page = _open_edit_page(page, created)
    edit_page.should_have_temperature_value(SAVED_TEMPERATURE_TEXT)

    edit_page.select_effort(CLEARING_EFFORT)
    edit_page.should_have_temperature_and_top_p_hidden()


# @case support-effort-parameter-newer-models_TC_006
@pytest.mark.assistant
@pytest.mark.ui
def test_max_effort_shows_token_warning_and_is_saved_and_shown_in_details(
    page, assistant_factory, assistant_utils, effort_model
):
    created = assistant_factory.create(llm_model_type=effort_model.base_name)

    assistants_page, edit_page = _open_edit_page(page, created)

    edit_page.select_effort(EFFORT_WITHOUT_WARNING)
    edit_page.should_not_show_effort_token_usage_warning(EFFORT_WITHOUT_WARNING)

    edit_page.select_effort(EFFORT_WITH_WARNING)
    edit_page.should_show_effort_token_usage_warning()

    edit_page.click_save()
    assistants_page.should_see_updating_popup(
        AssistantPopUpMessages.ASSISTANT_UPDATED_SUCCESS.value
    )
    assistants_page.should_see_assistant_with_name(created.name)

    view_page = assistants_page.click_assistant_view(created.name)
    view_page.should_see_config_effort(EFFORT_WITH_WARNING)

    assert_that(
        assistant_utils.get_assistant_by_id(created.id).effort,
        equal_to(EFFORT_WITH_WARNING),
        "The API did not echo the effort saved through the UI",
    )


# @case support-effort-parameter-newer-models_TC_008
@pytest.mark.assistant
@pytest.mark.ui
def test_switching_max_effort_assistant_to_non_effort_model_clears_effort_and_saves(
    page, assistant_factory, assistant_utils, effort_model, non_effort_model
):
    created = assistant_factory.create(
        llm_model_type=effort_model.base_name, effort=EFFORT_WITH_WARNING
    )

    assistants_page, edit_page = _open_edit_page(page, created)
    edit_page.should_have_effort_select_visible()

    edit_page.select_llm_model(non_effort_model.label)
    edit_page.should_not_have_effort_select()
    edit_page.should_not_show_effort_unsupported_alert(non_effort_model.label)

    edit_page.click_save()
    assistants_page.should_see_updating_popup(
        AssistantPopUpMessages.ASSISTANT_UPDATED_SUCCESS.value
    )

    saved = assistant_utils.get_assistant_by_id(created.id)
    assert_that(
        saved.llm_model_type,
        equal_to(non_effort_model.base_name),
        "The model switch was not saved",
    )
    assert_that(saved.effort, none(), "The effort was not cleared by the model switch")


# @case support-effort-parameter-newer-models_TC_015
@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.parametrize(
    "model",
    [ModelTypes.CLAUDE_4_6_SONNET, ModelTypes.CLAUDE_SONNET_4_6_VERTEX],
    ids=["bedrock_claude_sonnet_4_6", "vertex_claude_sonnet_4_6"],
)
def test_claude_temperature_above_one_is_blocked_for_assistant_with_saved_temperature(
    page, assistant_factory, model
):
    created = assistant_factory.create(
        llm_model_type=model.value, temperature=SAVED_TEMPERATURE
    )

    _, edit_page = _open_edit_page(page, created)
    edit_page.should_have_temperature_value(SAVED_TEMPERATURE_TEXT)

    edit_page.fill_temperature_and_leave_field(OVER_CAP_TEMPERATURE)
    edit_page.should_have_temperature_error_textarea(
        AssistantValidationErrors.TEMPERATURE_CLAUDE_NOT_VALID.value
    )

    edit_page.click_save()
    edit_page.should_have_temperature_error_textarea(
        AssistantValidationErrors.TEMPERATURE_CLAUDE_NOT_VALID.value
    )
    edit_page.should_not_see_success_toast()
