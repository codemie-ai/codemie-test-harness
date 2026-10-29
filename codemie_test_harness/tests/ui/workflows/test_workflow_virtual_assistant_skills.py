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

"""E2E test for skills shown in the workflow virtual assistant form.

The Skills multiselect builds its options from the scoped catalog request. A skill
selected in the virtual assistant config that is outside that catalog (other project,
not published) used to render as the literal text "null".
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.workflows.edit_workflow_page import (
    EditWorkflowPage,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name


@pytest.mark.skill
@pytest.mark.workflow
@pytest.mark.ui
def test_workflow_virtual_assistant_skill_outside_catalog_not_null(
    page, skill_in_other_project, workflow_with_virtual_assistant
):
    """Virtual assistant skill missing from the catalog is not "null".

    Steps:
    1. Create a skill in another project (project visibility, not published).
    2. Create a workflow in the default project whose virtual assistant has that skill id.
    3. Open the workflow editor and the assistant node config panel.
    4. Verify the Skills field shows the skill (name or id) and not "null".
    """
    workflow = workflow_with_virtual_assistant(
        get_random_name().replace("_", "-"), skill_ids=[skill_in_other_project.id]
    )

    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(workflow.id)
    panel = edit_page.open_assistant_node_config_panel()

    panel.should_show_selected_skill(
        skill_in_other_project.name, skill_in_other_project.id
    )
