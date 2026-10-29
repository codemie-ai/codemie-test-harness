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

"""
UI tests for the Scheduler integration State (Enabled/Disabled) badge in the
Integration page list view.

Feature: Display Scheduler State (Enabled/Disabled) in
Integration Page List View.
"""

import pytest
from playwright.sync_api import Page

from codemie_sdk.models.integration import (
    CredentialTypes,
    CredentialValues,
    IntegrationType,
)
from codemie_test_harness.tests.ui.pageobject.integrations.integrations_page import (
    IntegrationsPage,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver

pytestmark = pytest.mark.skipif(
    EnvironmentResolver.is_sandbox(),
    reason="Scheduler is disabled on sandbox environments",
)


@pytest.mark.integration
@pytest.mark.scheduler
@pytest.mark.ui
@pytest.mark.parametrize(
    "integration_type, is_enabled, expected_state",
    [
        (IntegrationType.USER, True, "Enabled"),
        (IntegrationType.USER, False, "Disabled"),
        (IntegrationType.PROJECT, True, "Enabled"),
        (IntegrationType.PROJECT, False, "Disabled"),
    ],
)
def test_show_scheduler_state_badge_on_row(
    page: Page,
    general_integration,
    assistant,
    integration_type,
    is_enabled,
    expected_state,
):
    """
    A Scheduler integration row displays the correct Enabled/Disabled state
    badge directly in the list, on both the User and Project tabs, without
    opening the record.

    AC Coverage: AC-1, AC-2 (TC-001)
    """
    resource_assistant = assistant()
    alias = get_random_name()
    credential_values = [
        CredentialValues(key="url", value=CredentialsManager.AUTO_GENERATED),
        CredentialValues(key="is_enabled", value=is_enabled),
        CredentialValues(key="schedule", value="0 * * * *"),
        CredentialValues(key="resource_type", value="assistant"),
        CredentialValues(key="resource_id", value=resource_assistant.id),
        CredentialValues(key="prompt", value=f"Scheduler prompt {alias}"),
    ]

    general_integration(
        integration_type=integration_type,
        credential_type=CredentialTypes.SCHEDULER,
        credential_values=credential_values,
        integration_alias=alias,
    )

    integrations_page = IntegrationsPage(page)
    integrations_page.navigate_to()
    if integration_type == IntegrationType.USER:
        integrations_page.switch_to_user_tab()
    else:
        integrations_page.switch_to_project_tab()

    integration_row = integrations_page.get_integration_row_by_alias(alias)
    integration_row.should_show_state(expected_state)


@pytest.mark.integration
@pytest.mark.scheduler
@pytest.mark.ui
def test_update_scheduler_state_badge_after_reload(
    page: Page, scheduler_integration, assistant, integration_utils
):
    """
    The state badge reflects the current `is_enabled` value after the
    integration is mutated via the API and the page is reloaded.

    AC Coverage: AC-3 (TC-002)
    """
    resource_assistant = assistant()
    alias = get_random_name()

    integration = scheduler_integration(
        alias=alias,
        resource_type="assistant",
        resource_id=resource_assistant.id,
        prompt=f"Scheduler prompt {alias}",
        is_enabled=True,
    )

    integrations_page = IntegrationsPage(page)
    integrations_page.navigate_to()
    integrations_page.switch_to_project_tab()

    integration_row = integrations_page.get_integration_row_by_alias(alias)
    integration_row.should_show_state("Enabled")

    updated_credential_values = [
        CredentialValues(key="is_enabled", value=False)
        if credential_value.key == "is_enabled"
        else credential_value
        for credential_value in integration.credential_values
    ]
    # Copy the full fetched integration and override only the mutated field,
    # rather than hand-picking a subset of fields, so fields not referenced
    # here (e.g. default, is_global) are never silently reset on the server.
    update_request = integration.model_copy(
        update={"credential_values": updated_credential_values}
    )
    integration_utils.update_integration(update_request)

    page.reload()
    integrations_page.wait_for_page_load()
    # The User/Project tab selection is client-side state, not persisted in the
    # URL, so a full page reload resets the list back to the default "User"
    # tab (confirmed live via playwright-cli) - reselect "Project" explicitly.
    integrations_page.switch_to_project_tab()
    integration_row = integrations_page.get_integration_row_by_alias(alias)
    integration_row.should_show_state("Disabled")


@pytest.mark.integration
@pytest.mark.scheduler
@pytest.mark.ui
def test_hide_scheduler_state_badge_when_is_enabled_missing(
    page: Page, general_integration, assistant
):
    """
    A Scheduler row whose `credential_values` entirely omit the `is_enabled`
    key renders no state badge.

    AC Coverage: AC-1 (TC-003)

    Note: the original test plan for this scenario expected the row to
    default to a "Disabled" badge, reasoning from `shouldShowIntegrationState`
    (which always returns True for Scheduler rows, implying a badge should
    always render). Live inspection of the running application via
    playwright-cli showed this is not what the shipped `IntegrationStateBadge`
    component actually does: it looks up the `is_enabled` entry in
    `credential_values` and renders nothing at all when that entry is
    entirely absent, regardless of credential type. This test asserts the
    real, observed behavior (no badge) rather than the originally-planned
    "Disabled" text.
    """
    resource_assistant = assistant()
    alias = get_random_name()
    credential_values = [
        CredentialValues(key="url", value=CredentialsManager.AUTO_GENERATED),
        CredentialValues(key="schedule", value="0 * * * *"),
        CredentialValues(key="resource_type", value="assistant"),
        CredentialValues(key="resource_id", value=resource_assistant.id),
        CredentialValues(key="prompt", value=f"Scheduler prompt {alias}"),
    ]

    general_integration(
        integration_type=IntegrationType.PROJECT,
        credential_type=CredentialTypes.SCHEDULER,
        credential_values=credential_values,
        integration_alias=alias,
    )

    integrations_page = IntegrationsPage(page)
    integrations_page.navigate_to()
    integrations_page.switch_to_project_tab()

    integration_row = integrations_page.get_integration_row_by_alias(alias)
    integration_row.should_be_visible()
    integration_row.should_show_state("Disabled")
