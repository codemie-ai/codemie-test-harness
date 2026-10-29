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

"""UI tests for budget controls on a personal project.

Covers:
  TC-001  A maintainer opening their own personal project in Projects management is not
          offered a Create Budget control

The maintainer (and the personal project named after their email) is created by the
`maintainer_credentials` fixture; the browser logs in as that maintainer.
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.administration.project_details_page import (
    ProjectDetailsPage,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_management_page import (
    ProjectManagementPage,
)


@pytest.mark.ui
@pytest.mark.project
@pytest.mark.parametrize("acting_credentials", ["maintainer"], indirect=True)
def test_maintainer_personal_project_has_no_create_budget_button(
    page, acting_credentials
):
    """
    Projects management sees the details page without a Create Budget control.
    """
    personal_project, _ = acting_credentials
    projects_page = ProjectManagementPage(page).navigate_to()
    projects_page.search_for(personal_project)

    projects_page.open_project(personal_project)

    details_page = ProjectDetailsPage(page)
    details_page.should_be_on_project_details_page(personal_project)
    details_page.should_not_offer_create_budget()
