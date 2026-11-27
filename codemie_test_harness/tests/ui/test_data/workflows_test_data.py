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

from codemie_test_harness.tests.test_data.workspace_script_test_data import JIRA_TOOL
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


# Exchange "Read messages" tool bound to a workflow Tool node. Its Folder, Start and
# Count arguments are required: codemie's args_schema extraction
# (ToolConfigExtractor) marks a non-optional field required unless its default is frozen,
# and ReadInput's folder/start/count defaults are plain ones
# (codemie_tools.ms_exchange.tools). Start is an int with ge=0, so 0 is a valid value.
EXCHANGE_TOOLKIT_NAME = "Microsoft Exchange"
EXCHANGE_READ_TOOL_NAME = "Exchange: Read messages"
EXCHANGE_READ_TOOL_ID = "exchange_read"
EXCHANGE_READ_FOLDER = "ocr"
EXCHANGE_READ_COUNT = 10
EXCHANGE_READ_START = 0

WORKFLOW_UPDATED_TOAST = "Workflow has been updated successfully!"

# Saving a global workflow whose script step may call the Jira tool through the author's own
# integration: the editor shows this one warning toast, kept open for 8 s (3 s is the default).
OWNER_INTEGRATION_TOAST = (
    "Saved. Script steps run these tools under the workflow author's integration "
    f"for everyone who runs the workflow: {JIRA_TOOL}."
)
# Part of the backend's raw warning message, which no toast may show.
OWNER_INTEGRATION_RAW_MESSAGE = "runs under the workflow author's integration ("
# Open time is measured from when the test first sees the toast, so it reads a little under the
# real 8 s; the lower bound rules out anything near the 3 s default, the upper bound leaves room
# for a slow runner and the closing animation.
OWNER_INTEGRATION_TOAST_MIN_OPEN_MS = 6_500
OWNER_INTEGRATION_TOAST_MAX_OPEN_MS = 11_000
