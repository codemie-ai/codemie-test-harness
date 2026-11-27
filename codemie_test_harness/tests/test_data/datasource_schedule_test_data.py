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

"""Test data for datasource schedule tests."""

from dataclasses import dataclass

# Both crons fire once a year (midnight on 1 and 2 January), so neither schedule
# starts a reindex while a test runs.
INITIAL_CRON = "0 0 1 1 *"
EDITED_CRON = "0 0 2 1 *"
SCHEDULE_TIMEZONE = "UTC"


@dataclass
class DatasourceSchedule:
    """The cron a datasource is created with and the cron another member edits it to."""

    initial_cron: str
    edited_cron: str
    timezone: str


def datasource_schedule_edit() -> DatasourceSchedule:
    return DatasourceSchedule(
        initial_cron=INITIAL_CRON,
        edited_cron=EDITED_CRON,
        timezone=SCHEDULE_TIMEZONE,
    )
