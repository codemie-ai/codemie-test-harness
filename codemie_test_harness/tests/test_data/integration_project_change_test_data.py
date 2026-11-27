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

"""Test data for changing the project of an existing integration."""

from dataclasses import dataclass
from typing import List

import pytest

from codemie_sdk.models.integration import CredentialValues, IntegrationType
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager

# TC_002 -- the PUT endpoint differs per scope (/v1/settings/project vs /v1/settings/user).
project_change_scope_test_data = [
    pytest.param(IntegrationType.PROJECT, id="project_scope"),
    pytest.param(IntegrationType.USER, id="user_scope"),
]

# Messages the backend returns for the rejected project changes.
ACCESS_DENIED_DETAILS = "You do not have sufficient permissions to access the project"
ALIAS_COLLISION_DETAILS = "There are more than one settings with the alias named"
NOT_OWNER_ACCESS_DENIED_MESSAGE = "Access denied"
NOT_OWNER_UPDATE_DETAILS = "to update this entity"

# Fixture names of callers who are not the owner of a personal integration; resolved lazily so
# each caller is only created for its own case.
non_owner_caller_test_data = [
    pytest.param("project_admin_non_owner_utils", id="project_admin"),
    pytest.param("platform_admin_non_owner_utils", id="platform_admin"),
]

# Message returned by a successful PUT /v1/settings/{project|user}/{id}.
INTEGRATION_UPDATED_MESSAGE = "Specified credentials updated"

# DELETE /v1/settings/project/{id}: refusal of a Project Admin who does not own the personal row,
# and the message of a successful delete.
NOT_OWNER_DELETE_DETAILS = (
    "You do not have the necessary permissions to delete this entity."
)
INTEGRATION_DELETED_MESSAGE = "Specified credential removed"

# Fixture names of callers who may delete another user's (or their own) personal integration through
# the project-level delete; resolved lazily so each caller is only created for its own case.
personal_integration_deleter_test_data = [
    pytest.param("owner_project_admin_utils", id="owner"),
    pytest.param("platform_admin_deleter_utils", id="platform_admin"),
    pytest.param("maintainer_deleter_utils", id="maintainer"),
]


# Rejection of a one-row move of a row whose stored alias belongs to another subsystem.
RESERVED_IDENTIFIERS_MESSAGE = "Reserved integration identifiers"
MANAGED_ALIAS_DETAILS = (
    "This alias is managed by an internal subsystem and cannot be transferred:"
)

# Stored aliases the backend treats as subsystem-managed: one per reserved prefix and the exact
# reserved alias (which must stay literal). The user-scope list hides ``__internal__`` rows, so that
# one is project-scope only.
INTERNAL_MANAGED_ALIAS = f"__internal__{get_random_name()}"
LITELLM_MANAGED_ALIAS = f"codemie:project:{get_random_name()}:category:premium_models"
SCHEDULE_MANAGED_ALIAS = f"Schedule_{get_random_name()}"
EXACT_RESERVED_ALIAS = "project_member_budget_tracking_enabled"

project_managed_alias_test_data = [
    pytest.param(INTERNAL_MANAGED_ALIAS, id="internal_prefix"),
    pytest.param(LITELLM_MANAGED_ALIAS, id="litellm_project_prefix"),
    pytest.param(SCHEDULE_MANAGED_ALIAS, id="schedule_prefix"),
    pytest.param(EXACT_RESERVED_ALIAS, id="exact_reserved_alias"),
]
user_managed_alias_test_data = [
    pytest.param(LITELLM_MANAGED_ALIAS, id="litellm_project_prefix"),
    pytest.param(SCHEDULE_MANAGED_ALIAS, id="schedule_prefix"),
]


@dataclass
class GitDatasourceSource:
    """Repository and matching Git integration credentials for a code datasource."""

    link: str
    credentials: List[CredentialValues]


def git_datasource_source() -> GitDatasourceSource:
    """Repository link and credentials for the Git provider selected by ``GIT_ENV``."""
    if CredentialsManager.get_parameter("GIT_ENV", "gitlab") == "gitlab":
        return GitDatasourceSource(
            link=CredentialsManager.get_parameter("GITLAB_PROJECT"),
            credentials=CredentialsManager.gitlab_credentials(),
        )
    return GitDatasourceSource(
        link=CredentialsManager.get_parameter("GITHUB_PROJECT"),
        credentials=CredentialsManager.github_credentials(),
    )
