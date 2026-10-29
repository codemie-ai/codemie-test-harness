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

"""
API tests for Marketplace clone counter.

Covers:
- TC-01 (P1): Clone action increments clone_count; default starts at zero.
- TC-04 (P2): Multiple sequential clones each increment clone_count by 1 (parametrised N∈{2,5}).
- TC-05 (P2): Clone action updates the assistant usage metric (clone_count).
- TC-06 (P3): Clone action does not alter existing like or dislike counts.
"""

import pytest
from hamcrest import assert_that, equal_to, greater_than

from codemie_sdk.models.assistant import ReactionType


# ---------------------------------------------------------------------------
# Module-scoped helper fixture: cloned assistants accumulated across a test
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# TC-01 (P1) — Clone action increments clone_count; default starts at zero
# ---------------------------------------------------------------------------


@pytest.mark.sanity
@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
def test_clone_count_starts_at_zero_and_increments_to_one(
    assistant, assistant_utils, cleanup_cloned_assistants
):
    """TC-01: Clone count default is 0; first clone increments it to 1."""
    # Arrange
    source = assistant()
    assistant_utils.publish_assistant_to_marketplace(
        source.id, categories=["quality-assurance"], ignore_recommendations=True
    )

    # Read initial clone count from marketplace scope
    marketplace_assistant = assistant_utils.get_assistant_by_name(
        source.name, scope="marketplace"
    )
    initial_clone_count = marketplace_assistant.clone_count or 0

    assert_that(
        initial_clone_count,
        equal_to(0),
        "Clone count should be 0 for a freshly published assistant",
    )

    # Act — clone via API using source_assistant_id
    cloned = assistant_utils.clone_assistant_api(source.id)
    cleanup_cloned_assistants.append(cloned)

    # Re-fetch source assistant from marketplace
    updated_assistant = assistant_utils.get_assistant_by_name(
        source.name, scope="marketplace"
    )

    # Assert
    assert_that(
        updated_assistant.clone_count,
        equal_to(initial_clone_count + 1),
        "Clone count should increment by 1 after first clone action",
    )


# ---------------------------------------------------------------------------
# TC-04 (P2) — Multiple sequential clones each increment clone_count by 1
# ---------------------------------------------------------------------------


@pytest.mark.not_for_parallel_run
@pytest.mark.sanity
@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
@pytest.mark.parametrize("n", [2, 5])
def test_sequential_clones_each_increment_clone_count(
    n, assistant, assistant_utils, cleanup_cloned_assistants
):
    """TC-04: After N sequential clones, clone_count equals N."""
    # Arrange
    source = assistant()
    assistant_utils.publish_assistant_to_marketplace(
        source.id, categories=["quality-assurance"], ignore_recommendations=True
    )

    # Act — clone N times sequentially
    for _ in range(n):
        cloned = assistant_utils.clone_assistant_api(source.id)
        cleanup_cloned_assistants.append(cloned)

    # Re-fetch source assistant from marketplace
    updated_assistant = assistant_utils.get_assistant_by_name(
        source.name, scope="marketplace"
    )

    # Assert
    assert_that(
        updated_assistant.clone_count,
        equal_to(n),
        f"Clone count should equal {n} after {n} sequential clone actions",
    )


# ---------------------------------------------------------------------------
# TC-05 (P2) — Clone action updates the assistant usage metric
# ---------------------------------------------------------------------------


@pytest.mark.sanity
@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
def test_clone_updates_assistant_usage_metric(
    assistant, assistant_utils, cleanup_cloned_assistants
):
    """TC-05: Clone action updates the clone_count usage metric (increments it)."""
    # Arrange
    source = assistant()
    assistant_utils.publish_assistant_to_marketplace(
        source.id, categories=["quality-assurance"], ignore_recommendations=True
    )

    marketplace_before = assistant_utils.get_assistant_by_name(
        source.name, scope="marketplace"
    )
    initial_metric = marketplace_before.clone_count or 0

    # Act
    cloned = assistant_utils.clone_assistant_api(source.id)
    cleanup_cloned_assistants.append(cloned)

    # Re-fetch
    marketplace_after = assistant_utils.get_assistant_by_name(
        source.name, scope="marketplace"
    )

    # Assert — usage metric (clone_count) has increased
    assert_that(
        marketplace_after.clone_count,
        greater_than(initial_metric),
        "clone_count (usage metric) should increase after a clone action",
    )


# ---------------------------------------------------------------------------
# TC-06 (P3) — Clone action does not alter existing like or dislike counts
# ---------------------------------------------------------------------------


@pytest.mark.sanity
@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
def test_clone_does_not_alter_reaction_counts(
    assistant, assistant_utils, cleanup_cloned_assistants
):
    """TC-06: After cloning, unique_likes_count and unique_dislikes_count are unchanged."""
    # Arrange — publish and add a LIKE reaction to establish a baseline
    source = assistant()
    assistant_utils.publish_assistant_to_marketplace(
        source.id, categories=["quality-assurance"], ignore_recommendations=True
    )

    assistant_utils.react_to_assistant(source.id, ReactionType.LIKE)

    after_reaction = assistant_utils.get_assistant_by_name(
        source.name, scope="marketplace"
    )
    baseline_likes = after_reaction.unique_likes_count or 0
    baseline_dislikes = after_reaction.unique_dislikes_count or 0

    # Act — clone
    cloned = assistant_utils.clone_assistant_api(source.id)
    cleanup_cloned_assistants.append(cloned)

    # Re-fetch
    after_clone = assistant_utils.get_assistant_by_name(
        source.name, scope="marketplace"
    )

    # Assert — reaction counts must not change
    assert_that(
        after_clone.unique_likes_count or 0,
        equal_to(baseline_likes),
        "unique_likes_count should not change after cloning",
    )
    assert_that(
        after_clone.unique_dislikes_count or 0,
        equal_to(baseline_dislikes),
        "unique_dislikes_count should not change after cloning",
    )
