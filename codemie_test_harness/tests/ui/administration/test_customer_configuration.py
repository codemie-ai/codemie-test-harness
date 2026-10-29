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

"""UI tests for Customer Configuration administration page.

Covers:
  SC-04 — Admin edits and resets config from Administration page (AC-24, 25, 27, 29)

Pattern:
  API used for cleanup only; all assertions are via the browser / page object.
"""

from __future__ import annotations

import pytest

from codemie_test_harness.tests.ui.pageobject.administration.customer_configuration_page import (
    CustomerConfigurationPage,
)
from codemie_test_harness.tests.ui.test_data.administration_test_data import (
    COMPONENT_ID_CHAT_DISCLAIMER,
    get_disclaimer_form_data,
)

# ── Constants ─────────────────────────────────────────────────────────────────

_COMPONENT_ID = COMPONENT_ID_CHAT_DISCLAIMER

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="function")
def customer_config_page(page):
    """Navigate to the Customer Configuration page and return the page object."""
    pom = CustomerConfigurationPage(page)
    pom.navigate_to()
    return pom


@pytest.fixture(scope="function")
def ensure_config_reset(customer_config_utils):
    """Ensure the chatDisclaimer setting is reset to default in teardown."""
    yield
    try:
        customer_config_utils.reset_setting(_COMPONENT_ID)
    except Exception:
        pass


# ── SC-04: Admin edits and resets config via UI ───────────────────────────────


@pytest.mark.customer_configuration
@pytest.mark.ui
def test_admin_can_edit_and_reset_customer_configuration(
    page, customer_config_page, ensure_config_reset
):
    """SC-04: Admin navigates to Customer Configuration, edits the disclaimer,
    observes the Overridden marker, then resets and sees Default from config.

    Covers AC-24 (reset restores default), AC-25 (fields match declarations),
    AC-27 (current value visible), AC-29 (default-from-config marker visible).
    """
    form_data = get_disclaimer_form_data()

    # ── AC-29: Page renders correctly with Default from config marker ────────
    customer_config_page.should_see_page_heading()
    customer_config_page.should_see_chat_disclaimer_card()
    customer_config_page.should_see_default_marker()

    # ── AC-25 / AC-27: Form controls are visible (match declarations schema) ─
    customer_config_page.should_see_disclaimer_switch()
    customer_config_page.should_see_disclaimer_text_field()

    # ── Edit: enable switch and fill disclaimer text ─────────────────────────
    customer_config_page.enable_disclaimer_switch()
    customer_config_page.fill_disclaimer_text(form_data.disclaimer_text)
    customer_config_page.click_save()

    # ── AC-27: Override marker appears after saving ──────────────────────────
    customer_config_page.should_see_overridden_marker()
    customer_config_page.should_have_disclaimer_text(form_data.disclaimer_text)

    # ── AC-24: Reset restores the Default from config marker ─────────────────
    customer_config_page.click_reset_to_default()
    customer_config_page.should_see_default_marker()
