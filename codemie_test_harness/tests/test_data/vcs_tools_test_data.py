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

import pytest

from codemie_test_harness.tests.enums.tools import VcsTool
from codemie_test_harness.tests.utils.azure_devops_seed import (
    AZURE_DEVOPS_SEED_PULL_REQUEST,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.github_seed import (
    GITHUB_SEED_FILE,
    GITHUB_SEED_ISSUE,
)
from codemie_test_harness.tests.utils.gitlab_seed import GITLAB_SEED_MERGE_REQUEST
from codemie_test_harness.tests.utils.jira_seed import Seeded


def _github_tool_task(seed) -> str:
    return (
        f"Using github tool get info about issue №{seed.number} for the repo "
        f"{seed.owner}/{seed.repo}. Do not wrap tool parameters in additional query object"
    )


def _response_for_github(seed) -> str:
    return f"""
    Issue #{seed.number} in `{seed.owner}/{seed.repo}`:

    - **Title:** {seed.title}
    - **State:** {seed.state}
    - **Author:** {seed.author}
    - **Created / Updated:** {seed.created_at} / {seed.updated_at}
    - **Body:** "{seed.body}"
    - **URLs:**
      - HTML: {seed.html_url}
      - API: {seed.api_url}
"""


GITHUB_TOOL_TASK = Seeded(GITHUB_SEED_ISSUE, _github_tool_task)
RESPONSE_FOR_GITHUB = Seeded(GITHUB_SEED_ISSUE, _response_for_github)

GITHUB_REPO_CONTENT_TOOL_TASK = (
    f"Get {CredentialsManager.get_parameter('GITHUB_PROJECT')} repo content"
)


def _response_for_github_repo_content(seed) -> str:
    return f"""
    The {seed.owner}/{seed.repo} repository's root directory contains several files,
    including `{seed.name}` ({seed.path}) — View file on GitHub.

    Would you like to see the contents of {seed.name} or get additional information about the repository?
"""


RESPONSE_FOR_GITHUB_REPO_CONTENT = Seeded(
    GITHUB_SEED_FILE, _response_for_github_repo_content
)


def _gitlab_tool_task(seed) -> str:
    return (
        f"Using gitlab tool get info about MR №{seed.iid} for repo with id "
        f"'{seed.project_id}'"
    )


def _response_for_gitlab(seed) -> str:
    return f"""
    Here is the information about Merge Request (MR) №{seed.iid} for the repository with id '{seed.project_id}':

    - **Title:** {seed.title}
    - **Description:** {seed.description}
    - **State:** {seed.state}
    - **Created At:** {seed.created_at}
    - **Target Branch:** {seed.target_branch}
    - **Source Branch:** {seed.source_branch}
    - **Author:** [{seed.author}]({seed.author_web_url})
    - **Web URL:** [Link to MR]({seed.web_url})
"""


GITLAB_TOOL_TASK = Seeded(GITLAB_SEED_MERGE_REQUEST, _gitlab_tool_task)
RESPONSE_FOR_GITLAB = Seeded(GITLAB_SEED_MERGE_REQUEST, _response_for_gitlab)


def _azure_devops_git_tool_task(seed) -> str:
    return (
        f"Using azuredevops tool get info about pull request №{seed.pull_request_id} "
        f"for project '{seed.project}' and repository '{seed.repository}'"
    )


def _response_for_azure_devops_git(seed) -> str:
    return f"""
    Here is the information about Pull Request #{seed.pull_request_id} for the repository '{seed.repository}':

    - **Title:** {seed.title}
    - **Description:** {seed.description}
    - **Status:** {seed.status}
    - **Created By:** {seed.created_by}
    - **Email:** {seed.created_by_email}
    - **Creation Date:** {seed.creation_date}
    - **Source Branch:** `refs/heads/{seed.source_branch}`
    - **Target Branch:** `refs/heads/{seed.target_branch}`
    - **Pull Request URL:** {seed.url}
"""


AZURE_DEVOPS_GIT_TOOL_TASK = Seeded(
    AZURE_DEVOPS_SEED_PULL_REQUEST, _azure_devops_git_tool_task
)
RESPONSE_FOR_AZURE_DEVOPS_GIT = Seeded(
    AZURE_DEVOPS_SEED_PULL_REQUEST, _response_for_azure_devops_git
)

vcs_tools_test_data = [
    pytest.param(
        VcsTool.GITHUB,
        GITHUB_TOOL_TASK,
        RESPONSE_FOR_GITHUB,
        marks=pytest.mark.github,
        id=VcsTool.GITHUB,
    ),
    pytest.param(
        VcsTool.GITLAB,
        GITLAB_TOOL_TASK,
        RESPONSE_FOR_GITLAB,
        marks=pytest.mark.gitlab,
        id=VcsTool.GITLAB,
    ),
    pytest.param(
        VcsTool.AZURE_DEVOPS_GIT,
        AZURE_DEVOPS_GIT_TOOL_TASK,
        RESPONSE_FOR_AZURE_DEVOPS_GIT,
        marks=pytest.mark.azure_devops_git,
        id=VcsTool.AZURE_DEVOPS_GIT,
    ),
    pytest.param(
        VcsTool.GITHUB,
        GITHUB_REPO_CONTENT_TOOL_TASK,
        RESPONSE_FOR_GITHUB_REPO_CONTENT,
        marks=pytest.mark.github,
        id="github_no_folders",
    ),
]
