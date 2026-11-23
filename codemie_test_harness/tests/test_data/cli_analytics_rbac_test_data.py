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

"""Independent AI Attribution role matrix and identifiable ingest data."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from codemie_test_harness.otlp_builder import build_hook_events
from codemie_test_harness.tests.utils.base_utils import get_random_name

ROLES = ("admin", "maintainer", "auditor", "project_admin", "regular")
GLOBAL_READERS = frozenset(("admin", "maintainer", "auditor"))
ENDPOINTS = (
    "overview",
    "cost",
    "users",
    "user-charts",
    "repositories",
    "projects",
    "tools",
    "activity",
    "efficiency",
    "frameworks",
)
DETAIL_CASES = (
    "own_shared",
    "admin_project",
    "other_project",
    "own_private",
    "other_private",
)
ROLE_FLAGS = {
    "admin": {"is_admin": True},
    "maintainer": {"is_maintainer": True},
    "auditor": {"is_auditor": True},
}


@dataclass(frozen=True)
class RoleSession:
    owner: str
    project: str
    private: bool
    ordinal: int
    trace_id: str = field(default_factory=get_random_name)

    @property
    def prompt(self):
        return f"Private prompt marker {self.trace_id}"

    @property
    def tokens(self):
        return self.ordinal * 118

    def events(self, prefix):
        events = build_hook_events(
            self.trace_id,
            self.project,
            self.owner,
            f"{prefix}/{self.trace_id}",
            self.prompt,
            now=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
        usage = next(e for e in events if e["type"] == "agent.usage.request")
        usage.update(input_tokens=self.ordinal * 101, output_tokens=self.ordinal * 17)
        return events
