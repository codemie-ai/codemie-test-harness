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

"""Test data for the marketplace admin approval gate (review queue) tests."""

from dataclasses import dataclass, field
from typing import List, Optional

import pytest

from codemie_test_harness.tests.test_data.marketplace_test_data import (
    COMPLETE_CATEGORIES,
    COMPLETE_DESCRIPTION,
    COMPLETE_SYSTEM_PROMPT,
    GOOD_CONVERSATION_STARTERS,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name

# Marketplace review states of an assistant, as the backend reports them.
DRAFT = "DRAFT"
PENDING_REVIEW = "PENDING_REVIEW"
APPROVED = "APPROVED"
REJECTED = "REJECTED"
WITHDRAWN = "WITHDRAWN"

# Reject reasons and force-publish override notices share one bound: 20-2000
# characters after trimming surrounding whitespace. It is separate from the core
# gates below.
REASON_MIN_LENGTH = 20
REASON_MAX_LENGTH = 2000

# Value the `marketplace_core_gates` fixture sets for description_min,
# system_prompt_min and substance_prompt_alt_min on every stand except production.
# Production thresholds are left as they are, so the data below is always built from
# the thresholds the stand actually reports (`CoreGates`), never from this constant.
CORE_GATE_MINIMUM = 10

# A description below the description_min gate makes the live gate recompute report a
# CRITICAL "description_length" finding. The assistant edit endpoint puts no lower
# bound on the description, so the edit is accepted.
DESCRIPTION_LENGTH_RULE = "description_length"
CRITICAL = "CRITICAL"

_SHORT_DESCRIPTION_BASE = "Too short to pass the gate. "
_DESCRIPTION_FILLER = " It answers everyday questions in a clear and friendly way."
_SYSTEM_PROMPT_FILLER = (
    " Always answer politely, stay on topic and say so when you do not know."
)

# Notice the backend records when an admin publishes straight to the marketplace.
ADMIN_SKIP_QUEUE_NOTICE = (
    "Published directly by an administrator or maintainer; "
    "administrators and maintainers skip the moderation queue."
)


@dataclass
class MarketplaceSubmission:
    """Content of an assistant that passes every deterministic publish gate."""

    name: str
    description: str
    system_prompt: str
    categories: List[str] = field(default_factory=list)
    conversation_starters: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class CoreGates:
    """The core gate thresholds of the stand the tests run against."""

    description_min: int
    system_prompt_min: int
    substance_prompt_alt_min: int

    @classmethod
    def from_config(cls, gates: dict) -> "CoreGates":
        return cls(
            description_min=gates["description_min"],
            system_prompt_min=gates["system_prompt_min"],
            substance_prompt_alt_min=gates["substance_prompt_alt_min"],
        )


def _extend_to(text: str, length: int, filler: str) -> str:
    """``text``, with ``filler`` appended until it has at least ``length`` characters."""
    while len(text) < length:
        text += filler
    return text


def build_marketplace_submission(
    gates: CoreGates,
    name: Optional[str] = None,
    categories: Optional[List[str]] = None,
) -> MarketplaceSubmission:
    """A submission with a unique name and content that clears the stand's core gates.

    The description reaches ``description_min`` and the system prompt reaches both
    ``system_prompt_min`` and ``substance_prompt_alt_min``, whatever their values.
    """
    prompt_minimum = max(gates.system_prompt_min, gates.substance_prompt_alt_min)
    return MarketplaceSubmission(
        name=name or get_random_name(),
        description=_extend_to(
            COMPLETE_DESCRIPTION, gates.description_min, _DESCRIPTION_FILLER
        ),
        system_prompt=_extend_to(
            COMPLETE_SYSTEM_PROMPT, prompt_minimum, _SYSTEM_PROMPT_FILLER
        ),
        categories=list(categories or [COMPLETE_CATEGORIES]),
        conversation_starters=list(GOOD_CONVERSATION_STARTERS),
    )


def publish_ready_content(gates: CoreGates) -> dict:
    """``description`` and ``system_prompt`` that clear the stand's core gates, for ``create_assistant``."""
    submission = build_marketplace_submission(gates)
    return {
        "description": submission.description,
        "system_prompt": submission.system_prompt,
    }


def fit_to_core_gates(config: dict, gates: CoreGates) -> dict:
    """``config`` with a description and system prompt that reach the stand's core gates.

    A deliberately wrong value (for a quality check) is repeated, not replaced, until it
    is long enough, so it still fails the quality check while passing the length gates.
    Fields that are absent or already long enough stay as they are.
    """
    fitted = dict(config)
    prompt_minimum = max(gates.system_prompt_min, gates.substance_prompt_alt_min)
    for name, minimum in (
        ("description", gates.description_min),
        ("system_prompt", prompt_minimum),
    ):
        value = fitted.get(name)
        if value:
            fitted[name] = _extend_to(value, minimum, f" {value}")
    return fitted


def build_short_description(gates: CoreGates) -> str:
    """A description one character below ``description_min``.

    The gate threshold is at least 1, so the length is never negative; with a threshold
    of 1 the only description below it is the empty one.
    """
    length = gates.description_min - 1
    return _extend_to(_SHORT_DESCRIPTION_BASE, length, _SHORT_DESCRIPTION_BASE)[
        :length
    ].strip()


def build_reason(length: int) -> str:
    """A decision reason whose trimmed length is exactly ``length``."""
    return "r" * length


def build_padded_reason(trimmed_length: int) -> str:
    """A reason that is long enough only until its surrounding whitespace is trimmed."""
    return f"   {build_reason(trimmed_length)}   "


VALID_REASON = build_reason(REASON_MIN_LENGTH * 2)


REJECTION_REASON = "The description does not explain what this assistant is for."

# Reasons around the 20-2000 bound (the length is measured after trimming).
REFUSED_REASON_PARAMS = [
    pytest.param(build_reason(REASON_MIN_LENGTH - 1), id="19-chars"),
    pytest.param(build_reason(REASON_MAX_LENGTH + 1), id="2001-chars"),
    pytest.param(
        build_padded_reason(REASON_MIN_LENGTH - 1), id="19-chars-plus-padding"
    ),
]
ACCEPTED_REASON_PARAMS = [
    pytest.param(build_reason(REASON_MIN_LENGTH), id="20-chars"),
    pytest.param(build_reason(REASON_MAX_LENGTH), id="2000-chars"),
]

# Every call a caller without the admin or maintainer role must be refused.
MANAGEMENT_ENDPOINT_PARAMS = [
    pytest.param(endpoint, id=endpoint)
    for endpoint in (
        "overview",
        "pending",
        "marketplace-assistants",
        "detail",
        "approve",
        "reject",
        "force-publish",
        "publish with force_publish=true",
    )
]

# Pending queue filters (TC-004): the pair fixture holds a clean assistant
# ("first", submitted first, name sorts first) and one with a CRITICAL finding
# ("second", submitted later, name sorts last).
GATE_RESULT_PARAMS = [
    pytest.param("all_clear", "first", "second", id="all_clear"),
    pytest.param("has_critical", "second", "first", id="has_critical"),
]
CATEGORY_FILTER_PARAMS = [
    pytest.param("first", "second", id="first-category"),
    pytest.param("second", "first", id="second-category"),
]
ORDER_BY_PARAMS = [
    pytest.param("submitted_asc", ("first", "second"), id="submitted_asc"),
    pytest.param("submitted_desc", ("second", "first"), id="submitted_desc"),
    pytest.param("name_asc", ("first", "second"), id="name_asc"),
]

# Assistants the owner has not published, queued and rejected (TC-016).
UNVERIFIED_STATE_PARAMS = [
    pytest.param("draft", DRAFT, id="draft"),
    pytest.param("pending", PENDING_REVIEW, id="pending"),
    pytest.param("rejected", REJECTED, id="rejected"),
]
