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

"""UI tests for the cards of hosted applications, the buttons that open them, and the keyboard
route to them."""

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
def test_keyboard_user_reaches_the_view_button_of_a_card_and_opens_the_viewer(
    page, ui_live_app
):
    # @case hosted-applications-upload-share-view_TC_020
    app, artifact = ui_live_app
    applications = HostedApplicationsPage(page).open_my_apps()

    applications.focus_view_button_by_keyboard(app.name)
    applications.should_have_focus_on_view_button(app.name)
    applications.press_enter()

    viewer = HostedApplicationViewerPage(page)
    viewer.should_be_on_view_route(app.id)
    viewer.should_show_content(app.name, artifact.marker)


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.ui
def test_keyboard_user_opens_the_upload_dialog_and_reaches_its_labelled_controls(
    page, ui_live_app
):
    # @case hosted-applications-upload-share-view_TC_020
    app, _ = ui_live_app
    details = HostedApplicationDetailsPage(page).open(app.id)

    details.focus_by_keyboard(details.upload_version_button)
    details.press_enter()

    details.should_show_upload_dialog()
    details.should_reach_upload_dialog_controls_by_keyboard()


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.ui
def test_view_button_on_the_card_opens_the_embedded_viewer_with_the_application(
    page, ui_live_app
):
    # @case hosted-applications-upload-share-view_TC_021
    app, artifact = ui_live_app
    applications = HostedApplicationsPage(page).open_my_apps()
    applications.should_show_open_buttons(app.name)

    applications.click_view(app.name)

    viewer = HostedApplicationViewerPage(page)
    viewer.should_be_on_view_route(app.id)
    viewer.should_show_content(app.name, artifact.marker)


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.ui
def test_open_in_new_tab_on_the_card_opens_the_application(page, ui_live_app):
    # @case hosted-applications-upload-share-view_TC_021
    app, artifact = ui_live_app
    applications = HostedApplicationsPage(page).open_my_apps()

    new_tab = applications.open_in_new_tab(app.name)

    new_tab.should_show_content(artifact.marker)
    new_tab.should_not_show_error_page()


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.ui
def test_open_in_new_tab_on_the_details_page_opens_the_application(page, ui_live_app):
    # @case hosted-applications-upload-share-view_TC_021
    app, artifact = ui_live_app
    details = HostedApplicationDetailsPage(page).open(app.id)
    details.should_show_open_buttons_enabled()

    new_tab = details.open_in_new_tab()

    new_tab.should_show_content(artifact.marker)
    new_tab.should_not_show_error_page()


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.ui
def test_open_in_new_tab_in_the_viewer_opens_the_application(page, ui_live_app):
    # @case hosted-applications-upload-share-view_TC_021
    app, artifact = ui_live_app
    viewer = HostedApplicationViewerPage(page).open(app.id)
    viewer.should_show_content(app.name, artifact.marker)

    new_tab = viewer.open_in_new_tab()

    new_tab.should_show_content(artifact.marker)
    new_tab.should_not_show_error_page()


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.ui
def test_open_in_new_tab_in_a_version_preview_opens_that_version(
    page, ui_unreleased_app
):
    # @case hosted-applications-upload-share-view_TC_021
    app, artifact, version = ui_unreleased_app
    viewer = HostedApplicationViewerPage(page).open_preview(app.id, version.id)
    viewer.should_show_content(app.name, artifact.marker)

    new_tab = viewer.open_in_new_tab()

    new_tab.should_show_content(artifact.marker)
    new_tab.should_not_show_error_page()


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.ui
def test_card_without_a_live_version_shows_its_statuses_and_a_clickable_activate_button(
    page, ui_unreleased_app
):
    # @case hosted-applications-upload-share-view_TC_022
    app, _, _ = ui_unreleased_app
    applications = HostedApplicationsPage(page).open_my_apps()

    applications.should_show_card_without_live_version(app.name)
    applications.click_activate_version(app.name)

    HostedApplicationDetailsPage(page).should_be_on_details_route(app.id)
