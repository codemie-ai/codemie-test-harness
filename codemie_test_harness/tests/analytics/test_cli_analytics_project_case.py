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

"""Plan TC-008: a project written in another letter case is
stored under the stored project name.

The ingest gate matches the project of `X-CodeMie-Project` and of the events case-insensitively, so a
batch naming the upper-case spelling is accepted for the existing project. It must then be stored,
and shown, under the stored name: the project filter and the project admin find the session, and
a filter of the spelling that was sent (a project that does not exist) does not. Runnable on its
own:

    pytest codemie_test_harness/tests/analytics/test_cli_analytics_project_case.py

Evidence limits: positive waits only (poll_until), no absence window; the filter by the sent
spelling is a check on what the read API returns, not proof of what is stored. Hook events over
NDJSON only: the same canonicalisation for hook events delivered as OTLP logs is covered by the
backend unit tests.
"""

import pytest
from hamcrest import assert_that, empty, equal_to, has_item, is_not

from codemie_test_harness.tests.test_data.cli_analytics_test_data import E7
from codemie_test_harness.tests.utils.cli_analytics_api_utils import (
    CliAnalyticsApi,
    assert_accepted,
)
from codemie_test_harness.tests.utils.cli_gate_utils import (
    listed_session_ids,
    make_batch,
    post_batch,
    wait_until_listed,
)

pytestmark = [
    pytest.mark.api,
    pytest.mark.cli_analytics,
]


def test_project_written_in_another_case_is_stored_under_the_stored_project(
    project_world,
):
    """TC-008 (AC-8, AC-6): header and events name the project in upper case; the batch is
    accepted and the session is returned for the stored project name, to its project admin and
    by the project filter, and for no filter of the spelling that was sent."""
    project = project_world.project
    sent_as = project.upper()
    admin = CliAnalyticsApi(project_world.clients["admin"])
    project_admin = CliAnalyticsApi(project_world.clients["project_admin"])
    assert_that(
        sent_as != project,
        equal_to(True),
        f"the project name {project!r} must be lower case for this check",
    )

    batch = make_batch(E7, names=[sent_as])
    response = post_batch(project_world.clients["member"], E7, batch, sent_as)
    assert_accepted(response, E7.signal, E7.ct)
    pending = wait_until_listed(admin, {batch.session_id: batch.repo})
    assert_that(pending, empty(), "the accepted hook session was never listed")

    assert_that(
        listed_session_ids(admin, batch.repo, project),
        has_item(batch.session_id),
        f"not returned by the filter of the stored project {project!r}",
    )
    assert_that(
        listed_session_ids(admin, batch.repo, sent_as),
        is_not(has_item(batch.session_id)),
        f"stored under {sent_as!r}, a project that does not exist, not under {project!r}",
    )
    assert_that(
        listed_session_ids(project_admin, batch.repo),
        has_item(batch.session_id),
        "the project admin does not see the accepted session",
    )
    assert_that(
        listed_session_ids(project_admin, batch.repo, project),
        has_item(batch.session_id),
        "the project admin does not see it with the stored project filter",
    )
    assert_that(
        listed_session_ids(project_admin, batch.repo, sent_as),
        is_not(has_item(batch.session_id)),
        f"the project admin sees it under the spelling {sent_as!r}",
    )
