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

"""UI tests for the categories of hosted applications: the create and edit forms, the publish
dialog, the details page and the category filter of the catalog.

The applications are created through the API, or through the form under test, and read back
through the API; the application and any category made for the test are deleted afterwards.
"""

import pytest
from hamcrest import assert_that, contains_inanyorder, equal_to, has_length, is_

from codemie_test_harness.tests.test_data.hosted_application_category_test_data import (
    CATEGORY_REQUIRED_TEXT,
    PUBLISHED_NEEDS_ONE_TEXT,
    UNKNOWN_CATEGORY_TEXT,
)
from codemie_test_harness.tests.ui.pageobject.hosted_applications.hosted_application_details_page import (
    HostedApplicationDetailsPage,
)
from codemie_test_harness.tests.ui.pageobject.hosted_applications.hosted_application_form_page import (
    HostedApplicationFormPage,
)
from codemie_test_harness.tests.ui.pageobject.hosted_applications.hosted_applications_page import (
    HostedApplicationsPage,
)
from codemie_test_harness.tests.ui.pageobject.hosted_applications.hosted_publish_dialog import (
    MENU_ITEM as PUBLISH_MENU_ITEM,
    HostedPublishDialog,
)
from codemie_test_harness.tests.utils.hosted_application_utils import category_ids

CAPABILITY = "features:hostedApplications"
DESCRIPTION = "Application created by an automated test"
CATALOG_COLLECTIONS = ["mine", "marketplace"]


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.ui
def test_publish_dialog_starts_with_the_apps_categories_and_publishes_the_picked_ones(
    page, ui_owner_apps, ui_project, hosted_categories
):
    # @case hosted-app-categories_TC_014
    first, second, third = hosted_categories
    app = ui_owner_apps.create_app(ui_project, categories=[first.id, second.id])
    applications = HostedApplicationsPage(page).open_collection_searched_by(
        "mine", app.name
    )

    applications.open_card_menu(app.name).choose_item(PUBLISH_MENU_ITEM)
    dialog = HostedPublishDialog(page).should_be_open()
    dialog.categories.should_have_picked([first.name, second.name])
    dialog.categories.toggle([second.name, third.name])
    dialog.categories.should_have_picked([first.name, third.name])
    dialog.publish().should_be_closed()

    published = ui_owner_apps.get_app(app.id)
    assert_that(published.is_global, is_(True), "the app is published")
    assert_that(
        category_ids(published),
        contains_inanyorder(first.id, third.id),
        "the app carries the final selection",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.ui
def test_publish_dialog_with_no_category_says_one_is_required_and_the_app_stays_unpublished(
    page, ui_owner_apps, ui_project
):
    # @case hosted-app-categories_TC_015
    app = ui_owner_apps.create_app(ui_project)
    applications = HostedApplicationsPage(page).open_collection_searched_by(
        "mine", app.name
    )
    applications.open_card_menu(app.name).choose_item(PUBLISH_MENU_ITEM)
    dialog = HostedPublishDialog(page).should_be_open()

    dialog.publish()

    dialog.should_show_alert(CATEGORY_REQUIRED_TEXT).should_be_open()
    assert_that(
        ui_owner_apps.get_app(app.id).is_global, is_(False), "the app is not published"
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.ui
def test_fourth_category_cannot_be_picked_in_the_create_form(
    page, hosted_categories, hosted_temp_category
):
    # @case hosted-app-categories_TC_016
    fourth = hosted_temp_category()
    picked = [category.name for category in hosted_categories]
    form = HostedApplicationFormPage(page).open_create()

    form.categories.toggle([*picked, fourth.name])

    form.should_refuse_a_fourth_category()
    form.categories.should_have_picked(picked)
    form.categories.should_not_have_picked(fourth.name)


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.ui
def test_fourth_category_cannot_be_picked_in_the_publish_dialog(
    page, ui_owner_apps, ui_project, hosted_categories, hosted_temp_category
):
    # @case hosted-app-categories_TC_016
    fourth = hosted_temp_category()
    picked = [category.name for category in hosted_categories]
    app = ui_owner_apps.create_app(ui_project)
    applications = HostedApplicationsPage(page).open_collection_searched_by(
        "mine", app.name
    )
    applications.open_card_menu(app.name).choose_item(PUBLISH_MENU_ITEM)
    dialog = HostedPublishDialog(page).should_be_open()

    dialog.categories.toggle([*picked, fourth.name])

    dialog.categories.should_have_picked(picked)
    dialog.categories.should_not_have_picked(fourth.name)
    dialog.should_show_no_alert()


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.ui
def test_create_form_creates_an_app_with_the_picked_categories(
    page, ui_owner_apps, ui_new_app_name, hosted_categories
):
    # @case hosted-app-categories_TC_017
    first, second = hosted_categories[:2]
    form = HostedApplicationFormPage(page).open_create()
    form.fill_in(ui_new_app_name, DESCRIPTION)
    form.categories.toggle([first.name, second.name])
    form.categories.should_have_picked([first.name, second.name])

    form.submit().should_have_created_application()

    created = ui_owner_apps.adopt(ui_new_app_name)
    assert_that(created, has_length(1), "one application was created")
    assert_that(
        category_ids(created[0]),
        contains_inanyorder(first.id, second.id),
        "the app carries the two picks",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.ui
def test_edit_form_of_an_unpublished_app_shows_its_categories_and_saves_a_changed_selection(
    page, ui_owner_apps, ui_project, hosted_categories
):
    # @case hosted-app-categories_TC_018
    first, second, third = hosted_categories
    app = ui_owner_apps.create_app(ui_project, categories=[first.id, second.id])
    form = HostedApplicationFormPage(page).open_edit(app.id)
    form.should_not_mark_categories_required()
    form.categories.should_have_picked([first.name, second.name])

    form.categories.toggle([second.name, third.name])
    form.submit().should_be_saved(app.id)

    assert_that(
        category_ids(ui_owner_apps.get_app(app.id)),
        contains_inanyorder(first.id, third.id),
        "the app carries the new selection",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.ui
def test_edit_form_of_a_published_app_requires_a_category_and_refuses_to_save_with_none(
    page, ui_owner_apps, ui_project, hosted_categories
):
    # @case hosted-app-categories_TC_019
    kept = hosted_categories[0]
    app = ui_owner_apps.create_app(ui_project, categories=[kept.id])
    ui_owner_apps.publish(app.id, [kept.id])
    form = HostedApplicationFormPage(page).open_edit(app.id)
    form.should_mark_categories_required()
    form.categories.should_have_picked([kept.name])

    form.categories.toggle([kept.name])
    form.submit()

    form.should_show_categories_error(PUBLISHED_NEEDS_ONE_TEXT)
    form.should_still_be_on_edit_form(app.id)
    reread = ui_owner_apps.get_app(app.id)
    assert_that(reread.is_global, is_(True), "the app is still published")
    assert_that(category_ids(reread), equal_to([kept.id]), "it keeps its category")


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.ui
def test_details_show_the_category_names_and_the_card_does_not(
    page, ui_owner_apps, ui_project, hosted_categories
):
    # @case hosted-app-categories_TC_020
    names = [category.name for category in hosted_categories[:2]]
    app = ui_owner_apps.create_app(
        ui_project, categories=[category.id for category in hosted_categories[:2]]
    )
    applications = HostedApplicationsPage(page).open_collection_searched_by(
        "mine", app.name
    )

    applications.should_show_no_category_names_on_card(app.name, names)

    HostedApplicationDetailsPage(page).open(app.id).should_list_categories(names)


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.parametrize(
    "ui_category_apps", CATALOG_COLLECTIONS, indirect=True, ids=CATALOG_COLLECTIONS
)
@pytest.mark.hosted_applications
@pytest.mark.ui
def test_catalog_category_filter_narrows_the_listed_apps_and_combines_with_the_name_search(
    page, ui_category_apps, hosted_categories
):
    # @case hosted-app-categories_TC_021
    world = ui_category_apps
    first, second = hosted_categories[:2]
    alpha, beta = world.names["alpha"], world.names["beta"]
    applications = HostedApplicationsPage(page).open_collection_searched_by(
        world.collection, world.token
    )
    applications.should_list_cards(world.listed)

    categories = applications.show_category_filter()
    categories.toggle([first.name])
    applications.should_list_cards([alpha])
    applications.should_not_list_cards([beta, world.names["plain"]])

    applications.show_category_filter().toggle([second.name])
    applications.should_list_cards([alpha, beta])
    applications.should_not_list_cards([world.names["plain"]])

    applications.search_by_name(beta)
    applications.should_list_cards([beta])
    applications.should_not_list_cards([alpha])


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.ui
def test_category_refused_by_the_server_is_shown_and_the_dialog_keeps_the_selection(
    page, ui_owner_apps, ui_project, hosted_temp_category, categories_utils
):
    # @case hosted-app-categories_TC_022
    category = hosted_temp_category()
    app = ui_owner_apps.create_app(ui_project)
    applications = HostedApplicationsPage(page).open_collection_searched_by(
        "mine", app.name
    )
    applications.open_card_menu(app.name).choose_item(PUBLISH_MENU_ITEM)
    dialog = HostedPublishDialog(page).should_be_open()
    dialog.categories.toggle([category.name])
    categories_utils.delete_category(category.id)

    dialog.publish()

    dialog.should_show_alert(UNKNOWN_CATEGORY_TEXT).should_be_open()
    dialog.categories.should_have_picked([category.name])
    assert_that(
        ui_owner_apps.get_app(app.id).is_global, is_(False), "the app is not published"
    )
