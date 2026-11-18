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

"""UI tests for the cards of hosted applications as a view-only recipient.

tests/ui/conftest.py logs the browser in as the primary account, which owns the applications.
This module overrides that login: the browser session is a fresh platform user the owner shared
each application with, so the user can view an application but not manage it.
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.hosted_applications.hosted_application_details_page import (
    HostedApplicationDetailsPage,
)
from codemie_test_harness.tests.ui.pageobject.hosted_applications.hosted_application_viewer_page import (
    HostedApplicationViewerPage,
)
from codemie_test_harness.tests.ui.pageobject.hosted_applications.hosted_applications_page import (
    NO_ACTIVE_VERSION,
    HostedApplicationsPage,
)
from codemie_test_harness.tests.ui.pageobject.login_page import LoginPage
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager

CAPABILITY = "features:hostedApplications"


@pytest.fixture(autouse=True)
def login(page, platform_user):
    """Override tests/ui/conftest.py login: authenticate as the view-only recipient."""
    LoginPage(page).login_suppressing_popups(
        platform_user.email,
        platform_user.password,
        platform_user.user_id,
        CredentialsManager.get_parameter("FRONTEND_URL", ""),
    )


@pytest.fixture
def share_with_recipient(ui_owner_apps, platform_user):
    """Share an application of the owner with the recipient; return the application."""

    def share(app):
        ui_owner_apps.service.share_with_users(app.id, [platform_user.user_id])
        return app

    return share


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.ui
def test_view_only_user_clicking_the_card_opens_the_viewer(
    page, ui_live_app, share_with_recipient
):
    # @case clicking-a-hosted-app-opens_TC_002
    app, artifact = ui_live_app
    share_with_recipient(app)
    applications = HostedApplicationsPage(page).open_shared_with_me()

    applications.should_name_card_for_opening(app.name)
    applications.click_card(app.name)

    viewer = HostedApplicationViewerPage(page)
    viewer.should_be_on_view_route(app.id)
    viewer.should_show_content(app.name, artifact.marker)


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.ui
def test_view_only_user_clicking_the_card_without_a_live_version_opens_its_details(
    page, ui_empty_app, share_with_recipient
):
    # @case clicking-a-hosted-app-opens_TC_004
    app = share_with_recipient(ui_empty_app)
    applications = HostedApplicationsPage(page).open_shared_with_me()

    applications.click_card_without_live_version(app.name)

    HostedApplicationDetailsPage(page).should_be_on_details_route(app.id)


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.ui
def test_card_menu_details_item_opens_details_for_a_view_only_user(
    page, ui_live_app, share_with_recipient
):
    # @case clicking-a-hosted-app-opens_TC_006
    app, _ = ui_live_app
    share_with_recipient(app)
    applications = HostedApplicationsPage(page).open_shared_with_me()

    menu = applications.open_card_menu(app.name)
    menu.should_list_item("Details")
    menu.choose_item("Details")

    HostedApplicationDetailsPage(page).should_be_on_details_route(app.id)


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.ui
def test_view_only_card_without_a_live_version_is_marked_and_cannot_open(
    page, ui_empty_app, share_with_recipient
):
    # @case clicking-a-hosted-app-opens_TC_009
    app = share_with_recipient(ui_empty_app)
    applications = HostedApplicationsPage(page).open_shared_with_me()

    applications.should_show_no_active_version_badge(app.name)
    applications.should_name_card_without_open(app.name)
    applications.should_have_only_card_and_menu_buttons(app.name)
    menu = applications.open_card_menu(app.name)
    menu.should_have_item_disabled_with_tooltip("Open", NO_ACTIVE_VERSION)
