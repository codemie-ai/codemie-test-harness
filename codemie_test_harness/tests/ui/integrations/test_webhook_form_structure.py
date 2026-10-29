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
UI tests for User-friendly Webhook integration setup screen.

Covers:
- TC-01: Webhook URL field is read-only with copy button; URL tracks alias-derived webhook_id.
- TC-02: Manual webhook_id edit disables alias auto-sync; field stays editable.
- TC-03: Advanced Security Settings accordion is collapsed by default; reveals fields on expand.
- TC-04: GitHub Settings accordion is collapsed by default; reveals all three fields on expand.

All tests navigate to /integrations/user/new, select Webhook credential type, and assert
the new UX behaviour.
"""

import pytest
from playwright.sync_api import Page

from codemie_test_harness.tests.ui.pageobject.integrations.create_integration_page import (
    CreateIntegrationPage,
)
from codemie_test_harness.tests.ui.pageobject.integrations.integrations_page import (
    IntegrationsPage,
)
from codemie_test_harness.tests.ui.test_data.integration_test_data import (
    IntegrationTestDataFactory,
)


# ---------------------------------------------------------------------------
# TC-01: Webhook URL read-only with copy button; URL tracks alias-derived slug
# ---------------------------------------------------------------------------


@pytest.mark.sanity
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.parametrize(
    "alias_input, expected_slug",
    [
        ("My Webhook Test", "my-webhook-test"),
        ("Hello World 2", "hello-world-2"),
    ],
    ids=["slug-with-spaces", "slug-with-number"],
)
def test_webhook_url_readonly_and_tracks_alias_slug(
    page: Page, alias_input: str, expected_slug: str
):
    """TC-01 — Webhook URL field is read-only; its value ends with the alias-derived slug.

    AC-1, AC-2, AC-3, AC-4:
    - A read-only Webhook URL field is displayed with a copy button.
    - The URL is constructed as {base_url}/api/v1/webhooks/{webhook_id}.
    - The old inline hint text is absent.
    - Editing Alias auto-fills webhook_id with a lowercase, hyphenated slug.
    """
    integrations_page = IntegrationsPage(page)
    create_integration_page = CreateIntegrationPage(page)
    test_data = IntegrationTestDataFactory.webhook_integration()

    integrations_page.navigate_to()
    integrations_page.navigate_to_user_integration_creation()

    # Select project and credential type to get the Webhook form rendered.
    create_integration_page.select_project(test_data.project)
    create_integration_page.select_credential_type(test_data.credential_type)

    # AC-1: Webhook URL field is visible.
    from playwright.sync_api import expect

    expect(create_integration_page.webhook_url_input).to_be_visible()

    # AC-1: Copy button is present beside the Webhook URL field.
    create_integration_page.should_have_webhook_url_copy_button_visible()

    # AC-2: Webhook URL field is read-only (user cannot type into it).
    create_integration_page.should_have_webhook_url_readonly()

    # AC-3: Old hint text must not appear (hint was "Full URL: /api/v1/webhooks/<id>").
    from playwright.sync_api import expect as pw_expect

    pw_expect(page.get_by_text("Full URL:", exact=False)).not_to_be_visible()

    # AC-4: Clear alias, type new alias, wait for React useEffect, assert slug.
    create_integration_page.fill_alias(alias_input)
    page.wait_for_timeout(500)

    create_integration_page.should_have_webhook_id_value(expected_slug)
    # The Webhook URL is built as {api_base}/v1/webhooks/{webhook_id} where
    # api_base = CODEMIE_API_DOMAIN (e.g. /code-assistant-api).
    # Checking for /webhooks/{slug} at the end is environment-agnostic.
    create_integration_page.should_have_webhook_url_ends_with(
        f"/webhooks/{expected_slug}"
    )


# ---------------------------------------------------------------------------
# TC-02: Manual webhook_id edit disables alias auto-sync; field stays editable
# ---------------------------------------------------------------------------


@pytest.mark.sanity
@pytest.mark.integration
@pytest.mark.ui
def test_manual_webhook_id_edit_disables_alias_auto_sync(page: Page):
    """TC-02 — After the user manually edits webhook_id, alias changes no longer overwrite it.

    AC-5, AC-6:
    - Once the user edits webhook_id directly, auto-sync from Alias is disabled.
    - The webhook_id field remains fully editable at all times.
    """
    integrations_page = IntegrationsPage(page)
    create_integration_page = CreateIntegrationPage(page)
    test_data = IntegrationTestDataFactory.webhook_integration()

    integrations_page.navigate_to()
    integrations_page.navigate_to_user_integration_creation()

    create_integration_page.select_project(test_data.project)
    create_integration_page.select_credential_type(test_data.credential_type)

    # Type an initial alias to trigger auto-fill.
    create_integration_page.fill_alias("first-alias")
    page.wait_for_timeout(500)

    # Confirm auto-fill populated webhook_id.
    create_integration_page.should_have_webhook_id_value("first-alias")

    # AC-5: Directly overwrite webhook_id to disable auto-sync.
    manual_id = "my-manual-webhook-id"
    create_integration_page.fill_webhook_id(manual_id)

    # Type a completely different alias value.
    create_integration_page.fill_alias("second-alias-should-not-overwrite")
    page.wait_for_timeout(500)

    # webhook_id must retain the manually-set value — auto-sync is disabled.
    create_integration_page.should_have_webhook_id_value(manual_id)

    # AC-6: webhook_id field is still editable.
    from playwright.sync_api import expect

    expect(create_integration_page.webhook_id_input).to_be_editable()


# ---------------------------------------------------------------------------
# TC-03: Advanced Security Settings accordion collapsed by default
# ---------------------------------------------------------------------------


@pytest.mark.sanity
@pytest.mark.integration
@pytest.mark.ui
def test_advanced_security_settings_accordion_collapsed_by_default_and_expands(
    page: Page,
):
    """TC-03 — Advanced Security Settings accordion is collapsed by default;
    reveals Secure Header Name and Value on expand.

    AC-7, AC-8:
    - 'Advanced Security Settings (optional)' header is present.
    - Secure Header Name and Value are NOT visible when collapsed.
    - After clicking the header, both fields become visible and editable.
    """
    integrations_page = IntegrationsPage(page)
    create_integration_page = CreateIntegrationPage(page)
    test_data = IntegrationTestDataFactory.webhook_integration()

    integrations_page.navigate_to()
    integrations_page.navigate_to_user_integration_creation()

    create_integration_page.select_project(test_data.project)
    create_integration_page.select_credential_type(test_data.credential_type)

    # AC-7: Accordion header is present.
    from playwright.sync_api import expect

    expect(create_integration_page.advanced_security_accordion_header).to_be_visible()

    # AC-7: Fields inside the accordion are NOT visible when collapsed.
    create_integration_page.should_have_advanced_security_accordion_collapsed()

    # AC-8: Expand accordion — both fields must become visible and editable.
    create_integration_page.expand_advanced_security_accordion()
    create_integration_page.should_have_secure_header_fields_visible()


# ---------------------------------------------------------------------------
# TC-04: GitHub Settings accordion collapsed by default
# ---------------------------------------------------------------------------


@pytest.mark.sanity
@pytest.mark.integration
@pytest.mark.ui
def test_github_settings_accordion_collapsed_by_default_and_expands(page: Page):
    """TC-04 — GitHub Settings accordion is collapsed by default;
    reveals SHA-256 toggle, Webhook Secret, and Event Filter on expand.

    AC-11, AC-12:
    - 'GitHub Settings (optional)' header is present.
    - SHA-256 toggle, Webhook Secret, and Event Filter are NOT visible when collapsed.
    - After clicking the header, all three fields become visible.
    """
    integrations_page = IntegrationsPage(page)
    create_integration_page = CreateIntegrationPage(page)
    test_data = IntegrationTestDataFactory.webhook_integration()

    integrations_page.navigate_to()
    integrations_page.navigate_to_user_integration_creation()

    create_integration_page.select_project(test_data.project)
    create_integration_page.select_credential_type(test_data.credential_type)

    # AC-11: Accordion header is present.
    from playwright.sync_api import expect

    expect(create_integration_page.github_settings_accordion_header).to_be_visible()

    # AC-11: Fields inside the accordion are NOT visible when collapsed.
    create_integration_page.should_have_github_settings_accordion_collapsed()

    # AC-12: Expand accordion — all three fields must become visible.
    create_integration_page.expand_github_settings_accordion()
    create_integration_page.should_have_github_settings_fields_visible()
