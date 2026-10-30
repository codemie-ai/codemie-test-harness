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

"""UI tests for the Config tab of Administration -> Marketplace management.

Pattern: the override is cleared through the API before and after each test
(``clean_marketplace_thresholds``); every behavioural assertion goes through
the page object.
"""

from __future__ import annotations

import pytest

from codemie_test_harness.tests.ui.pageobject.administration.marketplace_settings_page import (
    MarketplaceSettingsPage,
)
from codemie_test_harness.tests.ui.test_data.marketplace_thresholds_ui_test_data import (
    CHANGED_FORM_VALUES,
    CHANGED_GRACE_DAYS,
    DEFAULT_FORM_VALUES,
    LABEL_GRACE,
    MARKER_DEFAULT,
    MARKER_OVERRIDDEN,
)


@pytest.fixture(scope="function")
def marketplace_settings_page(page, clean_marketplace_thresholds):
    """Open the Config tab with no threshold override in place."""
    return MarketplaceSettingsPage(page).navigate_to_config_tab()


@pytest.mark.not_for_parallel_run
@pytest.mark.customer_configuration
@pytest.mark.marketplace
@pytest.mark.ui
def test_admin_can_save_and_reset_marketplace_thresholds_on_config_tab(
    marketplace_settings_page,
):
    """Config tab follows the other tabs; the thresholds card shows the five
    defaults with the 'Default from config' marker, switches to 'Overridden'
    (with a Reset button) after a save and back after a reset."""
    marketplace_settings_page.should_see_config_tab_last()
    marketplace_settings_page.should_see_thresholds_card()
    marketplace_settings_page.should_have_field_values(DEFAULT_FORM_VALUES)
    marketplace_settings_page.should_see_marker(MARKER_DEFAULT, MARKER_OVERRIDDEN)
    marketplace_settings_page.should_not_have_reset_button()

    marketplace_settings_page.fill_field(LABEL_GRACE, CHANGED_GRACE_DAYS)
    marketplace_settings_page.click_save()
    marketplace_settings_page.should_see_marker(MARKER_OVERRIDDEN, MARKER_DEFAULT)
    marketplace_settings_page.should_have_reset_button()
    marketplace_settings_page.should_have_field_values(CHANGED_FORM_VALUES)

    marketplace_settings_page.click_reset_to_default()
    marketplace_settings_page.should_see_marker(MARKER_DEFAULT, MARKER_OVERRIDDEN)
    marketplace_settings_page.should_not_have_reset_button()
    marketplace_settings_page.should_have_field_values(DEFAULT_FORM_VALUES)
