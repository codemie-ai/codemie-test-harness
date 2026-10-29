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
Help page object with property-based element locators.
Contains methods for interacting with help page sections, cards, and navigation.
"""

import re

from playwright.sync_api import expect, Locator
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.available_models_page import (
    AvailableModelsPage,
)
from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver


class HelpPage(BasePage):
    """Help page object with property-based element locators."""

    page_url = "/help"

    def __init__(self, page):
        super().__init__(page)

    # Page header elements
    @property
    def page_title(self) -> Locator:
        """Main page title 'Help Center'."""
        return self.page.locator("h1").filter(has_text="Help Center")

    @property
    def page_subtitle(self) -> Locator:
        """Page subtitle text."""
        return self.page.locator("p").filter(
            has_text="Your go-to place for assistance, learning, and updates."
        )

    # Section headers
    @property
    def ai_help_section_header(self) -> Locator:
        """AI Help section header."""
        return self.page.locator("h2").filter(has_text="AI Help")

    @property
    def ai_help_section_description(self) -> Locator:
        """AI Help section description."""
        return self.page.locator("p").filter(
            has_text="Get instant support from our smart tools."
        )

    @property
    def learning_resources_section_header(self) -> Locator:
        """Learning Resources section header."""
        return self.page.locator("h2").filter(has_text="Learning Resources")

    @property
    def learning_resources_section_description(self) -> Locator:
        """Learning Resources section description."""
        return self.page.locator("p").filter(
            has_text="Explore guides and videos to get the most out of the platform."
        )

    @property
    def product_updates_section_header(self) -> Locator:
        """Product Updates section header."""
        return self.page.locator("h2").filter(has_text="Product Updates")

    @property
    def product_updates_section_description(self) -> Locator:
        """Product Updates section description."""
        return self.page.locator("p").filter(
            has_text="Track what's new, and what's improved!"
        )

    @property
    def share_experience_section_header(self) -> Locator:
        """Share experience section header."""
        return self.page.locator("h2").filter(has_text="Share experience")

    # AI Help section cards
    @property
    def ai_run_faq_card(self) -> Locator:
        """AI/Run FAQ card."""
        return self.page.locator("h3").filter(has_text="AI/Run FAQ").locator("..")

    @property
    def ai_run_faq_title(self) -> Locator:
        """AI/Run FAQ card title."""
        return self.page.locator("h3").filter(has_text="AI/Run FAQ")

    @property
    def ai_run_faq_description(self) -> Locator:
        """AI/Run FAQ card description."""
        return self.page.locator("p").filter(
            has_text="This is smart CodeMie assistant which can help you with onboarding process"
        )

    @property
    def ai_run_faq_button(self) -> Locator:
        """Chat Now button on AI/Run FAQ card."""
        return self.page.locator(
            "//h3[contains(text(), 'AI/Run FAQ')]/ancestor::a//button[contains(text(), 'Chat Now')]"
        )

    @property
    def ai_run_chatbot_card(self) -> Locator:
        """AI/Run Chatbot card."""
        return self.page.locator("h3").filter(has_text="AI/Run Chatbot").locator("..")

    @property
    def ai_run_chatbot_title(self) -> Locator:
        """AI/Run Chatbot card title."""
        return self.page.locator("h3").filter(has_text="AI/Run Chatbot")

    @property
    def ai_run_chatbot_description(self) -> Locator:
        """AI/Run Chatbot card description."""
        return self.page.locator("p").filter(
            has_text="AI/Run Chatbot, the ultimate solution for real-time interactions"
        )

    @property
    def ai_run_chatbot_button(self) -> Locator:
        """Chat Now button on AI/Run Chatbot card."""
        return self.page.locator(
            "//h3[contains(text(), 'AI/Run Chatbot')]/ancestor::a//button[contains(text(), 'Chat Now')]"
        )

    # Learning Resources section cards
    @property
    def epam_video_portal_card(self) -> Locator:
        """EPAM Video Portal card."""
        return (
            self.page.locator("h3").filter(has_text="EPAM Video Portal").locator("..")
        )

    @property
    def epam_video_portal_title(self) -> Locator:
        """EPAM Video Portal card title."""
        return self.page.locator("h3").filter(has_text="EPAM Video Portal")

    @property
    def epam_video_portal_description(self) -> Locator:
        """EPAM Video Portal card description."""
        return self.page.locator("p").filter(
            has_text="Short tutorials, walkthroughs, and product tips."
        )

    @property
    def epam_video_portal_button(self) -> Locator:
        """Explore button on EPAM Video Portal card."""
        return self.page.locator(
            "//h3[contains(text(), 'EPAM Video Portal')]/ancestor::a//button[contains(text(), 'Explore')]"
        )

    @property
    def documentation_card(self) -> Locator:
        """Documentation card."""
        return self.page.locator("h3").filter(has_text="Documentation").locator("..")

    @property
    def documentation_title(self) -> Locator:
        """Documentation card title."""
        return self.page.locator("h3").filter(has_text="Documentation")

    @property
    def documentation_description(self) -> Locator:
        """Documentation card description."""
        return self.page.locator("p").filter(
            has_text="A source for getting started, platform and deployment guides"
        )

    @property
    def documentation_button(self) -> Locator:
        """View Docs button on Documentation card."""
        return self.page.locator(
            "//h3[contains(text(), 'Documentation')]/ancestor::a//button[contains(text(), 'View Docs')]"
        )

    @property
    def youtube_channel_card(self) -> Locator:
        """YouTube Channel card."""
        return self.page.locator("h3").filter(has_text="YouTube Channel").locator("..")

    @property
    def youtube_channel_title(self) -> Locator:
        """YouTube Channel card title."""
        return self.page.locator("h3").filter(has_text="YouTube Channel")

    @property
    def youtube_channel_description(self) -> Locator:
        """YouTube Channel card description."""
        return self.page.locator("p").filter(
            has_text="Watch tutorials and product guides on our YouTube channel."
        )

    @property
    def youtube_channel_button(self) -> Locator:
        """Explore button on YouTube Channel card."""
        return self.page.locator(
            "//h3[contains(text(), 'YouTube Channel')]/ancestor::a//button[contains(text(), 'Explore')]"
        )

    @property
    def learning_courses_card(self) -> Locator:
        """CodeMie Learning Courses card."""
        return (
            self.page.locator("h3")
            .filter(has_text="CodeMie Learning Courses")
            .locator("..")
        )

    @property
    def learning_courses_title(self) -> Locator:
        """CodeMie Learning Courses card title."""
        return self.page.locator("h3").filter(has_text="CodeMie Learning Courses")

    @property
    def learning_courses_description(self) -> Locator:
        """CodeMie Learning Courses card description."""
        return self.page.locator("p").filter(
            has_text="Explore comprehensive courses to deepen your knowledge and skills"
        )

    @property
    def learning_courses_button(self) -> Locator:
        """Open Courses button on CodeMie Learning Courses card."""
        return self.page.locator(
            "//h3[contains(text(), 'CodeMie Learning Courses')]/ancestor::a//button[contains(text(), 'Open Courses')]"
        )

    # Product Updates section cards
    @property
    def release_notes_card(self) -> Locator:
        """Release Notes card."""
        return self.page.locator("h3").filter(has_text="Release Notes").locator("..")

    @property
    def release_notes_title(self) -> Locator:
        """Release Notes card title."""
        return self.page.locator("h3").filter(has_text="Release Notes")

    @property
    def release_notes_description(self) -> Locator:
        """Release Notes card description."""
        return self.page.locator("p").filter(
            has_text="View the latest changes, fixes, and enhancements."
        )

    @property
    def release_notes_button(self) -> Locator:
        """See What's New button on Release Notes card."""
        return self.page.locator(
            "//h3[contains(text(), 'Release Notes')]/ancestor::a//button[contains(text(), 'See What')]"
        )

    # Share experience section cards
    @property
    def ai_run_feedback_card(self) -> Locator:
        """AI/Run Feedback card."""
        return self.page.locator("h3").filter(has_text="AI/Run Feedback").locator("..")

    @property
    def ai_run_feedback_title(self) -> Locator:
        """AI/Run Feedback card title."""
        return self.page.locator("h3").filter(has_text="AI/Run Feedback")

    @property
    def ai_run_feedback_description(self) -> Locator:
        """AI/Run Feedback card description."""
        return self.page.locator("p").filter(
            has_text="CodeMie assistant to report bugs and improvements into CodeMie Jira"
        )

    @property
    def ai_run_feedback_button(self) -> Locator:
        """Chat Now button on AI/Run Feedback card."""
        return self.page.locator(
            "//h3[contains(text(), 'AI/Run Feedback')]/ancestor::a//button[contains(text(), 'Chat Now')]"
        )

    @property
    def survey_card(self) -> Locator:
        """Survey card."""
        return self.page.locator("h3").filter(has_text="Survey").locator("..")

    @property
    def survey_title(self) -> Locator:
        """Survey card title."""
        return self.page.locator("h3").filter(has_text="Survey")

    @property
    def survey_description(self) -> Locator:
        """Survey card description."""
        return self.page.locator("p").filter(
            has_text="Fill out a survey to share your experience using CodeMie."
        )

    @property
    def survey_button(self) -> Locator:
        """Open Survey button on Survey card."""
        return self.page.locator(
            "//h3[contains(text(), 'Survey')]/ancestor::a//button[contains(text(), 'Open Survey')]"
        )

    # Interactive Tours section
    @property
    def interactive_tours_section_header(self) -> Locator:
        """Interactive Tours section header."""
        return self.page.locator("h2").filter(has_text="Interactive Tours")

    @property
    def interactive_tours_section_description(self) -> Locator:
        """Interactive Tours section description."""
        return self.page.locator("p").filter(
            has_text="Learn CodeMie features through guided, interactive tutorials."
        )

    @property
    def navigation_tour_title(self) -> Locator:
        return self.page.locator("h3").filter(
            has_text="Navigation & Core Features Tour"
        )

    @property
    def navigation_tour_description(self) -> Locator:
        return self.page.locator("p").filter(
            has_text="Complete walkthrough of the CodeMie navigation bar and all available features"
        )

    @property
    def chat_interface_tour_title(self) -> Locator:
        return self.page.locator("h3").filter(
            has_text="Chat Interface & First Conversation"
        )

    @property
    def chat_interface_tour_description(self) -> Locator:
        return self.page.locator("p").filter(
            has_text="Learn how to use the chat interface, start conversations with assistants"
        )

    @property
    def assistants_overview_tour_title(self) -> Locator:
        return self.page.locator("h3").filter(has_text="Assistants Overview & Creation")

    @property
    def assistants_overview_tour_description(self) -> Locator:
        return self.page.locator("p").filter(
            has_text="Explore the assistants catalog, understand capabilities"
        )

    @property
    def connect_integration_tour_title(self) -> Locator:
        return self.page.locator("h3").filter(has_text="Connect Your First Integration")

    @property
    def connect_integration_tour_description(self) -> Locator:
        return self.page.locator("p").filter(
            has_text="Walk through the integration form and configure Jira, Git, Plugin"
        )

    @property
    def add_datasource_tour_title(self) -> Locator:
        return self.page.locator("h3").filter(has_text="Add Your First Data Source")

    @property
    def add_datasource_tour_description(self) -> Locator:
        return self.page.locator("p").filter(
            has_text="Connect a data source to give assistants access to your organization"
        )

    @property
    def datasources_list_tour_title(self) -> Locator:
        return self.page.locator("h3").filter(has_text="Data Sources List & Indexing")

    @property
    def datasources_list_tour_description(self) -> Locator:
        return self.page.locator("p").filter(
            has_text="Learn how to monitor indexing status, trigger reindexing"
        )

    # Navigation methods
    @step
    def navigate_to(self):
        """Navigate to the Help page."""
        self.page.goto(self.page_url)
        self.wait_for_page_load()
        return self

    @step
    def navigate_to_available_models(self):
        """Navigate directly to the Available Models catalog page (/help/models)."""
        self.page.goto("/help/models")
        self.wait_for_page_load()
        return AvailableModelsPage(self.page)

    # Action methods
    @step
    def click_ai_run_faq_button(self):
        """Click the Chat Now button on AI/Run FAQ card."""
        self.ai_run_faq_button.click()
        return self

    @step
    def click_ai_run_chatbot_button(self):
        """Click the Chat Now button on AI/Run Chatbot card."""
        self.ai_run_chatbot_button.click()
        return self

    @step
    def click_epam_video_portal_button(self):
        """Click the Explore button on EPAM Video Portal card."""
        self.epam_video_portal_button.click()
        return self

    @step
    def click_documentation_button(self):
        """Click the View Docs button on Documentation card."""
        self.documentation_button.click()
        return self

    @step
    def click_youtube_channel_button(self):
        """Click the Explore button on YouTube Channel card."""
        self.youtube_channel_button.click()
        return self

    @step
    def click_learning_courses_button(self):
        """Click the Open Courses button on CodeMie Learning Courses card."""
        self.learning_courses_button.click()
        return self

    @step
    def click_release_notes_button(self):
        """Click the See What's New button on Release Notes card."""
        self.release_notes_button.click()
        return self

    @step
    def click_ai_run_feedback_button(self):
        """Click the Chat Now button on AI/Run Feedback card."""
        self.ai_run_feedback_button.click()
        return self

    @step
    def click_survey_button(self):
        """Click the Open Survey button on Survey card."""
        self.survey_button.click()
        return self

    # Verification methods
    @step
    def should_be_on_help_page(self):
        """Verify that we are on the help page."""
        expect(self.page_title).to_be_visible(timeout=15000)
        expect(self.page_subtitle).to_be_visible(timeout=15000)
        return self

    @step
    def should_have_all_sections_visible(self):
        """Verify that all main sections are visible."""
        expect(self.ai_help_section_header).to_be_visible(timeout=15000)
        expect(self.ai_help_section_description).to_be_visible()
        expect(self.learning_resources_section_header).to_be_visible()
        expect(self.learning_resources_section_description).to_be_visible()
        expect(self.product_updates_section_header).to_be_visible()
        expect(self.product_updates_section_description).to_be_visible()
        if not EnvironmentResolver.is_localhost():
            expect(self.share_experience_section_header).to_be_visible()
        expect(self.interactive_tours_section_header).to_be_visible()
        expect(self.interactive_tours_section_description).to_be_visible()
        return self

    @step
    def should_have_ai_help_cards_visible(self):
        """Verify that AI Help section cards are visible."""
        expect(self.ai_run_faq_card).to_be_visible()
        expect(self.ai_run_faq_title).to_be_visible()
        expect(self.ai_run_faq_description).to_be_visible()
        expect(self.ai_run_faq_button).to_be_visible()

        expect(self.ai_run_chatbot_card).to_be_visible()
        expect(self.ai_run_chatbot_title).to_be_visible()
        expect(self.ai_run_chatbot_description).to_be_visible()
        expect(self.ai_run_chatbot_button).to_be_visible()
        return self

    @step
    def should_have_learning_resources_cards_visible(self):
        """Verify that Learning Resources section cards are visible."""
        if not EnvironmentResolver.is_localhost():
            expect(self.epam_video_portal_card).to_be_visible()
            expect(self.epam_video_portal_title).to_be_visible()
            expect(self.epam_video_portal_description).to_be_visible()
            expect(self.epam_video_portal_button).to_be_visible()

        expect(self.documentation_card).to_be_visible()
        expect(self.documentation_title).to_be_visible()
        expect(self.documentation_description).to_be_visible()
        expect(self.documentation_button).to_be_visible()

        expect(self.youtube_channel_card).to_be_visible()
        expect(self.youtube_channel_title).to_be_visible()
        expect(self.youtube_channel_description).to_be_visible()
        expect(self.youtube_channel_button).to_be_visible()

        expect(self.learning_courses_card).to_be_visible()
        expect(self.learning_courses_title).to_be_visible()
        expect(self.learning_courses_description).to_be_visible()
        expect(self.learning_courses_button).to_be_visible()
        return self

    @step
    def should_have_product_updates_cards_visible(self):
        """Verify that Product Updates section cards are visible."""
        expect(self.release_notes_card).to_be_visible()
        expect(self.release_notes_title).to_be_visible()
        expect(self.release_notes_description).to_be_visible()
        expect(self.release_notes_button).to_be_visible()
        return self

    @step
    def should_have_share_experience_cards_visible(self):
        """Verify that Share experience section cards are visible."""
        if not EnvironmentResolver.is_localhost():
            expect(self.ai_run_feedback_card).to_be_visible()
            expect(self.ai_run_feedback_title).to_be_visible()
            expect(self.ai_run_feedback_description).to_be_visible()
            expect(self.ai_run_feedback_button).to_be_visible()

            expect(self.survey_card).to_be_visible()
            expect(self.survey_title).to_be_visible()
            expect(self.survey_description).to_be_visible()
            expect(self.survey_button).to_be_visible()
        return self

    @step
    def should_have_interactive_tours_cards_visible(self):
        """Verify that Interactive Tours section cards are visible."""
        expect(self.navigation_tour_title).to_be_visible()
        expect(self.navigation_tour_description).to_be_visible()

        expect(self.chat_interface_tour_title).to_be_visible()
        expect(self.chat_interface_tour_description).to_be_visible()

        expect(self.assistants_overview_tour_title).to_be_visible()
        expect(self.assistants_overview_tour_description).to_be_visible()

        expect(self.connect_integration_tour_title).to_be_visible()
        expect(self.connect_integration_tour_description).to_be_visible()

        expect(self.add_datasource_tour_title).to_be_visible()
        expect(self.add_datasource_tour_description).to_be_visible()

        expect(self.datasources_list_tour_title).to_be_visible()
        expect(self.datasources_list_tour_description).to_be_visible()
        return self

    @step
    def should_have_all_cards_visible(self):
        """Verify that all cards on the page are visible."""
        self.should_have_ai_help_cards_visible()
        self.should_have_learning_resources_cards_visible()
        self.should_have_product_updates_cards_visible()
        self.should_have_share_experience_cards_visible()
        self.should_have_interactive_tours_cards_visible()
        return self

    @step
    def should_navigate_to_url_containing(self, url_part: str):
        """Verify that navigation occurred to a URL containing the expected part."""
        expect(self.page).to_have_url(re.compile(re.escape(url_part)), timeout=10000)
        return self

    # Methods to get href attributes for external links
    @step
    def get_epam_video_portal_href(self) -> str:
        """Get the href attribute from EPAM Video Portal card link."""
        link_locator = self.page.locator(
            "//h3[contains(text(), 'EPAM Video Portal')]/ancestor::a"
        )
        return link_locator.get_attribute("href")

    @step
    def get_documentation_href(self) -> str:
        """Get the href attribute from Documentation card link."""
        link_locator = self.page.locator(
            "//h3[contains(text(), 'Documentation')]/ancestor::a"
        )
        return link_locator.get_attribute("href")

    @step
    def get_youtube_channel_href(self) -> str:
        """Get the href attribute from YouTube Channel card link."""
        link_locator = self.page.locator(
            "//h3[contains(text(), 'YouTube Channel')]/ancestor::a"
        )
        return link_locator.get_attribute("href")

    @step
    def get_learning_courses_href(self) -> str:
        """Get the href attribute from CodeMie Learning Courses card link."""
        link_locator = self.page.locator(
            "//h3[contains(text(), 'CodeMie Learning Courses')]/ancestor::a"
        )
        return link_locator.get_attribute("href")

    @step
    def get_survey_href(self) -> str:
        """Get the href attribute from Survey card link."""
        link_locator = self.page.locator("//h3[contains(text(), 'Survey')]/ancestor::a")
        return link_locator.get_attribute("href")
