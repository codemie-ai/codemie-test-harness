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


import pytest

from codemie_test_harness.tests.ui.pageobject.workflows.workflows_page import (
    WorkflowsPage,
)


# @case skills-and-workflows-favorite-state_TC_001
@pytest.mark.workflow
@pytest.mark.ui
def test_workflow_favorite_star_stays_filled_after_reload(page, workflow_to_favorite):
    """A favorited workflow keeps a filled star after the Workflows list is reloaded.

    The test runs as its own fresh user, so its favorites are private to it.
    """
    workflows_page = WorkflowsPage(page)
    workflows_page.open_my_workflows()
    workflows_page.should_show_workflow_not_favorited(workflow_to_favorite.name)

    workflows_page.favorite_workflow(workflow_to_favorite.name)
    workflows_page.should_show_workflow_favorited(workflow_to_favorite.name)

    workflows_page.refresh_page()
    workflows_page.should_see_my_workflows_card(workflow_to_favorite.name)
    workflows_page.should_show_workflow_favorited(workflow_to_favorite.name)
