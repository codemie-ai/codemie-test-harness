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

"""UI test: the Models tab lists every model the API returns.

The Project Details page's "Models" tab (between Members and Budgets) shows
which platform LLM models are available in the project. The number of model
rows rendered — and the "N of M models available" counter's total — must
match the number of models `client.llms.list()` returns, so no model is
silently dropped from the table (previously the routing models "Claude Router
Standard v1", "Claude Router Premium v1", "GPT Router Standard v1" were
omitted — fixed).
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.administration.project_details_page import (
    ProjectDetailsPage,
)


@pytest.mark.project
@pytest.mark.ui
def test_models_tab_lists_every_api_model(page, project_admin_setup, client):
    project_name, _, _, _ = project_admin_setup
    api_model_count = len(client.llms.list())

    details_page = ProjectDetailsPage(page)
    details_page.navigate_to(project_name)
    models = details_page.open_models_tab()
    models.should_be_visible()
    models.should_show_model_count(api_model_count)
