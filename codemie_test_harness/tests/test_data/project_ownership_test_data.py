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

"""Test data for project ownership transfer tests."""

from uuid import uuid4

# Error body returned for an unauthorized caller and for a missing project
# (existence hiding: the same generic message in both cases).
PROJECT_NOT_FOUND_MESSAGE = "Project not found"

# Error body returned when the target user id does not belong to any user
# (ProjectService.update_project_ownership -> require_active_user, EPMCDME-13928).
USER_NOT_FOUND_MESSAGE = "User not found"

# Error body returned when the project is personal (ProjectService.ERRORS.PERSONAL_UPDATE).
PERSONAL_PROJECT_UPDATE_MESSAGE = "Cannot update a personal project"

# Activity event recorded for every ownership transfer.
OWNERSHIP_CHANGED_EVENT_TYPE = "project.ownership_changed"


def get_transfer_message(project_name: str, new_owner_id: str) -> str:
    """Message of a successful PUT /v1/projects/{projectName}/ownership response."""
    return f"Ownership of '{project_name}' transferred to '{new_owner_id}'"


def get_nonexistent_user_id() -> str:
    """A well-formed user id that belongs to no user."""
    return str(uuid4())
