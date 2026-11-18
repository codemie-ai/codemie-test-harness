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

"""UI tests for sharing a hosted application by each of its managers, and for what others see.

tests/ui/conftest.py's autouse ``login`` signs in as the AUTH_USERNAME account. This module
overrides it: the browser signs in as the person of the test's ``view``, a user created for the
test, so the creator of the application is always someone else unless the view says ``creator``.
Users, projects and applications are made through the API and removed after the test.
"""

import pytest
from hamcrest import assert_that, contains_exactly, empty, is_, not_none

from codemie_test_harness.tests.test_data.hosted_application_test_data import (
    SHARE_SUSPENDED_MESSAGE,
    SHARING_SUSPENSION_REASON,
)
from codemie_test_harness.tests.ui.pageobject.hosted_applications.hosted_application_details_page import (
    HostedApplicationDetailsPage,
)
from codemie_test_harness.tests.ui.pageobject.hosted_applications.hosted_application_viewer_page import (
    HostedApplicationViewerPage,
)
from codemie_test_harness.tests.ui.pageobject.hosted_applications.hosted_applications_page import (
    HostedApplicationsPage,
)
from codemie_test_harness.tests.ui.pageobject.hosted_applications.hosted_share_dialog import (
    HostedShareDialog,
)
from codemie_test_harness.tests.ui.pageobject.login_page import LoginPage
from codemie_test_harness.tests.ui.test_data.hosted_application_ui_test_data import (
    CLIPBOARD_PERMISSIONS,
    MODERATOR_VIEWS,
    NON_MANAGER_VIEWS,
    PRIVATE_APP_HINT_VIEWS,
    REVOKE_LINK_MENU_ITEM,
    SHARE_DIALOG_VIEWS,
    SHARE_LINK_ROUTE,
    SHARE_MANAGER_VIEWS,
    SHARE_MENU_ITEM,
    SUSPEND_MENU_ITEM,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.hosted_sharing_utils import SharingWorld

CAPABILITY = "features:hostedApplications"


@pytest.fixture
def ui_sharing_world(hosted_people, view):
    """A live application of another user, shaped by the test's ``view``; see ``SharingWorld``."""
    return SharingWorld(hosted_people, shared=view.shared)


@pytest.fixture
def signed_in(ui_sharing_world, view):
    """The person in the role of the test's ``view``, created before the browser signs in."""
    return ui_sharing_world.person(view.role)


@pytest.fixture(autouse=True)
def login(page, signed_in):
    """Override tests/ui/conftest.py login: sign in as the person of the test's view."""
    LoginPage(page).login_suppressing_popups(
        signed_in.email,
        signed_in.password,
        signed_in.user_id,
        CredentialsManager.get_required_parameter("FRONTEND_URL"),
    )


@pytest.fixture
def clipboard_permissions(context):
    """Let the page read and write the clipboard so the copied link can be checked."""
    context.grant_permissions(CLIPBOARD_PERMISSIONS)


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.parametrize(
    "view", SHARE_MANAGER_VIEWS, ids=[item.id for item in SHARE_MANAGER_VIEWS]
)
@pytest.mark.hosted_applications
@pytest.mark.ui
def test_manager_who_is_not_the_creator_is_offered_share_and_sees_who_has_access(
    page, ui_sharing_world, view
):
    # @case hosted-app-managers-share_TC_010
    world = ui_sharing_world
    grantee = world.people.user()
    world.creator.service.share_with_users(world.app_id, [grantee.user_id])

    applications = HostedApplicationsPage(page).open_collection(
        view.collection, world.app_name
    )
    applications.open_card_menu(world.app_name)
    applications.should_offer_menu_items(SHARE_MENU_ITEM)
    applications.choose_menu_item(SHARE_MENU_ITEM)
    HostedShareDialog(page, world.app_name).should_be_open().should_list(grantee.email)

    details = HostedApplicationDetailsPage(page).open(world.app_id)
    details.should_list_shared_with(grantee.email)
    details.open_overflow_menu(world.app_name)
    details.should_offer_menu_items(SHARE_MENU_ITEM)

    HostedApplicationViewerPage(page).open(world.app_id).should_offer_share()


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.parametrize(
    "view", MODERATOR_VIEWS, ids=[item.id for item in MODERATOR_VIEWS]
)
@pytest.mark.hosted_applications
@pytest.mark.ui
def test_platform_admin_menus_offer_suspend_and_no_revoke_share_link(
    page, ui_sharing_world, view
):
    # @case hosted-app-managers-share_TC_010
    world = ui_sharing_world
    world.creator.service.create_share_link(world.app_id)

    applications = HostedApplicationsPage(page).open_collection(
        view.collection, world.app_name
    )
    applications.open_card_menu(world.app_name)
    applications.should_offer_menu_items(SUSPEND_MENU_ITEM)
    applications.should_not_offer_menu_item(REVOKE_LINK_MENU_ITEM)

    details = HostedApplicationDetailsPage(page).open(world.app_id)
    details.open_overflow_menu(world.app_name)
    details.should_offer_menu_items(SUSPEND_MENU_ITEM)
    details.should_not_offer_menu_item(REVOKE_LINK_MENU_ITEM)

    viewer = HostedApplicationViewerPage(page).open(world.app_id)
    viewer.open_actions_menu()
    viewer.should_offer_menu_items(SUSPEND_MENU_ITEM)
    viewer.should_not_offer_menu_item(REVOKE_LINK_MENU_ITEM)


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.parametrize(
    "view", SHARE_DIALOG_VIEWS, ids=[item.id for item in SHARE_DIALOG_VIEWS]
)
@pytest.mark.hosted_applications
@pytest.mark.ui
def test_manager_who_is_not_the_creator_manages_people_and_the_link_in_the_share_dialog(
    page, clipboard_permissions, ui_sharing_world, view
):
    # @case hosted-app-managers-share_TC_011
    world = ui_sharing_world
    person = world.people.user()
    latecomer = world.people.user()
    reviewer = world.people.user(admin=True)
    details = HostedApplicationDetailsPage(page).open(world.app_id)
    details.open_overflow_menu(world.app_name).choose_menu_item(SHARE_MENU_ITEM)
    dialog = HostedShareDialog(page, world.app_name).should_be_open()

    dialog.search(person.email).should_offer(person.name)
    dialog.search(world.creator.email).should_offer_nobody_instead_of(person.name)

    dialog.add(person.email, person.name).should_be_closed_after_sharing()
    assert_that(
        world.shared_with_ids(),
        contains_exactly(person.user_id),
        "the platform holds the grant the dialog made",
    )

    details.open_overflow_menu(world.app_name).choose_menu_item(SHARE_MENU_ITEM)
    dialog.should_list(person.email)
    dialog.remove(person.name).should_not_list(person.email).should_confirm_removal()
    assert_that(
        world.shared_with_ids(), empty(), "the platform no longer holds the grant"
    )

    dialog.copy_link().should_have_link()
    token = world.live_link_token()
    assert_that(token, not_none(), "copying created the application's share link")
    dialog.should_have_copied(SHARE_LINK_ROUTE + token)

    dialog.revoke_link().should_have_no_link()
    assert_that(world.live_link_token(), is_(None), "the platform has no live link")

    reviewer.service.suspend_application(world.app_id, SHARING_SUSPENSION_REASON)
    dialog.add(latecomer.email, latecomer.name).should_show_error(
        SHARE_SUSPENDED_MESSAGE
    )
    assert_that(world.shared_with_ids(), empty(), "the refused share granted nobody")


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.parametrize(
    "view", NON_MANAGER_VIEWS, ids=[item.id for item in NON_MANAGER_VIEWS]
)
@pytest.mark.hosted_applications
@pytest.mark.ui
def test_non_manager_is_offered_no_share_and_sees_the_signed_in_members_hint(
    page, ui_sharing_world, view
):
    # @case hosted-app-managers-share_TC_012
    world = ui_sharing_world

    applications = HostedApplicationsPage(page).open_collection(
        view.collection, world.app_name
    )
    applications.open_card_menu(world.app_name)
    applications.should_not_offer_menu_item(SHARE_MENU_ITEM)

    details = HostedApplicationDetailsPage(page).open(world.app_id)
    details.should_offer_no_actions(world.app_name)
    details.should_not_show_shared_with()
    details.should_show_access_hint(view.hint)


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.parametrize(
    "view", PRIVATE_APP_HINT_VIEWS, ids=[item.id for item in PRIVATE_APP_HINT_VIEWS]
)
@pytest.mark.hosted_applications
@pytest.mark.ui
def test_access_hint_of_a_private_unshared_application_follows_the_readers_role(
    page, ui_sharing_world, view
):
    # @case hosted-app-managers-share_TC_013
    HostedApplicationDetailsPage(page).open(
        ui_sharing_world.app_id
    ).should_show_access_hint(view.hint)
