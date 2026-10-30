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

"""Test data for the marketplace active-usage thresholds customer config
(``marketplaceThresholds`` declaration)."""

import random
from dataclasses import dataclass, field

import pytest

MARKETPLACE_THRESHOLDS_COMPONENT_ID = "marketplaceThresholds"

# Dynamic-config key backing the override row: ``build_key`` upper-snake-cases the
# camelCase component id and prefixes it with ``CUSTOMER_CONFIG__``.
MARKETPLACE_THRESHOLDS_DYNAMIC_CONFIG_KEY = "CUSTOMER_CONFIG__MARKETPLACE_THRESHOLDS"

THRESHOLD_FIELD_NAMES = {
    "hotMinUsers",
    "warmMinUsers",
    "coldMinUsers",
    "graceDays",
    "archiveDeadAfterDays",
}

# Deployment defaults the declaration resolves to when no override row exists.
DEFAULT_THRESHOLDS = {
    "hotMinUsers": "50",
    "warmMinUsers": "7",
    "coldMinUsers": "3",
    "graceDays": "60",
    "archiveDeadAfterDays": "30",
}

# Backend message for a value that fails the positive-integer pattern.
POSITIVE_INTEGER_MESSAGE = "Must be a positive integer"


def _random_threshold(low: int, high: int) -> str:
    return str(random.randint(low, high))


@dataclass
class MarketplaceThresholdsData:
    """All five threshold fields as strings, the wire type of the declaration.

    The defaults are random per instance so every run saves a payload no earlier
    run (or earlier test) stored; activity-log assertions can then only be
    satisfied by an event this run produced. The ranges keep every field
    different from the deployment default (hot 50, warm 7, cold 3, grace 60,
    archive 30) and cold below warm below hot.
    """

    hotMinUsers: str = field(default_factory=lambda: _random_threshold(1000, 9999))
    warmMinUsers: str = field(default_factory=lambda: _random_threshold(100, 999))
    coldMinUsers: str = field(default_factory=lambda: _random_threshold(8, 99))
    graceDays: str = field(default_factory=lambda: _random_threshold(61, 9999))
    archiveDeadAfterDays: str = field(
        default_factory=lambda: _random_threshold(31, 9999)
    )

    @property
    def as_settings(self) -> dict:
        """Return settings dict for PUT /v1/config/declarations/{id} body."""
        return {
            "hotMinUsers": self.hotMinUsers,
            "warmMinUsers": self.warmMinUsers,
            "coldMinUsers": self.coldMinUsers,
            "graceDays": self.graceDays,
            "archiveDeadAfterDays": self.archiveDeadAfterDays,
        }


def get_marketplace_thresholds_data(**overrides: str) -> MarketplaceThresholdsData:
    """Build a non-default, valid thresholds payload unique to this call.

    Args:
        overrides: Field values replacing the non-default ones, e.g.
            ``graceDays="400"``.

    Returns:
        :class:`MarketplaceThresholdsData` ready for use in tests.
    """
    return MarketplaceThresholdsData(**overrides)


# (field, value) rows rejected with 400: the pattern is ^[1-9][0-9]*$, so
# non-numeric, negative and zero values fail.
REJECTED_THRESHOLD_VALUES = [
    pytest.param("coldMinUsers", "abc", id="coldMinUsers-non-numeric"),
    pytest.param("coldMinUsers", "0", id="coldMinUsers-zero"),
    pytest.param("graceDays", "abc", id="graceDays-non-numeric"),
    pytest.param("graceDays", "-5", id="graceDays-negative"),
    pytest.param("archiveDeadAfterDays", "0", id="archiveDeadAfterDays-zero"),
]

# (field, value) rows accepted with 200: the pattern has no upper bound, so a
# value above 365 days is valid.
ACCEPTED_THRESHOLD_VALUES = [
    pytest.param("archiveDeadAfterDays", "400", id="archiveDeadAfterDays-above-365"),
]

# (payload mutation, expected message fragment) rows rejected with 400.
MALFORMED_PAYLOADS = [
    pytest.param(
        {"remove": "archiveDeadAfterDays"},
        "Missing configuration field",
        id="missing-field",
    ),
    pytest.param(
        {"add": {"unknownField": "1"}},
        "Unknown configuration fields",
        id="undeclared-field",
    ),
]


def build_malformed_payload(base: dict, mutation: dict) -> dict:
    """Return a copy of ``base`` with one field removed and/or one field added.

    Args:
        base: Valid settings payload.
        mutation: ``{"remove": <field>}`` and/or ``{"add": {<field>: <value>}}``.
    """
    payload = {k: v for k, v in base.items() if k != mutation.get("remove")}
    payload.update(mutation.get("add", {}))
    return payload
