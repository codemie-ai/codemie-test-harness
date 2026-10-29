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

"""UI test: 'Reset to global settings' restores the Models tab's default model
and model selection to the platform's global configuration.

Scenario: a project-level default model is chosen and applied (diverging from
the global default). Clicking "Reset to global settings" then must switch the
"Project default model" select back to the platform's global default model
(`client.llms.list()`'s single `default`-flagged model) and enable "Apply
changes"; applying it must check every model in the table.
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.administration.project_details_page import (
    ProjectDetailsPage,
)
from codemie_test_harness.tests.utils.llm_utils import (
    candidate_model_labels,
    global_default_model_label,
)

DEFAULT_SELECT_LABEL = "Project default model"


@pytest.mark.project
@pytest.mark.ui
def test_reset_to_global_settings_restores_default_model_and_selection(
    page, project_admin_setup, client
):
    project_name, _, _, _ = project_admin_setup

    details_page = ProjectDetailsPage(page)
    details_page.navigate_to(project_name)
    models = details_page.open_models_tab()
    models.should_be_visible()

    # Pick a project default model different from both the global default and the
    # project's current default, so selecting and applying it is an actual change.
    global_default_model = global_default_model_label(client)
    current_default_model = models.current_default_model(DEFAULT_SELECT_LABEL)
    candidates = candidate_model_labels(client)
    project_default_model = next(
        label
        for label in candidates
        if label != global_default_model and label not in current_default_model
    )
    models.select_default_model(DEFAULT_SELECT_LABEL, project_default_model)
    models.apply_changes()
    models.should_have_default_model_selected(
        DEFAULT_SELECT_LABEL, project_default_model
    )

    models.reset_to_global_settings()
    models.should_have_default_model_selected(
        DEFAULT_SELECT_LABEL, global_default_model
    )
    assert models.apply_changes_button.is_enabled(), (
        "'Apply changes' should be enabled after 'Reset to global settings'"
    )

    models.apply_changes()
    models.should_have_all_models_checked()
