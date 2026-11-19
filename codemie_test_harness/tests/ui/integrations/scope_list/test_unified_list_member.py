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

"""UI tests for the Integrations page as a plain member: only own user integrations, no Scope
filter, no project scope on the create form."""

import pytest

from codemie_sdk.models.integration import IntegrationType
from codemie_test_harness.tests.ui.pageobject.integrations.integration_form_page import (
    IntegrationFormPage,
)
from codemie_test_harness.tests.ui.pageobject.integrations.integrations_list_page import (
    IntegrationsListPage,
)
from codemie_test_harness.tests.ui.test_data.unified_integrations_ui_test_data import (
    DIAL,
    DIAL_MEMBER_HINT,
    PROJECT_ADMINS_ONLY_REASON,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.integration_utils import IntegrationUtils


@pytest.fixture
def ui_login_user(platform_user):
    """The browser signs in as a plain member."""
    return platform_user


# @case unified-integrations-list_TC_009
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.oss_standalone
def test_member_sees_only_own_user_integrations_and_no_scope_filter(
    page,
    platform_user,
    second_platform_user,
    seed_integration,
    scoped_integrations,
):
    own_alias = get_random_name()
    scoped_integrations.create(
        IntegrationUtils(platform_user.client),
        IntegrationType.USER,
        platform_user.email,
        own_alias,
    )
    scoped_integrations.create(
        IntegrationUtils(second_platform_user.client),
        IntegrationType.USER,
        second_platform_user.email,
        get_random_name(),
    )
    seed_integration(IntegrationType.USER)
    seed_integration(IntegrationType.PROJECT)
    list_page = IntegrationsListPage(page)

    list_page.navigate_to()

    list_page.should_show_rows([own_alias])
    list_page.should_not_offer_scope_filter()
    list_page.should_offer_global_filter()


# @case unified-integrations-list_TC_015
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.oss_standalone
def test_member_sees_project_scope_and_dial_disabled_on_the_create_form(page):
    form_page = IntegrationFormPage(page)

    form_page.navigate_to()

    form_page.should_have_project_scope_disabled(PROJECT_ADMINS_ONLY_REASON)

    form_page.open_credential_type_list()

    form_page.should_disable_credential_type(DIAL, DIAL_MEMBER_HINT)
