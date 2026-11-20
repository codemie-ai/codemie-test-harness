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

"""UI tests for the Project scope of the New Integration form: only administered projects, no
Global, and a scope change clears the project and Global. The signed-in user administers one
project and is a plain member of a second."""

import pytest
from hamcrest import assert_that, has_item, is_not

from codemie_test_harness.tests.ui.pageobject.integrations.integration_form_page import (
    IntegrationFormPage,
)
from codemie_test_harness.tests.ui.test_data.unified_integrations_ui_test_data import (
    PROJECT_CLEARED_NOTE,
    SCOPE_PROJECT,
)
from codemie_test_harness.tests.utils.user_utils import UserUtils


@pytest.fixture
def ui_login_user(project_admin_user, default_project_member, user_utils):
    """The project admin of project A, made a plain member of project B before signing in."""
    user_utils.assign_user_to_project(
        project_admin_user.user_id, default_project_member.project_b
    )
    return project_admin_user


@pytest.fixture
def administered_projects(fresh_project_admin_client, default_project_member):
    """Projects the signed-in user administers, as their profile lists them.

    The selector at Project scope offers the user's projects that appear in the profile's
    administered list; a personal project is a membership without the admin flag, so it is
    not among them.
    """
    me = UserUtils(fresh_project_admin_client).get_about_me()
    names = [p.name for p in me.projects if p.name in me.applications_admin]
    assert_that(names, has_item(default_project_member.project_a))
    assert_that(names, is_not(has_item(me.email)))
    return names


# @case unified-integrations-list_TC_014
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.prod_regression
@pytest.mark.oss_standalone
def test_project_scope_offers_only_administered_projects_and_a_scope_change_clears_the_project(
    page, default_project_member, administered_projects
):
    member_only = default_project_member.project_b
    form_page = IntegrationFormPage(page)
    form_page.navigate_to("scope=user")
    form_page.should_offer_global_switch()
    form_page.pick_project(member_only)
    form_page.switch_global_on()

    form_page.select_scope(SCOPE_PROJECT)

    form_page.should_have_project_cleared(member_only)
    form_page.should_show_note(PROJECT_CLEARED_NOTE)
    form_page.should_not_offer_global_switch()

    form_page.open_project_list()

    form_page.should_offer_exactly_projects(administered_projects)
    form_page.should_not_offer_project(member_only)
