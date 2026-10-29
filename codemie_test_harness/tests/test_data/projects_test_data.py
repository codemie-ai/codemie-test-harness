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

"""Test data for project management tests."""

import pytest

from codemie_test_harness.tests.utils.base_utils import get_random_name

# ── display_name constants ──────────────────────────────────────────────────

# Exactly 150 printable characters (boundary — must succeed)
DISPLAY_NAME_MAX = "A" * 150

# 151 characters — must be rejected by SDK validation (pydantic max_length=150)
DISPLAY_NAME_TOO_LONG = "A" * 151

# Multi-script unicode string: Cyrillic + CJK + emoji
DISPLAY_NAME_UNICODE = "Проект 项目 🚀"


def get_project_create_data_with_display_name():
    """Return project creation payload that includes a display_name."""
    base = get_project_create_data()
    base["display_name"] = f"Display {get_random_name()}"
    return base


def get_project_update_data_with_display_name():
    """Return project update payload that includes a new display_name."""
    return {
        "description": f"Updated project description {get_random_name()}",
        "display_name": f"Updated Display {get_random_name()}",
    }


def get_project_create_data():
    """Generate random project data for creation."""
    return {
        "name": get_random_name(),
        "description": f"Test project created by automated tests at {get_random_name()}",
    }


def get_project_update_data():
    """Generate random project data for update."""
    return {
        "name": get_random_name(),
        "description": f"Updated project description {get_random_name()}",
    }


# Test data for list projects with different parameters
list_projects_test_data = [
    pytest.param(
        {"page": 0, "per_page": 10},
        marks=[pytest.mark.smoke, pytest.mark.api],
        id="list_projects_first_page",
    ),
    pytest.param(
        {"page": 0, "per_page": 20, "sort_by": "name", "sort_order": "asc"},
        marks=pytest.mark.api,
        id="list_projects_sorted_by_name_asc",
    ),
    pytest.param(
        {"page": 0, "per_page": 20, "sort_by": "created_at", "sort_order": "desc"},
        marks=pytest.mark.api,
        id="list_projects_sorted_by_date_desc",
    ),
    pytest.param(
        {"page": 0, "per_page": 10, "include_counters": True},
        marks=pytest.mark.api,
        id="list_projects_with_counters",
    ),
]

# Test data for user assignment operations
user_assignment_test_data = [
    pytest.param(
        True,
        marks=[pytest.mark.smoke, pytest.mark.api],
        id="assign_as_project_admin",
    ),
    pytest.param(
        False,
        marks=pytest.mark.api,
        id="assign_as_regular_user",
    ),
]

# CSV test data for import validation
# Valid CSV format: email,role
# Valid role values: 'project_admin' or 'user'
csv_valid_content = b"""email,role
test_user_project@example.com,user
test_user_default@example.com,project_admin
"""

csv_not_exist_users_content = b"""email,role
432432@example.com,user
432424@example.com,project_admin
"""

csv_invalid_email_content = b"""email,role
invalid-email,user
test@example.com,project_admin
"""

csv_invalid_role_content = b"""email,role
test@example.com,invalid_role
"""

# All entries test validation-error scenarios (API returns 200 with per-row errors).
# The happy-path import test (existing user) lives in test_import_users_from_csv,
# which builds the CSV dynamically from the authenticated user's email.
csv_import_test_data = [
    pytest.param(
        csv_not_exist_users_content,
        "csv_not_exist_users_content.csv",
        marks=pytest.mark.api,
        id="csv_import_unknown_users",
    ),
    pytest.param(
        csv_invalid_email_content,
        "invalid_email.csv",
        marks=pytest.mark.api,
        id="csv_import_invalid_email",
    ),
    pytest.param(
        csv_invalid_role_content,
        "invalid_role.csv",
        marks=pytest.mark.api,
        id="csv_import_invalid_role",
    ),
]
