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
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager

# TC_002 -- the PUT endpoint differs per scope (/v1/settings/project vs /v1/settings/user).
project_change_scope_test_data = [
    pytest.param(IntegrationType.PROJECT, id="project_scope"),
    pytest.param(IntegrationType.USER, id="user_scope"),
]

# Messages the backend returns for the rejected project changes.
ACCESS_DENIED_DETAILS = "You do not have sufficient permissions to access the project"
ALIAS_COLLISION_DETAILS = "There are more than one settings with the alias named"

# Message returned by a successful PUT /v1/settings/{project|user}/{id}.
INTEGRATION_UPDATED_MESSAGE = "Specified credentials updated"


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
