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

from dataclasses import dataclass
from typing import List

import pytest

from codemie_test_harness.tests.utils.env_resolver import get_environment
from codemie_test_harness.tests.enums.environment import Environment


@dataclass
class EmbeddingData:
    """Data class to store Embedding models."""

    model_type: str
    environments: List[Environment]


# Hardcoded models for API tests
MODELS = [
    EmbeddingData("amazon.titan-embed-text-v2:0", Environment.get_aws_environments()),
    EmbeddingData("text-embedding-005", Environment.get_gcp_environments()),
    EmbeddingData(
        "codemie-text-embedding-ada-002", Environment.get_azure_environments()
    ),
]


def generate_test_data():
    """Generate pytest parameters for Embedding models"""
    env = get_environment()
    test_data = []

    for model in MODELS:
        test_data.append(
            pytest.param(
                model.model_type,
                marks=pytest.mark.skipif(
                    env not in model.environments,
                    reason=f"Skip on non {'/'.join(str(env) for env in model.environments[:-1])} envs",
                ),
            )
        )

    return test_data


def get_first_embedding_model_from_api():
    """Get only the first embedding model from API for smoke tests."""
    from codemie_test_harness.tests.utils.client_factory import get_client

    client = get_client()
    embedding_models = client.llms.list_embeddings()

    if embedding_models:
        first_model = embedding_models[0]
        return [pytest.param(first_model.base_name)]
    return []


index_test_data = generate_test_data()
