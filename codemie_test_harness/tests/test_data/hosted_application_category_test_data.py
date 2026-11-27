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

"""Test data for the categories of hosted applications: the platform's refusals, the category
lists that provoke them and the catalog scopes."""

from dataclasses import dataclass
from typing import Any, Callable, Optional

from codemie_test_harness.tests.utils.base_utils import get_random_name

REFUSED_STATUS = 422
CONFLICT_STATUS = 409
INVALID_REQUEST_CODE = "INVALID_REQUEST"
INVALID_CATEGORIES_CODE = "INVALID_CATEGORIES"
INVALID_FILTER_CODE = "INVALID_FILTER"
INVALID_CURSOR_CODE = "INVALID_CURSOR"
IDEMPOTENCY_CONFLICT_CODE = "IDEMPOTENCY_CONFLICT"

CATEGORY_REQUIRED_TEXT = "At least one category is required"
TOO_MANY_TEXT = "Maximum 3 categories allowed"
DUPLICATE_TEXT = "category IDs must be unique"
UNKNOWN_CATEGORY_TEXT = "Invalid category IDs"
PUBLISHED_NEEDS_ONE_TEXT = "A published application needs at least one category"
INVALID_FILTER_TEXT = "Invalid application filters"
CATEGORY_IN_USE_MESSAGE = "Cannot delete category"
ASSIGNED_APPLICATIONS_TEXT = "1 assigned hosted applications"

# The catalog takes at most 50 category ids of at most 256 characters each.
OVERSIZED_FILTER_COUNT = 51
OVERSIZED_FILTER_LENGTH = 257


@dataclass(frozen=True)
class CategoryRefusal:
    """A category list the platform refuses, and how it says so.

    ``ids`` builds the list to send from the platform's real categories; ``None`` means the
    request carries no ``categories`` at all.
    """

    id: str
    ids: Callable[[list[Any]], Optional[list[str]]]
    code: str
    text: str


def _unknown_id() -> str:
    return f"no-such-category-{get_random_name()}"


NO_CATEGORIES = CategoryRefusal(
    "none_sent", lambda _: None, INVALID_REQUEST_CODE, CATEGORY_REQUIRED_TEXT
)
EMPTY_CATEGORIES = CategoryRefusal(
    "empty_list", lambda _: [], INVALID_REQUEST_CODE, CATEGORY_REQUIRED_TEXT
)
TOO_MANY_CATEGORIES = CategoryRefusal(
    "four_ids",
    lambda real: [category.id for category in real] + [_unknown_id()],
    INVALID_REQUEST_CODE,
    TOO_MANY_TEXT,
)
REPEATED_CATEGORY = CategoryRefusal(
    "repeated_id",
    lambda real: [real[0].id, real[0].id],
    INVALID_REQUEST_CODE,
    DUPLICATE_TEXT,
)
UNKNOWN_CATEGORY = CategoryRefusal(
    "unknown_id",
    lambda real: [real[0].id, _unknown_id()],
    INVALID_CATEGORIES_CODE,
    UNKNOWN_CATEGORY_TEXT,
)

PUBLISH_REFUSALS = [
    NO_CATEGORIES,
    EMPTY_CATEGORIES,
    TOO_MANY_CATEGORIES,
    REPEATED_CATEGORY,
    UNKNOWN_CATEGORY,
]
# A create or an edit may carry no category, so only the lists that are wrong in themselves.
SAVE_REFUSALS = [TOO_MANY_CATEGORIES, REPEATED_CATEGORY, UNKNOWN_CATEGORY]


@dataclass(frozen=True)
class FilterRefusal:
    """A category filter the catalog answers with an invalid-filter refusal."""

    id: str
    ids: Callable[[], list[str]]


INVALID_FILTERS = [
    FilterRefusal("unknown_id", lambda: [_unknown_id()]),
    FilterRefusal(
        "fifty_one_ids",
        lambda: [f"{_unknown_id()}-{index}" for index in range(OVERSIZED_FILTER_COUNT)],
    ),
    FilterRefusal("overlong_id", lambda: ["x" * OVERSIZED_FILTER_LENGTH]),
]

# The catalog scopes the category filter applies to.
CATALOG_SCOPES = ["mine", "project", "marketplace", "shared"]
# What each app of a catalog scope is called after, and the categories it carries, as indexes
# into the three categories the test picked.
CATEGORY_APP_LABELS = {"alpha": [0], "beta": [1], "both": [0, 1], "plain": []}
