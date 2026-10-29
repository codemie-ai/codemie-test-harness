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
from hamcrest import assert_that, close_to, equal_to

from codemie_sdk.models.assistant import AssistantUpdateRequest
from codemie_test_harness.tests import PROJECT
from codemie_test_harness.tests.test_data.assistant_partial_update_test_data import (
    build_assistant_with_optional_fields,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name


@pytest.mark.sanity
@pytest.mark.assistant
@pytest.mark.api
def test_partial_update_preserves_omitted_optional_fields(
    assistant_factory, assistant_utils, default_llm
):
    """TC-01: Partial PUT preserves omitted optional fields (temperature, top_p).

    Regression: a partial update that omits optional None-default fields
    must not wipe the stored values. Verifies that temperature and top_p — explicitly
    set at creation — survive a partial update whose body contains only the required
    fields (name, description, system_prompt, project, llm_model_type).

    Note: description and system_prompt are REQUIRED fields in the SDK's
    AssistantRequestBase and cannot be omitted from an update call; they are passed
    through unchanged so their preservation is also asserted. The truly-optional fields
    (temperature, top_p) have None defaults in both the SDK and the backend model and
    are fully omitted from the update payload — these are the primary regression
    targets.
    """
    test_data = build_assistant_with_optional_fields()

    # Step 1: Create assistant with temperature and top_p explicitly set.
    created = assistant_factory.create(
        assistant_name=test_data.name,
        temperature=test_data.temperature,
        top_p=test_data.top_p,
    )

    full_assistant = assistant_utils.get_assistant_by_id(created.id)
    original_description = full_assistant.description
    original_system_prompt = full_assistant.system_prompt
    new_name = get_random_name()

    # Step 2: Build a partial update request — required fields only,
    # temperature and top_p intentionally omitted (absent from model_fields_set).
    partial_update_request = AssistantUpdateRequest(
        name=new_name,
        description=original_description,
        system_prompt=original_system_prompt,
        project=PROJECT,
        llm_model_type=default_llm.base_name,
    )
    assistant_utils.update_assistant(created.id, partial_update_request)

    # Step 3: GET the assistant and assert omitted optional fields were preserved,
    # and confirm the update was actually applied by checking the name changed.
    updated = assistant_utils.get_assistant_by_id(created.id)
    assert_that(
        updated.name,
        equal_to(new_name),
        "name was not updated — the partial update did not execute",
    )
    assert_that(
        updated.description,
        equal_to(original_description),
        "description changed unexpectedly after partial update",
    )
    assert_that(
        updated.system_prompt or "",
        equal_to(original_system_prompt),
        "system_prompt changed unexpectedly after partial update",
    )
    assert_that(
        updated.temperature,
        close_to(test_data.temperature, 1e-6),
        "temperature was wiped by partial update regression",
    )
    assert_that(
        updated.top_p,
        close_to(test_data.top_p, 1e-6),
        "top_p was wiped by partial update regression",
    )
