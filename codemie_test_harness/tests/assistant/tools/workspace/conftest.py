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

import pytest
from codemie_sdk.models.llm import LLMProvider
from requests import HTTPError


@pytest.fixture(scope="session")
def non_anthropic_multimodal_model(client):
    """Base name of an enabled, vision-capable, non-Anthropic model.

    Resolved dynamically from the backend (rather than a hardcoded ModelTypes
    constant) so the test doesn't break when a specific model goes stale,
    disabled, or unavailable in a given environment.
    """
    try:
        models = client.llms.list()
    except HTTPError as exc:
        pytest.skip(f"Could not fetch LLM models: {exc}")
    for model in models:
        name = (model.label or model.deployment_name).lower()
        if (
            model.enabled
            and model.multimodal
            and model.provider != LLMProvider.GOOGLE_VERTEXAI_ANTHROPIC
            and "claude" not in name
        ):
            return model.base_name
    pytest.skip("No enabled non-Anthropic multimodal model found in this environment")
