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

"""UI tests for the More options menu of hosted application cards, as the application's owner."""

import pytest

from codemie_test_harness.tests.ui.pageobject.hosted_applications.hosted_application_details_page import (
    HostedApplicationDetailsPage,
)
from codemie_test_harness.tests.ui.pageobject.hosted_applications.hosted_application_viewer_page import (
    HostedApplicationViewerPage,
)
from codemie_test_harness.tests.ui.pageobject.hosted_applications.hosted_applications_page import (
    HostedApplicationsPage,
)

CAPABILITY = "features:hostedApplications"


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.ui
def test_card_menu_details_item_opens_details_for_the_owner(page, ui_live_app):
    # @case clicking-a-hosted-app-opens_TC_006
    # @case clicking-a-hosted-app-opens_TC_003
    app, _ = ui_live_app
    applications = HostedApplicationsPage(page).open_my_apps()

    menu = applications.open_card_menu(app.name)
    applications.should_be_on_applications_route()
    menu.should_list_item("Details")
    menu.choose_item("Details")

    HostedApplicationDetailsPage(page).should_be_on_details_route(app.id)


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.ui
def test_details_and_viewer_menus_have_no_second_details_entry(page, ui_live_app):
    # @case clicking-a-hosted-app-opens_TC_007
    app, _ = ui_live_app
    applications = HostedApplicationsPage(page).open_my_apps()
    applications.open_card_menu(app.name).choose_item("Details")
    details = HostedApplicationDetailsPage(page)
    details.should_be_on_details_route(app.id)

    details_menu = details.open_more_options_menu(app.name)
    details_menu.should_list_items_matching("details", [])
    details_menu.close()
    details.click_open()

    viewer = HostedApplicationViewerPage(page)
    viewer.should_be_on_view_route(app.id)
    viewer_menu = viewer.open_actions_menu()
    viewer_menu.should_list_items_matching(
        "details|manage application", ["Manage application"]
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.ui
def test_openable_card_has_no_launch_button_and_its_menu_open_item_opens_the_viewer(
    page, ui_live_app
):
    # @case clicking-a-hosted-app-opens_TC_008
    app, _ = ui_live_app
    applications = HostedApplicationsPage(page).open_my_apps()

    applications.should_have_only_card_and_menu_buttons(app.name)
    menu = applications.open_card_menu(app.name)
    menu.should_have_item_enabled("Open")
    menu.choose_item("Open")

    HostedApplicationViewerPage(page).should_be_on_view_route(app.id)
