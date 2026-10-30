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

"""Utility class for Usage Attribution analytics operations."""

from datetime import datetime, timedelta, timezone
from typing import Any

from codemie_sdk.models.usage_attribution import (
    UsageAttributionQueryParams,
    UsageAttributionResponse,
    UsageAttributionSettingsResponse,
    UsageAttributionTableResponse,
)

from codemie_test_harness.tests.test_data.usage_attribution_test_data import (
    CATEGORIES,
    PERIOD_LAST_30_DAYS,
    USAGE_ATTRIBUTION_FEATURE_ID,
    ListCase,
    RangeCase,
)
from codemie_test_harness.tests.utils.base_utils import BaseUtils, poll_until

ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
# A cold analysis can take up to the server's two-minute computation limit.
ANALYSIS_TIMEOUT = 180
ANALYSIS_POLL_INTERVAL = 10


def parse_utc(value: str) -> datetime:
    """Parse a timestamp the API returns (``YYYY-MM-DDTHH:MM:SSZ``)."""
    return datetime.strptime(value, ISO_FORMAT).replace(tzinfo=timezone.utc)


def period_params(
    time_period: str = PERIOD_LAST_30_DAYS,
) -> UsageAttributionQueryParams:
    """Query parameters that select a named period."""
    return UsageAttributionQueryParams(time_period=time_period)


def custom_range_params(days: int) -> UsageAttributionQueryParams:
    """Query parameters for a custom range of ``days`` days ending now, on a 15-minute boundary.

    The API rounds the ends down to 15 minutes, so aligned ends reach it unchanged and the
    requested length is exact.
    """
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    end = now - timedelta(minutes=now.minute % 15)
    start = end - timedelta(days=days)
    return UsageAttributionQueryParams(
        start_date=start.strftime(ISO_FORMAT), end_date=end.strftime(ISO_FORMAT)
    )


def range_params(case: RangeCase) -> UsageAttributionQueryParams:
    """Query parameters for a ``RangeCase``."""
    if case.days is not None:
        return custom_range_params(case.days)
    return period_params(case.time_period)


def category_row(summary: UsageAttributionResponse, category: str) -> dict[str, Any]:
    """The row of ``category`` in the CLI categories of a CLI summary (rows come in the order of CATEGORIES)."""
    return summary.data["categories"][CATEGORIES.index(category)]


class UsageAttributionUtils(BaseUtils):
    """Reads of the Usage Attribution analytics through the SDK client."""

    def get_public_component(self) -> dict | None:
        """The feature's entry in the public configuration (``GET /v1/config``), or None when absent."""
        return next(
            (
                c
                for c in self.client.customer_config.get_config()
                if c.get("id") == USAGE_ATTRIBUTION_FEATURE_ID
            ),
            None,
        )

    def get_totals(
        self, params: UsageAttributionQueryParams | None = None
    ) -> UsageAttributionResponse:
        return self.client.usage_attribution.get_totals(params)

    def get_status(
        self, params: UsageAttributionQueryParams | None = None
    ) -> UsageAttributionResponse:
        return self.client.usage_attribution.get_status(params)

    def get_cli_summary(
        self, params: UsageAttributionQueryParams | None = None
    ) -> UsageAttributionResponse:
        return self.client.usage_attribution.get_cli_summary(params)

    def get_settings(self) -> UsageAttributionSettingsResponse:
        return self.client.usage_attribution.get_settings()

    def get_settled_cli_summary(
        self, params: UsageAttributionQueryParams | None = None
    ) -> UsageAttributionResponse:
        """A CLI summary served from a finished analysis.

        A stale analysis is shown while a newer one is computed; wait until the newer one is
        served, so the answer says what the cache holds for the period.
        """
        return poll_until(
            lambda: self.get_cli_summary(params),
            lambda response: not response.analysis.stale
            and not response.analysis.refreshing,
            timeout=ANALYSIS_TIMEOUT,
            interval=ANALYSIS_POLL_INTERVAL,
        )

    def get_breakdown(
        self,
        dimension: str,
        category: str,
        params: UsageAttributionQueryParams | None = None,
    ) -> UsageAttributionResponse:
        return self.client.usage_attribution.get_breakdown(
            params, dimension=dimension, category=category
        )

    def list_page(
        self,
        case: ListCase,
        params: UsageAttributionQueryParams | None = None,
        **query: Any,
    ) -> UsageAttributionTableResponse:
        """One page of the list of ``case``; ``query`` holds its scope or filter, search and paging."""
        return getattr(self.client.usage_attribution, case.list_method)(params, **query)

    def open_detail(
        self,
        case: ListCase,
        row: dict[str, Any],
        params: UsageAttributionQueryParams | None = None,
    ) -> UsageAttributionResponse:
        """The popup of a listed ``row``."""
        return getattr(self.client.usage_attribution, case.detail_method)(
            row[case.id_field], params
        )
