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
UI tests for the GitLab merge-request event filter on Webhook integrations.

Covers the checkbox-group settings-form field added for granular MR event
filtering: default-all-checked, persistence across a page reload, and the
guard against reducing the selection to zero.

Also covers:
- AC-9, AC-10: GitLab Settings accordion collapsed by default (assertion added to
  test_gitlab_mr_filter_defaults_to_all_actions_checked).
- TC-05 (AC-13, AC-14, AC-15, AC-16): Resource dropdown disabled before Resource
  Type selection; options show names not GUIDs; name persists on edit page.
"""

import re

import pytest
from playwright.sync_api import Page, expect

from codemie_test_harness.tests.ui.pageobject.integrations.create_integration_page import (
    CreateIntegrationPage,
)
from codemie_test_harness.tests.ui.pageobject.integrations.edit_integration_page import (
    EditIntegrationPage,
)
from codemie_test_harness.tests.ui.pageobject.integrations.integrations_page import (
    IntegrationsPage,
)
from codemie_test_harness.tests.ui.test_data.integration_test_data import (
    IntegrationTestDataFactory,
)


@pytest.mark.sanity
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.prod_regression
def test_gitlab_mr_filter_defaults_to_all_actions_checked(page: Page):
    """A freshly created Webhook integration shows every MR action checked.

    AC-9, AC-10: GitLab Settings accordion is collapsed by default; the GitLab
    Webhook Secret Token input must NOT be visible until the accordion is expanded.
    The accordion-collapsed assertion is performed BEFORE fill_gitlab_webhook_token
    is called, because that helper expands the accordion internally.
    """
    integrations_page = IntegrationsPage(page)
    create_integration_page = CreateIntegrationPage(page)
    test_data = IntegrationTestDataFactory.webhook_gitlab_integration()

    integrations_page.navigate_to()
    integrations_page.navigate_to_user_integration_creation()

    # Select project and credential type to render Webhook-specific fields;
    # do NOT call fill_webhook_integration_form yet because it would expand
    # the GitLab accordion before we can verify its default collapsed state.
    create_integration_page.select_project(test_data.project)
    create_integration_page.select_credential_type(test_data.credential_type)

    # AC-9, AC-10: GitLab Settings accordion must be collapsed by default.
    expect(create_integration_page.gitlab_webhook_token_input).not_to_be_visible()

    # Fill alias and webhook_id so the form is valid before interacting with MR filter.
    create_integration_page.fill_alias(test_data.alias)
    webhook_id = test_data.fields.get("webhook_id")
    if webhook_id:
        create_integration_page.fill_webhook_id(webhook_id)

    # enable_gitlab_mr_filter() calls expand_gitlab_settings_accordion() internally.
    create_integration_page.enable_gitlab_mr_filter()

    for action in create_integration_page.GITLAB_MR_ACTION_CHECKBOX_IDS:
        create_integration_page.should_have_gitlab_mr_action_checked(action)


_UUID_PATTERN = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE
)


@pytest.mark.sanity
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.prod_regression
def test_gitlab_mr_filter_selection_persists_after_save_and_reload(
    page: Page, assistant
):
    """Unchecking some MR actions, saving, and reloading the edit page keeps the selection.

    TC-05 (AC-13, AC-14, AC-15, AC-16): Also verifies that:
    - The Resource dropdown is disabled before select_resource_type() is called.
    - After selecting a Resource Type, the Resource dropdown is enabled.
    - Resource dropdown options show human-readable names (not GUIDs/UUIDs).
    - After saving and reopening the edit page, the resource name (not GUID) is shown.
    """
    integrations_page = IntegrationsPage(page)
    create_integration_page = CreateIntegrationPage(page)
    target_assistant = assistant()
    test_data = IntegrationTestDataFactory.webhook_gitlab_integration()

    integrations_page.navigate_to()
    integrations_page.navigate_to_user_integration_creation()

    # Fill everything except resource to get the form in base state.
    create_integration_page.select_project(test_data.project)
    create_integration_page.fill_alias(test_data.alias)
    create_integration_page.select_credential_type(test_data.credential_type)

    # TC-05 AC-14: resource dropdown must be disabled before a Resource Type is selected.
    create_integration_page.should_have_resource_dropdown_disabled()

    # Select resource type — dropdown should become enabled.
    create_integration_page.select_resource_type("Assistant")

    # TC-05 AC-14: resource dropdown must be enabled after Resource Type is set.
    create_integration_page.should_have_resource_dropdown_enabled()

    # TC-05 AC-13, AC-15: option labels must be names, not GUIDs.
    option_labels = create_integration_page.get_resource_dropdown_options()
    assert len(option_labels) > 0, (
        "Resource dropdown returned no options after selecting Resource Type 'Assistant' — "
        "cannot verify AC-13/AC-15 (dropdown may have failed to load)."
    )
    for label in option_labels:
        assert _UUID_PATTERN.search(label) is None, (
            f"Resource dropdown option '{label}' looks like a GUID — expected a name."
        )

    # Select the target assistant by name.
    create_integration_page.select_resource_by_name(target_assistant.name)

    # Fill remaining webhook fields.
    webhook_id = test_data.fields.get("webhook_id")
    if webhook_id:
        create_integration_page.fill_webhook_id(webhook_id)
    create_integration_page.fill_gitlab_webhook_token(
        test_data.fields.get("gitlab_webhook_token", "tok_placeholder")
    )
    create_integration_page.enable_gitlab_mr_filter()

    # Keep only "Created (open)" and "Merged" checked.
    for action in ("update", "close", "reopen", "approved_unapproved"):
        create_integration_page.toggle_gitlab_mr_action(action)

    create_integration_page.create_integration()
    integrations_page.wait_for_page_load()
    integrations_page.should_see_message(
        IntegrationTestDataFactory.success_messages["integration_created"]
    )

    edit_integration_page = EditIntegrationPage(page)
    edit_integration_page.navigate_to_edit_integration(
        project_name=test_data.project,
        credential_type=test_data.credential_type.value,
        alias=test_data.alias,
    )
    edit_integration_page.should_be_on_edit_integration_page()

    # TC-05 AC-16: resource name (not GUID) is shown in the edit page dropdown.
    # #resource_id is a PrimeReact Select container (div), not an <input> element.
    # input_value() only works on <input>/<textarea>/<select> — call inner_text() instead
    # to read the visible selected label from the PrimeReact component.
    resource_value = edit_integration_page.resource_dropdown.inner_text().strip()
    assert _UUID_PATTERN.search(resource_value) is None, (
        f"Edit page resource dropdown shows a GUID '{resource_value}' instead of a name."
    )

    edit_integration_page.should_have_gitlab_mr_action_checked("open")
    edit_integration_page.should_have_gitlab_mr_action_checked("merge")
    edit_integration_page.should_have_gitlab_mr_action_unchecked("update")
    edit_integration_page.should_have_gitlab_mr_action_unchecked("close")
    edit_integration_page.should_have_gitlab_mr_action_unchecked("reopen")
    edit_integration_page.should_have_gitlab_mr_action_unchecked("approved_unapproved")


@pytest.mark.sanity
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.prod_regression
def test_gitlab_mr_filter_blocks_unchecking_last_action(page: Page):
    """Unchecking the last remaining MR action is rejected with an inline error."""
    integrations_page = IntegrationsPage(page)
    create_integration_page = CreateIntegrationPage(page)
    test_data = IntegrationTestDataFactory.webhook_gitlab_integration()

    integrations_page.navigate_to()
    integrations_page.navigate_to_user_integration_creation()
    create_integration_page.fill_webhook_integration_form(test_data)
    create_integration_page.enable_gitlab_mr_filter()

    # Uncheck every action but the last one.
    for action in ("update", "close", "reopen", "merge", "approved_unapproved"):
        create_integration_page.toggle_gitlab_mr_action(action)
    create_integration_page.should_have_gitlab_mr_action_checked("open")

    # Attempting to uncheck the last one ("open") must be rejected.
    create_integration_page.toggle_gitlab_mr_action("open")

    create_integration_page.should_have_gitlab_mr_action_checked("open")
    create_integration_page.should_show_gitlab_mr_action_empty_selection_error()
