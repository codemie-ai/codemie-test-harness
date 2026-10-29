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

"""Test data for workflow-scoped personal integration mapping API tests.

Covers: Per-workflow scope for personal integration settings.
"""

from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class SlotAssignment:
    """A single integration slot assignment for user mapping."""

    name: str
    integration_id: Optional[str] = None
    explicit_none: bool = False

    def to_dict(self) -> dict:
        """Convert to API payload dict.

        The backend types ``tools_config`` as ``List[Dict[str, str]]`` — every value
        must be a string, so no boolean may be sent. Explicit "no integration" is
        expressed solely by ``integration_id=""``: the backend validator checks
        ``integration_id is None``, so an omitted value means "not set" (auto-lookup)
        while an empty string means "no integration". ``explicit_none`` is a
        frontend-only concept and is deliberately not sent.
        """
        item: dict = {"name": self.name}
        if self.explicit_none:
            item["integration_id"] = ""
        elif self.integration_id is not None:
            item["integration_id"] = self.integration_id
        return item


@dataclass
class UserMappingApiTestData:
    """Test data for a single user mapping API call.

    Encapsulates the assistant, optional workflow scope, and the slot
    assignments to save or assert against.
    """

    assistant_id: str
    slot_assignments: List[SlotAssignment] = field(default_factory=list)
    workflow_id: Optional[str] = None

    def to_tools_config(self) -> List[dict]:
        """Convert slot assignments to the ``tools_config`` payload format."""
        return [slot.to_dict() for slot in self.slot_assignments]
