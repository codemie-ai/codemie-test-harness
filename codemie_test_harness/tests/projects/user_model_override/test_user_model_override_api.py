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

"""API tests for the per-user model override routes of a project.

A project admin replaces the models one member may use, for one member or for several at
once, and reads the result back. The routes refuse callers without write access to the
project, refuse invalid input, and record the changes in the activity trail.
"""

import pytest
from hamcrest import (
    assert_that,
    contains_inanyorder,
    contains_string,
    equal_to,
    has_entries,
    has_item,
    has_length,
    not_,
)
from requests import HTTPError

from codemie_test_harness.tests.test_data.user_model_override_test_data import (
    ACTIVITY_DOMAIN,
    BATCH_FAILED_MESSAGE,
    INVALID_BATCH_REQUESTS,
    INVALID_PUT_REQUESTS,
    NOT_A_MEMBER_REASON,
    OVERRIDE_NOT_FOUND_MESSAGE,
    OVERRIDE_REMOVED_EVENT,
    OVERRIDE_ROUTES,
    OVERRIDE_SET_EVENT,
    PROJECT_NOT_FOUND_MESSAGE,
)
from codemie_test_harness.tests.utils.user_model_override_utils import (
    UserModelOverrideUtils,
    resolve_models,
)


@pytest.fixture
def override_caller(request):
    """The user behind the indirect parameter: a plain project member or a user outside the project.

    Only the selected user is created, so a run does not log in a user it never uses.
    """
    fixture = {"member": "platform_user", "outsider": "outsider_user"}[request.param]
    return request.getfixturevalue(fixture)


# @case user-level-model-override_TC_001
@pytest.mark.requires_capability("features:userModelOverride")
@pytest.mark.project
@pytest.mark.api
def test_project_admin_saves_override_for_member_and_reads_it_back(
    project_admin_overrides, override_project, platform_user, override_models
):
    first, second, _ = override_models
    overrides = project_admin_overrides.overrides

    saved = overrides.set_override(
        override_project, platform_user.user_id, [first, second], second
    )
    read = overrides.get_override(override_project, platform_user.user_id)

    for stored in (saved, read):
        assert_that(stored.user_id, equal_to(platform_user.user_id))
        assert_that(stored.project_name, equal_to(override_project))
        assert_that(stored.allowed_models, equal_to([first, second]))
        assert_that(stored.default_model, equal_to(second))
    assert_that(
        read.id, equal_to(saved.id), "GET must return the override that PUT saved"
    )


# @case user-level-model-override_TC_002
@pytest.mark.requires_capability("features:userModelOverride")
@pytest.mark.project
@pytest.mark.api
def test_bulk_grant_saves_same_override_for_every_selected_member(
    override_utils,
    override_project,
    platform_user,
    second_platform_user,
    override_models,
):
    first, second, _ = override_models
    members = [platform_user, second_platform_user]

    granted = override_utils.batch_grant(
        override_project, [m.user_id for m in members], [first, second], first
    )

    assert_that(
        [o.user_id for o in granted],
        contains_inanyorder(*[m.user_id for m in members]),
        "the batch must answer with one override per selected member",
    )
    for member in members:
        stored = override_utils.get_override(override_project, member.user_id)
        assert_that(stored.allowed_models, equal_to([first, second]))
        assert_that(stored.default_model, equal_to(first))


# @case user-level-model-override_TC_003
@pytest.mark.requires_capability("features:userModelOverride")
@pytest.mark.project
@pytest.mark.api
def test_bulk_grant_with_non_member_changes_no_user(
    override_utils, override_project, platform_user, outsider_user, override_models
):
    with pytest.raises(HTTPError) as exc_info:
        override_utils.batch_grant(
            override_project,
            [platform_user.user_id, outsider_user.user_id],
            override_models[:1],
        )

    response = exc_info.value.response
    assert_that(response.status_code, equal_to(400), response.text)
    error = response.json()["error"]
    assert_that(error["message"], equal_to(BATCH_FAILED_MESSAGE))
    assert_that(
        error["details"],
        equal_to(f"{outsider_user.user_id}: {NOT_A_MEMBER_REASON}"),
        "the refusal must name the user that is not a member",
    )
    assert_that(
        override_utils.users_with_override(override_project),
        not_(has_item(platform_user.user_id)),
        "the valid member must be left without an override",
    )
    with pytest.raises(HTTPError) as not_found:
        override_utils.get_override(override_project, platform_user.user_id)
    assert_that(not_found.value.response.status_code, equal_to(404))
    assert_that(
        not_found.value.response.json()["error"]["message"],
        equal_to(OVERRIDE_NOT_FOUND_MESSAGE),
    )


# @case user-level-model-override_TC_002
@pytest.mark.requires_capability("features:userModelOverride")
@pytest.mark.project
@pytest.mark.api
def test_bulk_revoke_removes_override_of_selected_members_only(
    override_utils,
    override_project,
    platform_user,
    second_platform_user,
    override_models,
):
    first, second, _ = override_models
    for member in (platform_user, second_platform_user):
        override_utils.set_override(
            override_project, member.user_id, [first, second], first
        )

    revoked = override_utils.batch_revoke(override_project, [platform_user.user_id])

    assert_that(
        [o.user_id for o in revoked],
        equal_to([platform_user.user_id]),
        "the batch must answer with the overrides it removed",
    )
    assert_that(
        override_utils.users_with_override(override_project),
        equal_to([second_platform_user.user_id]),
        "the member that was not selected keeps the override",
    )
    with pytest.raises(HTTPError) as not_found:
        override_utils.get_override(override_project, platform_user.user_id)
    assert_that(not_found.value.response.status_code, equal_to(404))


# @case user-level-model-override_TC_001
@pytest.mark.requires_capability("features:userModelOverride")
@pytest.mark.project
@pytest.mark.api
def test_list_returns_every_override_and_drops_the_deleted_one(
    override_utils,
    override_project,
    platform_user,
    second_platform_user,
    override_models,
):
    first, second, third = override_models
    override_utils.set_override(
        override_project, platform_user.user_id, [first, second], second
    )
    override_utils.set_override(override_project, second_platform_user.user_id, [third])

    listed = {o.user_id: o for o in override_utils.list_overrides(override_project)}

    assert_that(
        listed.keys(),
        contains_inanyorder(platform_user.user_id, second_platform_user.user_id),
    )
    assert_that(listed[platform_user.user_id].allowed_models, equal_to([first, second]))
    assert_that(listed[platform_user.user_id].default_model, equal_to(second))
    assert_that(listed[second_platform_user.user_id].allowed_models, equal_to([third]))
    assert_that(listed[second_platform_user.user_id].default_model, equal_to(None))

    override_utils.delete_override(override_project, platform_user.user_id)

    assert_that(
        override_utils.users_with_override(override_project),
        equal_to([second_platform_user.user_id]),
        "the deleted override must leave the list",
    )
    with pytest.raises(HTTPError) as not_found:
        override_utils.get_override(override_project, platform_user.user_id)
    assert_that(not_found.value.response.status_code, equal_to(404))
    assert_that(
        not_found.value.response.json()["error"]["message"],
        equal_to(OVERRIDE_NOT_FOUND_MESSAGE),
    )


# @case user-level-model-override_TC_001
@pytest.mark.requires_capability("features:userModelOverride")
@pytest.mark.project
@pytest.mark.api
def test_list_pages_through_overrides_with_skip_and_limit(
    override_utils,
    override_project,
    platform_user,
    second_platform_user,
    override_models,
):
    override_utils.batch_grant(
        override_project,
        [platform_user.user_id, second_platform_user.user_id],
        override_models[:1],
    )

    everything = override_utils.list_overrides(override_project)
    first_page = override_utils.list_overrides(override_project, limit=1)
    second_page = override_utils.list_overrides(override_project, skip=1, limit=1)
    past_the_end = override_utils.list_overrides(override_project, skip=2)

    assert_that(everything, has_length(2))
    assert_that(first_page, has_length(1))
    assert_that(second_page, has_length(1))
    assert_that(
        [o.user_id for o in first_page + second_page],
        equal_to([o.user_id for o in everything]),
        "the pages must cover the whole list in the same order",
    )
    assert_that(past_the_end, has_length(0))


# @case user-level-model-override_TC_013
@pytest.mark.requires_capability("features:userModelOverride")
@pytest.mark.project
@pytest.mark.api
@pytest.mark.parametrize("override_caller", ["member", "outsider"], indirect=True)
@pytest.mark.parametrize("route", OVERRIDE_ROUTES.values(), ids=OVERRIDE_ROUTES.keys())
def test_caller_without_write_access_gets_404_on_override_routes(
    override_utils,
    override_project,
    override_caller,
    second_platform_user,
    override_models,
    route,
):
    kept, replacement, _ = override_models
    override_utils.set_override(override_project, second_platform_user.user_id, [kept])
    caller_utils = UserModelOverrideUtils(override_caller.client)

    with pytest.raises(HTTPError) as exc_info:
        route(
            caller_utils, override_project, second_platform_user.user_id, [replacement]
        )

    response = exc_info.value.response
    assert_that(response.status_code, equal_to(404), response.text)
    assert_that(
        response.json()["error"]["message"], equal_to(PROJECT_NOT_FOUND_MESSAGE)
    )
    stored = override_utils.get_override(override_project, second_platform_user.user_id)
    assert_that(
        stored.allowed_models,
        equal_to([kept]),
        "a refused call must leave the override as it was",
    )


# @case user-level-model-override_TC_014
@pytest.mark.requires_capability("features:userModelOverride")
@pytest.mark.project
@pytest.mark.api
@pytest.mark.parametrize(
    "invalid", INVALID_PUT_REQUESTS.values(), ids=INVALID_PUT_REQUESTS.keys()
)
def test_override_with_invalid_input_is_refused(
    override_utils, override_project, platform_user, override_models, invalid
):
    named = {"a": override_models[0], "b": override_models[1]}

    with pytest.raises(HTTPError) as exc_info:
        override_utils.set_override(
            override_project,
            platform_user.user_id,
            resolve_models(invalid.allowed_models, named),
            named.get(invalid.default_model),
        )

    response = exc_info.value.response
    assert_that(response.status_code, equal_to(invalid.status), response.text)
    error = response.json()["error"]
    assert_that(error["message"], contains_string(invalid.message_part))
    if invalid.details_part:
        assert_that(str(error["details"]), contains_string(invalid.details_part))
    assert_that(
        override_utils.users_with_override(override_project),
        not_(has_item(platform_user.user_id)),
        "a refused request must not save an override",
    )


# @case user-level-model-override_TC_014
@pytest.mark.requires_capability("features:userModelOverride")
@pytest.mark.project
@pytest.mark.api
@pytest.mark.parametrize(
    "invalid", INVALID_BATCH_REQUESTS.values(), ids=INVALID_BATCH_REQUESTS.keys()
)
def test_batch_with_invalid_input_is_refused(
    override_utils, override_project, platform_user, override_models, invalid
):
    named = {"a": override_models[0]}

    with pytest.raises(HTTPError) as exc_info:
        override_utils.batch(
            override_project,
            invalid.operation,
            invalid.user_ids([platform_user.user_id]),
            invalid.models(named),
        )

    response = exc_info.value.response
    assert_that(response.status_code, equal_to(400), response.text)
    assert_that(response.json()["error"]["message"], equal_to(invalid.message))
    assert_that(
        override_utils.users_with_override(override_project),
        not_(has_item(platform_user.user_id)),
        "a refused batch must not save an override",
    )


# @case user-level-model-override_TC_015
@pytest.mark.requires_capability("features:userModelOverride")
@pytest.mark.project
@pytest.mark.api
def test_setting_and_removing_override_records_activity_events(
    project_admin_overrides,
    activity_utils,
    override_project,
    platform_user,
    override_models,
):
    first, second, _ = override_models
    overrides = project_admin_overrides.overrides

    overrides.set_override(
        override_project, platform_user.user_id, [first, second], first
    )
    overrides.delete_override(override_project, platform_user.user_id)

    set_events = activity_utils.list_activity_events(
        entity_id=platform_user.user_id,
        event_type=[OVERRIDE_SET_EVENT],
        domain=[ACTIVITY_DOMAIN],
    ).data
    removed_events = activity_utils.list_activity_events(
        entity_id=platform_user.user_id,
        event_type=[OVERRIDE_REMOVED_EVENT],
        domain=[ACTIVITY_DOMAIN],
    ).data

    assert_that(set_events, has_length(1), "one event for the saved override")
    assert_that(set_events[0].actor_id, equal_to(project_admin_overrides.user_id))
    assert_that(
        set_events[0].attributes,
        has_entries(
            project_name=override_project,
            new_allowed_models=[first, second],
            new_default_model=first,
        ),
    )
    assert_that(removed_events, has_length(1), "one event for the removed override")
    assert_that(removed_events[0].actor_id, equal_to(project_admin_overrides.user_id))
    assert_that(
        removed_events[0].attributes,
        has_entries(
            project_name=override_project,
            previous_allowed_models=[first, second],
            previous_default_model=first,
        ),
    )
