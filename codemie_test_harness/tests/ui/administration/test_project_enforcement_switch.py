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


"""UI + backend regression tests for the 'Enforce member spend limits' switch in Edit Project.

Covers: the switch for the Global Administrator, the Maintainer and the Project Admin of the
project; the explanation that precedes a change in each direction; storing a confirmed change
through the real backend and reading it back after reopening the project; Cancel; saving
without an enforcement change; a failed save followed by a retry; the audit record of the
acting user.

Not covered here: that a confirmed change re-applies member limits in LiteLLM. That lives in
tests/budgets/test_project_member_spend_limits.py (the UI sends the same PATCH).

Escape on the confirmation and the in-flight save live in
test_project_enforcement_confirmation.py. Role-based API rejection lives in
tests/projects/test_project_enforcement_permissions.py.

Projects and the maintainer and project-scoped accounts come from the module-scoped
`cli_ui_world` fixture (tests/ui/administration/conftest.py); the global admin is a fresh
platform admin that is not a maintainer (`admin_user`), so it reaches the project through the
admin rule only. Every test first sets the stored state it needs through
the API as the harness admin; the projects are deleted with the fixture.
"""

import pytest
from hamcrest import assert_that, equal_to, has_length, is_

from codemie_test_harness.tests.test_data.project_activity_test_data import (
    ENFORCEMENT_EVENT,
)
from codemie_test_harness.tests.ui.pageobject.administration.enforcement_confirmation_dialog import (
    EnforcementConfirmationDialog,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_details_page import (
    ProjectDetailsPage,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_management_page import (
    ProjectManagementPage,
)
from codemie_test_harness.tests.ui.test_data.project_enforcement_test_data import (
    DESCRIPTION_SUFFIX,
    ENFORCEMENT_FIELD,
    INJECTED_SAVE_FAILURE,
    ORIGINAL_DESCRIPTION,
)
from codemie_test_harness.tests.utils.activity_utils import ActivityUtils
from codemie_test_harness.tests.utils.cli_analytics_api_utils import (
    assert_stored_roles,
)

GLOBAL_ADMIN_ROLE = "admin_user"
GLOBAL_ADMIN = pytest.param(GLOBAL_ADMIN_ROLE, id="global admin")
MAINTAINER = pytest.param("cli_maintainer", id="maintainer")
PROJECT_ADMIN = pytest.param("cli_project_admin", id="project admin")

STORED_OFF = pytest.param(False, id="off to on")
STORED_ON = pytest.param(True, id="on to off")
STORED_OFF_UNCHANGED = pytest.param(False, id="stored off")
STORED_ON_UNCHANGED = pytest.param(True, id="stored on")

AS_ANY_ENFORCER = pytest.mark.parametrize(
    "acting_credentials", [GLOBAL_ADMIN, MAINTAINER, PROJECT_ADMIN], indirect=True
)
AS_GLOBAL_OR_PROJECT_ADMIN = pytest.mark.parametrize(
    "acting_credentials", [GLOBAL_ADMIN, PROJECT_ADMIN], indirect=True
)
AS_MEMBER = pytest.mark.parametrize(
    "acting_credentials", [pytest.param("cli_member", id="member")], indirect=True
)
AS_OTHER_PROJECT_ADMIN = pytest.mark.parametrize(
    "acting_credentials",
    [pytest.param("cli_other_project_admin", id="other project admin")],
    indirect=True,
)
AS_GLOBAL_ADMIN = pytest.mark.parametrize(
    "acting_credentials", [GLOBAL_ADMIN], indirect=True
)


def _enforcement(project_utils, project_name: str) -> bool:
    return getattr(project_utils.get_project_detail(project_name), ENFORCEMENT_FIELD)


def _prepare(project_utils, project_name: str, stored: bool):
    """Put the project into a known stored state: original description, given enforcement."""
    project_utils.update_project(project_name, description=ORIGINAL_DESCRIPTION)
    project_utils.set_enforce_member_spend_limits(project_name, stored)
    assert_that(
        _enforcement(project_utils, project_name),
        is_(stored),
        "precondition: the stored enforcement setting",
    )


@pytest.fixture(autouse=True)
def global_admin_is_not_maintainer(request, user_utils):
    """For the 'global admin' parameter: prove the acting user (a fresh platform admin from the
    `admin_user` fixture, not a member of the project) is a global admin and not a maintainer,
    so the switch reaches it through the admin rule (isAdmin), not the maintainer rule.
    Otherwise that parameter would silently repeat the maintainer case."""
    callspec = getattr(request.node, "callspec", None)
    if callspec is None or callspec.params.get("acting_credentials") != (
        GLOBAL_ADMIN_ROLE
    ):
        return
    user_id = request.getfixturevalue("acting_credentials")[2]
    assert_stored_roles(user_utils, user_id, is_admin=True, is_maintainer=False)


@pytest.fixture
def trail_instance_id(cli_ui_world, project_utils) -> str:
    """The id the project's activity trail is addressed by; the test is skipped on a backend
    that does not provide the trail (the project detail carries no project_instance_id)."""
    instance_id = project_utils.get_project_detail(
        cli_ui_world.target
    ).project_instance_id
    if instance_id is None:
        pytest.skip(
            "this backend has no project activity trail (no project_instance_id)"
        )
    return str(instance_id)


# ── Confirmed change is stored and survives reopening ───────────────────────────────


# @case project-admin-enforcement-switch-confirmation_TC_001
@AS_ANY_ENFORCER
@pytest.mark.parametrize("stored", [STORED_OFF, STORED_ON])
@pytest.mark.oss_standalone
@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_confirmed_enforcement_change_is_stored_and_survives_reopen(
    page, cli_ui_world, project_utils, stored
):
    """The switch is offered and enabled, the explanation matches the direction (header,
    every clause, confirm button), nothing is stored until Confirm, and after Confirm the
    backend and a reopened Edit Project show the new value."""
    project = cli_ui_world.target
    _prepare(project_utils, project, stored)
    details = ProjectDetailsPage(page).navigate_to(project)
    modal = details.open_edit_project()
    confirmation = EnforcementConfirmationDialog(page)

    modal.should_show_enforcement_switch()
    modal.should_have_enforcement_value(stored)
    modal.toggle_enforcement()
    modal.should_have_enforcement_value(not stored)
    modal.click_save_to_confirm_enforcement()

    confirmation.should_be_visible()
    confirmation.should_explain(turning_on=not stored)
    assert_that(
        _enforcement(project_utils, project),
        is_(stored),
        "nothing is stored before the user confirms",
    )

    confirmation.confirm()
    modal.should_show_project_updated_toast(project)
    confirmation.should_be_closed()
    assert_that(
        _enforcement(project_utils, project),
        is_(not stored),
        "the confirmed change is stored by the backend",
    )

    details.navigate_to(project)
    details.open_edit_project().should_have_enforcement_value(not stored)


# ── Audit: the acting user is recorded ─────────────────────────────────────────────


# @case project-admin-enforcement-switch-confirmation_TC_002
@AS_GLOBAL_OR_PROJECT_ADMIN
@pytest.mark.oss_standalone
@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_confirmed_change_is_audited_with_the_acting_user(
    page,
    cli_ui_world,
    project_utils,
    user_utils,
    maintainer_client,
    trail_instance_id,
    acting_credentials,
):
    """A change a project admin or a global admin confirms in the UI leaves one enforcement
    event that names the previous and the new value and the acting user (id and e-mail)."""
    project = cli_ui_world.target
    actor_id = acting_credentials[2]
    actor_email = user_utils.get_admin_user(actor_id).email
    _prepare(project_utils, project, False)
    activity = ActivityUtils(maintainer_client)
    events_before = activity.list_all_project_events(
        trail_instance_id, event_type=[ENFORCEMENT_EVENT]
    )
    modal = ProjectDetailsPage(page).navigate_to(project).open_edit_project()
    confirmation = EnforcementConfirmationDialog(page)

    modal.should_show_enforcement_switch()
    modal.toggle_enforcement()
    modal.click_save_to_confirm_enforcement()
    confirmation.should_be_visible()
    confirmation.confirm()
    modal.should_show_project_updated_toast(project)

    events = activity.list_all_project_events(
        trail_instance_id, event_type=[ENFORCEMENT_EVENT]
    )
    assert_that(
        events, has_length(len(events_before) + 1), "one enforcement event is recorded"
    )
    assert_that(
        events[0].attributes,
        equal_to(
            {
                "previous_enforce_member_spend_limits": False,
                "new_enforce_member_spend_limits": True,
            }
        ),
        "the event records the previous and the new value",
    )
    assert_that(events[0].actor_id, equal_to(actor_id), "the acting user's id")
    assert_that(
        events[0].actor_email, equal_to(actor_email), "the acting user's e-mail"
    )


# ── Cancel ─────────────────────────────────────────────────────────────────────────


# @case project-admin-enforcement-switch-confirmation_TC_004
@AS_GLOBAL_OR_PROJECT_ADMIN
@pytest.mark.parametrize("stored", [STORED_OFF, STORED_ON])
@pytest.mark.oss_standalone
@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_cancel_stores_nothing_and_keeps_the_other_edits(
    page, cli_ui_world, project_utils, stored
):
    """Cancel closes only the explanation and sends no request: the switch returns to its
    stored value, the form and the unrelated edit stay, nothing is stored; saving again then
    goes straight to the backend, stores only the other edit and asks nothing."""
    project = cli_ui_world.target
    edited = ORIGINAL_DESCRIPTION + DESCRIPTION_SUFFIX
    _prepare(project_utils, project, stored)
    modal = ProjectDetailsPage(page).navigate_to(project).open_edit_project()
    confirmation = EnforcementConfirmationDialog(page)

    modal.should_show_enforcement_switch()
    modal.append_to_edit_description(DESCRIPTION_SUFFIX)
    modal.toggle_enforcement()
    modal.start_counting_save_requests(project)
    modal.click_save_to_confirm_enforcement()
    confirmation.should_be_visible()
    confirmation.cancel()

    confirmation.should_be_closed()
    modal.should_remain_open_for_editing()
    modal.should_have_enforcement_value(stored)
    modal.should_have_edit_description(edited)
    detail = project_utils.get_project_detail(project)
    assert_that(
        detail.description, equal_to(ORIGINAL_DESCRIPTION), "Cancel stores nothing"
    )
    assert_that(
        getattr(detail, ENFORCEMENT_FIELD), is_(stored), "Cancel keeps the setting"
    )
    assert_that(
        modal.stop_counting_save_requests(),
        equal_to(0),
        "neither the Save that opened the confirmation nor Cancel sends a project PATCH",
    )

    request_body = modal.save_edit_capturing_request(project)
    modal.should_show_project_updated_toast(project)
    confirmation.should_be_closed()
    assert_that(
        request_body[ENFORCEMENT_FIELD],
        is_(stored),
        "the retry resends the stored value, not the cancelled one",
    )
    detail = project_utils.get_project_detail(project)
    assert_that(detail.description, equal_to(edited), "the other edit is stored")
    assert_that(
        getattr(detail, ENFORCEMENT_FIELD), is_(stored), "the setting is unchanged"
    )


# ── Save without an enforcement change ─────────────────────────────────────────────


# @case project-admin-enforcement-switch-confirmation_TC_008
@AS_ANY_ENFORCER
@pytest.mark.parametrize("stored", [STORED_OFF_UNCHANGED, STORED_ON_UNCHANGED])
@pytest.mark.oss_standalone
@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_save_without_enforcement_change_asks_no_confirmation(
    page, cli_ui_world, project_utils, stored
):
    """Saving another edit with the switch untouched shows no explanation: Save itself sends
    the project PATCH (a confirmation would hold it back), with the stored enforcement value,
    and the edit is stored without changing enforcement."""
    project = cli_ui_world.target
    edited = ORIGINAL_DESCRIPTION + DESCRIPTION_SUFFIX
    _prepare(project_utils, project, stored)
    modal = ProjectDetailsPage(page).navigate_to(project).open_edit_project()
    confirmation = EnforcementConfirmationDialog(page)

    modal.should_show_enforcement_switch()
    modal.append_to_edit_description(DESCRIPTION_SUFFIX)
    request_body = modal.save_edit_capturing_request(project)

    modal.should_show_project_updated_toast(project)
    confirmation.should_be_closed()
    assert_that(
        request_body[ENFORCEMENT_FIELD],
        is_(stored),
        "the save sends the stored enforcement value",
    )
    detail = project_utils.get_project_detail(project)
    assert_that(detail.description, equal_to(edited), "the edit is stored")
    assert_that(
        getattr(detail, ENFORCEMENT_FIELD), is_(stored), "enforcement unchanged"
    )


# @case project-admin-enforcement-switch-confirmation_TC_008
@AS_GLOBAL_ADMIN
@pytest.mark.oss_standalone
@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_toggling_back_to_the_stored_value_asks_no_confirmation(
    page, cli_ui_world, project_utils
):
    """A switch flipped twice is back at its stored value: Save itself sends the project
    PATCH with the stored value and asks nothing."""
    project = cli_ui_world.target
    edited = ORIGINAL_DESCRIPTION + DESCRIPTION_SUFFIX
    _prepare(project_utils, project, True)
    modal = ProjectDetailsPage(page).navigate_to(project).open_edit_project()
    confirmation = EnforcementConfirmationDialog(page)

    modal.should_show_enforcement_switch()
    modal.toggle_enforcement()
    modal.toggle_enforcement()
    modal.should_have_enforcement_value(True)
    modal.append_to_edit_description(DESCRIPTION_SUFFIX)
    request_body = modal.save_edit_capturing_request(project)

    modal.should_show_project_updated_toast(project)
    confirmation.should_be_closed()
    assert_that(
        request_body[ENFORCEMENT_FIELD],
        is_(True),
        "the save sends the stored enforcement value",
    )
    detail = project_utils.get_project_detail(project)
    assert_that(detail.description, equal_to(edited), "the edit is stored")
    assert_that(getattr(detail, ENFORCEMENT_FIELD), is_(True), "enforcement unchanged")


# ── Failed save and retry ──────────────────────────────────────────────────────────


# @case project-admin-enforcement-switch-confirmation_TC_007
@AS_GLOBAL_ADMIN
@pytest.mark.oss_standalone
@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_failed_confirmed_save_stores_nothing_and_retry_asks_again(
    page, cli_ui_world, project_utils
):
    """When the confirmed save fails (the browser's request is answered with HTTP 500 before
    it reaches the backend), the user is shown the error, nothing is stored, Edit Project stays
    open with the switch as the user set it and a new Save asks again; confirming then stores
    the change."""
    project = cli_ui_world.target
    _prepare(project_utils, project, False)
    modal = ProjectDetailsPage(page).navigate_to(project).open_edit_project()
    confirmation = EnforcementConfirmationDialog(page)

    modal.should_show_enforcement_switch()
    modal.toggle_enforcement()
    modal.click_save_to_confirm_enforcement()
    confirmation.should_be_visible()
    modal.fail_next_save_request(project, INJECTED_SAVE_FAILURE)
    confirmation.confirm()

    modal.should_show_save_error(INJECTED_SAVE_FAILURE)
    confirmation.should_be_closed()
    modal.should_remain_open_for_editing()
    modal.should_have_enforcement_value(True)
    assert_that(
        _enforcement(project_utils, project),
        is_(False),
        "the failed save stores nothing",
    )

    modal.click_save_to_confirm_enforcement()
    confirmation.should_be_visible()
    confirmation.should_explain_turning_on()
    confirmation.confirm()
    modal.should_show_project_updated_toast(project)
    assert_that(
        _enforcement(project_utils, project), is_(True), "the retry stores the change"
    )


# ── Users without rights over the project cannot reach its editing ─────────────────
# Edit Project is the only place with the enforcement switch. For these users it is not
# offered at all, so the switch is unreachable; the tests assert that, and nothing forces
# the dialog open.


# @case project-admin-enforcement-switch-confirmation_TC_013
@AS_MEMBER
@pytest.mark.oss_standalone
@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_project_member_cannot_open_edit_project(page, cli_ui_world):
    """A plain member sees the project but is offered neither 'Edit' in the list row nor
    'Edit Project' on the details page."""
    project = cli_ui_world.target
    listing = ProjectManagementPage(page)
    listing.navigate_to()
    listing.should_list_project(project)
    listing.should_not_offer_edit_action(project)

    ProjectDetailsPage(page).navigate_to(
        project
    ).should_show_project_without_edit_project_button()


# @case project-admin-enforcement-switch-confirmation_TC_013
@AS_OTHER_PROJECT_ADMIN
@pytest.mark.oss_standalone
@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_admin_of_another_project_cannot_open_edit_project_of_the_target(
    page, cli_ui_world, own_project
):
    """The admin of a different project can edit their own project (positive control) but the
    target is not listed for them, and opening its page directly shows 'Project not found'
    with no 'Edit Project'."""
    target = cli_ui_world.target
    listing = ProjectManagementPage(page)
    listing.navigate_to()
    listing.should_list_project(own_project)
    listing.should_offer_edit_action(own_project)
    listing.should_not_list_project(target)

    ProjectDetailsPage(page).navigate_to(
        target
    ).should_show_project_not_found_without_edit_project_button()
