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
from codemie_sdk.models.integration import CredentialTypes

from codemie_test_harness.tests.enums.tools import VcsTool, Toolkit
from codemie_test_harness.tests.utils.github_seed import GITHUB_SEED_ISSUE
from codemie_test_harness.tests.utils.gitlab_seed import GITLAB_SEED_MERGE_REQUEST
from codemie_test_harness.tests.utils.jira_seed import Seeded
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager


def _github_issue_query(seed) -> dict:
    return {
        "query": {
            "method": "GET",
            "url": f"https://api.github.com/repos/{seed.owner}/{seed.repo}/issues/{seed.number}",
            "method_arguments": {},
            "custom_headers": {},
        }
    }


def _github_issue_response(seed) -> str:
    return f"""
        {{
          "url" : "{seed.api_url}",
          "html_url" : "{seed.html_url}",
          "number" : {seed.number},
          "title" : "{seed.title}",
          "user" : {{
            "login" : "{seed.author}"
          }},
          "state" : "{seed.state}",
          "created_at" : "{seed.created_at}",
          "updated_at" : "{seed.updated_at}",
          "body" : "{seed.body}"
        }}
    """


def _gitlab_mr_query(seed) -> dict:
    return {
        "query": {
            "method": "GET",
            "url": f"/api/v4/projects/{seed.project_id}/merge_requests/{seed.iid}",
            "method_arguments": {},
        }
    }


def _gitlab_url() -> str:
    return CredentialsManager.get_parameter("GITLAB_URL").rstrip("/")


def _gitlab_mr_response(seed) -> str:
    return (
        f"HTTP: GET {_gitlab_url()}//api/v4/projects/{seed.project_id}/merge_requests/{seed.iid} -> "
        f'200 OK {{"id":{seed.iid},"iid":{seed.iid},"project_id":{seed.project_id},"title":"{seed.title}",'
        f'"description":"{seed.description}","state":"{seed.state}","created_at":"{seed.created_at}",'
        f'"target_branch":"{seed.target_branch}",'
        f'"source_branch":"{seed.source_branch}","web_url":"{seed.web_url}",'
        f'"diff_refs":{{"base_sha":"{seed.base_sha}","start_sha":"{seed.start_sha}","head_sha":"{seed.head_sha}"}}}}'
    )


def _gitlab_discussion_query(seed) -> dict:
    return {
        "query": {
            "method": "POST",
            "url": f"/api/v4/projects/{seed.project_id}/merge_requests/{seed.iid}/discussions",
            "method_arguments": {
                "body": "Regression: inline diff discussion via CodeMie GitLabTool",
                "position": {
                    "base_sha": seed.base_sha,
                    "start_sha": seed.start_sha,
                    "head_sha": seed.head_sha,
                    "position_type": "text",
                    "new_path": seed.file_path,
                    "new_line": 2,
                },
            },
        }
    }


def _gitlab_discussion_response(seed) -> str:
    return (
        f"HTTP: POST {_gitlab_url()}//api/v4/projects/{seed.project_id}/merge_requests/{seed.iid}/discussions -> "
        f'201 Created {{"notes":[{{"type":"DiffNote",'
        f'"body":"Regression: inline diff discussion via CodeMie GitLabTool",'
        f'"noteable_id":{seed.iid},"noteable_type":"MergeRequest","noteable_iid":{seed.iid},'
        f'"position":{{"base_sha":"{seed.base_sha}","start_sha":"{seed.start_sha}",'
        f'"head_sha":"{seed.head_sha}","new_path":"{seed.file_path}","new_line":2}}}}]}}'
    )


vcs_tools_test_data = [
    pytest.param(
        Toolkit.VCS,
        VcsTool.GITHUB,
        Seeded(GITHUB_SEED_ISSUE, _github_issue_query),
        Seeded(GITHUB_SEED_ISSUE, _github_issue_response),
        marks=pytest.mark.github,
        id=f"{CredentialTypes.GIT}_github",
    ),
    pytest.param(
        Toolkit.VCS,
        VcsTool.GITLAB,
        Seeded(GITLAB_SEED_MERGE_REQUEST, _gitlab_mr_query),
        Seeded(GITLAB_SEED_MERGE_REQUEST, _gitlab_mr_response),
        marks=pytest.mark.gitlab,
        id=f"{CredentialTypes.GIT}_gitlab",
    ),
    pytest.param(
        Toolkit.VCS,
        VcsTool.GITLAB,
        Seeded(GITLAB_SEED_MERGE_REQUEST, _gitlab_discussion_query),
        Seeded(GITLAB_SEED_MERGE_REQUEST, _gitlab_discussion_response),
        marks=pytest.mark.gitlab,
        id=f"{CredentialTypes.GIT}_gitlab_inline_discussion_json_body",
    ),
]
