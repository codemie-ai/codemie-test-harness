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

"""UI test data for the Model management administration page and the status
indicators of the model pickers and the models catalog."""

from dataclasses import dataclass
from typing import Callable

from codemie_sdk.models.admin import AdminLLMModel
from codemie_sdk.models.llm import ModelStatus

MODELS_MANAGEMENT_PATH = "/settings/administration/models"
MODELS_MANAGEMENT_HEADING = "Global model management"
SETTINGS_UPDATED_TOAST = "Model settings updated"

# Column headers of the model table; the cost header continues with "(in / out)".
MODEL_TABLE_COLUMNS = [
    "Model",
    "Provider",
    "Capabilities",
    "Cost / 1M tokens",
    "Status",
]

# Labels exactly as the page spells them (not the acceptance-criteria wording).
STATUS_LABELS = {
    ModelStatus.ENABLED: "Enabled",
    ModelStatus.DISABLED: "Disabled",
    ModelStatus.DEPRECATED: "Deprecated",
}
BULK_ACTION_LABELS = {
    ModelStatus.ENABLED: "Enable",
    ModelStatus.DISABLED: "Disable",
    ModelStatus.DEPRECATED: "Deprecate",
}

# Value of the Status filter with nothing checked.
ALL_STATUSES_LABEL = "All statuses"

# Statuses the UI tests move a model to.
CHANGED_STATUSES = [ModelStatus.DEPRECATED, ModelStatus.DISABLED]

# Provider values of the API → the labels of the Provider filter.
PROVIDER_LABELS = {
    "azure_openai": "Azure OpenAI",
    "aws_bedrock": "AWS Bedrock",
    "google_vertexai": "Google Vertex AI",
    "anthropic": "Anthropic",
    "vertex_ai-anthropic_models": "Vertex AI Anthropic",
}


def expected_summary(shown: list[AdminLLMModel], total: int) -> str:
    """Start of the summary line for the models shown out of `total`, as the page words it.

    Only the shown count, the total and the premium count are given: the premium
    count follows the filtered rows, while the disabled and deprecated counts are
    not known to.
    """
    premium = sum(1 for model in shown if model.is_premium)
    return f"{len(shown)} of {total} models · {premium} premium"


@dataclass(frozen=True)
class ListFilter:
    """A filter of the model list: how to apply it and which models it keeps."""

    apply: Callable  # (ModelsManagementPage, target model) -> None
    keeps: Callable  # (model, target model) -> bool


LIST_FILTERS = {
    "search": ListFilter(
        apply=lambda page, target: page.search_models(target.label),
        keeps=lambda model, target: (
            target.label.lower() in model.label.lower()
            or target.label.lower() in model.base_name.lower()
        ),
    ),
    "provider": ListFilter(
        apply=lambda page, target: page.select_provider(
            PROVIDER_LABELS.get(target.provider, target.provider)
        ),
        keeps=lambda model, target: model.provider == target.provider,
    ),
}


def pick_filter_target(models: list[AdminLLMModel]) -> AdminLLMModel:
    """A chat model with a provider: the filters are applied with its label and provider."""
    return next(
        model
        for model in sorted(models, key=lambda m: m.base_name)
        if model.model_type == "chat" and model.router_type is None and model.provider
    )
