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

"""Test data for the workflow revision history and rollback API tests."""

import pytest
import yaml

from codemie_test_harness.tests.utils.yaml_utils import (
    AssistantModel,
    StateModel,
    WorkflowYamlModel,
    prepare_yaml_content,
)

REVISION_STATE_ID = "revision_assistant"

# The history endpoint answers 20 revisions per page when no size is given.
DEFAULT_REVISIONS_PER_PAGE = 20

# Saves needed so the history holds more than one default page.
REVISIONS_ABOVE_DEFAULT_PAGE = DEFAULT_REVISIONS_PER_PAGE + 1

# Rollback error messages returned with HTTP 400.
INVALID_REVISION_INDEX_MESSAGE = "Invalid revision index."
NO_REVISION_HISTORY_MESSAGE = "No revision history available for this workflow."

# Message returned when the caller has no WRITE ability on the workflow.
ACCESS_DENIED_MESSAGE = "Access denied"


def revision_prompt(number: int) -> str:
    """System prompt that marks revision ``number`` of a workflow."""
    return f"Revision marker {number:03d}"


def build_revision_yaml(model_name: str, number: int) -> str:
    """Workflow yaml_config whose only variable part is the revision marker prompt."""
    workflow_yaml = WorkflowYamlModel(
        assistants=[
            AssistantModel(
                id=REVISION_STATE_ID,
                model=model_name,
                system_prompt=revision_prompt(number),
            )
        ],
        states=[StateModel(id=REVISION_STATE_ID, assistant_id=REVISION_STATE_ID)],
    )
    return prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))


def marker_prompt(yaml_config: str) -> str:
    """The revision marker prompt stored in a yaml_config."""
    return yaml.safe_load(yaml_config)["assistants"][0]["system_prompt"]


def parsed_config(yaml_config: str) -> dict:
    """A yaml_config as data, so comparisons ignore serialization whitespace."""
    return yaml.safe_load(yaml_config)


# TC_003: query values the API must reject.
INVALID_PAGING_PARAMS = [
    pytest.param({"per_page": 101}, id="per_page_above_100"),
    pytest.param({"per_page": 0}, id="per_page_zero"),
    pytest.param({"page": -1}, id="negative_page"),
]

# TC_006: saved revisions on the workflow and the 400 message expected for the
# revision_index equal to the history length.
OUT_OF_RANGE_ROLLBACK_CASES = [
    pytest.param(2, INVALID_REVISION_INDEX_MESSAGE, id="index_equal_to_history_length"),
    pytest.param(0, NO_REVISION_HISTORY_MESSAGE, id="workflow_without_history"),
]

# TC_008: calls a user without WRITE ability must not be able to make.
DENIED_ACTIONS = [
    pytest.param(
        lambda utils, workflow_id: utils.list_workflow_versions(workflow_id),
        id="list_revisions",
    ),
    pytest.param(
        lambda utils, workflow_id: utils.rollback_workflow(workflow_id, 0),
        id="rollback",
    ),
]

# TC_007: note stored with the rollback revision.
ROLLBACK_CHANGE_NOTES = "Restore the original configuration"
