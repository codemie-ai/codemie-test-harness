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

"""Test data for workflow Categories API tests."""

from dataclasses import dataclass
from typing import Callable, List, Optional

import pytest

from codemie_test_harness.tests.utils.base_utils import get_random_name

# Server limit on categories per workflow (WorkflowConfig.categories max_length)
MAX_WORKFLOW_CATEGORIES = 3

# A category ID that is guaranteed not to exist on any environment
UNKNOWN_CATEGORY_ID = "no_such_category_xyz"


@dataclass
class WorkflowCategoriesData:
    """Name and description for a workflow created by a categories test."""

    name: str
    description: str


class WorkflowCategoriesDataFactory:
    """Factory producing unique workflow data for categories tests."""

    @staticmethod
    def create() -> WorkflowCategoriesData:
        name = get_random_name()
        return WorkflowCategoriesData(
            name=name,
            description=f"Workflow categories test {name}",
        )


# TC-001: how many categories are sent on create
CREATE_CATEGORIES_PARAMS = [
    pytest.param(2, id="with_two_categories"),
    pytest.param(0, id="without_categories"),
]


@dataclass
class CategoriesUpdateCase:
    """TC-003: categories sent on update and the categories expected afterwards.

    Values are indexes into the environment's category list. ``None`` for
    ``update_indexes`` means the field is omitted from the update request.
    """

    update_indexes: Optional[List[int]]
    expected_indexes: List[int]


# The workflow is always created with category index 0
UPDATE_CATEGORIES_PARAMS = [
    pytest.param(CategoriesUpdateCase([1], [1]), id="replace"),
    pytest.param(CategoriesUpdateCase(None, [0]), id="omit_preserves"),
    pytest.param(CategoriesUpdateCase([], []), id="clear_with_empty_list"),
]


@dataclass
class InvalidCategoriesCase:
    """TC-004: invalid category payload and the rejection observed on the live env."""

    build_ids: Callable[[List[str]], List[str]]
    expected_status: int
    expected_text: str


def _over_limit_ids(existing_ids: List[str]) -> List[str]:
    # Length validation runs before ID validation, so padding with an unknown ID is safe.
    padded = existing_ids + [UNKNOWN_CATEGORY_ID]
    return padded[: MAX_WORKFLOW_CATEGORIES + 1]


def _unknown_ids(_existing_ids: List[str]) -> List[str]:
    return [UNKNOWN_CATEGORY_ID]


INVALID_CATEGORIES_PARAMS = [
    pytest.param(
        InvalidCategoriesCase(_over_limit_ids, 422, "categories"),
        id="four_categories",
    ),
    pytest.param(
        InvalidCategoriesCase(_unknown_ids, 400, UNKNOWN_CATEGORY_ID),
        id="unknown_category_id",
    ),
]
