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

"""Seed data for InfluxDB data-management tool tests: a persistent point with known values.

Pure logic only (no HTTP); InfluxDBUtils performs the requests. The point is written
fresh into a fixed ``codemie_harness_seed`` measurement on every run instead of being
hand-seeded once into a sandbox-only instance, so the fixture is self-healing across
sandbox resets and InfluxDB retention-policy expiry: there is always a point younger
than the retention window for the tests to query.
"""

from dataclasses import asdict, dataclass

INFLUXDB_SEED = "influxdb_seed_point"

SEED_MEASUREMENT = "codemie_harness_seed"
SEED_HOST = "codemie-test-harness"
SEED_REGION = "us-east-1"
SEED_CPU_LOAD = 42.0
# Query window used both to verify the write and in the query task/response the
# query tests send to the tool. Wider than the test session is ever expected to
# run, so a session that starts well before the InfluxDB tests execute never
# loses its own point off the end of the window.
SEED_QUERY_RANGE = "-24h"


@dataclass(frozen=True)
class InfluxDBSeedPoint:
    bucket: str
    # RFC3339 timestamp the point was written with.
    time: str
    # Unique per test session; written as a tag on the point and matched on
    # by every query, so a concurrent or rerun session's own point (same
    # measurement/host, written within the same range window) is never
    # mistaken for this one.
    run_id: str
    measurement: str = SEED_MEASUREMENT
    host: str = SEED_HOST
    region: str = SEED_REGION
    cpu_load: float = SEED_CPU_LOAD

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "InfluxDBSeedPoint":
        return cls(**data)
