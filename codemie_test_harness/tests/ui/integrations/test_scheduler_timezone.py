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
UI tests: timezone field in Scheduler integration creation form.

AC covered:
  AC-1  User can specify a timezone when creating a Scheduler integration (field visible, selectable)
  AC-4  UI shows which timezone is applied (edit page displays saved timezone)
  AC-5  Timezone field is visible before saving and can be changed (verified via S-02)

AC covered:
  AC-1  Dropdown shows each timezone option with UTC offset suffix
  AC-2  Display format is clear: Name (UTC±H) or Name (UTC±H:MM)
  AC-3  Selected field input shows UTC offset together with the timezone name
  AC-4  UTC itself is displayed as 'UTC (UTC+0)'
  AC-5  Sub-hour offsets render as (UTC+H:MM), e.g. 'Asia/Kolkata (UTC+5:30)'

Scenarios: S-02, S-03, TC-002

AC-5 scope note:
  AC-5 states "if a default time zone is preselected, it is visible to the user and can be
  changed before saving."  The integration creation form (settingsUIConfig.ts) does NOT
  pre-populate a default timezone — it renders the field with a placeholder instead, and
  Yup.string().required() ensures the user must select a value.  The browser-timezone default
  (getBrowserTimezone / useEditPopupForm.ts) is applied in the DataSource creation flow, not
  the integration creation flow tested here.  S-02 therefore covers the "field is visible and
  can be changed before saving" aspect of AC-5; the "preselected default" clause is not
  applicable to this form path.

AC-7 UI coverage — intentionally omitted (by-design):
  The timezone field is a selection-only autocomplete (PrimeReact Autocomplete).
  Users must select from the pre-populated IANA timezone list; free-form text that
  does not match a valid option cannot be submitted. The UI therefore cannot accept
  an invalid timezone value at the browser level. Server-side 422 validation for
  invalid timezone strings is covered by S-06 in test_scheduler_timezone.py (API).
  No additional UI validation test is required for AC-7.
"""

import pytest
from playwright.sync_api import Page
from urllib.parse import quote

from codemie_sdk.models.integration import CredentialTypes
from codemie_test_harness.tests import PROJECT
from codemie_test_harness.tests.ui.pageobject.integrations.create_integration_page import (
    CreateIntegrationPage,
)
from codemie_test_harness.tests.ui.pageobject.integrations.edit_integration_page import (
    EditIntegrationPage,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver

# ---------------------------------------------------------------------------
# UTC offset display — parametrize data for TC-002
# ---------------------------------------------------------------------------
_TIMEZONE_OFFSET_CASES = [
    pytest.param("Asia/Tokyo", "Asia/Tokyo (UTC+9)", id="standard-positive-offset"),
    pytest.param("UTC", "UTC (UTC+0)", id="zero-offset-utc"),
    # Playwright-bundled Chromium (and many older V8 builds) exposes "Asia/Calcutta" rather
    # than the canonical "Asia/Kolkata" from Intl.supportedValuesOf('timeZone').
    # "Asia/Calcutta" is still UTC+5:30, so it covers AC-5 (sub-hour H:MM offset format).
    pytest.param("Asia/Calcutta", "Asia/Calcutta (UTC+5:30)", id="sub-hour-offset"),
]

pytestmark = pytest.mark.skipif(
    EnvironmentResolver.is_sandbox(),
    reason="Scheduler is disabled on sandbox environments",
)


@pytest.mark.integration
@pytest.mark.scheduler
@pytest.mark.ui
@pytest.mark.prod_regression
def test_scheduler_form_shows_timezone_field_and_allows_selection(
    page: Page,
    assistant,
):
    """S-02 / TC-001: Scheduler integration creation form — timezone field visible and a timezone
    can be selected and saved; selected field shows UTC offset suffix.

    Steps:
    1. Navigate to create project integration page.
    2. Select Scheduler credential type.
    3. Assert timezone autocomplete field is visible (field presence — AC-5).
    4. Fill timezone 'Asia/Tokyo', schedule, alias, resource_type, resource_id.
    5. Assert chosen timezone shows UTC offset in the input field (AC-1, AC-2, AC-3).
    6. Submit form.
    7. Assert success toast appears.

    AC: AC-1, AC-5 (field visible, changeable before saving)
    AC: AC-1, AC-2, AC-3 (selected field displays 'Asia/Tokyo (UTC+9)')
    Note: The integration creation form does not preselect a default timezone
    (see module docstring for AC-5 scope note).
    """
    # Arrange
    resource_assistant = assistant()
    alias = get_random_name()
    timezone = "Asia/Tokyo"
    cron_schedule = "0 * * * *"

    create_page = CreateIntegrationPage(page)
    create_page.navigate_to_project_integration_creation()

    # Act — select Scheduler credential type
    create_page.select_credential_type(CredentialTypes.SCHEDULER)
    page.wait_for_timeout(500)

    # Assert — timezone autocomplete field is visible to the user (AC-5: field presence)
    create_page.should_have_timezone_autocomplete_visible()

    # Fill required form fields
    create_page.select_project(PROJECT)
    create_page.fill_alias(alias)
    create_page.fill_schedule(cron_schedule)
    create_page.fill_timezone(timezone)
    create_page.select_resource_type("Assistant")
    create_page.fill_resource_id(resource_assistant.id)

    # Assert — selected timezone shows UTC offset suffix
    create_page.should_have_timezone_value(timezone, with_offset=True)

    # Act — submit the form
    create_page.create_integration()

    # Assert — success toast confirms creation
    create_page.should_see_creation_success()


@pytest.mark.integration
@pytest.mark.scheduler
@pytest.mark.ui
@pytest.mark.prod_regression
def test_scheduler_edit_page_displays_saved_timezone(
    page: Page,
    assistant,
    scheduler_integration,
):
    """S-03 / TC-003: After creating a Scheduler integration with timezone='America/New_York',
    navigate to the edit page and verify the timezone autocomplete shows the saved value with
    UTC offset suffix.

    Steps:
    1. Create Scheduler integration via API with timezone='America/New_York'.
    2. Navigate to project edit page for that integration.
    3. Assert timezone autocomplete input shows 'America/New York (UTC-4)' or '(UTC-5)'
       (DST-safe regex match on the offset, AC-3).

    AC: AC-4
    AC: AC-3 (edit page selected field shows offset with saved timezone)
    """
    # Arrange — create integration via API with explicit timezone
    resource_assistant = assistant()
    alias = get_random_name()
    timezone = "America/New_York"

    integration = scheduler_integration(
        alias=alias,
        resource_type="assistant",
        resource_id=resource_assistant.id,
        timezone=timezone,
    )

    # Act — navigate to edit page (integrations list only has Edit / Delete — no separate details view)
    edit_url = (
        f"/integrations/project/edit"
        f"?project_name={quote(integration.project_name)}"
        f"&credential_type={quote(CredentialTypes.SCHEDULER.value)}"
        f"&alias={quote(integration.alias)}"
    )
    edit_page = EditIntegrationPage(page)
    edit_page.page.goto(edit_url)
    edit_page.wait_for_page_load()

    # Assert — timezone field shows the saved value with UTC offset suffix
    # DST-safe: America/New_York is UTC-4 (summer) or UTC-5 (winter); regex matches both
    edit_page.should_have_timezone_value(timezone, with_offset=True)


@pytest.mark.integration
@pytest.mark.scheduler
@pytest.mark.ui
@pytest.mark.parametrize("tz, expected_label", _TIMEZONE_OFFSET_CASES)
@pytest.mark.prod_regression
def test_scheduler_timezone_dropdown_option_shows_utc_offset(
    page: Page,
    tz: str,
    expected_label: str,
):
    """TC-002: Timezone dropdown option labels show correct UTC offset format — parameterized.

    Covers three cases:
    - Case A: 'Asia/Tokyo (UTC+9)' — standard positive offset (AC-1, AC-2)
    - Case B: 'UTC (UTC+0)' — zero-offset edge case (AC-4)
    - Case C: 'Asia/Kolkata (UTC+5:30)' — sub-hour H:MM format (AC-5)

    Steps:
    1. Navigate to create project integration page.
    2. Select Scheduler credential type.
    3. Assert timezone autocomplete field is visible.
    4. Open timezone dropdown via the dropdown button.
    5. Assert the option for 'tz' is visible and its label matches 'expected_label'
       (full UTC offset suffix present).

    AC: AC-1, AC-2, AC-4, AC-5
    """
    create_page = CreateIntegrationPage(page)
    create_page.navigate_to_project_integration_creation()

    # Select Scheduler credential type to reveal the timezone field
    create_page.select_credential_type(CredentialTypes.SCHEDULER)
    page.wait_for_timeout(500)

    # Assert timezone field rendered
    create_page.should_have_timezone_autocomplete_visible()

    # Assert the dropdown option label shows the expected UTC offset format (AC-1, AC-2, AC-4, AC-5)
    create_page.should_have_timezone_option_with_offset(tz, expected_label)
