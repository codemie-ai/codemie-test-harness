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

"""UI tests: the project Members page offers no 'Reset budget usage' control.

The per-member 'Budget Override' modal and the bulk 'Budget Override — N users' modal
keep their Cancel / Save Override actions but expose no reset-usage button, for the
project admin and for a maintainer (who used to see it).

The ``login`` fixture is overridden so the browser authenticates as the role under test
(``acting_role_credentials``, indirect parametrization); the project, budget group and
members come from the fixtures of conftest.py.
"""

import pytest
from hamcrest import assert_that, equal_to, is_not

from codemie_test_harness.tests.ui.pageobject.administration.project_details_page import (
    ProjectDetailsPage,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_members_budget_section import (
    ProjectMembersBudgetSection,
)
from codemie_test_harness.tests.ui.pageobject.login_page import LoginPage
from codemie_test_harness.tests.ui.test_data.budget_member_override_ui_test_data import (
    make_member_override_data,
)
from codemie_test_harness.tests.utils.admin_project_budget_utils import (
    AdminProjectBudgetUtils,
)
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager

ACTING_ROLES = [
    pytest.param("project_admin", id="project admin"),
    pytest.param("maintainer", id="maintainer"),
]


@pytest.fixture
def acting_role_credentials(request, project_admin_setup):
    """(email, password) of the role the browser logs in as."""
    if request.param == "maintainer":
        maintainer = request.getfixturevalue("maintainer_user")
        return maintainer.email, maintainer.password
    _, _, email, password = project_admin_setup
    return email, password


@pytest.fixture(autouse=True)
def login(page, acting_role_credentials):
    """Override conftest.py login — authenticate as the role under test."""
    email, password = acting_role_credentials
    user_id = get_client(username=email, password=password).users.about_me().user_id
    LoginPage(page).login_suppressing_popups(
        email,
        password,
        user_id,
        CredentialsManager.get_parameter("FRONTEND_URL", ""),
    )


# @case remove-reset-budget-usage_TC_001
@pytest.mark.parametrize("acting_role_credentials", ACTING_ROLES, indirect=True)
@pytest.mark.budget
@pytest.mark.ui
def test_members_page_has_no_reset_budget_usage_control(
    page,
    project_admin_setup,
    project_admin_setup_client,
    member_override_ui_ready,
    platform_budget_id,
    acting_role_credentials,
):
    project_name, _, pa_email, _ = project_admin_setup
    member_email, _, member_id = member_override_ui_ready
    typed_limit = make_member_override_data().hard_limit
    budget_utils = AdminProjectBudgetUtils(project_admin_setup_client)
    details_page = ProjectDetailsPage(page)
    members = ProjectMembersBudgetSection(page)

    details_page.navigate_to(project_name)
    details_page.should_be_on_project_details_page(project_name)
    details_page.open_members_tab()
    members.should_show_allocation_column()
    members.should_show_override_control(member_email)
    allocation_before = members.allocation_text(member_email)
    stored_before = budget_utils.get_member_allocation(platform_budget_id, member_id)

    modal = members.open_override_modal(member_email)
    modal.should_not_offer_reset_budget_usage()
    modal.should_offer_cancel_save_and_reason()
    modal.set_hard_limit(typed_limit)
    modal.cancel()

    modal.should_be_closed()
    members.should_show_allocation_text(member_email, allocation_before)
    stored_after = budget_utils.get_member_allocation(platform_budget_id, member_id)
    assert_that(
        stored_after["allocation_mode"],
        equal_to(stored_before["allocation_mode"]),
        "Cancel must not change the member's allocation mode",
    )
    assert_that(
        stored_after["allocated_max_budget"],
        equal_to(stored_before["allocated_max_budget"]),
        "Cancel must not persist the typed hard limit",
    )
    assert_that(
        stored_after["allocation_mode"],
        is_not(equal_to("fixed")),
        "Cancel must not create a fixed override",
    )

    members.select_members(pa_email, member_email)
    bulk_modal = members.open_bulk_override_modal(2)
    bulk_modal.should_not_offer_reset_budget_usage()
    bulk_modal.should_offer_cancel_and_save()
    bulk_modal.cancel()
    bulk_modal.should_be_closed()
