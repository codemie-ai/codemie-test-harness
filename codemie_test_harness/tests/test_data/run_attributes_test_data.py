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

"""Test data for the run attributes tests (chat, workflow execution and analytics)."""

import random
import string
from dataclasses import dataclass

import pytest

from codemie_test_harness.tests.utils.base_utils import get_random_name

RUN_PROMPT = "Reply with the single word OK."
WORKFLOW_TASK = "Run"

# Usage records reach the analytics index with a delay.
ANALYTICS_ROW_TIMEOUT = 180
ANALYTICS_ROW_INTERVAL = 5
ANALYTICS_PERIOD = "last_hour"
ANALYTICS_PAGE_SIZE = 100

MAX_KEYS = 4
MAX_VALUE_LENGTH = 128

CONVERSATION_NOT_FOUND = (
    "The conversation with ID [{conversation_id}] could not be found in the system."
)
ATTRIBUTES_IMMUTABLE_MESSAGE = "Run attributes cannot be changed"
INVALID_FILTER_MESSAGE = "Invalid attributes filter"
MISSING_KEY_MESSAGE = "Missing attribute key"
INVALID_KEY_MESSAGE = "Invalid attribute key"

MALFORMED_FILTER = "{not a json object"
MALFORMED_ATTRIBUTE_KEY = "Not A Valid Key!"


def get_attribute_key() -> str:
    """A valid, unique attribute key: analytics grouping and filtering are scoped to it."""
    suffix = "".join(random.choice(string.ascii_lowercase) for _ in range(10))
    return f"autotest.{suffix}"


def get_attribute_value() -> str:
    return get_random_name()


def get_attributes(count: int = 1) -> dict[str, str]:
    """``count`` valid attributes with keys and values unique to the call."""
    return {get_attribute_key(): get_attribute_value() for _ in range(count)}


@dataclass(frozen=True)
class InvalidAttributes:
    """Attributes the server must refuse, with the part of the 422 message that names the reason."""

    attributes: dict[str, str]
    message: str


TOO_MANY_KEYS = InvalidAttributes(
    attributes=get_attributes(MAX_KEYS + 1),
    message=f"Too many attributes: at most {MAX_KEYS} are allowed",
)

CHAT_INVALID_ATTRIBUTES = [
    pytest.param(TOO_MANY_KEYS, id="too-many-keys"),
    pytest.param(
        InvalidAttributes(
            attributes={"codemie.team": get_attribute_value()},
            message="uses a reserved prefix: codemie., otel.",
        ),
        id="reserved-codemie-prefix",
    ),
    pytest.param(
        InvalidAttributes(
            attributes={"UpperCase": get_attribute_value()},
            message="Invalid attribute key 'UpperCase'",
        ),
        id="uppercase-key",
    ),
    pytest.param(
        InvalidAttributes(
            attributes={get_attribute_key(): "a" * (MAX_VALUE_LENGTH + 1)},
            message=f"value must be 1-{MAX_VALUE_LENGTH} UTF-16 code units long",
        ),
        id="value-over-128-code-units",
    ),
    pytest.param(
        InvalidAttributes(
            attributes={get_attribute_key(): "lone-surrogate-\ud800"},
            message="value must not contain unpaired surrogates",
        ),
        id="lone-surrogate-value",
    ),
]

WORKFLOW_INVALID_ATTRIBUTES = [
    pytest.param(TOO_MANY_KEYS, id="too-many-keys"),
    pytest.param(
        InvalidAttributes(
            attributes={"otel.team": get_attribute_value()},
            message="uses a reserved prefix: codemie., otel.",
        ),
        id="reserved-otel-prefix",
    ),
]

# The run kinds a run surface is built for, by the analytics endpoint that lists their rows.
RUN_SURFACES = [
    pytest.param("chat", id="assistants-requests"),
    pytest.param("workflow", id="workflows-executions"),
]
RUN_SURFACES_BY_KIND = [
    pytest.param("chat", id="chat"),
    pytest.param("workflow", id="workflow"),
]

ATTRIBUTES_USAGE_KEY_ERRORS = [
    pytest.param(None, MISSING_KEY_MESSAGE, id="missing-key"),
    pytest.param(MALFORMED_ATTRIBUTE_KEY, INVALID_KEY_MESSAGE, id="malformed-key"),
]
