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

from datetime import datetime, timedelta

# Minutes ahead of "now" at which the scheduler cron fires. Setup (creating the
# schedulers and moving the resources) must finish before that minute starts.
CRON_LEAD_MINUTES = 3

# Upper bound for the positive-control scheduler to fire (lead time plus slack).
CONTROL_FIRE_TIMEOUT = 300

# Extra window, after the control scheduler has fired, in which the scheduler on
# the moved resource must still stay silent (it shares the control's cron minute).
MOVED_SCHEDULER_GRACE_TIMEOUT = 60


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


def shared_cron_schedule() -> str:
    """Hourly cron that fires CRON_LEAD_MINUTES from now.

    Computed once per test so the moved-resource scheduler and its positive
    control share exactly one cron minute.
    """
    fire_minute = (datetime.now() + timedelta(minutes=CRON_LEAD_MINUTES)).minute
    return f"{fire_minute} * * * *"
