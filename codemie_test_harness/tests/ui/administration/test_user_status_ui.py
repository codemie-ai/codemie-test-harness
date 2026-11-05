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

"""UI tests: deactivating and reactivating users from Administration > Users management.

State is seeded and verified through the API; the browser drives only the status change itself.
Users are disposable and removed by their fixture, so a failed run leaves nothing deactivated.
"""

import pytest
from hamcrest import assert_that, equal_to

from codemie_test_harness.tests.ui.pageobject.administration.user_management_page import (
    UserManagementPage,
)


@pytest.mark.user
@pytest.mark.ui
def test_deactivate_user_from_user_management_with_confirmation(
    page, user_utils, disposable_user
):
    # @case platform-admins-deactivate-reactivate-users_TC_014
    email, user_id, _ = disposable_user
    display_name = user_utils.get_display_name(user_id)
    users_page = UserManagementPage(page).navigate_to()
    users_page.search_user(email)

    users_page.choose_status_action(email, "deactivate")
    users_page.should_see_status_confirmation("deactivate", display_name)
    users_page.cancel_status_change("deactivate")

    users_page.should_not_see_deactivated_badge(email)
    assert_that(
        user_utils.get_admin_user(user_id).is_active,
        equal_to(True),
        "Cancelling the dialog must leave the user active",
    )

    users_page.choose_status_action(email, "deactivate")
    users_page.confirm_status_change("deactivate")

    users_page.should_see_status_toast("deactivate")
    users_page.should_see_deactivated_badge(email)
    assert_that(
        user_utils.get_admin_user(user_id).is_active,
        equal_to(False),
        "Confirming the dialog must deactivate the user",
    )


@pytest.mark.user
@pytest.mark.ui
def test_reactivate_user_from_user_management_with_confirmation(
    page, user_utils, disposable_user
):
    # @case platform-admins-deactivate-reactivate-users_TC_015
    email, user_id, _ = disposable_user
    display_name = user_utils.get_display_name(user_id)
    user_utils.deactivate_user(user_id)
    users_page = UserManagementPage(page).navigate_to()
    users_page.search_user(email)

    users_page.choose_status_action(email, "reactivate")
    users_page.should_see_status_confirmation("reactivate", display_name)
    users_page.cancel_status_change("reactivate")

    users_page.should_see_deactivated_badge(email)
    assert_that(
        user_utils.get_admin_user(user_id).is_active,
        equal_to(False),
        "Cancelling the dialog must leave the user deactivated",
    )

    users_page.choose_status_action(email, "reactivate")
    users_page.confirm_status_change("reactivate")

    users_page.should_see_status_toast("reactivate")
    users_page.should_not_see_deactivated_badge(email)
    users_page.should_offer_row_action(email, "Deactivate user")
    assert_that(
        user_utils.get_admin_user(user_id).is_active,
        equal_to(True),
        "Confirming the dialog must reactivate the user",
    )


@pytest.mark.user
@pytest.mark.ui
def test_user_management_shows_backend_error_when_status_change_fails(
    page, user_utils, disposable_user
):
    # @case platform-admins-deactivate-reactivate-users_TC_016
    email, user_id, _ = disposable_user
    user_utils.deactivate_user(user_id)
    users_page = UserManagementPage(page).navigate_to()
    users_page.search_user(email)
    users_page.should_see_deactivated_badge(email)

    user_utils.reactivate_user(user_id)
    users_page.choose_status_action(email, "reactivate")
    users_page.confirm_status_change("reactivate")

    users_page.should_see_error_toast_with_text("User is already active")


@pytest.mark.user
@pytest.mark.ui
def test_user_management_hides_deactivate_on_own_row(page, user_utils):
    # @case platform-admins-deactivate-reactivate-users_TC_017
    own_email = user_utils.get_about_me().email
    users_page = UserManagementPage(page).navigate_to()
    users_page.search_user(own_email)

    users_page.should_not_offer_row_action(own_email, "Deactivate user")
