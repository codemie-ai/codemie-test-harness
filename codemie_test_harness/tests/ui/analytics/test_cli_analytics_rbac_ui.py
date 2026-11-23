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

"""Real browser role regression for the AI Attribution tab and its sections."""

import pytest
from codemie_test_harness.tests.test_data.cli_analytics_rbac_test_data import ROLES
from codemie_test_harness.tests.ui.pageobject.analytics.analytics_page import (
    AnalyticsPage,
)
from codemie_test_harness.tests.ui.pageobject.analytics.cli_analytics_page import (
    CLIAnalyticsPage,
)
from codemie_test_harness.tests.ui.pageobject.login_page import LoginPage
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager


@pytest.fixture
def login(page, cli_rbac_world, role):
    """Override the default UI login with this exact disposable role."""
    user = cli_rbac_world.users[role]
    LoginPage(page).login_suppressing_popups(
        user.email,
        user.password,
        user.user_id,
        CredentialsManager.get_parameter("FRONTEND_URL"),
    )


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.cli_analytics
@pytest.mark.ui
def test_every_role_opens_the_tab_and_loads_all_sections(page, role):
    dashboard = AnalyticsPage(page).navigate_to().open_cli_analytics()
    dashboard.should_have_sections()
    dashboard.should_load_all_sections()


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.cli_analytics
@pytest.mark.ui
def test_every_role_opens_ai_attribution_by_direct_url(page, role):
    dashboard = CLIAnalyticsPage(page).navigate_to()
    dashboard.should_be_visible()
    dashboard.should_have_loaded_section(CLIAnalyticsPage.DEFAULT_SECTION)
