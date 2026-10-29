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

"""Seed data for Jira tests: a persistent marker issue plus two custom fields.

Pure logic only (no HTTP) so it can be unit tested; JiraUtils performs the
requests. The seed issue is created once per Jira project and reused by every
later run, so tests never depend on pre-existing tickets.
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Optional

import pytest
from filelock import FileLock, Timeout

SEED_SUMMARY = "CodeMie Test Harness Seed Issue"
SEED_DESCRIPTION = (
    "Seed issue used by codemie-test-harness Jira tests. Do not delete or edit."
)
CUSTOM_FIELD_VALUES = ("harness-cf-1", "harness-cf-2")

JIRA_SERVER_SEED = "jira_seed_issue"
JIRA_CLOUD_SEED = "jira_cloud_seed_issue"

LOCK_TIMEOUT_SECONDS = 300

# Plain-text custom field types, in order of preference.
_TEXT_FIELD_TYPES = (
    "com.atlassian.jira.plugin.system.customfieldtypes:textfield",
    "com.atlassian.jira.plugin.system.customfieldtypes:textarea",
)


@dataclass(frozen=True)
class CustomField:
    id: str
    name: str
    value: Optional[str] = None


@dataclass(frozen=True)
class SeedIssue:
    key: str
    project_key: str
    summary: str = SEED_SUMMARY
    description: str = SEED_DESCRIPTION
    custom_fields: tuple[CustomField, ...] = ()

    @property
    def jql(self) -> str:
        return build_seed_jql(self.project_key)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SeedIssue":
        custom_fields = tuple(CustomField(**cf) for cf in data.get("custom_fields", ()))
        return cls(**{**data, "custom_fields": custom_fields})


def build_seed_jql(project_key: str) -> str:
    """JQL matching the seed issue by phrase; exact match is checked in Python."""
    return f'project = "{project_key}" AND summary ~ "\\"{SEED_SUMMARY}\\""'


def find_seed_issue_key(
    issues: list[dict], summary: str = SEED_SUMMARY
) -> Optional[str]:
    """Key of the oldest issue whose summary equals ``summary`` exactly."""
    matches = [
        issue for issue in issues if issue.get("fields", {}).get("summary") == summary
    ]
    if not matches:
        return None
    return min(matches, key=lambda issue: int(issue["id"]))["key"]


def is_writable(editmeta_fields: dict, field_id: str) -> bool:
    return "set" in editmeta_fields.get(field_id, {}).get("operations", [])


def select_custom_fields(
    editmeta_fields: dict, overrides: list[str]
) -> list[tuple[str, str]]:
    """(id, name) of up to two custom fields to use; configured overrides win."""
    if overrides:
        return [
            (field_id, editmeta_fields.get(field_id, {}).get("name", field_id))
            for field_id in overrides[:2]
        ]

    candidates = [
        (field_id, meta)
        for field_id, meta in editmeta_fields.items()
        if field_id.startswith("customfield_")
        and meta.get("schema", {}).get("type") == "string"
        and meta.get("schema", {}).get("custom") in _TEXT_FIELD_TYPES
        and is_writable(editmeta_fields, field_id)
    ]
    candidates.sort(
        key=lambda c: (
            _TEXT_FIELD_TYPES.index(c[1]["schema"]["custom"]),
            int(c[0].split("_")[1]),
        )
    )
    return [(field_id, meta.get("name", field_id)) for field_id, meta in candidates[:2]]


@dataclass(frozen=True)
class Seeded:
    """Test data that is only known once the seed issue for ``fixture_name`` exists.

    Parametrize lists hold these; tests turn them into concrete values with
    the ``seeded`` fixture.
    """

    fixture_name: str
    render: Callable[[SeedIssue], Any]


def resolve_seeded(value: Any, getfixturevalue: Callable[[str], Any]) -> Any:
    if isinstance(value, Seeded):
        return value.render(getfixturevalue(value.fixture_name))
    return value


def require_custom_fields(
    seed: SeedIssue, count: int, with_values: bool = False
) -> list[CustomField]:
    """First ``count`` seed custom fields, or skip the test if there are fewer."""
    fields = [f for f in seed.custom_fields if f.value or not with_values]
    if len(fields) < count:
        kind = "populated " if with_values else ""
        pytest.skip(
            f"Need {count} {kind}Jira custom field(s) on {seed.key}, found {len(fields)}"
        )
    return fields[:count]


def resolve_shared(
    lock_dir: Optional[Path], name: str, produce: Callable[[], dict]
) -> dict:
    """Run ``produce`` once per test run and share its JSON result with all xdist workers.

    ``lock_dir`` is None outside xdist: there is a single process, so nothing is cached.
    """
    if lock_dir is None:
        return produce()

    cache = lock_dir / f"{name}.json"
    try:
        with FileLock(str(lock_dir / f"{name}.lock"), timeout=LOCK_TIMEOUT_SECONDS):
            if cache.is_file():
                return json.loads(cache.read_text())
            data = produce()
            cache.write_text(json.dumps(data))
            return data
    except Timeout as e:
        raise TimeoutError(
            f"Shared resolution of '{name}' did not finish within "
            f"{LOCK_TIMEOUT_SECONDS}s; another xdist worker is likely stuck or "
            f"failing — check its error output"
        ) from e
