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

"""Test data for webhook and scheduler tests that move the target resource to another project."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from hamcrest import assert_that, greater_than

# Minutes ahead of "now" at which the scheduler cron fires. Creating the two
# schedulers and moving the resource must finish before that minute starts; both
# take a few seconds, so the lead covers them with a wide margin.
CRON_LEAD_MINUTES = 3

# The cron is evaluated in this timezone, and the minute is computed in it too,
# so the result does not depend on the timezone of the machine running the tests.
CRON_TIMEZONE = "UTC"

# The cron minute must still be at least this far ahead once the move is done,
# otherwise the schedulers may not be armed in time to fire.
CRON_MIN_REMAINING_SECONDS = 10

# Upper bound for the positive-control scheduler to fire (lead time plus slack).
CONTROL_FIRE_TIMEOUT = 300

# Extra window, after the control scheduler has fired, in which the scheduler on
# the moved resource must still stay silent (it shares the control's cron minute).
MOVED_SCHEDULER_GRACE_TIMEOUT = 60

# pytest-timeout limit of the scheduler tests (the global limit is 300 s). It must
# stay above the control wait plus the absence window so the wait's own
# TimeoutError fires first and reports what was being waited for.
SCHEDULER_TEST_TIMEOUT = 600

assert CONTROL_FIRE_TIMEOUT + MOVED_SCHEDULER_GRACE_TIMEOUT < SCHEDULER_TEST_TIMEOUT, (
    "Scheduler test timeout must exceed the control wait plus the absence window."
)


@dataclass(frozen=True)
class SharedCron:
    """Hourly cron shared by the moved-resource scheduler and its positive control."""

    expression: str
    fire_at: datetime
    timezone: str = CRON_TIMEZONE

    def seconds_until_fire(self) -> float:
        return (self.fire_at - datetime.now(timezone.utc)).total_seconds()


def webhook_assistant_project_mismatch_detail(assistant_id: str, project: str) -> str:
    """401 detail the webhook returns for an assistant outside the webhook project."""
    return (
        f"Assistant '{assistant_id}' does not belong to the webhook project "
        f"'{project}'."
    )


def webhook_workflow_project_mismatch_detail(workflow_id: str, project: str) -> str:
    """401 detail the webhook returns for a workflow outside the webhook project."""
    return (
        f"Workflow '{workflow_id}' does not belong to the webhook project '{project}'."
    )


def shared_cron_schedule() -> SharedCron:
    """Hourly cron that fires CRON_LEAD_MINUTES from now, in CRON_TIMEZONE (UTC).

    Call it immediately before creating the schedulers, once per test, so the
    moved-resource scheduler and its positive control share exactly one cron
    minute and as little of the lead as possible is spent before it.
    """
    fire_at = (
        datetime.now(timezone.utc) + timedelta(minutes=CRON_LEAD_MINUTES)
    ).replace(second=0, microsecond=0)
    return SharedCron(expression=f"{fire_at.minute} * * * *", fire_at=fire_at)


def assert_cron_minute_still_ahead(cron: SharedCron) -> None:
    """Fail with a clear message when setup used up the cron lead.

    Once the cron minute has passed the next fire is about an hour away, so the
    control wait would end in a bare TimeoutError that looks like a product bug.
    """
    assert_that(
        cron.seconds_until_fire(),
        greater_than(CRON_MIN_REMAINING_SECONDS),
        f"Setup overran the cron lead: cron '{cron.expression}' ({cron.timezone}) "
        f"is due at {cron.fire_at:%H:%M}, which passed before the schedulers were "
        "created and the resource moved. The next fire is about an hour away; "
        "rerun the test.",
    )
