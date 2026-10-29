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

"""Project-level `cli_analytics_enabled` - read visibility, write authorisation, create.

Every visibility cell asserts exactly one of four kinds, because "no access" and "hidden field"
are different facts: the key PRESENT with the written value, the key ABSENT from the raw JSON
(not null, not false), an exact HTTP status, or the project NOT LISTED. Raw JSON is read through
`ProjectFlagUtils`, never through SDK models (they turn a missing key into None).

Roles: global admin and maintainer (the writers), project admin of the target project, project
admin of the other project only, member of both, auditor (member of neither), unrelated user.
State changes use the global admin.

Evidence limits (black box, only what the API returns): the AC-1 default of already existing
projects (migration) and the AC-4 defensive write check are backend-side and covered by backend
tests, not here. Scenario ids (TC-009..TC-014) refer to the approved test plan.
"""

import pytest
from hamcrest import (
    assert_that,
    equal_to,
    greater_than,
    has_entries,
    has_entry,
    has_length,
    instance_of,
    is_,
    none,
    only_contains,
    same_instance,
)

from codemie_test_harness.tests.test_data.project_cli_analytics_test_data import (
    FIELD_VARIANTS,
    NON_WRITER_ROLES,
    VISIBILITY_CASES,
    WRITER_ROLES,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.project_utils import ProjectUtils
from codemie_test_harness.tests.utils.project_visibility_utils import (
    CLI_ANALYTICS_KEY as KEY,
    assert_view,
)

pytestmark = [
    pytest.mark.api,
    pytest.mark.cli_analytics,
    pytest.mark.project,
]


@pytest.mark.parametrize(
    "route,which,role_api,state,expected", VISIBILITY_CASES, indirect=["role_api"]
)
def test_flag_visibility_per_route_role_and_state(
    roles_world, role_api, route, which, state, expected
):
    """TC-009 (AC-3, AC-4): the flag is shown with the written value only to the global admin,
    the maintainer and the project admin of that project; for the other roles the key is absent
    or the request is denied. The target carries `state`, the other project the opposite."""
    roles_world.require_route(route)
    roles_world.write_states(state)
    name = roles_world.project(which)

    view = role_api.view(route, name)

    assert_view(
        view,
        expected,
        roles_world.shown_flag(which, state),
        f"{route} of {name} as the requested role with the flag {state}",
    )


@pytest.mark.parametrize(
    "role_api", ["global_admin", "maintainer", "project_admin"], indirect=True
)
@pytest.mark.parametrize("state", [True, False], ids=["flag_on", "flag_off"])
def test_every_visible_route_shows_the_value_just_written(roles_world, role_api, state):
    """TC-009 values-equal-written (AC-2, AC-3): detail, list and, where mounted, the legacy
    route all show the value the global admin just changed to."""
    roles_world.admin.write_flag(roles_world.target, not state)
    roles_world.admin.write_flag(roles_world.target, state)

    values = role_api.visible_values(roles_world.target, roles_world.legacy_mounted)

    assert_that(
        values,
        has_entries(detail=same_instance(state), list=same_instance(state)),
        f"detail and list must show {state}",
    )
    assert_that(
        list(values.values()),
        only_contains(same_instance(state)),
        f"every route must show {state}, got {values}",
    )


@pytest.mark.parametrize("role_api", WRITER_ROLES, indirect=True)
def test_writer_sets_repeats_and_clears_the_flag(roles_world, role_api):
    """TC-010 (AC-2, AC-4): true persists, an unchanged value is accepted, an explicit null is
    a no-op, false persists."""
    target = roles_world.target
    roles_world.admin.write_flag(target, False)

    set_true = role_api.patch_project(target, {KEY: True})
    assert_that(set_true.status_code, equal_to(200), f"set true: {set_true.text}")
    assert_that(set_true.json(), has_entry(KEY, same_instance(True)), "set true answer")
    assert_that(
        roles_world.admin.read(target),
        has_entry(KEY, same_instance(True)),
        "true must persist on re-read",
    )

    repeat_true = role_api.patch_project(target, {KEY: True})
    assert_that(
        repeat_true.status_code, equal_to(200), f"unchanged true: {repeat_true.text}"
    )
    assert_that(
        roles_world.admin.read(target),
        has_entry(KEY, same_instance(True)),
        "an unchanged true must stay true",
    )

    explicit_null = role_api.patch_project(target, {KEY: None})
    assert_that(explicit_null.status_code, equal_to(200), f"null: {explicit_null.text}")
    assert_that(
        roles_world.admin.read(target),
        has_entry(KEY, same_instance(True)),
        "an explicit null must change nothing",
    )

    set_false = role_api.patch_project(target, {KEY: False})
    assert_that(set_false.status_code, equal_to(200), f"set false: {set_false.text}")
    assert_that(
        set_false.json(), has_entry(KEY, same_instance(False)), "set false answer"
    )
    assert_that(
        roles_world.admin.read(target),
        has_entry(KEY, same_instance(False)),
        "false must persist on re-read",
    )

    repeat_false = role_api.patch_project(target, {KEY: False})
    assert_that(
        repeat_false.status_code, equal_to(200), f"unchanged false: {repeat_false.text}"
    )
    assert_that(
        roles_world.admin.read(target),
        has_entry(KEY, same_instance(False)),
        "an unchanged false must stay false",
    )


@pytest.mark.parametrize("role_api", NON_WRITER_ROLES, indirect=True)
@pytest.mark.parametrize("start,sent", FIELD_VARIANTS)
def test_non_writer_patch_with_the_flag_is_denied_and_applies_nothing(
    roles_world, role_api, start, sent
):
    """TC-011 (AC-4): any body carrying the field, even unchanged or null, gets 403 and the
    description sent in the same PATCH is not applied."""
    base_description = f"base {get_random_name()}"
    roles_world.admin.write_flag(
        roles_world.target, start, description=base_description
    )

    response = role_api.patch_project(
        roles_world.target, {"description": "must-not-apply", KEY: sent}
    )

    assert_that(response.status_code, equal_to(403), f"body={response.text!r}")
    assert_that(
        roles_world.admin.read(roles_world.target),
        has_entries(
            description=base_description, cli_analytics_enabled=same_instance(start)
        ),
        "nothing of the denied PATCH may be applied",
    )


@pytest.mark.parametrize("role_api", ["project_admin"], indirect=True)
@pytest.mark.parametrize("state", [True, False], ids=["flag_on", "flag_off"])
def test_project_admin_edits_other_fields_and_leaves_the_flag(
    roles_world, role_api, state
):
    """TC-011 (AC-5): a project admin PATCH without the flag succeeds, applies the other field
    and keeps the flag."""
    roles_world.admin.write_flag(roles_world.target, state)
    new_description = f"edited {get_random_name()}"

    response = role_api.patch_project(
        roles_world.target, {"description": new_description}
    )

    assert_that(response.status_code, equal_to(200), f"body={response.text!r}")
    assert_that(response.json(), has_entry(KEY, same_instance(state)), "answer")
    assert_that(
        roles_world.admin.read(roles_world.target),
        has_entries(
            description=new_description, cli_analytics_enabled=same_instance(state)
        ),
        "the description is applied and the flag unchanged",
    )


@pytest.mark.parametrize(
    "role_api", ["project_admin", "other_project_admin"], indirect=True
)
def test_platform_admin_label_alone_is_no_global_writer(roles_world, role_api):
    """TC-011 (AC-4): a user who holds only the platform_admin label (not an admin, admin of
    some project) cannot write the flag."""
    email = role_api.client.users.about_me().email
    assert_that(
        roles_world.admin.has_platform_admin_label(email),
        is_(True),
        f"{email} does not carry the platform_admin label, the case proves nothing",
    )
    roles_world.admin.write_flag(roles_world.target, False)

    response = role_api.patch_project(roles_world.target, {KEY: True})

    assert_that(response.status_code, equal_to(403), f"body={response.text!r}")
    assert_that(
        roles_world.admin.read(roles_world.target),
        has_entry(KEY, same_instance(False)),
        "the flag must stay false",
    )


@pytest.mark.parametrize(
    "role_api,expected_status",
    [
        pytest.param("global_admin", 400, id="global_admin_is_rejected"),
        pytest.param("maintainer", 400, id="maintainer_is_rejected"),
        pytest.param("member", 403, id="owner_without_global_write_is_denied"),
    ],
    indirect=["role_api"],
)
def test_personal_project_cannot_be_enabled(roles_world, role_api, expected_status):
    """TC-012 (AC-4): enabling a personal project is rejected for a writer, and denied (403,
    before the personal-project rule) for its owner without global write; it stays false."""
    response = role_api.patch_project(roles_world.member_email, {KEY: True})

    assert_that(
        response.status_code, equal_to(expected_status), f"body={response.text!r}"
    )
    assert_that(
        roles_world.admin.read(roles_world.member_email),
        has_entry(KEY, same_instance(False)),
        "a personal project must stay disabled",
    )


def test_ordinary_creator_creates_a_project_without_the_field(
    roles_world, ordinary_creator_api
):
    """TC-013 (AC-1, AC-3, AC-4): an ordinary creator becomes project admin of the new project,
    sees it disabled and still cannot change the flag."""
    name = get_random_name()

    created = ordinary_creator_api.create_project({"name": name})

    assert_that(created.status_code, equal_to(201), f"body={created.text!r}")
    assert_that(created.json(), has_entry(KEY, same_instance(False)), "create answer")
    assert_that(
        ordinary_creator_api.read(name),
        has_entry(KEY, same_instance(False)),
        "the creator sees the project disabled",
    )
    denied = ordinary_creator_api.patch_project(name, {KEY: True})
    assert_that(denied.status_code, equal_to(403), f"body={denied.text!r}")
    assert_that(
        roles_world.admin.read(name),
        has_entry(KEY, same_instance(False)),
        "the denied write must not change the flag",
    )


@pytest.mark.parametrize("value", [True, False, None], ids=["true", "false", "null"])
def test_ordinary_creator_with_the_field_is_denied_before_any_mutation(
    roles_world, ordinary_creator_api, value
):
    """TC-013 (AC-4): create with the field gets 403 and no project exists afterwards."""
    name = get_random_name()

    response = ordinary_creator_api.create_project({"name": name, KEY: value})

    assert_that(response.status_code, equal_to(403), f"body={response.text!r}")
    assert_that(
        roles_world.admin.get_project(name).status_code,
        equal_to(404),
        "the project must not exist after the denied create",
    )
    assert_that(
        roles_world.admin.view("list", name).body,
        none(),
        "the project must not be listed after the denied create",
    )


@pytest.mark.parametrize("role_api", WRITER_ROLES, indirect=True)
def test_writer_created_project_defaults_to_disabled(roles_world, role_api):
    """TC-014 (AC-1): a project created by a writer without the field reads false."""
    name = get_random_name()

    response = role_api.create_project({"name": name})

    assert_that(response.status_code, equal_to(201), f"body={response.text!r}")
    assert_that(response.json(), has_entry(KEY, same_instance(False)), "create answer")
    assert_that(
        roles_world.admin.read(name),
        has_entry(KEY, same_instance(False)),
        "the default must be false on re-read",
    )


@pytest.mark.parametrize("role_api", WRITER_ROLES, indirect=True)
@pytest.mark.parametrize(
    "value", [True, False], ids=["explicit_true", "explicit_false"]
)
def test_writer_created_project_keeps_the_explicit_value(roles_world, role_api, value):
    """TC-014 (AC-2): the explicit value given on create persists on re-read."""
    name = get_random_name()

    response = role_api.create_project({"name": name, KEY: value})

    assert_that(response.status_code, equal_to(201), f"body={response.text!r}")
    assert_that(response.json(), has_entry(KEY, same_instance(value)), "create answer")
    assert_that(
        roles_world.admin.read(name),
        has_entry(KEY, same_instance(value)),
        "the explicit value must persist",
    )


def test_every_listed_project_exposes_a_boolean(roles_world):
    """TC-014 (AC-1): the global admin sees a boolean on the first page of the project list and
    on the world's own projects. Bounded sample, not every project of the shared stand (its
    total changes under parallel workers); the migration of already existing projects is
    backend-side and not asserted here."""
    items = roles_world.admin.list_sample([roles_world.target, roles_world.other])

    assert_that(items, has_length(greater_than(0)), "the project list is empty")
    assert_that(
        items,
        only_contains(has_entry(KEY, instance_of(bool))),
        f"every sampled project must expose {KEY} as a boolean",
    )


@pytest.mark.parametrize("role_api", ["global_admin"], indirect=True)
@pytest.mark.parametrize(
    "value", [True, False], ids=["sdk_sets_true", "sdk_sets_false"]
)
def test_sdk_update_round_trips_the_flag(roles_world, role_api, value):
    """TC-014 (AC-2): ProjectUtils.update_project carries the flag end to end. The value is
    read back twice: from the raw JSON (the wire contract) and through the SDK model
    (ProjectDetailResponse.cli_analytics_enabled), so a model that drops or mis-parses the
    field fails here."""
    projects = ProjectUtils(role_api.client)
    roles_world.admin.write_flag(roles_world.target, not value)

    projects.update_project(roles_world.target, cli_analytics_enabled=value)

    assert_that(
        roles_world.admin.read(roles_world.target),
        has_entry(KEY, same_instance(value)),
        "the value set through the SDK must persist",
    )
    assert_that(
        projects.get_project_detail(roles_world.target).cli_analytics_enabled,
        same_instance(value),
        "the SDK model must read back the value that was written",
    )
