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
UI Test Suite for Help Page
"""

from urllib.parse import urlparse

import pytest
from hamcrest import assert_that, contains_string

from codemie_test_harness.tests.ui.test_data.links_names_test_data import (
    AssistantNames,
    ExternalUrls,
    InternalUrls,
)
from codemie_test_harness.tests.ui.pageobject.chats.chat_page import ChatPage
from codemie_test_harness.tests.ui.pageobject.help_page import HelpPage


def _config_link(customer_config_utils, component_id: str) -> str:
    """Host and path of the link the platform config (GET /v1/config) sets for the component."""
    component = customer_config_utils.get_config_component(component_id)
    assert component, (
        f"Component '{component_id}' is not enabled in the platform config"
    )
    url = urlparse(component["settings"]["url"])
    return url.netloc + url.path


@pytest.mark.smoke
@pytest.mark.ui
@pytest.mark.help
def test_help_page_elements_persistence(page):
    """UI Test Suite for Help Page Elements Persistence"""
    # Navigate to Help page
    help_page = HelpPage(page)
    help_page.navigate_to()

    # Verify we are on the Help page
    help_page.should_be_on_help_page()

    # Verify all main sections are visible
    help_page.should_have_all_sections_visible()

    # Verify all cards are visible with their content
    help_page.should_have_all_cards_visible()


@pytest.mark.ui
@pytest.mark.help
def test_help_page_internal_links(page):
    """UI Test Suite for Help Page Internal Links"""
    help_page = HelpPage(page)
    chat_page = ChatPage(page)

    # Test AI/Run FAQ button - navigates to new chat
    help_page.navigate_to()
    help_page.should_be_on_help_page()
    help_page.click_ai_run_faq_button()
    help_page.should_navigate_to_url_containing(InternalUrls.CHATS)
    chat_page.should_have_chat_title(AssistantNames.AI_RUN_FAQ)

    # Test AI/Run Chatbot button - navigates to new chat
    help_page.navigate_to()
    help_page.should_be_on_help_page()
    help_page.click_ai_run_chatbot_button()
    help_page.should_navigate_to_url_containing(InternalUrls.CHATS)
    chat_page.should_have_chat_title(AssistantNames.AI_RUN_CHATBOT)

    # Test Release Notes button - navigates to release notes page
    help_page.navigate_to()
    help_page.should_be_on_help_page()
    help_page.click_release_notes_button()
    help_page.should_navigate_to_url_containing(InternalUrls.RELEASE_NOTES)

    # Test AI/Run Feedback button - navigates to new chat
    help_page.navigate_to()
    help_page.should_be_on_help_page()
    help_page.click_ai_run_feedback_button()
    help_page.should_navigate_to_url_containing(InternalUrls.CHATS)
    chat_page.should_have_chat_title(AssistantNames.AI_RUN_FEEDBACK)


@pytest.mark.ui
@pytest.mark.help
def test_help_page_external_links(page, customer_config_utils):
    """UI Test Suite for Help Page External Links"""
    help_page = HelpPage(page)
    help_page.navigate_to()
    help_page.should_be_on_help_page()

    # Test EPAM Video Portal button href
    video_portal_href = help_page.get_epam_video_portal_href()
    assert_that(
        video_portal_href,
        contains_string(_config_link(customer_config_utils, "videoPortal")),
    )

    # Test Documentation button href
    documentation_href = help_page.get_documentation_href()
    assert_that(documentation_href, contains_string(ExternalUrls.DOCUMENTATION))

    # Test YouTube Channel button href
    youtube_href = help_page.get_youtube_channel_href()
    assert_that(youtube_href, contains_string(ExternalUrls.YOUTUBE_CHANNEL))

    # Test CodeMie Learning Courses button href
    learning_courses_href = help_page.get_learning_courses_href()
    assert_that(
        learning_courses_href,
        contains_string(_config_link(customer_config_utils, "learningCourses")),
    )

    # Test Survey button href
    survey_href = help_page.get_survey_href()
    assert_that(survey_href, contains_string(ExternalUrls.SURVEY))
