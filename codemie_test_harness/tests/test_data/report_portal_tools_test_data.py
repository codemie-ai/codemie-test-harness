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

from codemie_test_harness.tests.enums.tools import Toolkit, ReportPortalTool
from codemie_test_harness.tests.utils.jira_seed import Seeded
from codemie_test_harness.tests.utils.report_portal_seed import (
    REPORT_PORTAL_SEED,
    REPORT_PORTAL_SEED_DASHBOARD,
)

rp_test_data = [
    (
        Toolkit.REPORT_PORTAL,
        ReportPortalTool.GET_EXTENDED_LAUNCH_DATA_AS_RAW,
        Seeded(
            REPORT_PORTAL_SEED,
            lambda seed: (
                f"Get details for the launch with ID {seed.id} in a raw HTML "
                "format. If content exceeds the token limit for display show "
                "truncated version"
            ),
        ),
        Seeded(
            REPORT_PORTAL_SEED,
            lambda seed: f"""
            The details for launch ID {seed.id} in raw HTML format were retrieved successfully.
            The HTML output's summary table shows:

            - Launch name: {seed.name}
            - Owner: {seed.owner}
            - Duration: approximately {seed.duration_seconds} seconds
            - Total tests: {seed.total}
            - Passed: {seed.passed}
            - Failed: {seed.failed}
            - Skipped: {seed.skipped}
        """,
        ),
    ),
    (
        Toolkit.REPORT_PORTAL,
        ReportPortalTool.GET_LAUNCH_DETAILS,
        Seeded(
            REPORT_PORTAL_SEED,
            lambda seed: f"Get details about launch with ID {seed.id}",
        ),
        Seeded(
            REPORT_PORTAL_SEED,
            lambda seed: f"""
            Here are the details for launch ID {seed.id}:

            - Name: {seed.name}
            - Owner: {seed.owner}
            - Launch Number: {seed.number}
            - Status: {seed.status}
            - Mode: {seed.mode}
            - Total Executions: {seed.total}
                - Passed: {seed.passed}
                - Failed: {seed.failed}
                - Skipped: {seed.skipped}
            - Approximate Duration: about {seed.duration_seconds} seconds

            If you need a breakdown of the skipped tests or a root cause analysis, let me know!
        """,
        ),
    ),
    (
        Toolkit.REPORT_PORTAL,
        ReportPortalTool.GET_ALL_LAUNCHES,
        "Get all launches with the attribute seed:true and return the number of launches found",
        Seeded(
            REPORT_PORTAL_SEED,
            lambda seed: (
                f"There is a total of {seed.attribute_launch_count} launch found "
                "with the attribute set to 'seed:true'."
            ),
        ),
    ),
    (
        Toolkit.REPORT_PORTAL,
        ReportPortalTool.FIND_TEST_ITEM_BY_ID,
        Seeded(
            REPORT_PORTAL_SEED,
            lambda seed: f"Get test item by ID {seed.passed_item_id}",
        ),
        Seeded(
            REPORT_PORTAL_SEED,
            lambda seed: f"""
            Here are the details for test item ID {seed.passed_item_id}:

            - Name: {seed.passed_item_name}
            - Code Reference: {seed.passed_item_code_ref}
            - Status: PASSED (executed 1 time, 1 passed)
            - Type: STEP (individual test step)
            - Launch ID: {seed.id}
            - Unique ID: {seed.passed_item_unique_id}

            If you need historical performance, flaky test analysis, or suggestions for improvements, let me know!
        """,
        ),
    ),
    (
        Toolkit.REPORT_PORTAL,
        ReportPortalTool.GET_TEST_ITEMS_FOR_LAUNCH,
        Seeded(
            REPORT_PORTAL_SEED, lambda seed: f"Get test items for launch ID {seed.id}"
        ),
        Seeded(
            REPORT_PORTAL_SEED,
            lambda seed: f"""
            Here are the test items for launch ID {seed.id}. This launch has {seed.total} test items in total:

            1. **{seed.passed_item_name}** — PASSED
            2. **{seed.failed_item_name}** — FAILED
            3. **{seed.skipped_item_name}** — SKIPPED
        """,
        ),
    ),
    (
        Toolkit.REPORT_PORTAL,
        ReportPortalTool.GET_LOGS_FOR_TEST_ITEM,
        Seeded(
            REPORT_PORTAL_SEED,
            lambda seed: f"Get the logs for test item ID {seed.passed_item_id}",
        ),
        Seeded(
            REPORT_PORTAL_SEED,
            lambda seed: f"""
            Here is the log for test item ID {seed.passed_item_id} (1 entry):

            1. INFO — {seed.log_message}
        """,
        ),
    ),
    (
        Toolkit.REPORT_PORTAL,
        ReportPortalTool.GET_USER_INFORMATION,
        Seeded(
            REPORT_PORTAL_SEED,
            lambda seed: f"Get user information from reportal with username {seed.owner}",
        ),
        Seeded(
            REPORT_PORTAL_SEED,
            # Full name and email are the real API-key owner's PII; only
            # non-personal identifying fields are asserted on.
            lambda seed: f"""
        User Information for username {seed.owner}
        Personal Details
        Username: {seed.owner}
        User ID: {seed.owner_user_id}
        Account Type: {seed.owner_account_type}
        Role: {seed.owner_role}
        """,
        ),
    ),
    pytest.param(
        Toolkit.REPORT_PORTAL,
        ReportPortalTool.GET_DASHBOARD_DATA,
        Seeded(
            REPORT_PORTAL_SEED_DASHBOARD,
            lambda seed: f"Get dashboard data from report portal where ID = {seed.id}",
        ),
        Seeded(
            REPORT_PORTAL_SEED_DASHBOARD,
            lambda seed: f"""
        Dashboard Details: {seed.name}
        I was able to retrieve the dashboard data for ID {seed.id}:
        Dashboard Information
        ID: {seed.id}
        Name: {seed.name}
        Owner: {seed.owner}
        Description: {seed.description}
        Dashboard Content
        This dashboard contains 1 widget: "{seed.widget_name}", a {seed.widget_type} widget sized {seed.widget_width}x{seed.widget_height} positioned at ({seed.widget_position_x}, {seed.widget_position_y}).
        """,
        ),
        marks=pytest.mark.smoke,
    ),
]
