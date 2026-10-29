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

import json
from urllib.parse import urlparse

from reportportal_client import step
from playwright.sync_api import expect

from codemie_test_harness.tests import CredentialsManager
from codemie_test_harness.tests.ui.pageobject.base_page import BasePage

# Pages marked as already visited in the onboarding tour, so the overrides below
# skip straight past it instead of replaying each step.
ONBOARDING_VISITED_PAGES = json.dumps(
    ["chat", "assistants", "workflows", "integrations", "datasources"]
)


class LoginPage(BasePage):
    """Login page object with property-based element locators."""

    page_url = "/"

    def __init__(self, page):
        super().__init__(page)

    # Page elements using @property decorator
    @property
    def username_input(self):
        """Username input field (Email address)."""
        return self.page.get_by_role("textbox", name="Email address")

    @property
    def password_input(self):
        """Password input field."""
        return self.page.get_by_role("textbox", name="Password")

    @property
    def submit_button(self):
        """Login submit button."""
        return self.page.get_by_role("button", name="Sign in to your account")

    @property
    def show_more_options_button(self):
        """Button/link to expand email/password login form."""
        return self.page.get_by_text("more options")

    @property
    def hide_options_button(self):
        """Button to collapse email/password login form."""
        return self.page.get_by_role("button", name="Hide sign-in options")

    @property
    def epam_sso_button(self):
        """Sign in with EPAM SSO button."""
        return self.page.get_by_role("button", name="Sign in with EPAM SSO")

    @property
    def login_form(self):
        """Main login form container."""
        return self.page.locator("form")

    @property
    def sign_in_heading(self):
        """Sign In heading."""
        return self.page.get_by_role("heading", name="Sign In")

    @property
    def error_message(self):
        """Error message display."""
        return self.page.locator("#input-error-username")

    # Navigation methods
    @step
    def navigate_to(self):
        """Navigate to the login page, retrying once after a delay on first timeout."""
        try:
            self.page.goto(self.page_url, timeout=60000)
        except Exception:
            self.page.wait_for_timeout(5000)
            self.page.goto(self.page_url, timeout=60000)
        return self

    @step
    def apply_onboarding_overrides(self, user_id, frontend_url: str):
        """Suppress the onboarding tour, AI popups, and the release popup via localStorage.

        Scoped to the frontend's origin via an init script, so the overrides apply
        regardless of which host (localhost or a remote environment) the test runs
        against without leaking into other origins the page may visit.
        """
        parsed = urlparse(frontend_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        self.page.add_init_script(f"""
            if (window.location.origin === '{origin}') {{
                localStorage.setItem('codemie-onboarding-completed', 'true');
                localStorage.setItem('{user_id}_onboarding-visited-pages', '{ONBOARDING_VISITED_PAGES}');
                localStorage.setItem('{user_id}_codemie-new-workflow-ai-popup', 'false');
                localStorage.setItem('codemie-new-asst-ai-popup', 'false');
                localStorage.setItem('disable-release-popup', 'true');
            }}
        """)
        return self

    @step
    def login_suppressing_popups(
        self, username: str, password: str, user_id, frontend_url: str
    ):
        """Full login flow: apply onboarding/popup overrides, then navigate and authenticate."""
        self.apply_onboarding_overrides(user_id, frontend_url)
        self.navigate_to()
        return self.login(username, password)

    # Action methods
    @step
    def expand_email_password_form(self):
        """Expand the email/password login form if not already visible."""
        if self.show_more_options_button.is_visible():
            self.show_more_options_button.click()
        return self

    @step
    def collapse_email_password_form(self):
        """Collapse the email/password login form."""
        if self.username_input.is_visible():
            self.hide_options_button.click()
            # Wait for form to be hidden
            self.username_input.wait_for(state="hidden", timeout=5000)
        return self

    @step
    def fill_username(self, username: str):
        """Fill the username field."""
        self.username_input.fill(username)
        return self

    @step
    def fill_password(self, password: str):
        """Fill the password field."""
        self.password_input.fill(password)
        return self

    @step
    def click_submit(self):
        """Click the submit button."""
        self.submit_button.click()
        return self

    @step
    def login(self, username: str, password: str):
        """Complete login process with username and password."""
        self.page.wait_for_load_state("networkidle", timeout=60000)
        self.expand_email_password_form()
        self.fill_username(username)
        self.fill_password(password)
        self.click_submit()
        # Wait for the full OAuth redirect chain to finish.
        # Timeout raised to 60 s to accommodate slow auth servers.
        self.page.wait_for_load_state("networkidle", timeout=60000)
        # Ensure the redirect chain has fully landed on the app (not still on the
        # Keycloak auth server).  networkidle can fire during a multi-hop OAuth
        # redirect; this guard prevents the AssistantsPage constructor's goto() from
        # racing with a still-pending server redirect.
        self.page.wait_for_url(lambda url: "openid-connect" not in url, timeout=60000)
        frontend_url = CredentialsManager.get_parameter("FRONTEND_URL", "")

        # Check if we got a 404 error page instead of the app. If so, redirect to frontend_url.
        try:
            self.page.locator("text=404 page not found").wait_for(
                timeout=3000, state="visible"
            )
            # 404 page detected, redirect to frontend_url
            if frontend_url:
                self.page.goto(frontend_url)
                self.page.wait_for_load_state("networkidle", timeout=60000)
        except Exception:
            # 404 page not found (good), we're on the app
            pass

        return BasePage(self.page)

    @step
    def click_epam_sso(self):
        """Click the EPAM SSO button."""
        self.epam_sso_button.click()
        return self

    # Verification methods
    @step
    def should_be_on_login_page(self):
        """Verify that we are on the login page.

        Checks for:
        - Sign In heading is visible
        - EPAM SSO button is visible (default option)
        - Show more options button is visible
        """
        expect(self.sign_in_heading).to_be_visible()
        expect(self.epam_sso_button).to_be_visible()
        expect(self.show_more_options_button).to_be_visible()
        return self

    @step
    def should_have_email_password_form_visible(self):
        """Verify that email/password form is expanded and visible."""
        expect(self.username_input).to_be_visible()
        expect(self.password_input).to_be_visible()
        expect(self.submit_button).to_be_visible()
        return self

    @step
    def should_not_have_email_password_form_visible(self):
        """Verify that email/password form is collapsed and not visible."""
        expect(self.username_input).not_to_be_visible()
        return self

    @step
    def should_have_error_message(self, error_text: str = None):
        """Verify that an error message is displayed."""
        expect(self.error_message).to_be_visible()
        if error_text:
            expect(self.error_message).to_contain_text(error_text)
        return self

    @step
    def should_not_have_error_message(self):
        """Verify that no error message is displayed."""
        expect(self.error_message).not_to_be_visible()
        return self
