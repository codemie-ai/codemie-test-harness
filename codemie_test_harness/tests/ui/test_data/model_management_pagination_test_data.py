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

"""UI test data for the paged list of the Model management administration page.

The page pages its list in the browser: it keeps the enabled entries of the admin
status list in API order, filters them, then cuts pages of `per_page` rows. The
helpers below compute the rows each page is expected to show from the API list.
"""

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Callable

from codemie_sdk.models.admin import AdminLLMModel
from codemie_sdk.models.llm import ModelStatus

# Page sizes the page offers; the first one is the default.
PAGE_SIZE_OPTIONS = [10, 20, 50, 100]
DEFAULT_PAGE_SIZE = PAGE_SIZE_OPTIONS[0]
# Page sizes the list is paged through end to end.
WALKED_PAGE_SIZES = [10, 20]

# A search text no model label or base name contains.
NO_MATCH_SEARCH = "zqxvnomatch"
EMPTY_LIST_TEXT = "No data available"

# Status the paged status-change test stages and applies.
PAGED_STATUS_CHANGE = ModelStatus.DEPRECATED

# Router type whose status is computed by the platform; such rows cannot be selected.
_COMPUTED_STATUS_ROUTER = "switchyard"


def page_size_label(per_page: int) -> str:
    """Option of the page-size control, as the page spells it ('20 items')."""
    return f"{per_page} items"


def listed_models(models: list[AdminLLMModel]) -> list[AdminLLMModel]:
    """Entries the page lists, in API order: the disabled-in-config ones are dropped."""
    return [model for model in models if model.enabled]


def base_names(models: list[AdminLLMModel]) -> list[str]:
    return [model.base_name for model in models]


def is_selectable(model: AdminLLMModel) -> bool:
    """Whether the row of the model has a selection checkbox (its status is editable)."""
    return model.router_type != _COMPUTED_STATUS_ROUTER


def page_count(total: int, per_page: int) -> int:
    """Number of pages; an empty list still has one page."""
    return max(1, math.ceil(total / per_page))


def page_slice(items: list, page_number: int, per_page: int) -> list:
    """Items of the 1-based page."""
    start = (page_number - 1) * per_page
    return items[start : start + per_page]


def page_of(names: list[str], base_name: str, per_page: int) -> int:
    """1-based page that holds the model."""
    return names.index(base_name) // per_page + 1


def other_page(page_number: int) -> int:
    """A page next to `page_number` to leave it for and come back from."""
    return page_number - 1 if page_number > 1 else page_number + 1


def matches_search(model: AdminLLMModel, text: str) -> bool:
    """The page's search: the label or the base name contains the text, case-insensitive."""
    query = text.strip().lower()
    return query in model.label.lower() or query in model.base_name.lower()


def _search_tokens(models: list[AdminLLMModel]) -> list[str]:
    tokens = {
        token
        for model in models
        for token in re.split(r"[^a-z0-9]+", model.base_name.lower())
        if len(token) >= 3 and not token.isdigit()
    }
    return sorted(tokens)


def search_text_with_most_matches(models: list[AdminLLMModel]) -> str:
    """A base-name token that the most listed models match (more than one page)."""
    return max(
        _search_tokens(models),
        key=lambda token: sum(1 for model in models if matches_search(model, token)),
    )


def search_text_with_one_page(models: list[AdminLLMModel]) -> str:
    """A base name that between 1 and DEFAULT_PAGE_SIZE listed models match."""
    return next(
        model.base_name
        for model in sorted(models, key=lambda m: m.base_name)
        if 1
        <= sum(1 for other in models if matches_search(other, model.base_name))
        <= DEFAULT_PAGE_SIZE
    )


def provider_model_on_page(
    models: list[AdminLLMModel], page_number: int
) -> AdminLLMModel:
    """A model on the given default-size page whose provider has the most listed models.

    The provider filter is applied by reading the provider of a visible row, so the
    model must be on the page the filter is applied from.
    """
    counts = Counter(model.provider for model in models if model.provider)
    on_page = [
        model
        for model in page_slice(models, page_number, DEFAULT_PAGE_SIZE)
        if model.provider
    ]
    return max(on_page, key=lambda model: counts[model.provider])


@dataclass(frozen=True)
class PagedFilter:
    """A list filter applied from a later page: its target, how to apply it, what it keeps."""

    pick: Callable  # (listed models) -> target
    apply: Callable  # (ModelsManagementPage, target) -> None
    keeps: Callable  # (model, target) -> bool


PAGED_FILTERS = {
    "search": PagedFilter(
        pick=search_text_with_most_matches,
        apply=lambda page, text: page.search_models(text),
        keeps=matches_search,
    ),
    "provider": PagedFilter(
        pick=lambda models: provider_model_on_page(models, 2),
        apply=lambda page, target: page.select_provider_of_model(target.base_name),
        keeps=lambda model, target: model.provider == target.provider,
    ),
}
