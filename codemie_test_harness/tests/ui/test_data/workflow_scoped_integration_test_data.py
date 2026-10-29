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

"""Test data for workflow-scoped integration UI tests.

Covers: Per-workflow scope for personal integration settings.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class WorkflowScopedMappingTestData:
    """Test data for workflow-scoped integration mapping UI tests.

    Captures the identifiers needed to navigate to a workflow node panel
    and interact with the 'Your Integration Settings' section.
    """

    workflow_id: str
    assistant_id: str
    integration_slot_id: str
    integration_id: Optional[str]
    apply_to_whole_assistant: bool = False
