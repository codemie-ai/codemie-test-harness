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

from codemie_test_harness.tests.enums.tools import Toolkit, AzureDevOpsTestPlanTool
from codemie_test_harness.tests.utils.ado_names import ADO_PROJECT_NAME, ado_text
from codemie_test_harness.tests.utils.ado_seed import (
    ADO_TEST_PLAN_SEED,
    SeedIdentity,
    SeedTestPlan,
)
from codemie_test_harness.tests.utils.jira_seed import Seeded


def _identity_minimal_snake(identity: SeedIdentity) -> dict:
    """``SeedIdentity`` as the reduced snake_case shape the test-plan tools use."""
    return {
        "id": identity.id,
        "display_name": identity.display_name,
        "unique_name": identity.unique_name,
    }


def _test_plan_json(plan: SeedTestPlan) -> dict:
    """Test plan as the get-test-plan tool returns it (fields derived from the seed)."""
    owner = _identity_minimal_snake(plan.owner)
    return {
        "id": plan.id,
        "name": plan.name,
        "area_path": ADO_PROJECT_NAME,
        "iteration": ADO_PROJECT_NAME,
        "start_date": plan.start_date,
        "end_date": plan.end_date,
        "state": "Active",
        "owner": owner,
        "test_outcome_settings": {"sync_outcome_across_suites": False},
        "project": {
            "id": plan.project_id,
            "name": ADO_PROJECT_NAME,
            "state": "unchanged",
            "visibility": "unchanged",
        },
        "root_suite": {"id": plan.root_suite_id, "name": plan.root_suite_name},
        "updated_by": _identity_minimal_snake(plan.updated_by),
        "updated_date": plan.updated_date,
    }


ado_test_plan_get_test_data = [
    pytest.param(
        Toolkit.AZURE_DEVOPS_TEST_PLAN,
        AzureDevOpsTestPlanTool.GET_TEST_PLAN,
        Seeded(
            ADO_TEST_PLAN_SEED,
            lambda seed: f"Show the Test Plan with ID {seed.id}. Provide output in json format",
        ),
        Seeded(
            ADO_TEST_PLAN_SEED,
            lambda seed: f"""
            Here is the Test Plan with ID {seed.id} in JSON format:

            ```json
            {json.dumps(_test_plan_json(seed), indent=2)}
            ```
            Let me know if you need more details or a different data format!
            """,
        ),
        marks=pytest.mark.smoke,
    ),
    (
        Toolkit.AZURE_DEVOPS_TEST_PLAN,
        AzureDevOpsTestPlanTool.GET_TEST_CASE,
        Seeded(
            ADO_TEST_PLAN_SEED,
            lambda seed: f"""
            Show the info about test case with ID {seed.test_case_id} in suite with ID {seed.suite_id} in test plan with ID {seed.id}.
            Data to show: Title, Automation Status, Priority, Description.
        """,
        ),
        Seeded(
            ADO_TEST_PLAN_SEED,
            lambda seed: f"""
            Here is the information for Test Case ID {seed.test_case_id} in Suite {seed.suite_id}, Plan {seed.id}:

            - Title: {seed.test_case_title}
            - Automation Status: {seed.test_case_automation_status}
            - Priority: {seed.test_case_priority}
            - Description: {seed.test_case_description}
        """,
        ),
    ),
    (
        Toolkit.AZURE_DEVOPS_TEST_PLAN,
        AzureDevOpsTestPlanTool.GET_TEST_CASES,
        Seeded(
            ADO_TEST_PLAN_SEED,
            lambda seed: f"""
            Show the info about all test cases in suite with ID {seed.suite_id} in test plan with ID {seed.id}.
            Data to show: Title, Automation Status, Priority, Description.
        """,
        ),
        Seeded(
            ADO_TEST_PLAN_SEED,
            lambda seed: f"""
            Here is the info about all test cases in suite ID {seed.suite_id} from test plan ID {seed.id}:

            1. Title: {seed.test_case_title}
            - Automation Status: {seed.test_case_automation_status}
            - Priority: {seed.test_case_priority}
            - Description: {seed.test_case_description}

            If you need info about more test cases or detailed fields, let me know!
        """,
        ),
    ),
    (
        Toolkit.AZURE_DEVOPS_TEST_PLAN,
        AzureDevOpsTestPlanTool.GET_TEST_SUITE,
        Seeded(
            ADO_TEST_PLAN_SEED,
            lambda seed: f"Show the info about all suites in test plan with ID {seed.id}.",
        ),
        Seeded(
            ADO_TEST_PLAN_SEED,
            lambda seed: f"""
            Here is the information about all suites in test plan with ID {seed.id}:

            1. Test Suite Name: {seed.root_suite_name}
               - Suite ID: {seed.root_suite_id}
               - Suite Type: Static Test Suite
               - Has children: Yes
               - Last Updated: {seed.updated_date}
               - Project: {ADO_PROJECT_NAME}

            2. Test Suite Name: {seed.suite_name}
               - Suite ID: {seed.suite_id}
               - Suite Type: Static Test Suite
               - Inherits default configurations
               - Parent Suite: {seed.root_suite_name} (ID: {seed.root_suite_id})
               - Project: {ADO_PROJECT_NAME}

            Both suites belong to the same project: {ADO_PROJECT_NAME}. The first suite is at the top level, and the second suite is a child of the first suite.
        """,
        ),
    ),
]

ADO_TEST_PLAN_CREATE_TEST_PLAN = {
    "prompt_to_assistant": ado_text("""
        Create a new test plan with name '{}' in '<ADO_PROJECT>' project.
        Provide short summary about result and the ID of created test plan in Json format: {{ "ID": "Number" }}
    """),
    "expected_llm_answer": ado_text("""
        The test plan named '{}' has been successfully created in the '<ADO_PROJECT>' project.
        Below is the summary of the result:

        ~~~json
        {{
          "ID": {}
        }}
        ~~~
    """),
}

ADO_TEST_PLAN_CREATE_SUITE = {
    "prompt_to_assistant": """
        Create a new test suite with random name
        use 'StaticTestSuite' type
        use parent suite ID {}
        use Test Plan ID {}.
        Provide short summary about result and the ID of created suite in Json format: {{ "ID": "Number" }}
    """,
    "expected_llm_answer": """
        The test suite was created successfully. Here is the summary and ID of the created suite:

        ```json
        {{
          "ID": {}
        }}
        ```
    """,
}

ADO_TEST_PLAN_ADD_TEST_CASE = {
    "prompt_to_assistant": """
        Add the test case with ID {test_case_id} to the test suite with ID {suite_id}. Use test plan with ID {plan_id}.
    """,
    "expected_llm_answer": "The test case with ID {test_case_id} has been successfully added to the test suite with ID {suite_id} under the test plan with ID {plan_id}.",
}

ADO_TEST_PLAN_DELETE_SUITE = {
    "prompt_to_assistant": ado_text(
        "Delete the Test Suite with ID {} under the Test Plan with ID {} in '<ADO_PROJECT>' project."
    ),
    "expected_llm_answer": ado_text("""
        The Test Suite with ID '{}' under the Test Plan with ID '{}' in the '<ADO_PROJECT>' project has been successfully deleted.
    """),
}

ADO_TEST_PLAN_DELETE_PLAN = {
    "prompt_to_assistant": ado_text(
        "Delete the Test Plan with ID {} in '<ADO_PROJECT>' project."
    ),
    "expected_llm_answer": ado_text(
        "The test plan with ID `{}` in the `<ADO_PROJECT>` project has been successfully deleted."
    ),
}
