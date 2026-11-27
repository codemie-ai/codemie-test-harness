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

"""Test data for the project-count badge of the Cost Centers management list."""

from dataclasses import dataclass, field

import pytest


@dataclass
class LinkedCostCenter:
    """A cost center created for a test and the projects linked to it."""

    id: str
    name: str
    project_names: list[str] = field(default_factory=list)

    @property
    def project_count(self) -> int:
        return len(self.project_names)


# Number of projects linked to the cost center under test: one, and none at all.
PROJECT_COUNTS = [
    pytest.param(1, id="with_projects"),
    pytest.param(0, id="zero_projects"),
]
