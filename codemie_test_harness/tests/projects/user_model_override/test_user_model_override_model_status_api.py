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

"""API tests for user model overrides that meet a model whose platform status changes.

A model the platform disabled is skipped when the default of a model list is chosen. A
deprecated model cannot be added to an override, but an override that already lists it keeps
it. The status is platform-wide: the tests use the dedicated "(Autotest)" models, put the
status back on teardown and run one after another in the `model_status` group.
"""

import pytest
from hamcrest import assert_that, contains_inanyorder, equal_to, has_item, not_
from requests import HTTPError

from codemie_sdk.models.llm import ModelStatus

from codemie_test_harness.tests.test_data.user_model_override_test_data import (
    BOTH_FEATURES,
    BATCH_FAILED_MESSAGE,
    OVERRIDE_NOT_FOUND_MESSAGE,
    deprecated_not_added_message,
)


# @case user-level-model-override_TC_008
@pytest.mark.xdist_group(name="model_status")
@pytest.mark.requires_capability(*BOTH_FEATURES)
@pytest.mark.project
@pytest.mark.api
def test_platform_disabled_override_default_falls_to_project_default(
    llm_model_status_utils,
    override_utils,
    override_project,
    platform_user,
    status_test_models,
    platform_default,
):
    override_default, project_default = (m.base_name for m in status_test_models)
    override_utils.set_project_default(override_project, project_default)
    override_utils.set_override(
        override_project,
        platform_user.user_id,
        [override_default, project_default, platform_default],
        override_default,
    )
    before = override_utils.default_base_names_listed(
        platform_user.client, override_project
    )

    llm_model_status_utils.apply_status(
        override_default, ModelStatus.DISABLED, platform_user.client
    )
    after = override_utils.default_base_names_listed(
        platform_user.client, override_project
    )

    assert_that(before, equal_to([override_default]), "the override default leads")
    assert_that(
        after,
        equal_to([project_default]),
        "a disabled override default must give way to the project default, not raise",
    )


# @case user-level-model-override_TC_011
@pytest.mark.xdist_group(name="model_status")
@pytest.mark.requires_capability("features:userModelOverride")
@pytest.mark.project
@pytest.mark.api
def test_deprecated_model_cannot_be_added_to_an_override(
    llm_model_status_utils,
    override_utils,
    override_project,
    platform_user,
    status_test_models,
):
    deprecated, _ = (m.base_name for m in status_test_models)
    llm_model_status_utils.apply_status(
        deprecated, ModelStatus.DEPRECATED, platform_user.client
    )

    with pytest.raises(HTTPError) as exc_info:
        override_utils.set_override(
            override_project, platform_user.user_id, [deprecated]
        )

    response = exc_info.value.response
    assert_that(response.status_code, equal_to(400), response.text)
    assert_that(
        response.json()["error"]["message"],
        equal_to(deprecated_not_added_message(deprecated)),
    )
    assert_that(
        override_utils.users_with_override(override_project),
        not_(has_item(platform_user.user_id)),
        "the refused save must not create an override",
    )


# @case user-level-model-override_TC_011
@pytest.mark.xdist_group(name="model_status")
@pytest.mark.requires_capability("features:userModelOverride")
@pytest.mark.project
@pytest.mark.api
def test_override_keeps_model_deprecated_after_it_was_saved(
    llm_model_status_utils,
    override_utils,
    override_project,
    platform_user,
    status_test_models,
):
    deprecated, other = (m.base_name for m in status_test_models)
    override_utils.set_override(
        override_project, platform_user.user_id, [deprecated, other], deprecated
    )
    llm_model_status_utils.apply_status(
        deprecated, ModelStatus.DEPRECATED, platform_user.client
    )

    resaved = override_utils.set_override(
        override_project, platform_user.user_id, [deprecated, other], other
    )

    stored = override_utils.get_override(override_project, platform_user.user_id)
    for override in (resaved, stored):
        assert_that(override.allowed_models, equal_to([deprecated, other]))
        assert_that(override.default_model, equal_to(other))


# @case user-level-model-override_TC_012
@pytest.mark.xdist_group(name="model_status")
@pytest.mark.requires_capability("features:userModelOverride")
@pytest.mark.project
@pytest.mark.api
def test_bulk_grant_of_deprecated_model_is_refused_when_a_user_lacks_it(
    llm_model_status_utils,
    override_utils,
    override_project,
    platform_user,
    second_platform_user,
    status_test_models,
):
    deprecated, other = (m.base_name for m in status_test_models)
    override_utils.set_override(
        override_project, platform_user.user_id, [deprecated, other], deprecated
    )
    llm_model_status_utils.apply_status(
        deprecated,
        ModelStatus.DEPRECATED,
        platform_user.client,
        second_platform_user.client,
    )

    with pytest.raises(HTTPError) as exc_info:
        override_utils.batch_grant(
            override_project,
            [platform_user.user_id, second_platform_user.user_id],
            [deprecated, other],
            other,
        )

    response = exc_info.value.response
    assert_that(response.status_code, equal_to(400), response.text)
    error = response.json()["error"]
    assert_that(error["message"], equal_to(BATCH_FAILED_MESSAGE))
    assert_that(error["details"], equal_to(deprecated_not_added_message(deprecated)))
    holder = override_utils.get_override(override_project, platform_user.user_id)
    assert_that(
        holder.default_model, equal_to(deprecated), "the holder is left as it was"
    )
    assert_that(
        override_utils.users_with_override(override_project),
        equal_to([platform_user.user_id]),
        "the user without the model must get no override",
    )
    with pytest.raises(HTTPError) as not_found:
        override_utils.get_override(override_project, second_platform_user.user_id)
    assert_that(
        not_found.value.response.json()["error"]["message"],
        equal_to(OVERRIDE_NOT_FOUND_MESSAGE),
    )


# @case user-level-model-override_TC_012
@pytest.mark.xdist_group(name="model_status")
@pytest.mark.requires_capability("features:userModelOverride")
@pytest.mark.project
@pytest.mark.api
def test_bulk_grant_of_deprecated_model_is_accepted_when_every_user_holds_it(
    llm_model_status_utils,
    override_utils,
    override_project,
    platform_user,
    second_platform_user,
    status_test_models,
):
    deprecated, other = (m.base_name for m in status_test_models)
    members = [platform_user, second_platform_user]
    for member in members:
        override_utils.set_override(
            override_project, member.user_id, [deprecated, other], deprecated
        )
    llm_model_status_utils.apply_status(
        deprecated,
        ModelStatus.DEPRECATED,
        platform_user.client,
        second_platform_user.client,
    )

    granted = override_utils.batch_grant(
        override_project, [m.user_id for m in members], [deprecated, other], other
    )

    assert_that(
        [o.user_id for o in granted],
        contains_inanyorder(*[m.user_id for m in members]),
    )
    for member in members:
        stored = override_utils.get_override(override_project, member.user_id)
        assert_that(stored.allowed_models, equal_to([deprecated, other]))
        assert_that(stored.default_model, equal_to(other))
