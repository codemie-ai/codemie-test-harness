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

"""UI tests for the Project Details Overview tab's 'Model availability' card.

Covers:
    TC-01  'Configure' navigates to the project's Models tab.
    TC-02  The card's '<N> of <M> models' count matches the real model
           selection (M = the platform's total model count from the API,
           N = the project's selected-model count shown on the Models tab).

Navigation path:
    /settings/administration/projects/{name} → Overview tab (default)
    → Model availability card
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.administration.project_details_page import (
    ProjectDetailsPage,
)


@pytest.mark.project
@pytest.mark.ui
def test_configure_navigates_to_models_tab(page, project_admin_setup, client):
    project_name, _, _, _ = project_admin_setup

    details_page = ProjectDetailsPage(page)
    details_page.navigate_to(project_name)

    details_page.click_configure_models()
    details_page.should_be_on_models_tab(project_name)


@pytest.mark.project
@pytest.mark.ui
def test_model_availability_count_matches_api_total(page, project_admin_setup, client):
    """The Overview card's '<N> of <M> models' must use the platform's real
    model count (`client.llms.list()`) as M, and the project's actual
    selected-model count (read from the Models tab) as N.
    """
    project_name, _, _, _ = project_admin_setup
    api_model_count = len(client.llms.list())

    details_page = ProjectDetailsPage(page)
    details_page.navigate_to(project_name)

    models = details_page.open_models_tab()
    models.should_be_visible()
    selected_count, total_count = models.selected_and_total_count()
    assert total_count == api_model_count, (
        f"Models tab total ({total_count}) does not match the API model "
        f"count ({api_model_count})"
    )

    details_page.navigate_to(project_name)
    details_page.should_have_selected_models_count(selected_count, api_model_count)
