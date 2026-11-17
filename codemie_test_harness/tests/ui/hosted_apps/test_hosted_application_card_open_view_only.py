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

"""UI tests for opening a hosted application from its card, as a view-only recipient.

tests/ui/conftest.py's autouse `login` authenticates as the primary account, which owns
the applications. This module overrides it so the browser session is a fresh platform
user the owner shared each application with: it can view the application but not manage it.
"""

import os

import pytest

from codemie_test_harness.tests.ui.pageobject.hosted_apps.hosted_application_details_page import (
    HostedApplicationDetailsPage,
)
from codemie_test_harness.tests.ui.pageobject.hosted_apps.hosted_application_viewer_page import (
    HostedApplicationViewerPage,
)
from codemie_test_harness.tests.ui.pageobject.hosted_apps.hosted_applications_page import (
    NO_ACTIVE_VERSION,
    HostedApplicationsPage,
)
from codemie_test_harness.tests.ui.pageobject.login_page import LoginPage
from codemie_test_harness.tests.utils.hosted_application_utils import (
    HostedVersionState,
)


@pytest.fixture(autouse=True)
def login(page, platform_user):
    """Override tests/ui/conftest.py login: authenticate as the view-only recipient."""
    LoginPage(page).login_suppressing_popups(
        platform_user.email,
        platform_user.password,
        platform_user.user_id,
        os.getenv("FRONTEND_URL", ""),
    )


@pytest.fixture
def shared_hosted_app(hosted_app, hosted_application_utils, platform_user):
    """Factory: an application owned by the primary account, shared with the recipient."""

    def _create(state: HostedVersionState):
        app = hosted_app(state)
        hosted_application_utils.share_with_users(app.id, [platform_user.user_id])
        return app

    return _create


@pytest.mark.ui
def test_view_only_card_click_opens_viewer(shared_hosted_app, page):
    """@case clicking-a-hosted-app-opens_TC_002"""
    app = shared_hosted_app(HostedVersionState.ACTIVE)

    apps_page = HostedApplicationsPage(page).open_shared_with_me()
    apps_page.should_name_card_for_opening(app.name)
    apps_page.click_card(app.name)

    HostedApplicationViewerPage(page).should_be_open(app.id, app.name)


@pytest.mark.ui
def test_card_click_without_active_version_opens_details_as_view_only_user(
    shared_hosted_app, page
):
    """@case clicking-a-hosted-app-opens_TC_004"""
    app = shared_hosted_app(HostedVersionState.NONE)

    apps_page = HostedApplicationsPage(page).open_shared_with_me()
    apps_page.click_card(app.name, openable=False)

    HostedApplicationDetailsPage(page).should_be_open(app.id)


@pytest.mark.ui
def test_card_menu_details_item_opens_details_as_view_only_user(
    shared_hosted_app, page
):
    """@case clicking-a-hosted-app-opens_TC_006"""
    app = shared_hosted_app(HostedVersionState.ACTIVE)

    apps_page = HostedApplicationsPage(page).open_shared_with_me()
    menu = apps_page.open_card_menu(app.name)
    menu.should_list_item("Details")
    menu.choose_item("Details")

    HostedApplicationDetailsPage(page).should_be_open(app.id)


@pytest.mark.ui
def test_view_only_card_without_active_version_is_marked_and_cannot_open(
    shared_hosted_app, page
):
    """@case clicking-a-hosted-app-opens_TC_009"""
    app = shared_hosted_app(HostedVersionState.NONE)

    apps_page = HostedApplicationsPage(page).open_shared_with_me()
    apps_page.should_show_no_active_version_badge(app.name)
    apps_page.should_name_card_without_open(app.name)
    apps_page.should_have_only_card_and_menu_buttons(app.name)
    menu = apps_page.open_card_menu(app.name)
    menu.should_have_item_disabled_with_tooltip("Open", NO_ACTIVE_VERSION)
