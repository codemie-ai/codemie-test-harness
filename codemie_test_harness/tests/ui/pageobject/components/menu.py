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
Menu component page object for the main navigation menu.
Contains methods for interacting with navigation links, logo, and user profile.
"""

import re

from reportportal_client import step
from playwright.sync_api import expect


class Menu:
    """Menu component with property-based element locators."""

    def __init__(self, page):
        self.page = page

    # Menu elements using @property decorator
    @property
    def menu_container(self):
        """Main menu container."""
        return self.page.locator("//body//header")

    @property
    def logo_link(self):
        """Logo link element."""
        return self.menu_container.locator(
            "a.h-12.flex.grow.gap-4.items-center.relative.select-none.text-nowrap.cursor-pointer.group"
        )

    @property
    def logo_svg(self):
        """Logo SVG element."""
        return self.logo_link.locator("svg")

    @property
    def logo_tooltip(self):
        """Logo tooltip text whn menu is expanded."""
        return self.page.locator('a:has-text("EPAM AI/RUN"):has-text("CodeMie")')

    @property
    def top_nav(self):
        """Top navigation container."""
        return self.menu_container.locator('nav[aria-label="top-nav-links"]')

    @property
    def chats_link(self):
        """Chats navigation link."""
        return self.page.get_by_role("link", name="Chats")

    @property
    def assistants_link(self):
        """Assistants navigation link."""
        return self.page.get_by_role("link", name="Assistants")

    @property
    def workflows_link(self):
        """Workflows navigation link."""
        return self.page.get_by_role("link", name="Workflows")

    @property
    def applications_link(self):
        """Applications navigation link."""
        return self.page.get_by_role("link", name="Applications")

    @property
    def secondary_nav(self):
        """Secondary navigation container."""
        return self.menu_container.locator('nav[aria-label="secondary-nav-links"]')

    @property
    def integrations_link(self):
        """Integrations navigation link."""
        return self.page.get_by_role("link", name="Integrations")

    @property
    def data_sources_link(self):
        """Data Sources navigation link."""
        return self.page.get_by_role("link", name="Data Sources")

    @property
    def ai_katas_link(self):
        """AI Katas navigation link."""
        return self.page.get_by_role("link", name="AI Katas")

    @property
    def skills_link(self):
        """Skills navigation link."""
        return self.page.get_by_role("link", name="Skills")

    @property
    def analytics_link(self):
        """Analytics navigation link."""
        return self.page.get_by_role("link", name="Analytics")

    @property
    def bottom_nav(self):
        """Bottom navigation container."""
        return self.menu_container.locator('nav[aria-label="bottom-nav-links"]')

    @property
    def faq_link(self):
        """FAQ navigation link."""
        return self.bottom_nav.get_by_role("button", name="FAQ")

    @property
    def chatbot_link(self):
        """Chatbot navigation link."""
        return self.bottom_nav.get_by_role("button", name="Chatbot")

    @property
    def faq_assistant_link(self):
        """FAQ assistant navigation link (legacy)."""
        return self.bottom_nav.locator('a[href="/assistants/codemie-onboarding/start"]')

    @property
    def prompt_assistant_link(self):
        """Prompt Engineer assistant navigation link (legacy)."""
        return self.bottom_nav.locator('a[href="/assistants/prompt-engineer/start"]')

    @property
    def switch_new_codemie(self):
        """Switch to new CodeMie."""
        return self.menu_container.locator(".switch")

    @property
    def hide_expand_menu_button(self):
        """Hide/Expand menu button."""
        return self.menu_container.get_by_role(
            "button", name=re.compile(r"^(Hide|Show) Menu$")
        )

    @property
    def help_link(self):
        """Help navigation link."""
        return self.page.get_by_role("link", name="Help")

    @property
    def profile_link(self):
        """Profile navigation link."""
        return self.page.get_by_role("link", name="Profile")

    @property
    def user_profile_button(self):
        """User profile button."""
        return self.menu_container.locator("button.cursor-pointer.group")

    @property
    def user_avatar(self):
        """User avatar image."""
        return self.user_profile_button.locator("img")

    # Action methods
    @step
    def click_logo(self):
        """Click on the EPAM AI/Run logo to navigate to new chat."""
        self.logo_link.click()
        return self

    @step
    def navigate_to_chats(self):
        """Navigate to the Chats page."""
        self.chats_link.click()
        return self

    @step
    def navigate_to_assistants(self):
        """Navigate to the Assistants page."""
        self.assistants_link.click()
        return self

    @step
    def navigate_to_workflows(self):
        """Navigate to the Workflows page."""
        self.workflows_link.click()
        return self

    @step
    def navigate_to_applications(self):
        """Navigate to the Applications page."""
        self.applications_link.click()
        return self

    @step
    def navigate_to_integrations(self):
        """Navigate to the Integrations page."""
        self.integrations_link.click()
        return self

    @step
    def navigate_to_data_sources(self):
        """Navigate to the Data Sources page."""
        self.data_sources_link.click()
        return self

    @step
    def navigate_to_ai_katas(self):
        """Navigate to the AI Katas page."""
        self.ai_katas_link.click()
        return self

    @step
    def navigate_to_skills(self):
        """Navigate to the Skills page."""
        self.skills_link.click()
        return self

    @step
    def navigate_to_analytics(self):
        """Navigate to the Analytics page."""
        self.analytics_link.click()
        return self

    @step
    def navigate_to_faq(self):
        """Navigate to the FAQ page."""
        self.faq_link.click()
        return self

    @step
    def navigate_to_chatbot(self):
        """Navigate to the Chatbot page."""
        self.chatbot_link.click()
        return self

    @step
    def navigate_to_help(self):
        """Navigate to the Help page."""
        self.help_link.click()
        return self

    @step
    def navigate_to_profile(self):
        """Navigate to the Profile page."""
        self.profile_link.click()
        return self

    @step
    def click_user_profile(self):
        """Click on the user profile button."""
        self.user_profile_button.click()
        return self

    @step
    def click_hide_menu(self):
        """Click the hide/expand menu button."""
        self.hide_expand_menu_button.click()
        return self

    # Utility methods
    @step
    def get_active_navigation_item(self):
        """
        Get the currently active navigation item.
        Returns the href of the active navigation link.
        """
        active_link = self.menu_container.locator("a.bg-new-panel-secondary")
        if active_link.is_visible():
            return active_link.get_attribute("href")
        return None

    @step
    def get_user_avatar_src(self):
        """Get the source URL of the user avatar image."""
        return self.user_avatar.get_attribute("src")

    # Verification methods
    @step
    def should_be_visible(self):
        """Verify that the menu is visible."""
        expect(self.menu_container).to_be_visible()
        return self

    @step
    def should_have_logo_visible(self):
        """Verify that the logo is visible."""
        expect(self.logo_link).to_be_visible()
        return self

    @step
    def should_have_user_avatar_visible(self):
        """Verify that the user avatar is visible."""
        expect(self.user_avatar).to_be_visible()
        return self

    @step
    def should_have_navigation_item_active(self, page_path: str):
        """
        Verify that a specific navigation item is active.

        Args:
            page_path (str): The path to check (e.g., "/workflows/")
        """
        active_href = self.get_active_navigation_item()
        assert active_href == page_path, (
            f"Expected active navigation item to be '{page_path}', but got '{active_href}'"
        )
        return self

    @step
    def should_have_complete_navigation_structure(self):
        """
        Verify that all main navigation elements are present and visible.
        Checks all navigation links and core UI elements.
        """
        # Core elements
        expect(self.menu_container).to_be_visible()
        expect(self.logo_link).to_be_visible()

        # Main navigation links
        expect(self.chats_link).to_be_visible()
        expect(self.assistants_link).to_be_visible()
        expect(self.workflows_link).to_be_visible()
        expect(self.applications_link).to_be_visible()

        # Secondary navigation links
        expect(self.integrations_link).to_be_visible()
        expect(self.data_sources_link).to_be_visible()
        expect(self.ai_katas_link).to_be_visible()
        expect(self.skills_link).to_be_visible()
        expect(self.analytics_link).to_be_visible()

        # Bottom navigation links
        expect(self.faq_link).to_be_visible()
        expect(self.chatbot_link).to_be_visible()
        expect(self.help_link).to_be_visible()

        # Control elements
        expect(self.user_profile_button).to_be_visible()
        expect(self.hide_expand_menu_button).to_be_visible()

        return self

    @step
    def should_have_tooltip_visible(self, tooltip_text: str):
        """Verify that a specific tooltip is visible."""
        tooltip = self.page.locator(f'span:has-text("{tooltip_text}")')
        expect(tooltip).to_be_visible()
        return self

    # Legacy methods for backward compatibility
    @step
    def is_menu_visible(self):
        """Check if the menu is visible on the page."""
        return self.menu_container.is_visible()

    @step
    def is_logo_visible(self):
        """Check if the logo is visible."""
        return self.logo_link.is_visible()

    @step
    def is_user_avatar_visible(self):
        """Check if the user avatar is visible."""
        return self.user_avatar.is_visible()

    @step
    def is_navigation_item_active(self, page_path: str):
        """
        Check if a specific navigation item is active.

        Args:
            page_path (str): The path to check (e.g., "/workflows/")

        Returns:
            bool: True if the navigation item is currently active
        """
        active_href = self.get_active_navigation_item()
        return active_href == page_path if active_href else False

    @step
    def verify_navigation_structure(self):
        """
        Verify that all main navigation elements are present.

        Returns:
            dict: A dictionary with the visibility status of each navigation section
        """
        return {
            "menu_visible": self.menu_container.is_visible(),
            "logo_visible": self.logo_link.is_visible(),
            "top_nav_visible": self.top_nav.is_visible(),
            "secondary_nav_visible": self.secondary_nav.is_visible(),
            "bottom_nav_visible": self.bottom_nav.is_visible(),
            "user_profile_visible": self.user_profile_button.is_visible(),
            "chats_link_visible": self.chats_link.is_visible(),
            "assistants_link_visible": self.assistants_link.is_visible(),
            "workflows_link_visible": self.workflows_link.is_visible(),
            "applications_link_visible": self.applications_link.is_visible(),
            "integrations_link_visible": self.integrations_link.is_visible(),
            "data_sources_link_visible": self.data_sources_link.is_visible(),
            "ai_katas_link_visible": self.ai_katas_link.is_visible(),
            "skills_link_visible": self.skills_link.is_visible(),
            "analytics_link_visible": self.analytics_link.is_visible(),
            "help_link_visible": self.help_link.is_visible(),
            "faq_assistant_link_visible": self.faq_assistant_link.is_visible(),
            "prompt_assistant_link_visible": self.prompt_assistant_link.is_visible(),
            "switch_to_new_codemie_visible": self.switch_new_codemie.is_visible(),
            "hide_expand_menu_visible": self.hide_expand_menu_button.is_visible(),
        }
