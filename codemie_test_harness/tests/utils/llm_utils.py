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

from collections import Counter

from codemie_sdk.models.llm import LLMModel, ModelStatus

from codemie_test_harness.tests.utils.base_utils import BaseUtils


class LLMUtils(BaseUtils):
    def list_llm_models(self):
        return self.client.llms.list()

    def list_embedding_llm_models(self):
        return self.client.llms.list_embeddings()


def candidate_model_labels(client) -> list[str]:
    """Model labels from the live platform catalog instead of hardcoded names that
    may be renamed or retired: enabled, not a routing model, and unique among all
    labels (a repeated label would make the table row ambiguous to target).
    """
    models = client.llms.list()
    label_counts = Counter(model.label for model in models if model.label)
    return [
        model.label
        for model in models
        if model.label
        and label_counts[model.label] == 1
        and model.enabled
        and not model.is_router
    ]


def global_default_model_label(client) -> str:
    """The label of the platform's global default model (`LLMModel.default is
    True`), read from the live catalog instead of a hardcoded name that may be
    renamed or retired.

    Raises:
        AssertionError: if no model or more than one model is flagged default
            (the platform is expected to have exactly one global default).
    """
    models = client.llms.list()
    defaults = [model for model in models if model.default]
    assert len(defaults) == 1, (
        f"Expected exactly one model flagged as global default, found "
        f"{len(defaults)}: {[m.label for m in defaults]}"
    )
    return defaults[0].label


def selectable_chat_models(client, exclude: tuple[str, ...] = ()) -> list[LLMModel]:
    """Enabled web chat models a project admin can tick and pick as the project default.

    Read from the live catalog: status Enabled (a Deprecated model is not offered
    as a default), not a router, not CLI only, and a label that is part of no other
    label (so its row on the Models tab can be found by label alone). Models whose
    base name is in `exclude` are left out.
    """
    all_labels = [
        model.label.lower()
        for model in client.llms.list(include_all=True)
        if model.label
    ]
    return [
        model
        for model in client.llms.list()
        if model.label
        and model.base_name not in exclude
        and model.enabled
        and model.status in (None, ModelStatus.ENABLED)
        and not model.is_router
        and not model.forbidden_for_web
        and sum(1 for label in all_labels if model.label.lower() in label) == 1
    ]
