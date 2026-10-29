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

"""UI tests for the project-level CLI Analytics setting (plan TC-015..TC-018).

The Edit Project dialog has an 'Enable CLI Analytics' toggle, Overview > Project information
shows 'CLI Analytics: Enabled / Disabled'. Global Administrator and Maintainer view and change
the setting; the Project Admin of the project sees it read-only; everyone else sees nothing.
Editing other fields as Project Admin must not send the setting.

Needs the stand with the FE feature bundle (FRONTEND_URL) and a BE with features:cliAnalytics on,
real roles (ENV other than local). Auditor scenarios provision a dedicated account; AUDITOR_*
configuration is not required.

Accounts and projects come from the module-scoped `cli_ui_world` fixture
(tests/ui/administration/conftest.py): the role users are created once per module, so a test
costs one browser login. The BE rate-limits POST /v1/local-auth/login (RATE_LIMIT_LOGIN); a 429
is an error, never retried here. Pace large runs or raise the limit on an isolated stand only.
"""

import pytest
from hamcrest import assert_that, equal_to, has_key, is_, is_not

from codemie_test_harness.tests.ui.pageobject.administration.project_details_page import (
    ProjectDetailsPage,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_management_page import (
    ProjectManagementPage,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_modal_page import (
    ProjectModal,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.project_visibility_utils import CLI_ANALYTICS_KEY

pytestmark = [
    pytest.mark.ui,
    pytest.mark.project,
    pytest.mark.cli_analytics,
]

GLOBAL_ADMIN = pytest.param("cli_global_admin", id="global admin")
MAINTAINER = pytest.param("cli_maintainer", id="maintainer")
PROJECT_ADMIN = pytest.param("cli_project_admin", id="project admin")
OTHER_PROJECT_ADMIN = pytest.param("cli_other_project_admin", id="other project admin")
MEMBER = pytest.param("cli_member", id="member")
AUDITOR = pytest.param("cli_auditor", id="auditor")
UNRELATED_USER = pytest.param("cli_unrelated_user", id="unrelated user")

STATES = [pytest.param(False, id="disabled"), pytest.param(True, id="enabled")]

AS_WRITER = pytest.mark.parametrize(
    "acting_credentials", [GLOBAL_ADMIN, MAINTAINER], indirect=True
)
AS_WRITER_OR_PROJECT_ADMIN = pytest.mark.parametrize(
    "acting_credentials", [GLOBAL_ADMIN, MAINTAINER, PROJECT_ADMIN], indirect=True
)
AS_PROJECT_ADMIN = pytest.mark.parametrize(
    "acting_credentials", [PROJECT_ADMIN], indirect=True
)
AS_MEMBER_OR_AUDITOR = pytest.mark.parametrize(
    "acting_credentials", [MEMBER, AUDITOR], indirect=True
)
AS_USER_WITHOUT_ACCESS = pytest.mark.parametrize(
    "acting_credentials", [OTHER_PROJECT_ADMIN, UNRELATED_USER], indirect=True
)


# ── TC-015: writers change the toggle, it persists; personal project has no toggle ──


@AS_WRITER
@pytest.mark.parametrize("start", STATES)
def test_writer_changes_toggle_and_it_persists_after_reload(
    page, project_flag_api, cli_ui_world, start
):
    """TC-015 (AC-2): a writer opens Edit Project, sees an editable toggle with the hint,
    flips it and saves; the API readback and a reloaded page show the new value."""
    project = cli_ui_world.target
    project_flag_api.write_flag(project, start)
    details = ProjectDetailsPage(page).navigate_to(project)
    details.should_have_edit_project_button()
    modal = details.open_edit_project()

    modal.should_show_cli_analytics_switch()
    modal.should_have_cli_analytics_editable()
    modal.should_have_cli_analytics_value(start)
    modal.should_show_cli_analytics_hint()

    modal.toggle_cli_analytics()
    modal.should_have_cli_analytics_value(not start)
    modal.click_save()
    modal.should_show_project_updated_toast(project)
    assert_that(project_flag_api.read(project)[CLI_ANALYTICS_KEY], is_(not start))

    details.navigate_to(project)
    details.should_show_cli_analytics_status(not start)
    details.open_edit_project().should_have_cli_analytics_value(not start)


@AS_WRITER
def test_personal_project_edit_dialog_has_no_toggle(page, cli_ui_world):
    """TC-015 (AC-1): the Edit dialog of a personal project, opened by a writer from the
    projects list, has no CLI Analytics switch at all."""
    listing = ProjectManagementPage(page)
    listing.navigate_to()
    listing.search_for(cli_ui_world.personal)
    listing.click_edit_project(cli_ui_world.personal)
    ProjectModal(page).should_be_visible().should_not_show_cli_analytics_switch()


# ── TC-016: project admin sees a read-only toggle, saving does not send the flag ───


@AS_PROJECT_ADMIN
@pytest.mark.parametrize("state", STATES)
def test_project_admin_sees_read_only_toggle_and_save_does_not_send_flag(
    page, project_flag_api, cli_ui_world, state
):
    """TC-016 (AC-3, AC-5): the toggle shows the current value, disabled; editing the
    description and saving sends no cli_analytics_enabled key, changes the description and
    leaves the flag as it was."""
    project = cli_ui_world.target
    new_description = get_random_name()
    project_flag_api.write_flag(project, state)
    modal = ProjectDetailsPage(page).navigate_to(project).open_edit_project()

    modal.should_show_cli_analytics_switch()
    modal.should_have_cli_analytics_read_only()
    modal.should_have_cli_analytics_value(state)

    modal.fill_description(new_description)
    request_body = modal.save_capturing_request(project)
    assert_that(request_body, is_not(has_key(CLI_ANALYTICS_KEY)))
    assert_that(request_body["description"], equal_to(new_description))

    modal.should_show_project_updated_toast(project)
    saved = project_flag_api.read(project)
    assert_that(saved["description"], equal_to(new_description))
    assert_that(saved[CLI_ANALYTICS_KEY], is_(state))


# ── TC-017: edit actions and project visibility per role ──────────────────────────


@AS_WRITER_OR_PROJECT_ADMIN
def test_edit_actions_are_offered_to_writers_and_project_admin(page, cli_ui_world):
    """TC-017 (AC-2, AC-3): the list row offers 'Edit' and the details page has 'Edit Project'."""
    listing = ProjectManagementPage(page)
    listing.navigate_to()
    listing.should_list_project(cli_ui_world.target)
    listing.should_offer_edit_action(cli_ui_world.target)
    ProjectDetailsPage(page).navigate_to(
        cli_ui_world.target
    ).should_have_edit_project_button()


@AS_MEMBER_OR_AUDITOR
def test_edit_actions_are_absent_for_member_and_auditor(page, cli_ui_world):
    """TC-017 (AC-4): the project IS listed and shown, but offers no 'Edit' in the list row and
    no 'Edit Project' on the details page (strict: the absence is not an unloaded page)."""
    listing = ProjectManagementPage(page)
    listing.navigate_to()
    listing.should_list_project(cli_ui_world.target)
    listing.should_not_offer_edit_action(cli_ui_world.target)
    ProjectDetailsPage(page).navigate_to(
        cli_ui_world.target
    ).should_show_project_without_edit_project_button()


@AS_USER_WITHOUT_ACCESS
def test_project_is_not_visible_to_other_project_admin_and_unrelated_user(
    page, cli_ui_world, own_project
):
    """TC-017 (AC-3, AC-4): the user's own project is listed (positive control), the target is
    neither listed nor offers 'Edit Project' (not found, or Overview without a button)."""
    listing = ProjectManagementPage(page)
    listing.navigate_to()
    listing.should_list_project(own_project)
    listing.should_not_list_project(cli_ui_world.target)
    ProjectDetailsPage(page).navigate_to(
        cli_ui_world.target
    ).should_not_have_edit_project_button()


# ── TC-018: Overview status per role and state ────────────────────────────────────


@AS_WRITER_OR_PROJECT_ADMIN
@pytest.mark.parametrize("state", STATES)
def test_overview_shows_cli_analytics_status_to_viewers(
    page, project_flag_api, cli_ui_world, state
):
    """TC-018 (AC-2, AC-3): Overview > Project information shows 'CLI Analytics' as
    Enabled / Disabled to the global admin, maintainer and project admin."""
    project_flag_api.write_flag(cli_ui_world.target, state)
    ProjectDetailsPage(page).navigate_to(
        cli_ui_world.target
    ).should_show_cli_analytics_status(state)


@AS_MEMBER_OR_AUDITOR
@pytest.mark.parametrize("state", STATES)
def test_overview_shows_no_status_to_member_and_auditor(
    page, project_flag_api, cli_ui_world, state
):
    """TC-018 (AC-4): the project IS shown (strict) but has no 'CLI Analytics' item."""
    project_flag_api.write_flag(cli_ui_world.target, state)
    ProjectDetailsPage(page).navigate_to(
        cli_ui_world.target
    ).should_show_project_without_cli_analytics_status()


@AS_USER_WITHOUT_ACCESS
@pytest.mark.parametrize("state", STATES)
def test_overview_shows_no_status_to_users_without_access(
    page, project_flag_api, cli_ui_world, state
):
    """TC-018 (AC-4): a user without access gets 'Project not found' (or an Overview) and no
    'CLI Analytics' item."""
    project_flag_api.write_flag(cli_ui_world.target, state)
    ProjectDetailsPage(page).navigate_to(
        cli_ui_world.target
    ).should_not_show_cli_analytics_status()
