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

"""UI test: the 'Premium only' and 'Selected only' filters on the Project Details
Models tab.

'Premium only' narrows the model table to premium models (rows carrying the
Premium badge). 'Selected only' narrows it to models whose checkbox is checked.
Both are client-side filters over the table, so they can be exercised without
applying any change.
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.administration.project_details_page import (
    ProjectDetailsPage,
)
from codemie_test_harness.tests.utils.llm_utils import candidate_model_labels


def _labels_by_premium(client, premium: bool) -> list[str]:
    """Unambiguous enabled model labels that are (or are not) premium, per the API."""
    premium_api_labels = {
        model.label for model in client.llms.list() if bool(model.is_premium) == premium
    }
    return [
        label for label in candidate_model_labels(client) if label in premium_api_labels
    ]


@pytest.mark.project
@pytest.mark.ui
def test_premium_only_filter_shows_only_premium_models(
    page, project_admin_setup, client
):
    project_name, _, _, _ = project_admin_setup

    details_page = ProjectDetailsPage(page)
    details_page.navigate_to(project_name)
    models = details_page.open_models_tab()
    models.should_be_visible()

    premium_model = _labels_by_premium(client, premium=True)[0]
    non_premium_model = _labels_by_premium(client, premium=False)[0]

    models.scroll_to_end_of_model_list()
    unfiltered_count = models.visible_model_rows().count()
    models.set_premium_only(True)
    filtered_count = models.should_show_only_premium_models()
    assert filtered_count < unfiltered_count, (
        f"'Premium only' did not narrow the table: {unfiltered_count} -> {filtered_count}"
    )
    models.should_not_show_model(non_premium_model)

    models.set_premium_only(False)
    models.should_show_model_count(unfiltered_count)
    assert models.model_row_exact(premium_model).count() == 1, (
        f"Premium model '{premium_model}' is missing after clearing 'Premium only'"
    )


@pytest.mark.project
@pytest.mark.ui
def test_selected_only_filter_shows_only_checked_models(
    page, project_admin_setup, client
):
    project_name, _, _, _ = project_admin_setup

    details_page = ProjectDetailsPage(page)
    details_page.navigate_to(project_name)
    models = details_page.open_models_tab()
    models.should_be_visible()

    # Uncheck one candidate (not applied — the filter reads the current form state).
    candidates = candidate_model_labels(client)
    excluded_model = models.exclude_first_removable_model(candidates)

    models.set_selected_only(True)
    selected_count = models.should_show_only_selected_models()
    models.should_not_show_model(excluded_model)
    models.should_show_selected_count(selected_count)

    models.set_selected_only(False)
    assert models.model_row_exact(excluded_model).count() == 1, (
        f"Unchecked model '{excluded_model}' is missing after clearing 'Selected only'"
    )
