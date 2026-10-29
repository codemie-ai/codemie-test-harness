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

from codemie_test_harness.tests.enums.tools import Toolkit, ReportPortalTool
from codemie_test_harness.tests.utils.jira_seed import Seeded
from codemie_test_harness.tests.utils.report_portal_seed import (
    REPORT_PORTAL_SEED,
    REPORT_PORTAL_SEED_DASHBOARD,
)

report_portal_tools_test_data = [
    (
        Toolkit.REPORT_PORTAL,
        ReportPortalTool.GET_LAUNCH_DETAILS,
        Seeded(REPORT_PORTAL_SEED, lambda seed: {"launch_id": str(seed.id)}),
        Seeded(
            REPORT_PORTAL_SEED,
            lambda seed: f"""
            {{
              "owner" : "{seed.owner}",
              "id" : {seed.id},
              "uuid" : "{seed.uuid}",
              "name" : "{seed.name}",
              "number" : {seed.number},
              "startTime" : "{seed.start_time}",
              "endTime" : "{seed.end_time}",
              "status" : "{seed.status}",
              "statistics" : {{
                "executions" : {{
                  "total" : {seed.total},
                  "passed" : {seed.passed},
                  "failed" : {seed.failed},
                  "skipped" : {seed.skipped}
                }}
              }},
              "attributes" : [ {{
                "key" : "seed",
                "value" : "true"
              }} ],
              "mode" : "{seed.mode}",
              "approximateDuration" : {seed.approximate_duration},
              "hasRetries" : false,
              "rerun" : false
            }}
        """,
        ),
    ),
    (
        # Report Portal keeps adding real "Pytest Regression" launches every time
        # this project reruns, so the page's total count and its older entries
        # are never stable, and the seed launch (created once, reused
        # afterwards) sinks further down the newest-first sort over time. The
        # expected text therefore does not claim a page-1 position for it --
        # only that page 1's launches include this one, which the similarity
        # grader can match regardless of where it falls in the list.
        Toolkit.REPORT_PORTAL,
        ReportPortalTool.GET_ALL_LAUNCHES,
        {"page_number": 1},
        Seeded(
            REPORT_PORTAL_SEED,
            lambda seed: f"""
            Among the launches on page 1 is:
            {{
              "owner" : "{seed.owner}",
              "id" : {seed.id},
              "name" : "{seed.name}",
              "status" : "{seed.status}",
              "statistics" : {{
                "executions" : {{
                  "total" : {seed.total},
                  "passed" : {seed.passed},
                  "failed" : {seed.failed},
                  "skipped" : {seed.skipped}
                }}
              }},
              "attributes" : [ {{
                "key" : "seed",
                "value" : "true"
              }} ]
            }}
            The page also contains other launches.
        """,
        ),
    ),
    (
        Toolkit.REPORT_PORTAL,
        ReportPortalTool.FIND_TEST_ITEM_BY_ID,
        Seeded(REPORT_PORTAL_SEED, lambda seed: {"item_id": str(seed.passed_item_id)}),
        Seeded(
            REPORT_PORTAL_SEED,
            lambda seed: f"""
            {{
              "id" : {seed.passed_item_id},
              "name" : "{seed.passed_item_name}",
              "codeRef" : "{seed.passed_item_code_ref}",
              "type" : "STEP",
              "status" : "PASSED",
              "statistics" : {{
                "executions" : {{
                  "total" : 1,
                  "passed" : 1
                }},
                "defects" : {{ }}
              }},
              "hasChildren" : false,
              "hasStats" : true,
              "launchId" : {seed.id},
              "uniqueId" : "{seed.passed_item_unique_id}",
              "path" : "{seed.passed_item_id}"
            }}
        """,
        ),
    ),
    (
        Toolkit.REPORT_PORTAL,
        ReportPortalTool.GET_TEST_ITEMS_FOR_LAUNCH,
        Seeded(
            REPORT_PORTAL_SEED,
            lambda seed: {
                "launch_id": str(seed.id),
                "page_number": 1,
                "status": "SKIPPED",
            },
        ),
        Seeded(
            REPORT_PORTAL_SEED,
            lambda seed: f"""
            {{
              "content" : [ {{
                "id" : {seed.skipped_item_id},
                "name" : "{seed.skipped_item_name}",
                "type" : "STEP",
                "status" : "SKIPPED",
                "hasChildren" : false,
                "hasStats" : true,
                "launchId" : {seed.id},
                "path" : "{seed.skipped_item_id}"
              }} ],
              "page" : {{
                "number" : 1,
                "size" : 20,
                "totalElements" : 1,
                "totalPages" : 1
              }}
            }}
        """,
        ),
    ),
    (
        Toolkit.REPORT_PORTAL,
        ReportPortalTool.GET_LOGS_FOR_TEST_ITEM,
        Seeded(
            REPORT_PORTAL_SEED,
            lambda seed: {"item_id": str(seed.passed_item_id), "page_number": 1},
        ),
        Seeded(
            REPORT_PORTAL_SEED,
            lambda seed: f"""
            {{
              "content" : [ {{
                "message" : "{seed.log_message}",
                "level" : "INFO",
                "itemId" : {seed.passed_item_id}
              }} ],
              "page" : {{
                "number" : 1,
                "size" : 20,
                "totalElements" : 1,
                "totalPages" : 1
              }}
            }}
        """,
        ),
    ),
    (
        Toolkit.REPORT_PORTAL,
        ReportPortalTool.GET_USER_INFORMATION,
        Seeded(REPORT_PORTAL_SEED, lambda seed: {"username": seed.owner}),
        Seeded(
            REPORT_PORTAL_SEED,
            # "email" and "fullName" are the real API-key owner's PII and are
            # deliberately not asserted on. "active"/"photoLoaded" aren't part
            # of the seed (they reflect live, mutable profile state), so they
            # are left out rather than pinned to a guessed literal.
            lambda seed: f"""
        {{
            "uuid": "{seed.owner_uuid}",
            "id": {seed.owner_user_id},
            "userId": "{seed.owner}",
            "accountType": "{seed.owner_account_type}",
            "userRole": "{seed.owner_role}"
        }},
        """,
        ),
    ),
    (
        Toolkit.REPORT_PORTAL,
        ReportPortalTool.GET_DASHBOARD_DATA,
        Seeded(
            REPORT_PORTAL_SEED_DASHBOARD, lambda seed: {"dashboard_id": str(seed.id)}
        ),
        Seeded(
            REPORT_PORTAL_SEED_DASHBOARD,
            lambda seed: f"""
        {{
            "description": "{seed.description}",
            "owner": "{seed.owner}",
            "id": {seed.id},
            "name": "{seed.name}",
            "widgets": [
                {{
                    "widgetName": "{seed.widget_name}",
                    "widgetId": {seed.widget_id},
                    "widgetType": "{seed.widget_type}",
                    "widgetSize": {{
                        "width": {seed.widget_width},
                        "height": {seed.widget_height}
                    }},
                    "widgetPosition": {{
                        "positionX": {seed.widget_position_x},
                        "positionY": {seed.widget_position_y}
                    }},
                    "widgetOptions": {{}}
                }}
            ]
        }},
        """,
        ),
    ),
]
