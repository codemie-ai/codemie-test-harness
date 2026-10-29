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

from codemie_test_harness.tests.utils.confluence_seed import (
    CONFLUENCE_CLOUD_SEED,
    CONFLUENCE_SERVER_SEED,
    SEED_TEXT,
)
from codemie_test_harness.tests.utils.jira_seed import (
    JIRA_CLOUD_SEED,
    JIRA_SERVER_SEED,
    Seeded,
)


def _jira_title_prompt(seed) -> str:
    return f"Get a title for {seed.key} ticket."


def _jira_title_response(seed) -> str:
    return f"""
    The title for ticket {seed.key} is:
    {seed.summary}
"""


JIRA_TOOL_PROMPT = Seeded(JIRA_SERVER_SEED, _jira_title_prompt)

RESPONSE_FOR_JIRA_TOOL = Seeded(JIRA_SERVER_SEED, _jira_title_response)


def _confluence_title_prompt(seed) -> str:
    return f"""
    Use any of tools available: Generic Confluence Tool with the params:
    relative_url='/rest/api/content/search'
    method='GET'
    params='{{'cql': '{seed.cql}', 'limit': 5, 'expand': 'body.storage'}}'
    or Search Kb tool
    and return the page content
"""


def _confluence_title_response(seed) -> str:
    return f"""
    Result:
    The page "{seed.title}" says: {SEED_TEXT}
"""


CONFLUENCE_TOOL_PROMPT = Seeded(CONFLUENCE_SERVER_SEED, _confluence_title_prompt)

RESPONSE_FOR_CONFLUENCE_TOOL = Seeded(
    CONFLUENCE_SERVER_SEED, _confluence_title_response
)

RESPONSE_FOR_CONFLUENCE_TOOL_UNAUTHORIZED = """
    It appears that the search could not be completed due to authentication issues (HTTP Status 401 – Unauthorized). 
    To access the knowledge base, valid authentication credentials are required.


    Please provide authentication credentials or ensure that I have the necessary permissions to access the 
    Confluence knowledge base. If you need further assistance, feel free to ask!
"""

JIRA_CLOUD_TOOL_PROMPT = Seeded(JIRA_CLOUD_SEED, _jira_title_prompt)

RESPONSE_FOR_JIRA_CLOUD_TOOL = Seeded(JIRA_CLOUD_SEED, _jira_title_response)

CONFLUENCE_CLOUD_TOOL_PROMPT = Seeded(CONFLUENCE_CLOUD_SEED, _confluence_title_prompt)

RESPONSE_FOR_CONFLUENCE_CLOUD_TOOL = Seeded(
    CONFLUENCE_CLOUD_SEED, _confluence_title_response
)


def _jira_seed_fixture(jira_type: str) -> str:
    return JIRA_CLOUD_SEED if jira_type == "cloud" else JIRA_SERVER_SEED


def get_jira_tool_create_prompt(jira_type: str) -> Seeded:
    return Seeded(
        _jira_seed_fixture(jira_type),
        lambda seed: (
            "Create a new issue in Jira with the following details. "
            "For generic jira tool use exactly the same parameters: "
            "relative_url=/rest/api/2/issue "
            "method=POST "
            f"params={{'fields': {{'project': {{'key': '{seed.project_key}'}}, 'summary': '%s Test issue created by automation', "
            "'description': 'This is a test issue created for testing purposes', 'issuetype': {'name': 'Task'}}}}}"
        ),
    )


def get_response_for_jira_tool_create(jira_type: str) -> Seeded:
    return Seeded(
        _jira_seed_fixture(jira_type),
        lambda seed: f"""
    The issue has been successfully created in Jira. Here are the details:

       - **Key**: {seed.project_key}-.....
       - **Link**: [{seed.project_key}-.....](https://jira.....)
""",
    )


def _confluence_seed_fixture(confluence_type: str) -> str:
    return (
        CONFLUENCE_CLOUD_SEED if confluence_type == "cloud" else CONFLUENCE_SERVER_SEED
    )


def get_confluence_tool_create_prompt(confluence_type: str) -> Seeded:
    return Seeded(
        _confluence_seed_fixture(confluence_type),
        lambda seed: f"""
    Create a new page in Confluence with the following details using Generic Confluence Tool with the params:
    relative_url='/rest/api/content'
    method='POST'
    params={{'type': 'page', 'title': '%s Test Page Created by Automation', 'space': {{'key': '{seed.space_key}'}},
    'body': {{'storage': {{'value': '<p>This is a test page created for testing purposes.</p>', 'representation': 'storage'}}}}}}
""",
    )


def get_response_for_confluence_tool_create(confluence_type: str) -> Seeded:
    return Seeded(
        _confluence_seed_fixture(confluence_type),
        lambda seed: f"""
    Successfully created a new page in Confluence.
    The page has been created with the following details:
    - Title: Test Page Created by Automation
    - Space: {seed.space_key}
    - Content: This is a test page created for testing purposes.
""",
    )
