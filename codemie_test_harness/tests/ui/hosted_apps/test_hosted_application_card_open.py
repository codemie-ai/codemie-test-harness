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

"""UI tests for opening a hosted application from its card, as the application's owner.

The browser session is the primary test account (tests/ui/conftest.py `login`), which owns
every application the tests create. The view-only side is in
test_hosted_application_card_open_view_only.py.
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.hosted_apps.hosted_application_details_page import (
    HostedApplicationDetailsPage,
)
from codemie_test_harness.tests.ui.pageobject.hosted_apps.hosted_application_viewer_page import (
    HostedApplicationViewerPage,
)
from codemie_test_harness.tests.ui.pageobject.hosted_apps.hosted_applications_page import (
    HostedApplicationsPage,
)
from codemie_test_harness.tests.ui.test_data.hosted_applications_test_data import (
    CARD_ACTIVATIONS,
    DETAILS_LAUNCH_BUTTON_STATES,
    NEXT_STEP_BUTTONS,
)
from codemie_test_harness.tests.utils.hosted_application_utils import (
    HostedVersionState,
)


@pytest.mark.parametrize("activation", CARD_ACTIVATIONS)
@pytest.mark.ui
def test_open_viewer_by_activating_card(hosted_app, page, activation):
    """@case clicking-a-hosted-app-opens_TC_001"""
    app = hosted_app(HostedVersionState.ACTIVE)

    apps_page = HostedApplicationsPage(page).open_my_apps()
    apps_page.should_name_card_for_opening(app.name)
    apps_page.activate_card(app.name, activation)

    HostedApplicationViewerPage(page).should_be_open(app.id, app.name)


@pytest.mark.ui
def test_card_menu_runs_only_its_action_and_does_not_open_viewer(hosted_app, page):
    """@case clicking-a-hosted-app-opens_TC_003"""
    app = hosted_app(HostedVersionState.ACTIVE)

    apps_page = HostedApplicationsPage(page).open_my_apps()
    menu = apps_page.open_card_menu(app.name)
    apps_page.should_still_list_card(app.name)
    menu.choose_item("Details")

    HostedApplicationDetailsPage(page).should_be_open(app.id)


@pytest.mark.ui
def test_card_click_without_active_version_opens_details_as_manager(hosted_app, page):
    """@case clicking-a-hosted-app-opens_TC_004"""
    app = hosted_app(HostedVersionState.NONE)

    apps_page = HostedApplicationsPage(page).open_my_apps()
    apps_page.click_card(app.name, openable=False)

    HostedApplicationDetailsPage(page).should_be_open(app.id)


@pytest.mark.parametrize("state, label", NEXT_STEP_BUTTONS)
@pytest.mark.ui
def test_manager_next_step_button_leads_to_details(hosted_app, page, state, label):
    """@case clicking-a-hosted-app-opens_TC_005"""
    app = hosted_app(state)

    apps_page = HostedApplicationsPage(page).open_my_apps()
    apps_page.should_show_next_step_button(app.name, label)
    details_page = apps_page.click_next_step_button(app.name, label)

    details_page.should_be_open(app.id)


@pytest.mark.ui
def test_card_menu_details_item_opens_details_as_owner(hosted_app, page):
    """@case clicking-a-hosted-app-opens_TC_006"""
    app = hosted_app(HostedVersionState.ACTIVE)

    apps_page = HostedApplicationsPage(page).open_my_apps()
    menu = apps_page.open_card_menu(app.name)
    menu.should_list_item("Details")
    menu.choose_item("Details")

    HostedApplicationDetailsPage(page).should_be_open(app.id)


@pytest.mark.ui
def test_details_and_viewer_menus_have_no_second_details_entry(hosted_app, page):
    """@case clicking-a-hosted-app-opens_TC_007"""
    app = hosted_app(HostedVersionState.ACTIVE)

    apps_page = HostedApplicationsPage(page).open_my_apps()
    details_page = apps_page.open_details_from_card_menu(app.name)
    details_page.should_be_open(app.id)
    details_menu = details_page.open_more_options_menu(app.name)
    details_menu.should_not_list_item("Details")
    details_menu.close()

    viewer_page = details_page.click_launch_button()
    viewer_page.should_be_open(app.id, app.name)
    viewer_menu = viewer_page.open_actions_menu()
    viewer_menu.should_list_one_item_matching("Manage application|Application details")
    viewer_menu.should_not_list_item("Details")


@pytest.mark.ui
def test_openable_card_has_no_launch_button_and_menu_open_item_opens_viewer(
    hosted_app, page
):
    """@case clicking-a-hosted-app-opens_TC_008"""
    app = hosted_app(HostedVersionState.ACTIVE)

    apps_page = HostedApplicationsPage(page).open_my_apps()
    apps_page.should_have_only_card_and_menu_buttons(app.name)
    menu = apps_page.open_card_menu(app.name)
    menu.should_have_item_enabled("Open")
    menu.choose_item("Open")

    HostedApplicationViewerPage(page).should_be_open(app.id, app.name)


@pytest.mark.parametrize("state, enabled", DETAILS_LAUNCH_BUTTON_STATES)
@pytest.mark.ui
def test_details_page_open_button_state_follows_active_version(
    hosted_app, page, state, enabled
):
    """@case clicking-a-hosted-app-opens_TC_010"""
    app = hosted_app(state)

    apps_page = HostedApplicationsPage(page).open_my_apps()
    details_page = apps_page.open_details_from_card_menu(app.name)

    details_page.should_be_open(app.id)
    details_page.should_have_launch_button(enabled)
