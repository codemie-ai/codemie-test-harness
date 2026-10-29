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

import logging
import uuid
from datetime import datetime, timezone

import requests

from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.influxdb_seed import (
    SEED_CPU_LOAD,
    SEED_HOST,
    SEED_MEASUREMENT,
    SEED_QUERY_RANGE,
    SEED_REGION,
    InfluxDBSeedPoint,
)

logger = logging.getLogger(__name__)

WRITE_PATH = "/api/v2/write"
QUERY_PATH = "/api/v2/query"


class InfluxDBUtils:
    """Utility class for writing to and querying the InfluxDB v2 HTTP API."""

    def __init__(self):
        url = CredentialsManager.get_parameter("SANDBOX_INFLUX_URL").rstrip("/")
        port = CredentialsManager.get_parameter("SANDBOX_INFLUX_PORT")
        self.url = f"{url}:{port}" if port else url
        self.org = CredentialsManager.get_parameter("SANDBOX_INFLUX_ORG_NAME")
        self.bucket = CredentialsManager.get_parameter("SANDBOX_INFLUX_BUCKET")
        self.auth_header = {
            "Authorization": f"Token {CredentialsManager.get_parameter('SANDBOX_INFLUX_TOKEN')}"
        }

    def _write_seed_point(self, run_id: str, timestamp_ns: int) -> None:
        line = (
            f"{SEED_MEASUREMENT},hostname={SEED_HOST},region={SEED_REGION},run_id={run_id} "
            f"cpu_load={SEED_CPU_LOAD} {timestamp_ns}"
        )
        response = requests.post(
            f"{self.url}{WRITE_PATH}",
            params={"org": self.org, "bucket": self.bucket, "precision": "ns"},
            headers=self.auth_header,
            data=line.encode("utf-8"),
            timeout=60,
        )
        response.raise_for_status()

    def _query_seed_point(self, run_id: str) -> str:
        flux = (
            f'from(bucket: "{self.bucket}") '
            f"|> range(start: {SEED_QUERY_RANGE}) "
            f'|> filter(fn: (r) => r._measurement == "{SEED_MEASUREMENT}" '
            f'and r.hostname == "{SEED_HOST}" and r.run_id == "{run_id}")'
        )
        response = requests.post(
            f"{self.url}{QUERY_PATH}",
            params={"org": self.org},
            headers={
                **self.auth_header,
                "Content-Type": "application/vnd.flux",
                "Accept": "application/csv",
            },
            data=flux.encode("utf-8"),
            timeout=60,
        )
        response.raise_for_status()
        return response.text

    def ensure_seed(self) -> InfluxDBSeedPoint:
        """Write a fresh seed point and confirm the query API returns it.

        Writing on every call instead of upserting a single fixed point keeps the
        point's timestamp inside the bucket's retention window, so the fixture never
        goes stale from a retention-policy expiry or a sandbox reset. The point is
        tagged with a run-unique ``run_id`` so a concurrent or rerun session's own
        point for the same measurement/host is never mistaken for this one.
        """
        run_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        # Built from integer seconds/microseconds rather than
        # ``now.timestamp() * 1_000_000_000``: at today's epoch magnitude that
        # float multiplication silently loses sub-microsecond precision.
        timestamp_ns = int(now.timestamp()) * 1_000_000_000 + now.microsecond * 1_000
        self._write_seed_point(run_id, timestamp_ns)

        csv = self._query_seed_point(run_id)
        if SEED_MEASUREMENT not in csv or SEED_HOST not in csv:
            raise RuntimeError(
                f"InfluxDB seed point was written but the follow-up query did not "
                f"return it: {csv!r}"
            )

        logger.info(
            f"Ensured InfluxDB seed point in measurement {SEED_MEASUREMENT} "
            f"(bucket {self.bucket}, run_id {run_id})"
        )
        # RFC3339 with a 9-digit nanosecond fraction and a "Z" suffix, matching
        # the format InfluxDB itself returns for a nanosecond-precision point --
        # not Python's isoformat(), which uses 6-digit microseconds and a
        # "+00:00" offset and would not match the tool's actual output.
        rfc3339_time = (
            now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond * 1_000:09d}Z"
        )
        return InfluxDBSeedPoint(bucket=self.bucket, time=rfc3339_time, run_id=run_id)
