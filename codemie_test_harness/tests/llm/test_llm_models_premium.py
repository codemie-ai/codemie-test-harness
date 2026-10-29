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
from hamcrest import assert_that, equal_to, greater_than, has_length


@pytest.fixture(scope="module")
def llm_models(client):
    return client.llms.list()


@pytest.mark.smoke
@pytest.mark.llm
@pytest.mark.api
@pytest.mark.production_check
def test_llm_models_have_is_premium_field(llm_models):
    """Every model must expose is_premium as a boolean (not None)."""
    assert_that(
        llm_models,
        has_length(greater_than(0)),
        "Expected at least one LLM model in the list response",
    )

    missing_field = [m for m in llm_models if m.is_premium is None]
    missing_labels = [m.label or m.deployment_name or str(m) for m in missing_field]
    assert_that(
        len(missing_field),
        equal_to(0),
        f"These models are missing the is_premium field: {missing_labels}",
    )

    premium_models = [m for m in llm_models if m.is_premium is True]
    non_premium_models = [m for m in llm_models if m.is_premium is False]

    assert_that(
        len(premium_models),
        greater_than(0),
        "Expected at least one model with is_premium=True in the environment",
    )

    assert_that(
        len(non_premium_models),
        greater_than(0),
        "Expected at least one model with is_premium=False in the environment",
    )


@pytest.mark.llm
@pytest.mark.api
@pytest.mark.production_check
def test_known_premium_model_has_is_premium_true(llm_models):
    """The first model with is_premium=True must not have the flag inverted."""
    premium_models = [m for m in llm_models if m.is_premium is True]

    assert_that(
        len(premium_models),
        greater_than(0),
        "Expected at least one model with is_premium=True in the environment",
    )

    first_premium = premium_models[0]
    label = first_premium.label or first_premium.deployment_name
    assert_that(
        first_premium.is_premium,
        equal_to(True),
        f"Model '{label}' expected is_premium=True",
    )
