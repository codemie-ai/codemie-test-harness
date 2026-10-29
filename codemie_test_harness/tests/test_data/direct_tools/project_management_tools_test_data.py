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

import json

import pytest

from codemie_test_harness.tests.enums.tools import Toolkit, ProjectManagementTool
from codemie_test_harness.tests.utils.confluence_seed import CONFLUENCE_SERVER_SEED
from codemie_test_harness.tests.utils.constants import ProjectManagementIntegrationType
from codemie_test_harness.tests.utils.jira_seed import JIRA_SERVER_SEED, Seeded

project_management_tools_data = [
    pytest.param(
        Toolkit.PROJECT_MANAGEMENT,
        ProjectManagementTool.JIRA,
        ProjectManagementIntegrationType.JIRA,
        Seeded(
            JIRA_SERVER_SEED,
            lambda seed: {
                "method": "GET",
                "relative_url": f"/rest/api/2/issue/{seed.key}",
                "params": '{"fields": "summary,description"}',
            },
        ),
        Seeded(
            JIRA_SERVER_SEED,
            lambda seed: (
                f"HTTP: GET /rest/api/2/issue/{seed.key} -> 200 OK "
                f'{{"key":"{seed.key}","fields":{{"summary":"{seed.summary}",'
                f'"description":"{seed.description}"}}}}'
            ),
        ),
        marks=[pytest.mark.jira, pytest.mark.smoke],
        id=ProjectManagementIntegrationType.JIRA,
    ),
    pytest.param(
        Toolkit.PROJECT_MANAGEMENT,
        ProjectManagementTool.JIRA,
        ProjectManagementIntegrationType.JIRA,
        Seeded(
            JIRA_SERVER_SEED,
            lambda seed: {
                "method": "POST",
                "relative_url": "/rest/api/2/issue",
                "params": json.dumps(
                    {
                        "fields": {
                            "project": {"key": seed.project_key},
                            "summary": "Autotest direct tool issue",
                            "description": "General Description: general_description\nBusiness Value: business_value\nPreconditions: preconditions\nScenarios of Use: scenarios_of_use\nExpected Results: expected_results\nAffected Areas: affected_areas\nAcceptance Criteria: acceptance_criteria",
                            "issuetype": {"name": "Task"},
                        }
                    }
                ),
            },
        ),
        Seeded(
            JIRA_SERVER_SEED,
            lambda seed: (
                'HTTP: POST /rest/api/2/issue -> 201 Created {"id":"...",'
                f'"key":"{seed.project_key}-...","self":"https://.../rest/api/2/issue/..."}}'
            ),
        ),
        marks=pytest.mark.jira,
        id="jira - create",
    ),
    pytest.param(
        Toolkit.PROJECT_MANAGEMENT,
        ProjectManagementTool.CONFLUENCE,
        ProjectManagementIntegrationType.CONFLUENCE,
        Seeded(
            CONFLUENCE_SERVER_SEED,
            lambda seed: {
                "method": "GET",
                "relative_url": "/rest/api/content/search",
                "params": json.dumps(
                    {"cql": seed.cql, "limit": 5, "expand": "body.storage"}
                ),
                "is_markdown": False,
            },
        ),
        Seeded(
            CONFLUENCE_SERVER_SEED,
            lambda seed: (
                f"HTTP: GET /rest/api/content/search -> 200 OK "
                f'{{"results":[{{"id":"{seed.id}","type":"page","status":"current",'
                f'"title":"{seed.title}","body":{{"storage":{{"value":"{seed.body}",'
                f'"representation":"storage"}}}}}}],"start":0,"limit":5,"size":1}}'
            ),
        ),
        marks=pytest.mark.confluence,
        id=ProjectManagementIntegrationType.CONFLUENCE,
    ),
]
