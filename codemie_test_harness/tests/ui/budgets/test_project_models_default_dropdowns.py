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

"""UI test: models selected on the Project Details Models tab are offered in the
default-model dropdown.

The Models tab's checkboxes define which platform models are available in the
project. Only those models should be offered by the "Project default model"
select: a model that is unchecked and applied must disappear from it, and a
model that stays checked must remain.
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.administration.project_details_page import (
    ProjectDetailsPage,
)
from codemie_test_harness.tests.utils.llm_utils import candidate_model_labels

DEFAULT_SELECT_LABEL = "Project default model"


@pytest.mark.project
@pytest.mark.ui
def test_selected_models_are_offered_in_default_dropdown(
    page, project_admin_setup, client
):
    project_name, _, _, _ = project_admin_setup

    details_page = ProjectDetailsPage(page)
    details_page.navigate_to(project_name)
    models = details_page.open_models_tab()
    models.should_be_visible()

    # The model currently used as the project default cannot be unchecked, so try
    # candidates until one registers. included_model is any other candidate, left
    # checked — it must remain offered.
    candidates = candidate_model_labels(client)
    excluded_model = models.exclude_first_removable_model(candidates)
    included_model = next(label for label in candidates if label != excluded_model)
    models.apply_changes()

    models.should_not_offer_model_in_default_dropdown(
        DEFAULT_SELECT_LABEL, excluded_model
    )
    models.should_offer_model_in_default_dropdown(DEFAULT_SELECT_LABEL, included_model)
