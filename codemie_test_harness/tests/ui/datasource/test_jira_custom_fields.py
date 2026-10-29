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

"""UI tests for Jira KB custom_fields picker in create and edit forms."""

import pytest
from playwright.sync_api import expect

from codemie_test_harness.tests.ui.pageobject.datasources.create_edit_datasource_page import (
    CreateEditDatasourcePage,
)
from codemie_test_harness.tests.ui.test_data.datasource_test_data import (
    DataSourceFilterType,
)
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.datasource_utils import DataSourceUtils
from codemie_test_harness.tests.utils.jira_seed import require_custom_fields


# ---------------------------------------------------------------------------
# TC_003 — Create Jira KB datasource form shows JiraCustomFieldsField component
# ---------------------------------------------------------------------------


@pytest.mark.datasource
@pytest.mark.jira
@pytest.mark.ui
@pytest.mark.smoke
def test_create_jira_datasource_form_shows_custom_fields_picker(page, jira_integration):
    """
    After selecting the Jira KB datasource type on the Create Datasource form,
    the JiraCustomFieldsField component (added at IndexTypeJira.tsx:74) must be
    visible.  This confirms the UI correctly renders the custom fields picker so
    users can select fields before submitting.

    VERIFY: Run playwright-cli on the Jira KB create form to confirm the exact
    container selector for the custom fields MultiSelect (expected: element
    associated with label text 'Custom fields').
    """
    create_page = CreateEditDatasourcePage(page)
    create_page.navigate_to()

    create_page.select_datasource_type(DataSourceFilterType.JIRA)

    # JQL field must still be visible (existing field, unchanged)
    create_page.should_see_jql_field()

    # JiraCustomFieldsField must be visible after datasource type is set to Jira.
    # Uses the stable element id rather than aria-label (which matches two elements).
    expect(page.locator("#jiraCustomFields")).to_be_visible()


# ---------------------------------------------------------------------------
# TC_007 — Edit form pre-populates jiraCustomFields from existing config
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def jira_datasource_with_custom_fields(jira_integration, jira_seed_issue):
    """Create a Jira KB datasource with a known custom field, clean up after test.

    The datasource is created via the API (create via API / assert via UI pattern)
    so the test can focus on the UI pre-population behaviour.
    """
    client = get_client()
    utils = DataSourceUtils(client)
    field = require_custom_fields(jira_seed_issue, 1)[0]

    datasource = utils.create_jira_datasource(
        setting_id=jira_integration.id,
        custom_fields=[field.id],
    )

    yield datasource, field

    utils.delete_datasource(datasource)


@pytest.mark.datasource
@pytest.mark.jira
@pytest.mark.ui
def test_edit_jira_datasource_form_prepopulates_custom_fields(
    page, jira_datasource_with_custom_fields
):
    """
    When opening the edit form for a Jira KB datasource that was created with
    custom_fields configured, the jiraCustomFields MultiSelect must be
    pre-populated from defaults.jira.custom_fields (initialised in
    useEditPopupForm.ts:523) so the user can see and modify the existing
    selection without losing it.

    The chip renders the configured field's display name.
    """
    datasource, custom_field = jira_datasource_with_custom_fields

    edit_url = f"/data-sources/{datasource.id}/edit"
    page.goto(edit_url)
    page.wait_for_load_state("networkidle")

    # Confirm the form loaded (disabled name input shows in edit mode)
    expect(page.locator("input#name[disabled]")).to_be_visible(timeout=30000)

    # The custom fields widget must be visible (stable element id).
    multiselect = page.locator("#jiraCustomFields")
    expect(multiselect).to_be_visible()

    # The selected chip shows the field's display name (not its ID).
    expect(multiselect).to_contain_text(custom_field.name)
