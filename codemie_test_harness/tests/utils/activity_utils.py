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

"""SDK wrapper around the maintainer-only activity events client."""

from typing import List, Optional

from requests import HTTPError

from codemie_sdk.models.activity_event import (
    ActivityEventFilterOptions,
    PaginatedActivityEventResponse,
)
from codemie_test_harness.tests.utils.base_utils import BaseUtils


class ActivityUtils(BaseUtils):
    """Thin wrapper around client.activity_events for test use.

    All methods delegate to client.activity_events (ActivityEventService).
    The wrapped client must have maintainer privileges; non-maintainer callers
    will receive HTTP 403 — use *_status_code helpers for access-control tests.
    """

    def list_activity_events(
        self,
        *,
        actor_id: Optional[str] = None,
        domain: Optional[List[str]] = None,
        event_type: Optional[List[str]] = None,
        entity_type: Optional[List[str]] = None,
        entity_id: Optional[str] = None,
        from_dt: Optional[str] = None,
        to_dt: Optional[str] = None,
        sort_dir: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> PaginatedActivityEventResponse:
        """List activity events through the SDK service."""
        return self.client.activity_events.list_events(
            actor_id=actor_id,
            domain=domain,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            from_dt=from_dt,
            to_dt=to_dt,
            sort_dir=sort_dir,
            limit=limit,
            offset=offset,
        )

    def get_filter_options(self) -> ActivityEventFilterOptions:
        """Return available filter options for the activity events endpoint."""
        return self.client.activity_events.get_filter_options()

    def list_events_status_code(self, **kwargs) -> int:
        """Return the HTTP status code for a list_activity_events call.

        Useful for access-control assertions without raising on 4xx.
        """
        try:
            self.list_activity_events(**kwargs)
            return 200
        except HTTPError as e:
            return e.response.status_code

    def get_filter_options_status_code(self) -> int:
        """Return the HTTP status code for a get_filter_options call."""
        try:
            self.get_filter_options()
            return 200
        except HTTPError as e:
            return e.response.status_code
