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

"""API tests for how a user model override shapes the models a member sees and may use.

An override is the member's whole model set in the project, whether it adds a model the
project does not allow or leaves out one the project allows. It decides the model list of the
project, the default model of that list and the model a new assistant may use.
"""

import pytest
from hamcrest import assert_that, equal_to, has_item, has_items, not_
from requests import HTTPError

from codemie_test_harness.tests.test_data.user_model_override_test_data import (
    DEFAULT_TIERS,
    NOT_IN_OVERRIDE_DETAILS,
    not_allowed_message,
)
from codemie_test_harness.tests.utils.assistant_utils import AssistantUtils

BOTH_FEATURES = ("features:userModelOverride", "features:projectModelOverride")


# @case user-level-model-override_TC_004
@pytest.mark.requires_capability(*BOTH_FEATURES)
@pytest.mark.project
@pytest.mark.api
def test_override_replaces_project_model_set_in_model_list(
    override_utils, override_project, platform_user, override_models
):
    project_model, override_model, _ = override_models
    override_utils.restrict_project_models(
        override_project, [project_model], project_model
    )
    before = override_utils.base_names_listed(platform_user.client, override_project)

    override_utils.set_override(
        override_project, platform_user.user_id, [override_model]
    )
    after = override_utils.base_names_listed(platform_user.client, override_project)

    assert_that(before, has_item(project_model), "the project model is listed")
    assert_that(before, not_(has_item(override_model)), "the project set is the limit")
    assert_that(
        after,
        has_item(override_model),
        "the override model outside the project is listed",
    )
    assert_that(
        after,
        not_(has_item(project_model)),
        "the project model the override leaves out is gone",
    )


# @case user-level-model-override_TC_005
@pytest.mark.requires_capability("features:userModelOverride")
@pytest.mark.project
@pytest.mark.api
def test_narrowed_member_loses_model_other_members_keep(
    override_utils,
    override_project,
    platform_user,
    second_platform_user,
    override_models,
):
    kept, left_out, _ = override_models
    override_utils.restrict_project_models(override_project, [left_out, kept], kept)

    override_utils.set_override(override_project, platform_user.user_id, [kept])

    narrowed = override_utils.base_names_listed(platform_user.client, override_project)
    other = override_utils.base_names_listed(
        second_platform_user.client, override_project
    )
    assert_that(narrowed, has_item(kept))
    assert_that(
        narrowed, not_(has_item(left_out)), "the narrowed member loses the model"
    )
    assert_that(other, has_items(kept, left_out), "the other member keeps both models")


# @case user-level-model-override_TC_006
@pytest.mark.requires_capability(*BOTH_FEATURES)
@pytest.mark.project
@pytest.mark.api
def test_assistant_with_override_model_outside_project_set_is_created(
    override_utils,
    override_project,
    platform_user,
    override_models,
    member_assistants,
):
    project_model, override_model, _ = override_models
    override_utils.restrict_project_models(
        override_project, [project_model], project_model
    )
    override_utils.set_override(
        override_project, platform_user.user_id, [override_model]
    )

    created = member_assistants(
        platform_user.client,
        llm_model_type=override_model,
        project_name=override_project,
    )

    stored = AssistantUtils(platform_user.client).get_assistant_by_id(created.id)
    assert_that(stored.llm_model_type, equal_to(override_model))
    assert_that(stored.project, equal_to(override_project))


# @case user-level-model-override_TC_006
@pytest.mark.requires_capability("features:userModelOverride")
@pytest.mark.project
@pytest.mark.api
def test_assistant_with_model_left_out_of_override_is_rejected(
    override_utils, override_project, platform_user, override_models
):
    kept, left_out, _ = override_models
    override_utils.restrict_project_models(override_project, [left_out, kept], kept)
    override_utils.set_override(override_project, platform_user.user_id, [kept])

    with pytest.raises(HTTPError) as exc_info:
        AssistantUtils(platform_user.client).send_create_assistant_request(
            llm_model_type=left_out, project_name=override_project
        )

    response = exc_info.value.response
    assert_that(response.status_code, equal_to(400), response.text)
    error = response.json()["error"]
    assert_that(
        error["message"], equal_to(not_allowed_message(left_out, override_project))
    )
    assert_that(error["details"], equal_to(NOT_IN_OVERRIDE_DETAILS))


# @case user-level-model-override_TC_007
@pytest.mark.xdist_group(name="model_status")
@pytest.mark.requires_capability(*BOTH_FEATURES)
@pytest.mark.project
@pytest.mark.api
@pytest.mark.parametrize("tier", DEFAULT_TIERS.values(), ids=DEFAULT_TIERS.keys())
def test_model_list_default_follows_override_then_project_then_platform_default(
    override_utils,
    override_project,
    platform_user,
    override_models,
    platform_default,
    tier,
):
    named = {
        "x": override_models[0],
        "y": override_models[1],
        "platform": platform_default,
    }
    override_utils.set_project_default(
        override_project, named.get(tier.project_default)
    )
    override_utils.set_override(
        override_project,
        platform_user.user_id,
        list(named.values()),
        named.get(tier.override_default),
    )

    flagged = override_utils.default_base_names_listed(
        platform_user.client, override_project
    )

    assert_that(
        flagged,
        equal_to([named[tier.expected]]),
        "exactly one model must be flagged as default, the one the tier names",
    )
