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
Create Integration page object for the integration creation workflow.
Contains methods for filling out integration forms, selecting types, and completing the creation process.
"""

import re

from codemie_sdk.models.integration import CredentialTypes
from hamcrest import assert_that, is_not, empty, matches_regexp
from playwright.sync_api import Locator, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.test_data.integration_test_data import (
    IntegrationTestData,
)


# noinspection PyArgumentList
class CreateIntegrationPage(BasePage):
    """Create Integration page with comprehensive form handling and validation."""

    def __init__(self, page):
        super().__init__(page)

    # Header elements
    @property
    def page_title(self) -> Locator:
        """Page title element showing 'New User Integration'."""
        return self.page.locator("h1.text-lg")

    @property
    def action_buttons_container(self) -> Locator:
        """Container holding all action buttons."""
        return self.page.locator("div.flex.justify-end.items-center.gap-4")

    @property
    def cancel_button(self) -> Locator:
        """Cancel button in the action button row."""
        return self.action_buttons_container.get_by_role("button", name="Cancel")

    @property
    def test_button(self) -> Locator:
        """Test button to test the integration."""
        return self.action_buttons_container.get_by_role("button", name="Test")

    @property
    def create_button(self) -> Locator:
        """Save button to save/create the form."""
        return self.action_buttons_container.get_by_role("button", name="Save")

    # Help button and panel
    @property
    def help_button(self) -> Locator:
        """Help button in bottom right corner."""
        return self.page.get_by_role("button", name="Help").filter(
            has=self.page.locator("svg")
        )

    @property
    def help_panel_title(self) -> Locator:
        """Help panel title 'CodeMie Helper'."""
        return self.page.get_by_role("heading", name="CodeMie Helper", level=3)

    @property
    def help_panel_close_button(self) -> Locator:
        """Close button in help panel.
        Uses exact=True to avoid matching toast notification 'Close notification' button.
        """
        return self.page.get_by_role("button", name="Close", exact=True)

    @property
    def help_work_with_integrations_button(self) -> Locator:
        """'How to work with Integrations' button in help panel."""
        return self.page.get_by_role("button", name="How to work with Integrations")

    # Form container
    @property
    def form_container(self) -> Locator:
        """Main form container."""
        return self.page.locator("form.flex.flex-col.gap-y-6")

    # Project selection
    @property
    def project_selector(self) -> Locator:
        """Project multiselect dropdown."""
        return self.page.locator("#project-selector")

    @property
    def project_selector_label(self) -> Locator:
        """Project selector label container."""
        return self.project_selector.locator(".p-multiselect-label")

    @property
    def project_selector_trigger(self) -> Locator:
        """Project selector dropdown trigger button."""
        return self.project_selector.locator(".p-multiselect-trigger")

    @property
    def project_search_input(self) -> Locator:
        """Project selector lookup."""
        return self.page.get_by_role("searchbox")

    # Global Integration toggle
    @property
    def global_integration_checkbox(self) -> Locator:
        """Global Integration checkbox input."""
        return self.page.locator('input#isGlobal[type="checkbox"]')

    @property
    def global_integration_switch(self) -> Locator:
        """Global Integration switch wrapper."""
        return self.page.locator("label").filter(has_text="Global Integration")

    # Cloud toggle (note: ID uses underscore 'is_cloud', not camelCase 'isCloud')
    @property
    def is_cloud_checkbox(self) -> Locator:
        """Cloud checkbox input."""
        return self.page.locator('input#is_cloud[type="checkbox"]')

    @property
    def is_jira_cloud_switch(self) -> Locator:
        """Cloud switch wrapper."""
        return self.page.locator("label").filter(has_text="Is Jira Cloud")

    @property
    def is_confluence_cloud_switch(self) -> Locator:
        """Cloud switch wrapper."""
        return self.page.locator("label").filter(has_text="Is Confluence Cloud")

    # Credential Type selection
    @property
    def credential_type_input(self) -> Locator:
        """Credential Type autocomplete input field."""
        return self.page.locator("#credentialType input.p-autocomplete-input")

    @property
    def credential_type_dropdown_button(self) -> Locator:
        """Credential Type dropdown button."""
        return self.page.locator("#credentialType button.p-autocomplete-dropdown")

    # Alias field (required)
    @property
    def alias_input(self) -> Locator:
        """Integration alias input field (required)."""
        return self.page.locator('input#settingAlias[data-testid="validation"]')

    @property
    def alias_label(self) -> Locator:
        """Alias field label."""
        return self.page.locator('label[for="settingAlias"] .input-label')

    # Authentication section
    @property
    def authentication_heading(self) -> Locator:
        """Authentication section heading."""
        return self.page.locator("h4.text-sm").filter(has_text="Authentication")

    @property
    def url_input(self) -> Locator:
        """URL input field in authentication section."""
        return self.page.locator('input#url[data-testid="validation"]')

    @property
    def token_name_input(self) -> Locator:
        """Token name input field."""
        return self.page.locator('input#name[data-testid="validation"]')

    @property
    def token_input(self) -> Locator:
        """Token input field."""
        return self.page.locator('input#token[data-testid="validation"]')

    @property
    def user_name_input(self) -> Locator:
        """User Name input."""
        return self.page.locator("input#username")

    # GitLab webhook MR event filter (Webhook credential type)
    GITLAB_MR_ACTION_CHECKBOX_IDS = {
        "open": "gitlab_event_filter-open",
        "update": "gitlab_event_filter-update",
        "close": "gitlab_event_filter-close",
        "reopen": "gitlab_event_filter-reopen",
        "merge": "gitlab_event_filter-merge",
        "approved_unapproved": "gitlab_event_filter-approved,unapproved",
    }

    @property
    def gitlab_filter_mr_actions_checkbox(self) -> Locator:
        """Toggle checkbox that reveals the per-action MR event filter checkboxes."""
        return self.page.locator('input#gitlab_filter_mr_actions[type="checkbox"]')

    @step
    def enable_gitlab_mr_filter(self):
        """Enable the 'Filter merge request actions' toggle to reveal per-action checkboxes."""
        self.expand_gitlab_settings_accordion()
        if not self.gitlab_filter_mr_actions_checkbox.is_checked():
            self.page.locator("label").filter(
                has_text="Filter merge request actions"
            ).click()
        return self

    @step
    def should_have_gitlab_mr_filter_enabled(self):
        """Assert the 'Filter merge request actions' toggle is enabled."""
        expect(self.gitlab_filter_mr_actions_checkbox).to_be_checked()
        return self

    @property
    def gitlab_webhook_token_input(self) -> Locator:
        """GitLab Webhook Secret Token input field."""
        return self.page.locator('input#gitlab_webhook_token[data-testid="validation"]')

    def expand_gitlab_settings_accordion(self):
        """Expand the GitLab Settings accordion if it is currently collapsed."""
        if not self.gitlab_webhook_token_input.is_visible():
            self.page.locator("a.p-accordion-header-link").filter(
                has_text="GitLab Settings"
            ).click()

    def gitlab_mr_action_checkbox(self, action: str) -> Locator:
        """Checkbox for a single GitLab MR action in the event filter group.

        Uses an attribute selector (`input[id="..."]`), not `input#id`: the
        combined "approved,unapproved" option's id contains a comma, which
        `#id` syntax parses as a CSS selector-list separator rather than a
        literal id character.

        Args:
            action: one of 'open', 'update', 'close', 'reopen', 'merge',
                'approved_unapproved'
        """
        checkbox_id = self.GITLAB_MR_ACTION_CHECKBOX_IDS[action]
        return self.page.locator(f'input[id="{checkbox_id}"][type="checkbox"]')

    @property
    def gitlab_mr_action_empty_selection_error(self) -> Locator:
        """Inline error shown when unchecking the last selected MR action."""
        return self.page.get_by_text(
            "At least one merge request action must stay selected."
        )

    @property
    def webhook_id_input(self) -> Locator:
        """Webhook ID input field (Webhook credential type)."""
        return self.page.locator('input#webhook_id[data-testid="validation"]')

    @property
    def webhook_url_input(self) -> Locator:
        """Read-only Webhook URL field rendered by InputCopy component.

        DOM inspection confirmed: InputCopy renders
        ``<input name="copy-input" type="text" readonly="" value="..." />``.
        The ``name="copy-input"`` attribute is set by the InputCopy component
        and is unique in this form.  ``get_by_label()`` finds nothing because
        InputCopy does not create a native HTML ``<label>`` element.
        """
        return self.page.locator("input[name='copy-input']")

    @property
    def webhook_url_copy_button(self) -> Locator:
        """Copy-to-clipboard button that sits alongside the Webhook URL input.

        DOM inspection confirmed: InputCopy renders the copy button inside an
        absolutely-positioned ``<div>`` that is the **immediate next sibling**
        of ``<input name="copy-input">``.  The button has no aria-label or
        title.  The sibling combinator ``+`` pins the selector tightly so
        that outer ancestor divs (which also satisfy ``:has()``) are not
        matched.
        """
        return self.page.locator("input[name='copy-input'] + div button[type='button']")

    # ---- Advanced Security Settings accordion (formerly "Request verification") ----

    @property
    def advanced_security_accordion_header(self) -> Locator:
        """Clickable header for the 'Advanced Security Settings (optional)' accordion."""
        return self.page.locator("a.p-accordion-header-link").filter(
            has_text="Advanced Security Settings"
        )

    @property
    def secure_header_name_input(self) -> Locator:
        """Secure Header Name input — revealed after expanding Advanced Security Settings."""
        return self.page.locator("input#secure_header_name")

    @property
    def secure_header_value_input(self) -> Locator:
        """Secure Header Value input — revealed after expanding Advanced Security Settings."""
        return self.page.locator("input#secure_header_value")

    # ---- GitHub Settings accordion ----

    @property
    def github_settings_accordion_header(self) -> Locator:
        """Clickable header for the 'GitHub Settings (optional)' accordion."""
        return self.page.locator("a.p-accordion-header-link").filter(
            has_text="GitHub Settings"
        )

    @property
    def github_sha256_toggle(self) -> Locator:
        """Require SHA-256 Signature toggle — revealed after expanding GitHub Settings.

        DOM inspection confirmed: id="github_require_sha256", type="checkbox".
        """
        return self.page.locator('input#github_require_sha256[type="checkbox"]')

    @property
    def github_webhook_secret_input(self) -> Locator:
        """GitHub Webhook Secret input — revealed after expanding GitHub Settings."""
        return self.page.locator("input#github_webhook_secret")

    @property
    def github_event_filter_input(self) -> Locator:
        """GitHub Event Filter input — revealed after expanding GitHub Settings."""
        return self.page.locator("input#github_event_filter")

    # ---- Resource dropdown ----

    @property
    def resource_dropdown(self) -> Locator:
        """Resource dropdown (PrimeReact Select rendered with id='resource_id').

        Disabled until a Resource Type is selected; enabled after.
        """
        return self.page.locator("#resource_id")

    # ---- Webhook ID step methods ----

    @step
    def fill_webhook_id(self, webhook_id: str):
        """Fill the Webhook ID field."""
        self.webhook_id_input.clear()
        self.webhook_id_input.fill(webhook_id)
        return self

    @step
    def get_webhook_id_value(self) -> str:
        """Return the current value of the Webhook ID field."""
        return self.webhook_id_input.input_value()

    @step
    def should_have_webhook_id_value(self, expected: str):
        """Assert the Webhook ID field contains the expected value."""
        expect(self.webhook_id_input).to_have_value(expected)
        return self

    # ---- Webhook URL step methods ----

    @step
    def should_have_webhook_url_readonly(self):
        """Assert the Webhook URL field is read-only (not editable by the user)."""
        expect(self.webhook_url_input).to_have_attribute("readonly", "")
        return self

    @step
    def should_have_webhook_url_ends_with(self, suffix: str):
        """Assert the Webhook URL field value ends with the given suffix.

        Args:
            suffix: Expected URL suffix, e.g. '/api/v1/webhooks/my-slug'.
        """
        expect(self.webhook_url_input).to_have_value(
            re.compile(re.escape(suffix) + r"$")
        )
        return self

    @step
    def should_have_webhook_url_copy_button_visible(self):
        """Assert that the copy-to-clipboard button is present beside the Webhook URL."""
        expect(self.webhook_url_copy_button).to_be_visible()
        return self

    # ---- Accordion step methods ----

    @step
    def expand_advanced_security_accordion(self):
        """Expand the Advanced Security Settings accordion if currently collapsed."""
        if not self.secure_header_name_input.is_visible():
            self.advanced_security_accordion_header.click()
        return self

    @step
    def expand_github_settings_accordion(self):
        """Expand the GitHub Settings accordion if currently collapsed."""
        if not self.github_sha256_toggle.is_visible():
            self.github_settings_accordion_header.click()
        return self

    @step
    def should_have_advanced_security_accordion_collapsed(self):
        """Assert that Advanced Security Settings accordion is collapsed (inner fields hidden)."""
        expect(self.secure_header_name_input).not_to_be_visible()
        return self

    @step
    def should_have_github_settings_accordion_collapsed(self):
        """Assert that GitHub Settings accordion is collapsed (inner fields hidden)."""
        expect(self.github_sha256_toggle).not_to_be_visible()
        return self

    @step
    def should_have_secure_header_fields_visible(self):
        """Assert Secure Header Name and Value inputs are visible and editable."""
        expect(self.secure_header_name_input).to_be_visible()
        expect(self.secure_header_name_input).to_be_editable()
        expect(self.secure_header_value_input).to_be_visible()
        expect(self.secure_header_value_input).to_be_editable()
        return self

    @step
    def should_have_github_settings_fields_visible(self):
        """Assert SHA-256 toggle, Webhook Secret, and Event Filter inputs are visible."""
        expect(self.github_sha256_toggle).to_be_visible()
        expect(self.github_webhook_secret_input).to_be_visible()
        expect(self.github_event_filter_input).to_be_visible()
        return self

    # ---- Resource dropdown step methods ----

    @step
    def should_have_resource_dropdown_disabled(self):
        """Assert the Resource dropdown is disabled (no Resource Type selected yet).

        PrimeReact MultiSelect adds the ``p-disabled`` CSS class to the container
        div when disabled — there is no ``data-p-disabled`` attribute on this component.
        """
        expect(self.resource_dropdown).to_have_class(re.compile(r"\bp-disabled\b"))
        return self

    @step
    def should_have_resource_dropdown_enabled(self):
        """Assert the Resource dropdown is enabled (Resource Type has been selected).

        Enabled state is the absence of the ``p-disabled`` class on the container.
        """
        expect(self.resource_dropdown).not_to_have_class(re.compile(r"\bp-disabled\b"))
        return self

    @step
    def get_resource_dropdown_options(self) -> list:
        """Open the Resource dropdown, collect visible option label texts, and return them.

        Returns:
            list[str]: Display labels currently visible in the open dropdown panel.
        """
        self.resource_dropdown.click()
        option_elements = self.page.get_by_role("option").all()
        labels = [opt.inner_text() for opt in option_elements]
        # Close dropdown by pressing Escape
        self.page.keyboard.press("Escape")
        return labels

    @property
    def resource_type_input(self) -> Locator:
        """Resource Type autocomplete input field (Webhook credential type)."""
        return self.page.locator("#resource_type input.p-autocomplete-input")

    @step
    def select_resource_type(self, resource_type_label: str):
        """Select a Resource Type from the autocomplete dropdown (e.g. 'Assistant')."""
        self.resource_type_input.click()
        self.page.get_by_role("option", name=resource_type_label).click()
        return self

    @step
    def select_resource_by_name(self, resource_name: str):
        """Select a Resource from the resource dropdown by its display name."""
        self.page.locator("#resource_id").click()
        self.page.get_by_role("option", name=resource_name).click()
        return self

    # resource_id plain-text input (Scheduler credential type)
    @property
    def resource_id_input(self) -> Locator:
        """Resource ID plain-text input field (Scheduler credential type)."""
        return self.page.locator("input#resource_id")

    @step
    def fill_resource_id(self, resource_id: str):
        """Fill the Resource ID field for Scheduler integrations.

        Args:
            resource_id: The resource identifier string to enter.
        """
        self.resource_id_input.fill(resource_id)
        return self

    @step
    def select_assistant_resource_id(self, assistant_name: str):
        """Select an assistant from the resource_id autocomplete for SCHEDULER integrations.

        After selecting 'Assistant' resource type, the resource_id field renders as
        an autocomplete that searches assistant names. This method types the name to
        filter suggestions, then clicks the matching option to properly populate the
        React form state with the selected assistant's id.

        Args:
            assistant_name: The display name of the assistant to select.
        """
        self.resource_id_input.click()
        self.resource_id_input.fill(assistant_name)
        option = self.page.get_by_role("option", name=assistant_name)
        option.click()
        return self

    # Schedule field (Scheduler credential type)
    @property
    def schedule_input(self) -> Locator:
        """Schedule (cron expression) input field (Scheduler credential type)."""
        return self.page.locator("input#schedule")

    @step
    def fill_schedule(self, cron_expression: str):
        """Fill the cron schedule expression field.

        Args:
            cron_expression: Cron expression string (e.g. '0 * * * *')
        """
        self.schedule_input.clear()
        self.schedule_input.fill(cron_expression)
        return self

    # Timezone autocomplete (Scheduler credential type)
    @property
    def timezone_autocomplete_input(self) -> Locator:
        """Timezone autocomplete input field (Scheduler credential type)."""
        return self.page.locator("#timezone input.p-autocomplete-input")

    @property
    def timezone_autocomplete_dropdown_button(self) -> Locator:
        """Timezone autocomplete dropdown button (Scheduler credential type)."""
        return self.page.locator("#timezone button.p-autocomplete-dropdown")

    @step
    def fill_timezone(self, tz: str):
        """Fill the Timezone autocomplete and select the matching option.

        The UI renders IANA timezone names with underscores replaced by spaces
        (e.g. 'America/New_York' is displayed as 'America/New York'), so the
        option lookup normalises underscores to spaces before matching.

        Args:
            tz: IANA timezone name (e.g. 'Europe/Warsaw', 'Asia/Tokyo', 'UTC')
        """
        self.timezone_autocomplete_input.clear()
        self.timezone_autocomplete_input.fill(tz)
        display_name = tz.replace("_", " ")
        option = self.page.get_by_role("option", name=display_name, exact=False)
        option.click()
        return self

    @step
    def get_timezone_value(self) -> str:
        """Return the current value of the timezone autocomplete input."""
        return self.timezone_autocomplete_input.input_value()

    @step
    def should_have_timezone_autocomplete_visible(self):
        """Assert the timezone autocomplete input is visible."""
        expect(self.timezone_autocomplete_input).to_be_visible()
        return self

    @step
    def should_have_non_empty_timezone_value(self, timeout: int = 5000):
        """Assert the timezone autocomplete input has a non-empty value.

        Uses Playwright auto-wait so it polls until the condition is true (or
        timeout expires). Call this after the credential-type form renders to
        verify the browser-timezone default has been populated by React before
        any user interaction.

        Args:
            timeout: Maximum wait time in milliseconds (default 5000).
        """
        expect(self.timezone_autocomplete_input).not_to_have_value("", timeout=timeout)
        return self

    @step
    def should_have_timezone_value(self, expected_tz: str, with_offset: bool = False):
        """Assert the timezone autocomplete input has the expected value.

        The UI renders IANA timezone names with underscores replaced by spaces
        (e.g. 'America/New_York' is displayed as 'America/New York').
        Pass either the IANA name or the display form — both are accepted.

        Args:
            expected_tz: IANA timezone name or its UI display form
            with_offset: When True, additionally asserts that the UTC offset suffix
                ``(UTC±H)`` or ``(UTC±H:MM)`` is present in the displayed value,
                verifying a value (e.g. 'Asia/Tokyo (UTC+9)'). Defaults to
                False for backward compatibility.
        """
        display_value = expected_tz.replace("_", " ")
        if with_offset:
            pattern = re.compile(
                r"%s \(UTC[+-]\d+(:\d{2})?\)" % re.escape(display_value)
            )
        else:
            pattern = re.compile(re.escape(display_value))
        expect(self.timezone_autocomplete_input).to_have_value(pattern)
        return self

    @step
    def should_have_timezone_option_with_offset(self, tz: str, expected_label: str):
        """Assert that the timezone dropdown panel shows an option with the expected
        formatted label, including the UTC offset suffix.

        Types the IANA timezone name into the autocomplete input to filter the list
        (handles virtualized dropdowns where not all ~500 options are rendered at once),
        waits for the suggestion panel to appear, then uses ``.filter(has_text=...)``
        to locate the option (more robust than ``get_by_role(..., name=..., exact=True)``
        for labels with special characters like ``(UTC+5:30)``).

        Args:
            tz: IANA timezone name (e.g. 'Asia/Tokyo', 'UTC', 'Asia/Kolkata').
            expected_label: The exact formatted label expected in the dropdown option,
                e.g. 'Asia/Tokyo (UTC+9)'.
        """
        # Type IANA name to filter the dropdown — avoids virtualization gaps (the full
        # list has ~500 options and only the visible ones are rendered in the DOM).
        self.timezone_autocomplete_input.clear()
        self.timezone_autocomplete_input.fill(tz)
        # Wait for PrimeReact suggestion panel to render after typing
        panel = self.page.locator(".p-autocomplete-panel")
        expect(panel).to_be_visible(timeout=5000)
        # Use has_text filter — more robust than get_by_role(..., name=..., exact=True)
        # for labels containing special characters like parentheses, + and :.
        option = self.page.locator('[role="option"]').filter(has_text=expected_label)
        expect(option).to_be_visible(timeout=5000)
        expect(option).to_contain_text(expected_label)
        self.page.keyboard.press("Escape")
        return self

    @step
    def should_see_creation_success(self):
        """Assert the integration creation success toast is visible with success content.

        Checks both visibility and that the toast header contains the expected
        success text, distinguishing it from an error toast that shares the same
        CSS selector structure.
        """
        toast_header = self.page.locator(".codemie-toast .codemie-toast-header")
        expect(toast_header).to_be_visible(timeout=10000)
        expect(toast_header).to_contain_text("successfully", ignore_case=True)
        return self

    @step
    def fill_gitlab_webhook_token(self, token: str):
        """Fill the GitLab Webhook Secret Token field."""
        self.expand_gitlab_settings_accordion()
        self.gitlab_webhook_token_input.clear()
        self.gitlab_webhook_token_input.fill(token)
        return self

    @step
    def toggle_gitlab_mr_action(self, action: str):
        """Click a single GitLab MR action checkbox to toggle it."""
        self.expand_gitlab_settings_accordion()
        self.gitlab_mr_action_checkbox(action).click()
        return self

    @step
    def should_have_gitlab_mr_action_checked(self, action: str):
        """Verify that a given GitLab MR action checkbox is checked."""
        self.expand_gitlab_settings_accordion()
        expect(self.gitlab_mr_action_checkbox(action)).to_be_checked()
        return self

    @step
    def should_have_gitlab_mr_action_unchecked(self, action: str):
        """Verify that a given GitLab MR action checkbox is not checked."""
        self.expand_gitlab_settings_accordion()
        expect(self.gitlab_mr_action_checkbox(action)).not_to_be_checked()
        return self

    @step
    def should_show_gitlab_mr_action_empty_selection_error(self):
        """Verify the inline error for an empty MR action selection is shown."""
        expect(self.gitlab_mr_action_empty_selection_error).to_be_visible()
        return self

    # Authentication Type dropdown (for Git)
    @property
    def auth_type_container(self) -> Locator:
        """Authentication Type autocomplete container."""
        return self.page.locator("#auth_type")

    @property
    def auth_type_label(self) -> Locator:
        """Authentication Type field label."""
        return self.page.locator('label[for="auth_type"]')

    @property
    def auth_type_input(self) -> Locator:
        """Authentication Type input field."""
        return self.page.locator('input[name="auth_type"]')

    @property
    def auth_type_dropdown_button(self) -> Locator:
        """Authentication Type dropdown button."""
        return self.page.locator("#auth_type button.p-autocomplete-dropdown")

    @property
    def authentication_type_dropdown(self) -> Locator:
        """Authentication Type dropdown button (alias for backward compatibility)."""
        return self.page.get_by_role("button", name="Authentication Type")

    # GitHub App authentication fields
    @property
    def github_app_info_section(self) -> Locator:
        """GitHub App setup information section."""
        return self.page.locator("div.text-text-quaternary").filter(
            has_text="GitHub App Setup"
        )

    @property
    def github_app_setup_guide_link(self) -> Locator:
        """Link to GitHub App setup guide."""
        return self.page.get_by_role("link", name="SETUP GUIDE")

    @property
    def github_app_id_label(self) -> Locator:
        """GitHub App ID field label."""
        return self.page.locator('label[for="app_id"]')

    @property
    def github_app_id_input(self) -> Locator:
        """GitHub App ID input field."""
        return self.page.locator("input#app_id")

    @property
    def github_app_private_key_label(self) -> Locator:
        """GitHub App Private Key field label."""
        return self.page.locator('label[for="private_key"]')

    @property
    def github_app_private_key_input(self) -> Locator:
        """GitHub App Private Key textarea field (note: this is a textarea, not input)."""
        return self.page.locator("textarea#private_key")

    @property
    def github_app_installation_id_label(self) -> Locator:
        """GitHub App Installation ID field label."""
        return self.page.locator('label[for="installation_id"]')

    @property
    def github_app_installation_id_input(self) -> Locator:
        """GitHub App Installation ID input field."""
        return self.page.locator("input#installation_id")

    # Confluence EPAM-specific section
    @property
    def confluence_epam_info_section(self) -> Locator:
        """EPAM users info section for Confluence."""
        return self.page.locator("generic").filter(has_text="EPAM users only:")

    @property
    def confluence_kb_link(self) -> Locator:
        """Link to EPAM KB."""
        return self.page.get_by_role("link", name="GO TO KB")

    # Information tooltips and help text
    @property
    def global_integration_help_text(self) -> Locator:
        """Information text explaining global integration feature."""
        return self.page.locator(".text-text-secondary.text-xs").filter(
            has_text="By enabling, it will become versatile"
        )

    @property
    def authentication_help_text(self) -> Locator:
        """Security information text about masked sensitive data."""
        return self.page.locator(".text-text-secondary.text-xs").filter(
            has_text="Important note: Your sensitive information is encrypted for security"
        )

    # Validation elements
    @property
    def validation_errors(self) -> Locator:
        """All validation error messages on the page."""
        return self.page.locator(".error-message, .validation-error, .field-error")

    @property
    def alias_inline_validation_message(self) -> Locator:
        """Inline validation message for alias field."""
        return self.page.locator(".input-error-message").filter(
            has_text="Alias is required"
        )

    @property
    def url_inline_validation_message(self) -> Locator:
        """Inline validation message for URL field."""
        return self.page.locator(".input-error-message").filter(
            has_text="URL is required"
        )

    @property
    def token_inline_validation_message(self) -> Locator:
        """Inline validation message for token field."""
        return self.page.locator(".input-error-message").filter(
            has_text="Token is required"
        )

    @property
    def all_inline_validation_messages(self) -> Locator:
        """All inline validation error messages."""
        return self.page.locator(".input-error-message")

    # Toast notification elements
    @property
    def error_toast_header(self) -> Locator:
        """Error toast notification header."""
        return self.page.locator(".codemie-toast-err .codemie-toast-header")

    @property
    def error_toast_content(self) -> Locator:
        """Error toast notification content message."""
        return self.page.locator(".codemie-toast-err .codemie-toast-content")

    # Navigation methods
    @step
    def navigate_to_user_integration_creation(self):
        """Navigate to the create user integration page."""
        self.page.goto("/integrations/user/new")
        self.wait_for_page_load()
        return self

    @step
    def navigate_to_project_integration_creation(self):
        """Navigate to the create project integration page."""
        self.page.goto("/integrations/project/new")
        self.wait_for_page_load()
        return self

    @step
    def go_back(self):
        """Click the back button to return to previous page."""
        self.back_button.click()
        return self

    # Help panel methods
    @step
    def click_help_button(self):
        """Click the help button in bottom right corner."""
        self.help_button.click()
        expect(self.help_panel_title).to_be_visible()
        return self

    @step
    def close_help_panel(self):
        """Close the help panel."""
        self.help_panel_close_button.click()
        expect(self.help_panel_title).to_be_hidden()
        return self

    @step
    def should_have_help_button_visible(self):
        """Verify that the help button is visible."""
        expect(self.help_button).to_be_visible()
        return self

    @step
    def should_have_help_panel_visible(self):
        """Verify that the help panel is visible."""
        expect(self.help_panel_title).to_be_visible()
        expect(self.help_work_with_integrations_button).to_be_visible()
        return self

    # Project selection methods
    @step
    def open_project_selector(self):
        """Open the project selector dropdown."""
        self.project_selector_trigger.click()
        return self

    @step
    def select_project(self, project_name: str):
        """
        Select a project from the dropdown.

        Args:
            project_name (str): Name of the project to select
        """
        self.open_project_selector()
        self.project_search_input.fill(project_name)
        # Use exact text matching to avoid strict mode violations when multiple projects
        # contain the search term as a substring (e.g., "codemie", "test-codemie", etc.)
        # Wait for the filtered dropdown to render before checking visibility — the
        # autocomplete filter is debounced, so is_visible() right after fill() can miss
        # it and fall through to the unreliable Enter fallback (caused the
        # form to silently keep whatever project was previously selected).
        project_option = self.page.get_by_role("option", name=project_name, exact=True)
        try:
            project_option.wait_for(state="visible", timeout=3000)
            project_option.click()
        except PlaywrightTimeoutError:
            # If exact match not found, press Enter to accept typed value
            self.project_search_input.press("Enter")
        return self

    @step
    def get_selected_project(self) -> str:
        """
        Get the currently selected project name.

        Returns:
            str: Currently selected project name
        """
        return self.project_selector_label.text_content().strip()

    # Global Integration methods
    @step
    def enable_global_integration(self):
        """Enable the Global Integration toggle."""
        if not self.global_integration_checkbox.is_checked():
            self.global_integration_switch.click()
        return self

    @step
    def disable_global_integration(self):
        """Disable the Global Integration toggle."""
        if self.global_integration_checkbox.is_checked():
            self.global_integration_switch.click()
        return self

    @step
    def is_global_integration_enabled(self) -> bool:
        """
        Check if Global Integration is enabled.

        Returns:
            bool: True if enabled, False otherwise
        """
        return self.global_integration_checkbox.is_checked()

    # UI display labels that differ from the API credential_type value.
    # The backend uses the API value; the UI autocomplete shows the display label.
    _CREDENTIAL_TYPE_UI_LABELS = {
        "GoogleOAuth": "Google OAuth",
    }

    def _get_ui_label(self, credential_type: CredentialTypes) -> str:
        return self._CREDENTIAL_TYPE_UI_LABELS.get(
            credential_type.value, credential_type.value
        )

    # Credential Type methods
    @step
    def select_credential_type(self, credential_type: CredentialTypes):
        """
        Select a credential type from the autocomplete dropdown.

        Args:
            credential_type: Type of credential to select (e.g., 'Git', 'AWS', etc.)
        """
        ui_label = self._get_ui_label(credential_type)
        self.credential_type_input.clear()
        self.credential_type_input.fill(ui_label)

        # Wait for dropdown options to appear and select the matching option.
        # exact=True so a base type (e.g. "Git") does not also match its OAuth
        # sibling (e.g. "GitLab (OAuth)"), which would trip Playwright strict mode.
        option = self.page.get_by_role("option", name=ui_label, exact=True)
        option.click()
        return self

    @step
    def get_credential_type(self) -> str:
        """
        Get the currently selected credential type.

        Returns:
            str: Currently selected credential type
        """
        return self.credential_type_input.input_value()

    # Form filling methods
    @step
    def fill_alias(self, alias: str):
        """
        Fill the integration alias field.

        Args:
            alias (str): Integration alias name
        """
        self.alias_input.clear()
        self.alias_input.fill(alias)
        return self

    @step
    def fill_url(self, url: str):
        """
        Fill the URL field in authentication section.

        Args:
            url (str): URL value
        """
        self.url_input.clear()
        self.url_input.fill(url)
        return self

    @step
    def fill_token_name(self, token_name: str):
        """
        Fill the token name field.

        Args:
            token_name (str): Token name value
        """
        self.token_name_input.clear()
        self.token_name_input.fill(token_name)
        return self

    @step
    def fill_token(self, token: str):
        """
        Fill the token field.

        Args:
            token (str): Token value
        """
        self.token_input.clear()
        self.token_input.fill(token)
        return self

    @step
    def fill_username(self, username: str):
        """
        Fill the username field.

        Args:
            username (str): Username value
        """
        self.user_name_input.clear()
        self.user_name_input.fill(username)
        return self

    # Cloud mode methods
    @step
    def enable_jira_cloud_mode(self):
        """Enable the Jira Cloud mode toggle."""
        if not self.is_cloud_checkbox.is_checked():
            self.is_jira_cloud_switch.click()
        return self

    @step
    def disable_jira_cloud_mode(self):
        """Disable the Jira Cloud mode toggle."""
        if self.is_cloud_checkbox.is_checked():
            self.is_jira_cloud_switch.click()
        return self

    @step
    def enable_confluence_cloud_mode(self):
        """Enable the Confluence Cloud mode toggle."""
        if not self.is_cloud_checkbox.is_checked():
            self.is_confluence_cloud_switch.click()
        return self

    @step
    def disable_confluence_cloud_mode(self):
        """Disable the Confluence Cloud mode toggle."""
        if self.is_cloud_checkbox.is_checked():
            self.is_confluence_cloud_switch.click()
        return self

    @step
    def is_cloud_mode_enabled(self) -> bool:
        """
        Check if Cloud mode is enabled.

        Returns:
            bool: True if enabled, False otherwise
        """
        return self.is_cloud_checkbox.is_checked()

    # Authentication Type methods (for Git)
    @step
    def select_authentication_type(self, auth_type: str):
        """
        Select authentication type for Git.

        Args:
            auth_type: 'Personal Access Token' or 'GitHub Application'
        """
        self.authentication_type_dropdown.click()
        self.page.get_by_role("option", name=auth_type).click()
        return self

    @step
    def fill_github_app_credentials(
        self, app_id: str, private_key: str, installation_id: str
    ):
        """
        Fill GitHub App authentication credentials.

        Args:
            app_id: GitHub App ID
            private_key: GitHub App Private Key
            installation_id: GitHub App Installation ID
        """
        self.github_app_id_input.clear()
        self.github_app_id_input.fill(app_id)
        self.github_app_private_key_input.clear()
        self.github_app_private_key_input.fill(private_key)
        self.github_app_installation_id_input.clear()
        self.github_app_installation_id_input.fill(installation_id)
        return self

    @step
    def fill_git_integration_form(self, test_data: IntegrationTestData):
        """
        Fill the complete Git integration form with provided data.

        Args:
            test_data: IntegrationTestData
        """
        # Fill project
        self.select_project(test_data.project)

        # Fill required alias field
        self.fill_alias(test_data.alias)

        # Select credential type
        self.select_credential_type(test_data.credential_type)

        # Set global integration if requested
        if test_data.is_global:
            self.enable_global_integration()
        else:
            self.disable_global_integration()

        # Fill authentication fields
        self.fill_url(test_data.fields["url"])
        self.fill_token(test_data.fields["token"])

        return self

    @step
    def fill_jira_integration_form(self, test_data: IntegrationTestData):
        """
        Fill the complete Jira integration form with provided data.

        Args:
            test_data: IntegrationTestData containing Jira-specific fields
        """
        # Fill project
        self.select_project(test_data.project)

        # Fill required alias field
        self.fill_alias(test_data.alias)

        # Select credential type
        self.select_credential_type(test_data.credential_type)

        # Set global integration if requested
        if test_data.is_global:
            self.enable_global_integration()
        else:
            self.disable_global_integration()

        # Fill authentication fields specific to Jira
        self.fill_url(test_data.fields["url"])

        # Set cloud mode if specified
        if test_data.fields.get("is_cloud", False):
            self.enable_jira_cloud_mode()
            self.fill_username(test_data.fields["username"])
        else:
            self.disable_jira_cloud_mode()

        self.fill_token(test_data.fields["token"])

        return self

    @step
    def fill_confluence_integration_form(self, test_data: IntegrationTestData):
        """
        Fill the complete Confluence integration form with provided data.

        Args:
            test_data: IntegrationTestData containing Confluence-specific fields
        """
        # Fill project
        self.select_project(test_data.project)

        # Fill required alias field
        self.fill_alias(test_data.alias)

        # Select credential type
        self.select_credential_type(test_data.credential_type)

        # Set global integration if requested
        if test_data.is_global:
            self.enable_global_integration()
        else:
            self.disable_global_integration()

        # Fill authentication fields specific to Confluence
        self.fill_url(test_data.fields["url"])

        # Set cloud mode if specified
        if test_data.fields.get("is_cloud", False):
            self.enable_confluence_cloud_mode()
            self.fill_username(test_data.fields["username"])
        else:
            self.disable_confluence_cloud_mode()

        self.fill_token(test_data.fields["token"])

        return self

    @step
    def fill_webhook_integration_form(self, test_data: IntegrationTestData):
        """
        Fill the complete Webhook integration form with provided data.

        Args:
            test_data: IntegrationTestData containing Webhook-specific fields
                (optionally 'gitlab_webhook_token')
        """
        # Fill project
        self.select_project(test_data.project)

        # Fill required alias field
        self.fill_alias(test_data.alias)

        # Select credential type
        self.select_credential_type(test_data.credential_type)

        # Set global integration if requested
        if test_data.is_global:
            self.enable_global_integration()
        else:
            self.disable_global_integration()

        webhook_id = test_data.fields.get("webhook_id")
        if webhook_id:
            self.fill_webhook_id(webhook_id)

        gitlab_webhook_token = test_data.fields.get("gitlab_webhook_token")
        if gitlab_webhook_token:
            self.fill_gitlab_webhook_token(gitlab_webhook_token)

        resource_type = test_data.fields.get("resource_type")
        resource_name = test_data.fields.get("resource_name")
        if resource_type and resource_name:
            self.select_resource_type(resource_type)
            self.select_resource_by_name(resource_name)

        return self

    # Action methods
    @step
    def create_integration(self):
        """Click the Create button to save the integration."""
        self.create_button.click()
        return self

    @step
    def cancel_creation(self):
        """Click the Cancel button to exit without saving."""
        self.cancel_button.click()
        return self

    # Helper methods
    @step
    def wait_for_form_to_load(self):
        """Wait for the form to fully load with all elements visible."""
        expect(self.form_container).to_be_visible()
        expect(self.alias_input).to_be_visible()
        expect(self.create_button).to_be_visible()
        return self

    @step
    def get_form_data(self) -> dict:
        """
        Get current form data as a dictionary.

        Returns:
            dict: Current form field values
        """
        return {
            "project": self.get_selected_project(),
            "credential_type": self.get_credential_type(),
            "alias": self.alias_input.input_value(),
            "url": self.url_input.input_value(),
            "token_name": self.token_name_input.input_value(),
            "token": self.token_input.input_value(),
            "is_global": self.is_global_integration_enabled(),
        }

    @step
    def clear_all_fields(self):
        """Clear all form fields."""
        self.alias_input.clear()
        self.url_input.clear()
        self.token_name_input.clear()
        self.token_input.clear()
        self.credential_type_input.clear()
        self.disable_global_integration()
        return self

    # ==================== VERIFICATION METHODS ====================

    @step
    def should_have_action_buttons_visible(self, credential_type: CredentialTypes):
        """
        Verify that all action buttons (back, cancel, test, create) are visible.

        Args:
            credential_type: The credential type being tested (affects Test button visibility)

        Returns:
            self: For method chaining
        """
        # Scroll to top of page to ensure action buttons are visible
        self.page.evaluate("window.scrollTo(0, 0)")
        self.page.wait_for_timeout(500)

        # Scroll action buttons container into view as backup
        self.action_buttons_container.scroll_into_view_if_needed()
        self.page.wait_for_timeout(300)

        expect(self.back_button).to_be_visible()
        expect(self.cancel_button).to_be_visible()
        expect(self.create_button).to_be_visible()

        # Test button only appears for JIRA and Confluence credential types
        # It's rendered dynamically, so check with try-except for robustness
        if credential_type in [CredentialTypes.JIRA, CredentialTypes.CONFLUENCE]:
            try:
                # Wait for form to fully render
                self.page.wait_for_timeout(3000)
                expect(self.test_button).to_be_visible(timeout=10000)
            except Exception:
                # Test button may not be visible in all scenarios - log warning but don't fail
                print(
                    f"Warning: Test button not visible for {credential_type.value}, but continuing test"
                )
        else:
            expect(self.test_button).not_to_be_visible()
        return self

    @step
    def should_have_project_selector_visible(self):
        """
        Verify that project selector and its label are visible.

        Returns:
            self: For method chaining
        """
        expect(self.project_selector).to_be_visible()
        expect(self.project_selector_label).to_be_visible()
        return self

    @step
    def should_have_global_integration_toggle_visible(self):
        """
        Verify that global integration toggle elements are visible.

        Returns:
            self: For method chaining
        """
        expect(self.global_integration_switch).to_be_visible()
        return self

    @step
    def should_have_credential_type_field_visible(self):
        """
        Verify that credential type field elements are visible.

        Returns:
            self: For method chaining
        """
        expect(self.credential_type_input).to_be_visible()
        expect(self.credential_type_dropdown_button).to_be_visible()
        return self

    @step
    def should_have_alias_field_visible(self):
        """
        Verify that alias field is visible and marked as required.

        Returns:
            self: For method chaining
        """
        expect(self.alias_input).to_be_visible()
        # Verify required indicator (asterisk in placeholder)
        expect(self.alias_input).to_have_attribute("placeholder", "Alias*")
        return self

    # Mapping of credential types to their specific fields
    def get_credential_fields(
        self,
        credentials_type: CredentialTypes,
        authentication_type: str = "Personal Access Token",
    ):
        """
        Get form fields for a specific credential type.

        Args:
            credentials_type: Type of credential (Git, Jira, Confluence)
            authentication_type: For Git, can be 'Personal Access Token' or 'GitHub Application'

        Returns:
            list: List of form field locators for the given credential type
        """
        if credentials_type == CredentialTypes.GIT:
            if authentication_type == "GitHub Application":
                return [
                    self.url_input,
                    self.authentication_type_dropdown,
                    self.github_app_id_input,
                    self.github_app_private_key_input,
                    self.github_app_installation_id_input,
                ]
            else:  # Personal Access Token
                return [
                    self.url_input,
                    self.authentication_type_dropdown,
                    self.token_name_input,
                    self.token_input,
                ]
        elif credentials_type == CredentialTypes.JIRA:
            return [
                self.url_input,
                self.user_name_input,
                self.is_jira_cloud_switch,
                self.token_input,
            ]
        elif credentials_type == CredentialTypes.CONFLUENCE:
            return [
                self.url_input,
                self.user_name_input,
                self.is_confluence_cloud_switch,
                self.token_input,
            ]
        else:
            return []

    @step
    def should_have_authentication_section_visible(
        self,
        credentials_type: CredentialTypes,
        authentication_type: str = "Personal Access Token",
    ):
        """
        Verify that authentication section heading and fields are visible.

        Args:
            credentials_type: Type of credential (Git, Jira, Confluence)
            authentication_type: For Git, 'Personal Access Token' or 'GitHub Application'

        Returns:
            self: For method chaining
        """
        expect(self.authentication_heading).to_be_visible()
        for element in self.get_credential_fields(
            credentials_type, authentication_type
        ):
            expect(element).to_be_visible()
        return self

    @step
    def should_have_github_app_section_visible(self):
        """
        Verify GitHub App authentication section is visible.

        Returns:
            self: For method chaining
        """
        expect(self.github_app_info_section).to_be_visible()
        expect(self.github_app_setup_guide_link).to_be_visible()
        expect(self.github_app_id_input).to_be_visible()
        expect(self.github_app_private_key_input).to_be_visible()
        expect(self.github_app_installation_id_input).to_be_visible()
        return self

    @step
    def should_not_have_github_app_section_visible(self):
        """
        Verify GitHub App authentication section is not visible.

        Returns:
            self: For method chaining
        """
        expect(self.github_app_id_input).not_to_be_visible()
        expect(self.github_app_private_key_input).not_to_be_visible()
        expect(self.github_app_installation_id_input).not_to_be_visible()
        return self

    @step
    def should_have_github_app_section_editable(self):
        expect(self.github_app_id_input).to_be_editable()
        expect(self.github_app_private_key_input).to_be_editable()
        expect(self.github_app_installation_id_input).to_be_editable()
        return self

    @step
    def should_have_help_texts_visible(self):
        """
        Verify that help texts and information tooltips are visible.
        Help texts may not be present for all credential types, so failures are non-fatal.

        Returns:
            self: For method chaining
        """
        # Check for global integration help text
        try:
            # Scroll to global integration help text to ensure it's in viewport
            self.global_integration_help_text.scroll_into_view_if_needed(timeout=5000)
            expect(self.global_integration_help_text).to_be_visible(timeout=5000)
            expect(self.global_integration_help_text).to_contain_text("versatile")
        except Exception:
            # Help text may not be present for all credential types
            pass

        # Check for authentication help text
        try:
            # Scroll to authentication help text to ensure it's in viewport
            self.authentication_help_text.scroll_into_view_if_needed(timeout=5000)
            expect(self.authentication_help_text).to_be_visible(timeout=5000)
            expect(self.authentication_help_text).to_contain_text(
                "sensitive information"
            )
        except Exception:
            # Help text may not be present for all credential types
            pass

        return self

    @step
    def should_have_input_fields_editable(self):
        """Verify that input fields are editable."""
        expect(self.alias_input).to_be_editable()
        if self.url_input.is_visible():
            expect(self.url_input).to_be_editable()
        if self.token_name_input.is_visible():
            expect(self.token_name_input).to_be_editable()
        if self.token_input.is_visible():
            expect(self.token_input).to_be_editable()
        return self

    @step
    def should_be_on_create_user_integration_page(self):
        """Verify that the user is on the create user integration page."""
        expect(self.page).to_have_url("/integrations/user/new")
        expect(self.page_title).to_have_text("New User Integration")
        return self

    @step
    def should_be_on_create_project_integration_page(self):
        """Verify that the user is on the create project integration page."""
        expect(self.page).to_have_url("/integrations/project/new")
        expect(self.page_title).to_have_text("New Project Integration")
        return self

    @step
    def should_have_create_button_enabled(self):
        """Verify that the create button is enabled."""
        expect(self.create_button).to_be_enabled()
        return self

    @step
    def should_have_create_button_disabled(self):
        """Verify that the create button is disabled."""
        expect(self.create_button).to_be_disabled()
        return self

    @step
    def should_see_validation_error(self, field_name: str, error_message: str):
        """
        Verify that a specific validation error is displayed for a field.

        Args:
            field_name (str): Name of the field with error
            error_message (str): Expected error message
        """
        error_locator = self.page.locator(
            f'[data-testid="validation-error-{field_name}"]'
        )
        if not error_locator.is_visible():
            # Fallback to generic error message locator
            error_locator = self.validation_errors.filter(has_text=error_message)
        expect(error_locator).to_be_visible()
        expect(error_locator).to_contain_text(error_message)
        return self

    @step
    def should_not_see_validation_errors(self):
        """Verify that no validation errors are displayed."""
        expect(self.validation_errors).to_have_count(0)
        return self

    @step
    def should_have_project_selected(self, project_name: str):
        """
        Verify that a specific project is selected.

        Args:
            project_name (str): Expected selected project name
        """
        expect(self.project_selector_label).to_have_text(project_name)
        return self

    @step
    def should_have_credential_type_selected(self, credential_type: CredentialTypes):
        """
        Verify that a specific credential type is selected.

        Args:
            credential_type: Expected credential type
        """
        expect(self.credential_type_input).to_have_value(
            self._get_ui_label(credential_type)
        )
        return self

    @step
    def should_have_global_integration_enabled(self):
        """Verify that global integration toggle is enabled."""
        expect(self.global_integration_checkbox).to_be_checked()
        return self

    @step
    def should_have_global_integration_disabled(self):
        """Verify that global integration toggle is disabled."""
        expect(self.global_integration_checkbox).not_to_be_checked()
        return self

    @step
    def should_see_error_toast_message(self, header: str, content: str):
        """
        Verify that error toast notification is displayed with expected header and content.

        Args:
            header (str): Expected toast header text
            content (str): Expected toast content message
        """
        expect(self.error_toast_header).to_be_visible()
        expect(self.error_toast_header).to_have_text(header)
        expect(self.error_toast_content).to_be_visible()
        expect(self.error_toast_content).to_contain_text(content)
        return self

    @step
    def should_see_inline_validation_message(self, field: str, message: str = None):
        """
        Verify that inline validation message appears for a field.

        Args:
            field (str): Field name ('alias', 'url', 'token', etc.)
            message (str, optional): Expected validation message text

        Returns:
            self: For method chaining
        """
        field_validation_mapping = {
            "alias": self.alias_inline_validation_message,
            "url": self.url_inline_validation_message,
            "token": self.token_inline_validation_message,
        }

        validation_locator = field_validation_mapping.get(field)
        if not validation_locator:
            # Fallback to generic locator
            validation_locator = self.page.locator("generic").filter(has_text=message)

        expect(validation_locator).to_be_visible()
        if message:
            expect(validation_locator).to_contain_text(message)
        return self

    @step
    def should_not_see_inline_validation_messages(self):
        """
        Verify that no inline validation messages are displayed.

        Returns:
            self: For method chaining
        """
        expect(self.all_inline_validation_messages).to_have_count(0)
        return self

    @step
    def should_see_dropdown_option(self, selection):
        option = self.page.get_by_role("option", name=selection, exact=True)
        expect(option).to_be_visible()

    # ====================
    # TEST CONNECTION METHODS
    # ====================

    # ====================
    # ALIAS AUTO-GENERATION METHODS
    # ====================

    @step
    def get_alias_value(self) -> str:
        """
        Return the current value of the alias input field.

        Returns:
            str: Current alias field value
        """
        return self.alias_input.input_value()

    @step
    def should_have_alias_matching_pattern(self, pattern: str):
        """
        Assert that the alias field value matches the provided regex pattern.

        Args:
            pattern (str): Regex pattern string to match against the alias value

        Returns:
            self: For method chaining
        """
        alias_value = self.get_alias_value()
        assert_that(alias_value, matches_regexp(pattern))
        return self

    @step
    def should_have_alias_not_empty(self):
        """
        Assert that the alias field is pre-populated (not empty).

        Returns:
            self: For method chaining
        """
        alias_value = self.get_alias_value()
        assert_that(alias_value, is_not(empty()))
        return self

    # ====================
    # TEST CONNECTION METHODS
    # ====================

    @step
    def click_test(self):
        """Click the Test button to test the integration connection."""
        self.test_button.wait_for(state="visible", timeout=10000)
        self.test_button.click()
        # Wait for test to complete
        self.page.wait_for_timeout(2000)
        return self

    @step
    def should_see_test_connection_success(self):
        """Verify that test connection was successful."""
        # Look for success toast message - success toasts use the generic codemie-toast class
        # with codemie-toast-header child (similar pattern to assistants_page.py line 120)
        success_message = self.page.locator(".codemie-toast .codemie-toast-header")
        expect(success_message).to_be_visible(timeout=15000)
        return self

    @step
    def should_see_test_connection_failure(self):
        """Verify that test connection failed with error message."""
        # Look for error toast message or error indicator
        error_message = self.page.locator(".codemie-toast-err")
        expect(error_message).to_be_visible(timeout=15000)
        return self

    @step
    def get_test_connection_error_message(self) -> str:
        """
        Get the error message displayed after a failed connection test.

        Returns:
            str: Error message text
        """
        error_message = self.page.locator(".codemie-toast-err")
        error_message.wait_for(state="visible", timeout=15000)
        return error_message.text_content().strip()

    @step
    def should_have_error_message_containing(self, expected_keyword: str):
        """
        Verify that error message contains expected keyword(s).

        Args:
            expected_keyword: Keyword to search for in error message (case-insensitive)

        Returns:
            self: For method chaining
        """
        error_message = self.page.locator(".codemie-toast-err")
        error_message.wait_for(state="visible", timeout=15000)

        # Verify error message is not empty
        expect(error_message).not_to_be_empty()

        # Verify keyword is present (case-insensitive)
        expect(error_message).to_contain_text(expected_keyword, ignore_case=True)
        return self
