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

"""UI tests for the ChatDisclaimer component in the chat page.

Covers:
  SC-05 — Chat disclaimer shown and non-dismissible when enabled (AC-31, 32, 33)

Pattern:
  API enables the disclaimer for setup; UI asserts display behaviour only.
  API resets the disclaimer in teardown.
"""

from __future__ import annotations

import pytest

from codemie_test_harness.tests.test_data.customer_config_test_data import (
    get_disclaimer_settings_data,
)
from codemie_test_harness.tests.ui.pageobject.components.chat_disclaimer_component import (
    ChatDisclaimerComponent,
)

# ── Constants ─────────────────────────────────────────────────────────────────

_COMPONENT_ID = "chatDisclaimer"

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="function")
def enabled_disclaimer(customer_config_utils):
    """Enable the chat disclaimer via API and reset it in teardown.

    Yields the settings data that was saved so tests can assert the text.
    """
    settings_data = get_disclaimer_settings_data()
    customer_config_utils.save_setting(_COMPONENT_ID, settings_data.as_settings)
    yield settings_data
    try:
        customer_config_utils.reset_setting(_COMPONENT_ID)
    except Exception:
        pass


# ── SC-05: Chat disclaimer visible and non-dismissible ────────────────────────


@pytest.mark.chat
@pytest.mark.ui
def test_chat_disclaimer_visible_and_non_dismissible(
    page, navigate_to_new_chat_page, enabled_disclaimer
):
    """SC-05: When the disclaimer is enabled, it appears below the composer,
    cannot be dismissed, and renders embedded URLs as clickable links.

    Covers AC-31 (visible), AC-32 (non-dismissible), AC-33 (link rendering).
    """
    chat_page = navigate_to_new_chat_page(page)

    disclaimer = ChatDisclaimerComponent(chat_page.page)

    # ── AC-31: Disclaimer element is visible below the message input ─────────
    disclaimer.should_be_visible()

    # ── AC-32: No dismiss / close button on the disclaimer ───────────────────
    disclaimer.should_not_have_dismiss_button()

    # ── AC-33: Embedded URL renders as a clickable anchor element ────────────
    disclaimer.should_have_link()
