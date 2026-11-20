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

from dataclasses import dataclass
from typing import Callable, List, Optional

from requests import HTTPError

from codemie_sdk.models.activity_event import (
    ActivityEventFilterOptions,
    ActivityEventListItem,
    ActivityEventProjectMetadata,
    PaginatedActivityEventResponse,
    ProjectActivityEventsResponse,
)
from codemie_test_harness.tests.utils.base_utils import BaseUtils


# Largest page the project trail serves; one request returns a small test project's whole trail.
MAX_TRAIL_PAGE = 1000


@dataclass(frozen=True)
class ApiDenial:
    """Outcome of a request that is expected to fail: status, error message and raw body.

    ``status_code`` is 200 and ``message`` None when the request succeeded.
    """

    status_code: int
    message: Optional[str]
    body: str


def _error_message(response) -> Optional[str]:
    try:
        return response.json()["error"]["message"]
    except (ValueError, KeyError, TypeError):
        return None


def _denial(call: Callable[[], object]) -> ApiDenial:
    try:
        call()
    except HTTPError as e:
        return ApiDenial(
            e.response.status_code, _error_message(e.response), e.response.text
        )
    return ApiDenial(200, None, "")


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

    def list_budget_deleted_events(self, budget_id: str) -> list:
        """The ``budget.deleted`` activity events recorded for a budget id."""
        return self.list_activity_events(
            entity_id=budget_id,
            event_type=["budget.deleted"],
            domain=["budget_management"],
        ).data

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

    def list_project_events(
        self,
        project_instance_id: str,
        *,
        actor_id: Optional[str] = None,
        domain: Optional[List[str]] = None,
        event_type: Optional[List[str]] = None,
        category: Optional[List[str]] = None,
        from_dt: Optional[str] = None,
        to_dt: Optional[str] = None,
        sort_dir: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> ProjectActivityEventsResponse:
        """One page of a project's activity trail (GET /v1/projects/{id}/activity-events)."""
        return self.client.activity_events.list_project_events(
            project_instance_id,
            actor_id=actor_id,
            domain=domain,
            event_type=event_type,
            category=category,
            from_dt=from_dt,
            to_dt=to_dt,
            sort_dir=sort_dir,
            limit=limit,
            offset=offset,
        )

    def list_all_project_events(
        self, project_instance_id: str, **filters
    ) -> List[ActivityEventListItem]:
        """Every matching event of a project's trail in one request, newest first by default."""
        return self.list_project_events(
            project_instance_id, limit=MAX_TRAIL_PAGE, **filters
        ).data

    def page_project_events(
        self, project_instance_id: str, page_size: int, sort_dir: str
    ) -> List[List[ActivityEventListItem]]:
        """Walk the trail page by page with limit/offset; returns the pages in request order."""
        pages = []
        offset = 0
        total = None
        while total is None or offset < total:
            response = self.list_project_events(
                project_instance_id,
                limit=page_size,
                offset=offset,
                sort_dir=sort_dir,
            )
            total = response.pagination.total
            pages.append(response.data)
            offset += page_size
        return pages

    def get_project_event_metadata(
        self, project_instance_id: str
    ) -> ActivityEventProjectMetadata:
        """Event types, domains and categories present in a project's trail."""
        return self.client.activity_events.get_project_event_metadata(
            project_instance_id
        )

    def project_events_denial(self, project_instance_id: str, **filters) -> ApiDenial:
        """Status and error of a trail request, without raising on 4xx."""
        return _denial(lambda: self.list_project_events(project_instance_id, **filters))

    def project_event_metadata_denial(self, project_instance_id: str) -> ApiDenial:
        """Status and error of a metadata request, without raising on 4xx."""
        return _denial(lambda: self.get_project_event_metadata(project_instance_id))
