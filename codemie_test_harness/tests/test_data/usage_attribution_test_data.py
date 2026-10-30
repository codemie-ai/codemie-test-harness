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

"""Test data for the Usage Attribution analytics tests."""

from dataclasses import dataclass, field

import pytest

USAGE_ATTRIBUTION_FEATURE_ID = "features:usageAttribution"

# Money fields are rounded to cents on the server, so sums of several rounded fields may differ by a few cents.
MONEY_TOLERANCE = 0.05
# A breakdown total is the sum of its rows, each rounded to cents.
TOTAL_TOLERANCE = 0.01
# A breakdown lists at most 12 named buckets; the rest is folded into one "Other" bucket, listed last.
MAX_NAMED_BUCKETS = 12
OTHER_BUCKET_LABEL = "Other"

MAX_RANGE_DAYS = 90
CLAMPED_RANGE_DAYS = 120

PERIOD_LAST_30_DAYS = "last_30_days"

CATEGORIES = (
    "production",
    "learning",
    "testing",
    "experimental",
    "pet_project",
    "unclassified",
)
PAYERS = ("charged", "shared", "personal")
CACHE_STATES = ("hit", "miss", "shared", "stale")
REUSED_CACHE_STATES = ("hit", "shared")

# Roles by the name of the fixture that provides their client.
ROLES_WITH_ACCESS = [
    pytest.param("client", id="admin"),
    pytest.param("maintainer_client", id="maintainer"),
    pytest.param("auditor_client", id="auditor"),
]
ROLES_WITHOUT_ACCESS = [
    pytest.param("project_admin_client", id="project-admin"),
    pytest.param("member_client", id="member"),
]
FORBIDDEN = 403


@dataclass(frozen=True)
class RangeCase:
    """A way to select the period: a named one, or a custom range of ``days`` ending now."""

    time_period: str | None = None
    days: int | None = None


RANGES_WITH_SAME_CATEGORIES = [
    pytest.param(RangeCase(time_period="last_7_days"), id="7-days"),
    pytest.param(RangeCase(time_period="last_30_days"), id="30-days"),
    pytest.param(RangeCase(days=14), id="custom-14-days"),
]

# Fields every fast totals response carries, whatever the range.
TOTALS_FIELDS = ("total", "web", "cli", "charged_back", "who_pays", "excluded")


@dataclass(frozen=True)
class ListCase:
    """A paginated Usage Attribution list and the popup that opens from its first row."""

    list_method: str
    detail_method: str
    id_field: str
    detail_sections: tuple[str, ...]
    all_rows: dict[str, str] = field(default_factory=dict)


SCOPED_LISTS = [
    pytest.param(
        ListCase(
            list_method="get_shared_projects",
            detail_method="get_shared_project",
            id_field="name",
            detail_sections=(
                "repos",
                "cli_people",
                "agents",
                "models",
                "web_people",
                "assets",
                "web_types",
                "models_all",
            ),
            all_rows={"scope": "all"},
        ),
        id="shared-projects",
    ),
    pytest.param(
        ListCase(
            list_method="get_repository_groups",
            detail_method="get_repository_group",
            id_field="id",
            detail_sections=(
                "categories",
                "repos",
                "models",
                "agents",
                "projects",
                "people",
                "sessions",
                "why",
                "related",
            ),
            all_rows={"scope": "all"},
        ),
        id="repository-groups",
    ),
]
PEOPLE_CASE = ListCase(
    list_method="get_people",
    detail_method="get_person",
    id_field="uid",
    detail_sections=(
        "projects",
        "repos",
        "by_category",
        "reasons",
        "allocated",
        "sessions",
        "models",
        "agents",
        "recent",
        "assets",
        "chargeback",
    ),
    all_rows={"filter": "all"},
)
PEOPLE_LIST = pytest.param(PEOPLE_CASE, id="people")
ALL_LISTS = [*SCOPED_LISTS, PEOPLE_LIST]

PEOPLE_FILTERS = ("all", "cand", "prod", "exp", "shared", "platform")

# The defaults the feature ships with, by the key GET /settings lists them under.
SHIPPED_SETTING_DEFAULTS = {
    "sharedProjectThresholdPer30Days": 1000,
    "repositoryGroupThresholdPer30Days": 1000,
    "experimentsHighlightPer30Days": 500,
    "platformPeopleFilterPer30Days": 300,
    "candidateProductionDaysPer30Days": 5,
    "minimumConfidence": 50,
    "productionMinFamilies": 2,
    "thresholds.activeDaysProduction": 5,
    "allocateByPerson.enabled": True,
    "allocateByPerson.minClassifiedShare": 0.1,
    "allocateByPerson.minClassifiedSpend": 5,
    "groupMinSignals": 2,
    "minimumEvidenceDays": 30,
}
SHIPPED_FIXED_SETTINGS = {
    "max_range_days": 90,
    "analysis_cache_minutes": 15,
}
SHIPPED_TUNING = {
    "enabled": True,
    "roles": ["admin", "maintainer"],
    "max_override_bytes": 4096,
}

# What GET /v1/config may carry for the feature: the analysis settings are served only by its own endpoint.
PUBLIC_COMPONENT_FIELDS = ("enabled", "availableForExternal", "name", "description")

SETTINGS_BY_ROLE = [
    pytest.param("client", True, True, id="admin"),
    pytest.param("auditor_client", False, False, id="auditor"),
]
