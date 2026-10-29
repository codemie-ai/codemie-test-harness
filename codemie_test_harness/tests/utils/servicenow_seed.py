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

"""Seed data for ServiceNow tests: a persistent marker incident.

Pure logic only (no HTTP) so it can be unit tested; ServiceNowUtils performs the
requests. The seed incident is created once in the configured ServiceNow instance
and reused by every later run, so tests never depend on a pre-existing incident
such as the previously hardcoded INC0000060. It is looked up by short_description,
which survives a Personal Developer Instance reset (unlike sys_id and host name).
"""

from dataclasses import asdict, dataclass
from typing import Optional

SEED_SHORT_DESCRIPTION = "CodeMie Test Harness Seed Incident"
SEED_DESCRIPTION = "Seed incident used by codemie-test-harness ServiceNow tests. Do not delete or edit."

SERVICENOW_SEED_INCIDENT = "servicenow_seed_incident"

SEED_FIELDS = "sys_id,number,short_description,state,sys_created_on"


@dataclass(frozen=True)
class SeedIncident:
    sys_id: str
    number: str
    short_description: str = SEED_SHORT_DESCRIPTION
    state: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SeedIncident":
        return cls(**data)


def build_seed_query(short_description: str = SEED_SHORT_DESCRIPTION) -> str:
    """Encoded query matching incidents whose short_description equals the given text."""
    return f"short_description={short_description}"


def find_seed_incident(
    records: list[dict], short_description: str = SEED_SHORT_DESCRIPTION
) -> Optional[dict]:
    """The oldest incident whose short_description equals ``short_description`` exactly."""
    matches = [
        record
        for record in records
        if record.get("short_description") == short_description
    ]
    if not matches:
        return None
    return min(matches, key=lambda record: record["sys_created_on"])


def seed_incident_from_record(record: dict) -> SeedIncident:
    return SeedIncident(
        sys_id=record["sys_id"],
        number=record["number"],
        short_description=record["short_description"],
        state=record["state"],
    )


def seed_tool_expectation(seed: SeedIncident) -> dict:
    """Stable subset of the incident record that the direct tool test asserts."""
    return {
        "number": seed.number,
        "short_description": seed.short_description,
        "state": seed.state,
    }


def seed_expected_response(seed: SeedIncident) -> str:
    """Assistant answer that describes the seed incident (compared by similarity)."""
    return f"""
        Here is the information for the incident `{seed.number}`:

        - **Number**: {seed.number}
        - **Short Description**: {seed.short_description}
        - **State**: {seed.state}
    """
