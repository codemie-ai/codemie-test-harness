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
UI Test Suite for Assistant Marketplace Feature

This test suite implements UI automated tests for the Assistant Marketplace
following Page Object Model (POM) best practices.

Test Coverage:
- Assistant Marketplace browsing
- Publishing assistants to marketplace
- Ratings and feedback visibility
- Marketplace filtering (Categories, Created By)
- Marketplace search
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.assistants.assistants_page import (
    AssistantsPage,
)
from codemie_test_harness.tests.ui.pageobject.assistants.assistants_marketplace_page import (
    AssistantsMarketplacePage,
)
from codemie_test_harness.tests.ui.pageobject.assistants.create_edit_assistant_page import (
    CreateEditAssistantPage,
)
from codemie_test_harness.tests.ui.test_data.assistant_test_data import (
    get_marketplace_assistant_data,
    get_sub_assistant_marketplace_data,
)
from codemie_test_harness.tests.utils.logger_util import setup_logger

logger = setup_logger(__name__)


@pytest.fixture
def parent_with_published_and_unpublished_sub_assistants(
    assistant_factory, assistant_utils
):
    """Parent assistant with one sub-assistant already on Marketplace and one private.

    Created via API. The published sub-assistant is unpublished on teardown so the
    shared Marketplace is not polluted; assistants are deleted by assistant_factory.
    """
    test_data = get_sub_assistant_marketplace_data()
    published_sub_assistant = assistant_factory.create(
        assistant_name=test_data.published_sub_assistant_name
    )
    unpublished_sub_assistant = assistant_factory.create(
        assistant_name=test_data.unpublished_sub_assistant_name
    )
    assistant_utils.publish_assistant_to_marketplace(
        published_sub_assistant.id,
        categories=["quality-assurance"],
        ignore_recommendations=True,
    )
    try:
        assistant_factory.create(
            assistant_name=test_data.parent_name,
            assistant_ids=[published_sub_assistant.id, unpublished_sub_assistant.id],
        )
        yield test_data
    finally:
        try:
            assistant_utils.unpublish_assistant_from_marketplace(
                published_sub_assistant.id
            )
        except Exception as e:
            logger.error(
                f"Failed to unpublish assistant {published_sub_assistant.id}: {e}"
            )


@pytest.mark.sanity
@pytest.mark.assistant
@pytest.mark.ui
def test_assistants_marketplace_page_elements_visibility(page):
    """
    Test #1: Verify Marketplace page loads with browse UI.

    AC: Browse Assistant Marketplace page - Page structure and navigation.
    """
    # Navigate to Assistants page first
    assistants_page = AssistantsPage(page)
    assistants_page.navigate_to()

    # Switch to Marketplace tab
    marketplace_page = assistants_page.switch_to_marketplace_tab()

    # Verify on Marketplace page
    marketplace_page.should_be_on_marketplace_page()

    # Verify marketplace elements are visible
    marketplace_page.should_have_marketplace_elements_visible()
    marketplace_page.should_have_filters_visible()

    # Verify marketplace displays assistant cards
    marketplace_page.should_display_assistants()

    # Verify assistants count is greater than 0
    marketplace_page.should_have_assistant_count_number()

    # Verify assistant card elements are visible
    marketplace_page.should_have_assistant_card_elements_visible()


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.assistant
@pytest.mark.ui
def test_publish_assistant_to_marketplace(page):
    """
    Test #2: Verify Marketplace publish dialog and category selection.

    Final AI quality validation and publish behavior are covered at backend level
    and are intentionally not triggered here.
    """
    # Navigate to assistants list
    assistants_page = AssistantsPage(page)
    assistants_page.navigate_to()

    # Create a private assistant
    test_data = get_marketplace_assistant_data()
    create_page = CreateEditAssistantPage(page)
    create_page.navigate_to()

    create_page.create_assistant(
        name=test_data.name,
        description=test_data.description,
        system_prompt=test_data.system_prompt,
        shared=False,
    )

    # Search for the newly created assistant
    assistants_page.should_see_assistant_with_name(test_data.name)

    # Click publish from 3-dot menu
    assistants_page.publish_assistant_to_marketplace(test_data.name)

    # Verify publish dialog and category selection
    assistants_page.publish_confirm_dialog_should_be_visible()
    assistants_page.select_category_in_publish_dialog()


@pytest.mark.assistant
@pytest.mark.ui
def test_marketplace_ratings_and_feedback_visibility(page):
    """
    Test #3: Verify ratings and feedback are visible on marketplace assistant cards.

    AC: View marketplace ratings and feedback - Ratings/feedback controls are present.
    """
    # Navigate to marketplace
    marketplace_page = AssistantsMarketplacePage(page)
    marketplace_page.navigate_to()

    # Verify marketplace page loads
    marketplace_page.should_be_on_marketplace_page()

    # Verify ratings and feedback controls (like/dislike buttons) are visible
    marketplace_page.should_have_ratings_and_feedback_visible()


@pytest.mark.assistant
@pytest.mark.ui
def test_marketplace_filter_by_category(page, assistant, assistant_utils):
    """
    Test #4: Filter marketplace assistants by category.

    AC: Filter marketplace items by category - Categories filter.
    """
    # Create assistant
    created_assistant = assistant()

    # Publish directly with ignore_recommendations=True and categories
    assistant_utils.publish_assistant_to_marketplace(
        created_assistant.id,
        categories=["quality-assurance"],
        ignore_recommendations=True,
    )

    # Navigate to marketplace
    marketplace_page = AssistantsMarketplacePage(page)
    marketplace_page.navigate_to()

    # Filter by the Quality Assurance category
    marketplace_page.filter_by_category()

    # Search for the published assistant first, then verify it appears
    marketplace_page.search_assistants(created_assistant.name)
    marketplace_page.should_see_assistant_in_marketplace(created_assistant.name)


@pytest.mark.sanity
@pytest.mark.assistant
@pytest.mark.ui
def test_marketplace_search_assistants_by_name(
    page,
    assistant,
    assistant_utils,
):
    """
    Test #5: Search assistants in marketplace.

    AC: Search marketplace by name/keyword - Search functionality.
    """
    # Create assistant
    created_assistant = assistant()

    # Publish directly without live LLM quality validation
    assistant_utils.publish_assistant_to_marketplace(
        created_assistant.id,
        categories=["quality-assurance"],
        ignore_recommendations=True,
    )

    # Navigate to marketplace
    marketplace_page = AssistantsMarketplacePage(page)
    marketplace_page.navigate_to()

    # Search for assistant by name first, then verify it appears
    marketplace_page.search_assistants(created_assistant.name)
    marketplace_page.should_see_assistant_in_marketplace(created_assistant.name)


@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.not_for_parallel_run
def test_publish_modal_lists_only_unpublished_sub_assistants(
    page, parent_with_published_and_unpublished_sub_assistants
):
    """
    Test #6: Publish modal offers only unpublished sub-assistants for publishing.

    Sub-assistants already on Marketplace are shown as info only
    (no checkbox, no categories); unpublished ones are listed, unchecked by default,
    and do not request categories until ticked. Publishing is still not completed:
    the dialog is never confirmed (the positive control only ticks a checkbox).
    """
    test_data = parent_with_published_and_unpublished_sub_assistants

    # Open the Publish to Marketplace dialog for the parent assistant
    assistants_page = AssistantsPage(page)
    assistants_page.navigate_to()
    assistants_page.search_assistants(test_data.parent_name)
    assistants_page.should_see_assistant_with_name(test_data.parent_name)
    assistants_page.publish_assistant_to_marketplace(test_data.parent_name)
    assistants_page.publish_confirm_dialog_should_be_visible()
    assistants_page.publish_dialog_should_finish_validation()

    # Already published sub-assistant: info line only, not a publish candidate
    assistants_page.publish_dialog_should_show_published_sub_assistants_info(
        [test_data.published_sub_assistant_name]
    )
    assistants_page.publish_dialog_should_not_list_sub_assistant(
        test_data.published_sub_assistant_name
    )

    # Unpublished sub-assistant: selectable, unchecked, no categories requested
    assistants_page.publish_dialog_should_list_unpublished_sub_assistant(
        test_data.unpublished_sub_assistant_name
    )
    assistants_page.publish_dialog_sub_assistant_should_be_unchecked(
        test_data.unpublished_sub_assistant_name
    )
    assistants_page.publish_dialog_should_not_request_categories_for_sub_assistant(
        test_data.unpublished_sub_assistant_name
    )
    assistants_page.publish_dialog_should_request_categories_once_sub_assistant_selected(
        test_data.unpublished_sub_assistant_name
    )
