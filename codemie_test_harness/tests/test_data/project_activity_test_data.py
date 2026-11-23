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

"""Test data for the project-scoped activity trail."""

import uuid

# Raised for a caller who may not read the trail, an unknown project and a personal project alike.
PROJECT_ACTIVITY_NOT_FOUND_MESSAGE = "Project activity history not found"

PROJECT_ACTIVITY_CATEGORIES = ["Budget", "Members", "Settings", "Account"]

# event_type -> (label, category), the backend's activity taxonomy for the events the tests create.
EVENT_TAXONOMY = {
    "project.created": ("Project Created", "Settings"),
    "project.updated": ("Project Updated", "Settings"),
    "project.deleted": ("Project Deleted", "Settings"),
    "project.member_spend_enforcement.updated": (
        "Member Spend Enforcement Updated",
        "Budget",
    ),
    "user.project.assigned": ("User Project Assigned", "Members"),
    "budget.project_budget_group.created": ("Project Budget Group Created", "Budget"),
    "budget.project_budget_group.deleted": ("Project Budget Group Deleted", "Budget"),
}

# Description updates the project administrator makes in the populated trail.
ADMIN_UPDATES = 2

ENFORCEMENT_EVENT = "project.member_spend_enforcement.updated"

# (query parameter, value no backend knows, fragment the validation error must contain)
UNKNOWN_FILTER_VALUES = [
    ("domain", "no_such_domain", "Unknown domain: no_such_domain"),
    ("event_type", "no.such.event", "Unknown event_type: no.such.event"),
    ("category", "NoSuchCategory", "Unknown category: NoSuchCategory"),
]


def unknown_project_instance_id() -> str:
    """A well-formed project instance id that belongs to no project."""
    return str(uuid.uuid4())
