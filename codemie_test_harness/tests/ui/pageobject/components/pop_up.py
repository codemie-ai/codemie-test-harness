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

from reportportal_client import step
from playwright.sync_api import expect


class PopUp:
    """Pop-up component with property-based element locators."""

    def __init__(self, page):
        self.page = page

    # Pop-up elements using @property decorator
    @property
    def pop_up(self):
        """Main pop-up container."""
        return self.page.locator(".popup")

    @property
    def menu(self):
        """Pop-up menu text."""
        return self.pop_up.locator(".popup-header")

    @property
    def body(self):
        """Pop-up body content."""
        return self.pop_up.locator(".text-center")

    @property
    def submit_button(self):
        """Primary submit button."""
        return self.pop_up.locator(".primary")

    @property
    def cancel_button(self):
        """Secondary cancel button."""
        return self.pop_up.locator(".secondary")

    @property
    def close_button(self):
        """Close button (X)."""
        return self.pop_up.locator(".close-btn")

    # Legacy properties for backward compatibility
    @property
    def submit(self):
        """Alias for submit_button."""
        return self.submit_button

    @property
    def cancel(self):
        """Alias for cancel_button."""
        return self.cancel_button

    @property
    def close(self):
        """Alias for close_button."""
        return self.close_button

    # Action methods
    @step
    def click_submit(self):
        """Click the submit button."""
        self.submit_button.click()
        return self

    @step
    def click_cancel(self):
        """Click the cancel button."""
        self.cancel_button.click()
        return self

    @step
    def click_close(self):
        """Click the close button."""
        self.close_button.click()
        return self

    @step
    def close_popup(self):
        """Close the pop-up using the close button."""
        self.close_button.click()
        return self

    # Verification methods
    @step
    def should_be_visible(self):
        """Verify that the pop-up is visible."""
        expect(self.pop_up).to_be_visible()
        return self

    @step
    def should_be_hidden(self):
        """Verify that the pop-up is hidden."""
        expect(self.pop_up).to_be_hidden()
        return self

    @step
    def should_have_header(self, expected_text: str):
        """Verify the pop-up header text."""
        expect(self.header).to_have_text(expected_text)
        return self

    @step
    def should_have_body(self, expected_text: str):
        """Verify the pop-up body text."""
        expect(self.body).to_have_text(expected_text)
        return self

    @step
    def should_have_submit_button(self, expected_text: str = None):
        """Verify the submit button is visible and optionally check its text."""
        expect(self.submit_button).to_be_visible()
        if expected_text:
            expect(self.submit_button).to_have_text(expected_text)
        return self

    @step
    def should_have_cancel_button(self, expected_text: str = None):
        """Verify the cancel button is visible and optionally check its text."""
        expect(self.cancel_button).to_be_visible()
        if expected_text:
            expect(self.cancel_button).to_have_text(expected_text)
        return self

    @step
    def should_have_close_button(self):
        """Verify the close button is visible."""
        expect(self.close_button).to_be_visible()
        return self
