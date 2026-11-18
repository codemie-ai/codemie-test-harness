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

"""Catalog helpers and expected values for the assistant effort parameter tests."""

# Effort levels in ascending order; the catalog lists a model's levels in this order.
EFFORT_ORDER = ["low", "medium", "high", "xhigh", "max"]

# Level to move to when an update changes the effort, for each level a test creates with.
EFFORT_UPDATE_TARGETS = {"low": "medium", "medium": "high", "high": "low"}

CLAUDE_MARKER = "claude"


def effort_levels(model):
    """Effort levels a catalog model declares as plain strings, or None for no support."""
    features = model.features
    if features is None or features.effort is None:
        return None
    return [getattr(level, "value", level) for level in features.effort]


def effort_catalog_violations(models) -> list[str]:
    """Describe every model whose declared effort levels break the catalog contract.

    A declared list must be non-empty, hold only known levels and be in ascending order
    without repeats.
    """
    violations = []
    for model in models:
        levels = effort_levels(model)
        if levels is None:
            continue
        unknown = [level for level in levels if level not in EFFORT_ORDER]
        ranks = [EFFORT_ORDER.index(level) for level in levels if level in EFFORT_ORDER]
        if not levels or unknown or ranks != sorted(set(ranks)):
            violations.append(f"{model.base_name}: {levels}")
    return violations


def models_with_effort(models) -> list:
    return [model for model in models if effort_levels(model)]


def models_without_effort(models) -> list:
    return [model for model in models if effort_levels(model) is None]


def models_missing_temperature_flag(models) -> list[str]:
    """Names of models whose features.temperature is not a boolean."""
    return [
        model.base_name
        for model in models
        if model.features is None or not isinstance(model.features.temperature, bool)
    ]


def models_rejecting_temperature(models) -> list:
    return [
        model
        for model in models
        if model.features is not None and model.features.temperature is False
    ]


def claude_effort_models(models) -> list:
    """Enabled Claude models that declare effort levels, non-premium ones first."""
    candidates = [
        model
        for model in models_with_effort(models)
        if CLAUDE_MARKER in model.base_name.lower()
        and model.enabled
        and not model.is_router
    ]
    return sorted(candidates, key=lambda model: bool(model.is_premium))


def level_above_ceiling(levels: list[str]):
    """An effort level the model does not declare, above its lowest level.

    The level right above the model's highest declared one when one exists. A model
    that declares max has no level above it, so the first undeclared level inside its
    range (a gap, for example xhigh) is used; the backend clamps it down to the nearest
    declared level below. None when every level is declared.
    """
    ceiling_rank = max(EFFORT_ORDER.index(level) for level in levels)
    if ceiling_rank < len(EFFORT_ORDER) - 1:
        return EFFORT_ORDER[ceiling_rank + 1]
    undeclared = [level for level in EFFORT_ORDER if level not in levels]
    return undeclared[0] if undeclared else None


def chat_effort_for(levels: list[str], role: str):
    """The effort a chat test sends for a role: lowest, highest or above_ceiling."""
    if role == "lowest":
        return levels[0]
    if role == "highest":
        return levels[-1]
    return level_above_ceiling(levels)


def model_by_label(models, label: str):
    """The catalog model with the given display label, or None."""
    matches = [model for model in models if model.label == label]
    return matches[0] if matches else None


# One-word prompt whose reply any working model answers the same way.
GREETING_PROMPT = "Just say one word: 'Hello'"
EXPECTED_GREETING = "Hello"
