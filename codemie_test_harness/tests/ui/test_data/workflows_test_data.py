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

"""Test data for the Generate Workflow with AI UI popup and workflow categories."""

from dataclasses import dataclass

from codemie_test_harness.tests.utils.base_utils import get_random_name

# A valid NL description used to fill the "What should your workflow do?"
# textarea in the "Generate Workflow with AI" popup happy-path UI tests
# (TC-01/TC-02/TC-03) that only need *some* generated workflow to render,
# edit, or drag on the canvas — the exact behavior doesn't matter for those.
GENERATE_WORKFLOW_DESCRIPTION = "Create a workflow that will say hi. Nothing else"

# Tooltip shown on the disabled "Remove" option for a workflow execution
# history item that is still linked to a live conversation.
EXECUTION_REMOVE_BLOCKED_TOOLTIP_TEXT = (
    "This execution is part of a Chat and can't be deleted from this interface"
)

# Minimal YAML used when a workflow is created through the UI form
CATEGORIES_WORKFLOW_YAML = """
assistants:
  - id: categories_assistant
    system_prompt: You are helpful assistant

states:
  - id: categories_assistant
    assistant_id: categories_assistant
    next:
      state_id: end
"""

# The UI categories field accepts at most this many categories
MAX_UI_CATEGORIES = 3


@dataclass
class WorkflowCategoriesUiData:
    """Names for the workflows used by the categories UI tests.

    Both names share ``prefix`` so the list can be narrowed with the search box
    and the category filter checked on just these two workflows.
    """

    prefix: str
    with_category_name: str
    without_category_name: str


class WorkflowCategoriesUiDataFactory:
    """Factory producing unique names for the categories UI tests."""

    @staticmethod
    def create() -> WorkflowCategoriesUiData:
        prefix = get_random_name()
        return WorkflowCategoriesUiData(
            prefix=prefix,
            with_category_name=f"{prefix}-with-cat",
            without_category_name=f"{prefix}-no-cat",
        )
