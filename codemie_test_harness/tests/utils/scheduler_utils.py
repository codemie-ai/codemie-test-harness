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

"""Helpers for reading CodeMie schedulers through the SDK."""

from typing import Optional

from codemie_sdk.models.scheduler import SchedulerListItem

from codemie_test_harness.tests.utils.base_utils import BaseUtils

# Largest page the scheduler list accepts.
SCHEDULER_PAGE_SIZE = 100


class SchedulerUtils(BaseUtils):
    def find_scheduler(self, scheduler_id: str) -> Optional[SchedulerListItem]:
        """Return the row with this id from the caller's scheduler list, or None.

        Reads every page of ``GET /v1/schedulers``, so the row is found on a stand
        that holds more schedulers than one page.
        """
        page = 0
        while True:
            listed = self.client.schedulers.list(
                page=page, per_page=SCHEDULER_PAGE_SIZE
            )
            match = next(
                (item for item in listed.items if item.id == scheduler_id), None
            )
            if match is not None or page + 1 >= listed.pagination.pages:
                return match
            page += 1
