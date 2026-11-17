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

"""API tests for how assistants behave when the status of their model changes.

A Deprecated model is refused for new work but keeps serving existing work; a
Disabled model is replaced by a fallback when an assistant is read or run: the
project default model, or the global default when the project has none. A new
project is created with a default model of its own and no model restriction, so
each test sets the project default or clears it before the model is disabled.
"""

import pytest
from hamcrest import assert_that, equal_to, greater_than, has_length
from requests import HTTPError

from codemie_sdk.models.assistant import AssistantUpdateRequest
from codemie_sdk.models.llm import ModelStatus

from codemie_test_harness.tests.test_data.llm_model_status_test_data import (
    DEPRECATED_REASON,
    DISABLED_FALLBACK_REASON,
    NOT_SELECTABLE_MESSAGE,
    not_selectable_details,
)
from codemie_test_harness.tests.utils.base_utils import poll_until
from codemie_test_harness.tests.utils.llm_model_status_utils import (
    CATALOG_PROPAGATION_TIMEOUT,
)

CHAT_PROMPT = "Reply with one short sentence."


@pytest.fixture
def isolated_project_name(project):
    """A new project: no project default model and no model restriction."""
    return project().name


# @case platform-model-management_TC_006
@pytest.mark.not_for_parallel_run
@pytest.mark.llm
@pytest.mark.api
def test_deprecated_model_is_rejected_for_new_assistant(
    llm_model_status_utils, assistant_utils, status_test_model, isolated_project_name
):
    base_name = status_test_model.base_name
    llm_model_status_utils.apply_status(base_name, ModelStatus.DEPRECATED)

    with pytest.raises(HTTPError) as exc_info:
        assistant_utils.send_create_assistant_request(
            llm_model_type=base_name, project_name=isolated_project_name
        )

    response = exc_info.value.response
    assert_that(response.status_code, equal_to(400), response.text)
    error = response.json()["error"]
    assert_that(error["message"], equal_to(NOT_SELECTABLE_MESSAGE))
    assert_that(
        error["details"],
        equal_to(not_selectable_details(base_name, DEPRECATED_REASON)),
        "the refusal must name the model and say that it is deprecated",
    )


# @case platform-model-management_TC_007
@pytest.mark.not_for_parallel_run
@pytest.mark.llm
@pytest.mark.api
def test_assistant_keeps_working_after_its_model_is_deprecated(
    llm_model_status_utils,
    assistant_utils,
    status_test_model,
    isolated_project_name,
    assistant_factory,
):
    base_name = status_test_model.base_name
    created = assistant_factory.create(
        llm_model_type=base_name, project_name=isolated_project_name
    )
    stored = assistant_utils.get_assistant_by_id(created.id)
    llm_model_status_utils.apply_status(base_name, ModelStatus.DEPRECATED)

    answer = assistant_utils.ask_assistant(created, CHAT_PROMPT)

    assert_that(
        answer, has_length(greater_than(0)), "chat on a deprecated model must answer"
    )
    update_response = assistant_utils.update_assistant(
        created.id,
        AssistantUpdateRequest(
            name=stored.name,
            slug=stored.slug,
            description="Integration test assistant [updated]",
            system_prompt="Act as a helpful assistant",
            project=isolated_project_name,
            llm_model_type=base_name,
        ),
    )
    assert_that(
        update_response.message,
        equal_to("Specified assistant updated"),
        "an update that keeps the deprecated model must be accepted",
    )
    assert_that(
        assistant_utils.get_assistant_by_id(created.id).llm_model_type,
        equal_to(base_name),
        "the assistant must stay on its deprecated model",
    )


# @case platform-model-management_TC_008
@pytest.mark.not_for_parallel_run
@pytest.mark.llm
@pytest.mark.api
def test_assistant_on_disabled_model_runs_on_the_project_default_model(
    llm_model_status_utils,
    assistant_utils,
    project_utils,
    status_test_models,
    isolated_project_name,
    assistant_factory,
):
    disabled_model, project_default = status_test_models
    project_utils.set_default_model(isolated_project_name, project_default.base_name)
    created = assistant_factory.create(
        llm_model_type=disabled_model.base_name, project_name=isolated_project_name
    )
    llm_model_status_utils.apply_status(disabled_model.base_name, ModelStatus.DISABLED)

    detail = poll_until(
        lambda: assistant_utils.get_assistant_by_id(created.id),
        lambda assistant: assistant.llm_model_type != disabled_model.base_name,
        timeout=CATALOG_PROPAGATION_TIMEOUT,
    )

    assert_that(
        detail.llm_model_type,
        equal_to(project_default.base_name),
        "the assistant detail must show the project default instead of the disabled model",
    )
    assert_that(detail.effective_llm_model_reason, equal_to(DISABLED_FALLBACK_REASON))
    answer = assistant_utils.ask_assistant(created, CHAT_PROMPT)
    assert_that(
        answer,
        has_length(greater_than(0)),
        "chat on a disabled model must answer on the project default",
    )


# @case platform-model-management_TC_008
@pytest.mark.not_for_parallel_run
@pytest.mark.llm
@pytest.mark.api
def test_assistant_on_disabled_model_runs_on_the_global_default_without_a_project_default(
    llm_model_status_utils,
    assistant_utils,
    project_utils,
    status_test_model,
    isolated_project_name,
    assistant_factory,
):
    base_name = status_test_model.base_name
    project_utils.reset_model_settings(isolated_project_name)
    created = assistant_factory.create(
        llm_model_type=base_name, project_name=isolated_project_name
    )
    global_default = llm_model_status_utils.get_default().effective_base_name
    llm_model_status_utils.apply_status(base_name, ModelStatus.DISABLED)

    detail = poll_until(
        lambda: assistant_utils.get_assistant_by_id(created.id),
        lambda assistant: assistant.llm_model_type != base_name,
        timeout=CATALOG_PROPAGATION_TIMEOUT,
    )

    assert_that(
        detail.llm_model_type,
        equal_to(global_default),
        "the assistant detail must show the global default instead of the disabled model",
    )
    assert_that(detail.effective_llm_model_reason, equal_to(DISABLED_FALLBACK_REASON))
    answer = assistant_utils.ask_assistant(created, CHAT_PROMPT)
    assert_that(
        answer,
        has_length(greater_than(0)),
        "chat on a disabled model must answer on the global default",
    )
