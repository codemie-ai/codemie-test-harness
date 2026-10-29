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

from codemie_test_harness.tests.enums.tools import Toolkit, AzureDevOpsTestPlanTool
from codemie_test_harness.tests.utils.ado_names import ADO_PROJECT_NAME
from codemie_test_harness.tests.utils.ado_seed import (
    ADO_TEST_PLAN_SEED,
    SeedIdentity,
    SeedTestPlan,
)
from codemie_test_harness.tests.utils.jira_seed import Seeded


def _identity_full_snake(identity: SeedIdentity) -> dict:
    """``SeedIdentity`` as the full snake_case shape the test-plan tools use."""
    return {
        "_links": {},
        "descriptor": identity.descriptor,
        "display_name": identity.display_name,
        "url": identity.profile_url,
        "id": identity.id,
        "image_url": identity.avatar_url,
        "unique_name": identity.unique_name,
    }


def _project(seed: SeedTestPlan) -> dict:
    return {
        "id": seed.project_id,
        "last_update_time": "0001-01-01T00:00:00.000Z",
        "name": ADO_PROJECT_NAME,
        "state": "unchanged",
        "visibility": "unchanged",
    }


def _plan_json(seed: SeedTestPlan) -> str:
    return json.dumps(
        {
            "area_path": ADO_PROJECT_NAME,
            "end_date": seed.end_date,
            "iteration": ADO_PROJECT_NAME,
            "name": seed.name,
            "owner": _identity_full_snake(seed.owner),
            "start_date": seed.start_date,
            "state": "Active",
            "test_outcome_settings": {"sync_outcome_across_suites": False},
            "revision": 1,
            "id": seed.id,
            "project": _project(seed),
            "root_suite": {"id": seed.root_suite_id, "name": seed.root_suite_name},
            "updated_by": _identity_full_snake(seed.updated_by),
            "updated_date": seed.updated_date,
        },
        indent=2,
    )


def _test_case_item(seed: SeedTestPlan) -> dict:
    return {
        "links": {},
        "point_assignments": [
            {
                "configuration_id": 1,
                "configuration_name": "Windows 10",
                "tester": _identity_full_snake(seed.owner),
            }
        ],
        "project": _project(seed),
        "test_plan": {"id": seed.id, "name": seed.name},
        "test_suite": {"id": seed.suite_id, "name": seed.suite_name},
        "work_item": {
            "id": seed.test_case_id,
            "name": seed.test_case_title,
            "work_item_fields": [
                {"System.State": "Design"},
                {"System.WorkItemType": "Test Case"},
                {"Microsoft.VSTS.Common.Priority": seed.test_case_priority},
                {
                    "Microsoft.VSTS.TCM.AutomationStatus": seed.test_case_automation_status
                },
            ],
        },
    }


def _test_case_json(seed: SeedTestPlan) -> str:
    return json.dumps([_test_case_item(seed)], indent=2)


def _suites_json(seed: SeedTestPlan) -> str:
    return json.dumps(
        [
            {
                "default_configurations": [{"id": 1, "name": "Windows 10"}],
                "inherit_default_configurations": False,
                "name": seed.root_suite_name,
                "suite_type": "staticTestSuite",
                "has_children": True,
                "id": seed.root_suite_id,
                "last_updated_date": seed.updated_date,
                "plan": {"id": seed.id, "name": seed.name},
                "project": _project(seed),
            },
            {
                "inherit_default_configurations": True,
                "name": seed.suite_name,
                "parent_suite": {
                    "id": seed.root_suite_id,
                    "name": seed.root_suite_name,
                },
                "suite_type": "staticTestSuite",
                "id": seed.suite_id,
                "last_updated_date": seed.updated_date,
                "plan": {"id": seed.id, "name": seed.name},
                "project": _project(seed),
            },
        ],
        indent=2,
    )


ado_test_plan_get_test_data = [
    (
        Toolkit.AZURE_DEVOPS_TEST_PLAN,
        AzureDevOpsTestPlanTool.GET_TEST_PLAN,
        Seeded(ADO_TEST_PLAN_SEED, lambda seed: {"plan_id": seed.id}),
        Seeded(ADO_TEST_PLAN_SEED, _plan_json),
    ),
    (
        Toolkit.AZURE_DEVOPS_TEST_PLAN,
        AzureDevOpsTestPlanTool.GET_TEST_CASE,
        Seeded(
            ADO_TEST_PLAN_SEED,
            lambda seed: {
                "plan_id": seed.id,
                "suite_id": seed.suite_id,
                "test_case_id": str(seed.test_case_id),
            },
        ),
        Seeded(
            ADO_TEST_PLAN_SEED,
            lambda seed: json.dumps(_test_case_item(seed), indent=2),
        ),
    ),
    (
        Toolkit.AZURE_DEVOPS_TEST_PLAN,
        AzureDevOpsTestPlanTool.GET_TEST_CASES,
        Seeded(
            ADO_TEST_PLAN_SEED,
            lambda seed: {"plan_id": seed.id, "suite_id": seed.suite_id},
        ),
        Seeded(ADO_TEST_PLAN_SEED, _test_case_json),
    ),
    (
        Toolkit.AZURE_DEVOPS_TEST_PLAN,
        AzureDevOpsTestPlanTool.GET_TEST_SUITE,
        Seeded(ADO_TEST_PLAN_SEED, lambda seed: {"plan_id": seed.id}),
        Seeded(ADO_TEST_PLAN_SEED, _suites_json),
    ),
]
