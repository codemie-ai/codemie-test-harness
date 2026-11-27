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

"""Test data for the model status API tests."""

from codemie_sdk.models.admin import LLMModelStatusBulkItem
from codemie_sdk.models.llm import ModelStatus

from codemie_test_harness.tests.utils.base_utils import get_random_name

# Statuses that make a model unusable as the global default.
NON_SELECTABLE_STATUSES = [ModelStatus.DEPRECATED, ModelStatus.DISABLED]

# What the platform answers when a model cannot be chosen for new work or as the default.
NOT_SELECTABLE_MESSAGE = "Model not selectable"
DEPRECATED_REASON = "model is deprecated"
UNAVAILABLE_REASON = "model is not available"

# The assistant detail explains the replacement of a Disabled model with this text.
DISABLED_FALLBACK_REASON = (
    "The configured model is disabled. An available fallback is used."
)

# A bulk status request may carry at most this many items.
BULK_UPDATE_LIMIT = 100


def not_selectable_details(base_name: str, reason: str) -> str:
    """Error details for a model that cannot be chosen."""
    return f"Model '{base_name}' is not selectable: {reason}"


def unknown_model_name() -> str:
    """A base name that is in no catalog."""
    return f"{get_random_name()}-unknown-model"


# ── Non-admin access: route → call, parametrized by name ─────────────────────

ADMIN_STATUS_ROUTES = {
    "get_status_list": lambda admin, base_name: admin.list_llm_model_statuses(),
    "put_model_status": lambda admin, base_name: admin.set_llm_model_status(
        base_name, ModelStatus.DISABLED
    ),
    "post_bulk_status": lambda admin, base_name: admin.bulk_set_llm_model_statuses(
        [LLMModelStatusBulkItem(base_name=base_name, status=ModelStatus.DISABLED)]
    ),
}


# ── Invalid bulk requests: name → (builder of (base_name, status) items, text the refusal names) ──


def _duplicate_base_name_items() -> list[tuple[str, ModelStatus]]:
    base_name = unknown_model_name()
    return [(base_name, ModelStatus.DISABLED), (base_name, ModelStatus.DEPRECATED)]


def _over_limit_items() -> list[tuple[str, ModelStatus]]:
    prefix = unknown_model_name()
    return [
        (f"{prefix}-{index}", ModelStatus.DISABLED)
        for index in range(BULK_UPDATE_LIMIT + 1)
    ]


INVALID_BULK_REQUESTS = {
    "duplicate_base_name": (
        _duplicate_base_name_items,
        "duplicate base_name",
    ),
    "over_limit": (
        _over_limit_items,
        f"at most {BULK_UPDATE_LIMIT} items",
    ),
}

# ── Status changes: (status before, status set) ───────────────────────────────

STATUS_TRANSITIONS = [
    (ModelStatus.DISABLED, ModelStatus.ENABLED),
    (ModelStatus.ENABLED, ModelStatus.DISABLED),
    (ModelStatus.ENABLED, ModelStatus.DEPRECATED),
]
STATUS_TRANSITION_IDS = [f"{a.value}_to_{b.value}" for a, b in STATUS_TRANSITIONS]

# Status → the status the regular user's catalog shows for the model (None: not listed).
CATALOG_STATUS_BY_STATUS = {
    ModelStatus.ENABLED: ModelStatus.ENABLED,
    ModelStatus.DEPRECATED: ModelStatus.DEPRECATED,
    ModelStatus.DISABLED: None,
}

# Status → the reason the global default refusal names.
DEFAULT_REFUSAL_REASON = {
    ModelStatus.DEPRECATED: DEPRECATED_REASON,
    ModelStatus.DISABLED: UNAVAILABLE_REASON,
}
