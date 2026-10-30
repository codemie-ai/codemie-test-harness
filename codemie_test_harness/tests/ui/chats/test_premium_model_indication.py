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

import pytest

from codemie_test_harness.tests.ui.pageobject.available_models_page import (
    AvailableModelsPage,
)


# ---------------------------------------------------------------------------
# TC-01  Premium badge and tooltip visible in chat model picker
# ---------------------------------------------------------------------------


@pytest.mark.smoke
@pytest.mark.chat
@pytest.mark.premium_model
@pytest.mark.ui
@pytest.mark.prod_regression
def test_premium_badge_and_tooltip_in_chat_model_picker(
    page, navigate_to_new_chat_page, premium_model_name
):
    """Assert PremiumModelBadge and its tooltip text are present inside the chat
    model picker listbox for a known premium model (AC-1, AC-3)."""
    chat_page = navigate_to_new_chat_page(page)

    # Open picker from the default state
    chat_page.model_selector_button.click()
    page.get_by_role("combobox", name="Search LLM models").wait_for(
        state="visible", timeout=5000
    )
    page.get_by_role("combobox", name="Search LLM models").fill(premium_model_name)

    # Badge is visible inside the premium option
    chat_page.should_show_premium_badge_in_picker(premium_model_name)

    # Tooltip attribute on badge wrapper carries exact text (no live hover needed)
    chat_page.should_show_correct_premium_tooltip_in_picker(premium_model_name)

    # Close picker
    page.keyboard.press("Escape")


# ---------------------------------------------------------------------------
# TC-02  Premium badge and tooltip visible in assistant configuration picker
# ---------------------------------------------------------------------------


@pytest.mark.chat
@pytest.mark.premium_model
@pytest.mark.ui
@pytest.mark.prod_regression
def test_premium_badge_and_tooltip_in_configuration_panel(
    page, navigate_to_new_chat_page, premium_model_name
):
    """Assert PremiumModelBadge is visible in the chat configuration LLM dropdown
    for a known premium model (AC-2, AC-3)."""
    chat_page = navigate_to_new_chat_page(page)
    chat_page.open_configuration()
    config_panel = chat_page.chat_configuration_panel

    # Open the LLM multiselect dropdown and search for the premium model
    config_panel.open_llm_dropdown_and_search(premium_model_name)

    # Badge is visible inside the premium option
    config_panel.should_show_premium_badge_for_model(premium_model_name)

    # Tooltip attribute carries the correct text
    config_panel.should_show_premium_tooltip_for_model(
        premium_model_name,
        chat_page.PREMIUM_TOOLTIP_TEXT,
    )

    # Close the dropdown
    page.keyboard.press("Escape")


# ---------------------------------------------------------------------------
# TC-03  Non-premium model shows no premium badge in chat model picker
# ---------------------------------------------------------------------------


@pytest.mark.chat
@pytest.mark.premium_model
@pytest.mark.ui
@pytest.mark.prod_regression
def test_no_premium_badge_for_non_premium_model_in_chat_picker(
    page, navigate_to_new_chat_page, non_premium_model_name
):
    """Assert no PremiumModelBadge element is present for a known non-premium
    model in the chat model picker (AC-1)."""
    chat_page = navigate_to_new_chat_page(page)

    chat_page.model_selector_button.click()
    page.get_by_role("combobox", name="Search LLM models").wait_for(
        state="visible", timeout=5000
    )
    page.get_by_role("combobox", name="Search LLM models").fill(non_premium_model_name)

    chat_page.should_not_show_premium_badge_in_picker(non_premium_model_name)

    page.keyboard.press("Escape")


# ---------------------------------------------------------------------------
# TC-04  Selecting premium model shows highlight, notice, link, and tooltip
# ---------------------------------------------------------------------------


@pytest.mark.smoke
@pytest.mark.chat
@pytest.mark.premium_model
@pytest.mark.ui
@pytest.mark.prod_regression
def test_selecting_premium_model_shows_all_indicators(
    page, navigate_to_new_chat_page, premium_model_name
):
    """After selecting a premium model:
    - chat input has amber ring highlight (AC-4)
    - active model selector carries premium tooltip marker (AC-9)
    - dismissible notice is visible with dismiss button and details link (AC-5, AC-6)
    """
    chat_page = navigate_to_new_chat_page(page)
    chat_page.select_premium_model(premium_model_name)

    # Amber ring on chat input wrapper (AC-4)
    chat_page.should_show_premium_highlight()

    # Active model selector button carries premium tooltip content attribute (AC-9)
    chat_page.should_show_premium_tooltip_on_active_selector()

    # Dismissible notice with details link must be present (AC-5, AC-6)
    chat_page.should_show_premium_notice()
    chat_page.should_show_premium_notice_dismiss_button()
    chat_page.should_show_premium_notice_details_link()


# ---------------------------------------------------------------------------
# TC-05  Premium notice reappears after dismiss / after switching back
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "flow",
    [
        pytest.param("dismiss_and_reload", id="a-dismiss-then-reload"),
        pytest.param("switch_back", id="b-switch-back-to-premium"),
    ],
)
@pytest.mark.chat
@pytest.mark.premium_model
@pytest.mark.ui
@pytest.mark.prod_regression
def test_premium_notice_reappears(
    page,
    navigate_to_new_chat_page,
    premium_model_name,
    non_premium_model_name,
    flow,
):
    """Premium model active notice must reappear after dismiss (AC-7):
    - case (a): dismiss notice, navigate away and back → notice visible again.
    - case (b): select premium, switch to non-premium, switch back → notice visible.
    """
    chat_page = navigate_to_new_chat_page(page)
    chat_page.select_premium_model(premium_model_name)

    # Notice must be present immediately after selecting a premium model (AC-5)
    chat_page.should_show_premium_notice()

    if flow == "dismiss_and_reload":
        # Dismiss notice
        chat_page.dismiss_premium_notice()
        chat_page.should_not_show_premium_notice()

        # Navigate away and back to the same chat — local React state resets
        chat_id = chat_page.chat_id
        page.goto("/chats")
        chat_page.navigate_to(chat_id)
        chat_page.should_show_premium_notice()

    else:  # switch_back
        # Switch to non-premium — all indicators clear
        chat_page.open_model_picker_for_model(premium_model_name, is_premium=True)
        chat_page.select_model_in_open_picker(non_premium_model_name, is_premium=False)
        chat_page.should_not_show_premium_notice()

        # Switch back to premium — notice must reappear
        chat_page.open_model_picker_for_model(non_premium_model_name, is_premium=False)
        chat_page.select_model_in_open_picker(premium_model_name, is_premium=True)
        chat_page.should_show_premium_notice()


# ---------------------------------------------------------------------------
# TC-06  All premium indicators clear when switching to non-premium model
# ---------------------------------------------------------------------------


@pytest.mark.smoke
@pytest.mark.chat
@pytest.mark.premium_model
@pytest.mark.ui
@pytest.mark.prod_regression
def test_premium_indicators_clear_on_switch_to_non_premium(
    page,
    navigate_to_new_chat_page,
    premium_model_name,
    non_premium_model_name,
):
    """After switching from a premium model back to a non-premium model, all premium
    UI indicators (amber ring, notice, active badge) must disappear (AC-8)."""
    chat_page = navigate_to_new_chat_page(page)

    # Select premium model — ring highlight must appear
    chat_page.select_premium_model(premium_model_name)
    chat_page.should_show_premium_highlight()

    # Switch to non-premium — ring and notice (if present) must clear
    chat_page.open_model_picker_for_model(premium_model_name, is_premium=True)
    chat_page.select_model_in_open_picker(non_premium_model_name, is_premium=False)

    chat_page.should_not_show_premium_indicators()


# ---------------------------------------------------------------------------
# TC-07  Help Center available models page shows premium marks and filters
# ---------------------------------------------------------------------------


@pytest.mark.smoke
@pytest.mark.chat
@pytest.mark.premium_model
@pytest.mark.ui
@pytest.mark.prod_regression
def test_help_models_page_shows_premium_marks_and_filters(page, premium_model_name):
    """Available models page must load with:
    - model table with at least one premium-marked row for a known premium model
    - text filter, provider filter, and premium-only filter visible and interactable
    (AC-10)."""
    available_models_page = AvailableModelsPage(page)
    available_models_page.navigate_to()

    available_models_page.should_show_available_models_heading()
    available_models_page.should_show_model_table()
    available_models_page.should_show_filter_controls()

    # At least one premium mark exists
    available_models_page.should_show_at_least_one_premium_model()

    # The known premium model carries a premium mark
    available_models_page.should_show_model_with_premium_mark(premium_model_name)

    # Filters are interactable — fill text filter and verify no error
    available_models_page.fill_text_filter(premium_model_name)
    available_models_page.should_show_model_with_premium_mark(premium_model_name)


# ---------------------------------------------------------------------------
# TC-08  Help Center premium-only filter shows only premium models
# ---------------------------------------------------------------------------


@pytest.mark.chat
@pytest.mark.premium_model
@pytest.mark.ui
@pytest.mark.prod_regression
def test_help_models_premium_only_filter(
    page,
    premium_model_name,
    non_premium_model_name,
):
    """After activating the 'Premium only' filter all visible rows must have a
    premium mark and a known non-premium model must not appear (AC-10)."""
    available_models_page = AvailableModelsPage(page)
    available_models_page.navigate_to()
    available_models_page.should_show_model_table()

    available_models_page.enable_premium_only_filter()

    # All rows visible after filter must carry a premium mark
    available_models_page.should_show_only_premium_models()

    # Known non-premium model must be absent from filtered list
    available_models_page.should_not_show_model(non_premium_model_name)
