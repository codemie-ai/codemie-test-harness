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
UI tests for Marketplace clone counter badge.

Covers:
- TC-02 (P1): Clone count badge is visible on marketplace assistant card.
- TC-03 (P2): Clone count badge updates on marketplace card after clone via UI.

Also covers TC_001: the Favorites card shows the same usage and
clone metrics as the Marketplace card.
"""

from dataclasses import dataclass

import pytest

from codemie_sdk.models.assistant import ReactionType

from codemie_test_harness.tests.ui.pageobject.assistants.assistants_marketplace_page import (
    AssistantsMarketplacePage,
)
from codemie_test_harness.tests.ui.pageobject.assistants.create_edit_assistant_page import (
    CreateEditAssistantPage,
)
from codemie_test_harness.tests.ui.test_data.assistant_test_data import (
    FAVORITES_METRICS_SCENARIOS,
    FavoritesMetricsScenario,
    expected_clone_label,
    expected_usage_label,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name


# ---------------------------------------------------------------------------
# Module-scoped helper fixture: cloned assistant names for API teardown
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# TC-02 (P1) — Clone count badge is visible on marketplace assistant card
# ---------------------------------------------------------------------------


@pytest.mark.sanity
@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.ui
def test_clone_count_badge_visible_on_marketplace_card(page):
    """TC-02: Clone count badge element is visible on the first assistant card.

    Navigates directly to /assistants/marketplace and asserts the badge rendered
    by the frontend MR is present and visible.
    """
    marketplace_page = AssistantsMarketplacePage(page)
    marketplace_page.navigate_to()
    marketplace_page.should_have_clone_count_visible()


# ---------------------------------------------------------------------------
# TC-03 (P2) — Clone count badge updates on marketplace card after clone via UI
# ---------------------------------------------------------------------------


@pytest.mark.not_for_parallel_run
@pytest.mark.sanity
@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.ui
def test_clone_count_badge_updates_after_ui_clone(
    page, assistant, assistant_utils, cleanup_cloned_assistants
):
    """TC-03: Badge on marketplace card increments by 1 after cloning via 3-dot menu.

    Flow:
    1. Publish a fresh assistant to marketplace via API.
    2. Navigate to marketplace and search for the assistant.
    3. Read the initial clone count from the card badge.
    4. Open 3-dot menu → Clone → navigates to new assistant form (pre-filled).
    5. Fill a unique name (form may open with empty name field), record name for cleanup.
    6. Click Save to complete the clone.
    7. Navigate back to marketplace, search for source assistant.
    8. Assert badge shows initial_count + 1.
    """
    # Arrange — create and publish source assistant via API
    source = assistant()
    assistant_utils.publish_assistant_to_marketplace(
        source.id, categories=["quality-assurance"], ignore_recommendations=True
    )

    marketplace_page = AssistantsMarketplacePage(page)
    marketplace_page.navigate_to()
    marketplace_page.search_assistants(source.name)

    # Record initial clone count from badge
    initial_badge_value = marketplace_page.get_clone_count_value(source.name)

    # Act — clone via 3-dot menu (navigates to new assistant form)
    marketplace_page.clone_assistant_via_ui(source.name)

    # The clone form may open with an empty name field; always fill a unique name
    # before saving so the Save button is not blocked by validation.
    create_page = CreateEditAssistantPage(page)
    cloned_name = get_random_name()
    create_page.fill_name(cloned_name)
    cleanup_cloned_assistants.append(cloned_name)

    # Submit the form to complete the clone
    create_page.save_button.click()
    create_page.wait_for_page_load()

    # Navigate back to marketplace and verify badge incremented
    marketplace_page.navigate_to()
    marketplace_page.search_assistants(source.name)
    marketplace_page.should_have_clone_count_value(source.name, initial_badge_value + 1)


# ---------------------------------------------------------------------------
# TC_001 — Favorites card shows the same usage and clone metrics
# as the Marketplace card
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SeededMarketplaceAssistant:
    """A published assistant plus the exact card labels its seeded metrics produce."""

    name: str
    usage_label: str
    clone_label: str


@pytest.fixture
def seeded_marketplace_assistant(
    request, assistant_factory, assistant_utils, cleanup_cloned_assistants
):
    """Publish an assistant, seed its usage and clone counters and like it, all via API.

    The like does not move the usage or clone counters (verified on the live stand).

    ``request.param`` is a ``FavoritesMetricsScenario``. The assistant is deleted by
    ``assistant_factory`` and API clones by ``cleanup_cloned_assistants``.
    """
    scenario: FavoritesMetricsScenario = request.param
    source = assistant_factory.create()
    assistant_utils.publish_assistant_to_marketplace(
        source.id, categories=["quality-assurance"], ignore_recommendations=True
    )
    for _ in range(scenario.chats):
        assistant_utils.ask_assistant(source, "Say hello")
    for _ in range(scenario.clones):
        cleanup_cloned_assistants.append(assistant_utils.clone_assistant_api(source.id))
    assistant_utils.react_to_assistant(source.id, ReactionType.LIKE)
    return SeededMarketplaceAssistant(
        name=source.name,
        usage_label=expected_usage_label(scenario.expected_usage),
        clone_label=expected_clone_label(source.name, scenario.expected_clones),
    )


@pytest.mark.not_for_parallel_run
@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.parametrize(
    "seeded_marketplace_assistant",
    FAVORITES_METRICS_SCENARIOS,
    indirect=True,
)
def test_favorites_card_metrics_match_marketplace_card(
    page, seeded_marketplace_assistant
):
    """TC_001: Favorites card usage and clone labels equal the Marketplace card.

    Flow (non-zero metrics and real zero metrics):
    1. Read the seeded usage and clone labels on the Marketplace card.
    2. Mark the assistant as Favorite.
    3. Open the Favorites category; the card shows the same labels.
    4. Reload the page; the labels are unchanged.
    5. Switch Marketplace -> Favorites again; the labels are unchanged.
    6. The user's like, the dislike control and the favorite status are intact on the Favorites card.
    """
    seeded = seeded_marketplace_assistant
    marketplace_page = AssistantsMarketplacePage(page)

    # Marketplace card carries the seeded metrics
    marketplace_page.navigate_to()
    marketplace_page.search_assistants(seeded.name)
    marketplace_page.should_have_usage_label(seeded.name, seeded.usage_label)
    marketplace_page.should_have_clone_label(seeded.name, seeded.clone_label)

    # Favorite it and compare the Favorites card
    marketplace_page.add_assistant_to_favorites(seeded.name)
    marketplace_page.should_be_favorited(seeded.name)
    marketplace_page.open_favorites_category()
    marketplace_page.should_be_on_favorites_category()
    marketplace_page.should_have_usage_label(seeded.name, seeded.usage_label)
    marketplace_page.should_have_clone_label(seeded.name, seeded.clone_label)

    # Metrics survive a page reload
    marketplace_page.reload_page()
    marketplace_page.should_be_on_favorites_category()
    marketplace_page.should_have_usage_label(seeded.name, seeded.usage_label)
    marketplace_page.should_have_clone_label(seeded.name, seeded.clone_label)

    # Metrics survive switching Marketplace -> Favorites
    marketplace_page.switch_to_marketplace_category()
    marketplace_page.should_be_on_marketplace_page()
    marketplace_page.search_assistants(seeded.name)
    marketplace_page.should_have_usage_label(seeded.name, seeded.usage_label)
    marketplace_page.should_have_clone_label(seeded.name, seeded.clone_label)
    marketplace_page.open_favorites_category()
    marketplace_page.should_have_usage_label(seeded.name, seeded.usage_label)
    marketplace_page.should_have_clone_label(seeded.name, seeded.clone_label)

    # The like the user gave, the dislike control and the favorite status survive on the Favorites card
    marketplace_page.should_show_liked_state(seeded.name, likes=1, dislikes=0)
    marketplace_page.should_be_favorited(seeded.name)
