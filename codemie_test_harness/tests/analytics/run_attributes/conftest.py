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

"""Fixtures for the run attributes tests: a chat and a workflow to start runs with."""

import pytest

from codemie_test_harness.tests.test_data.run_attributes_test_data import (
    WORKFLOW_TASK,
)
from codemie_test_harness.tests.utils.run_attributes_utils import (
    ChatRunSurface,
    WorkflowRunSurface,
)


@pytest.fixture
def chat_surface(
    assistant_factory, analytics_utils, assistant_utils, conversation_utils
):
    """Runs of a fresh assistant; the assistant and its conversations go with the test."""
    return ChatRunSurface(
        analytics_utils, assistant_factory.create(), assistant_utils, conversation_utils
    )


@pytest.fixture
def workflow_surface(
    assistant_factory, workflow_with_assistant, analytics_utils, workflow_utils
):
    """Executions of a fresh workflow on a fresh assistant; both go with the test."""
    workflow = workflow_with_assistant(assistant_factory.create(), WORKFLOW_TASK)
    return WorkflowRunSurface(analytics_utils, workflow, workflow_utils)


@pytest.fixture
def run_surface(request):
    """The surface named by the indirect parameter: ``chat`` or ``workflow``."""
    return request.getfixturevalue(f"{request.param}_surface")
